package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"gopkg.in/yaml.v3"
)

const (
	serverName         = "boltz-compute-mcp"
	serverVersion      = "0.1.0"
	defaultOutputDir   = "./boltz-experiments"
	requestFileName    = "request.json"
	metadataFileName   = ".boltz-mcp.json"
	pidFileName        = "download-results.pid"
	logFileName        = "download-results.log"
	boltzRunFileName   = ".boltz-run.json"
	defaultListLimit   = 20
	defaultTotalLimit  = 20
	defaultStatusLines = 30
)

type resourceDescriptor struct {
	Resource string
	Type     string
	Prefix   string
}

var resourceDescriptors = []resourceDescriptor{
	{Resource: "predictions:structure-and-binding", Type: "prediction", Prefix: "pred"},
	{Resource: "protein:design", Type: "protein_design_ppi", Prefix: "prot_des"},
	{Resource: "protein:library-screen", Type: "protein_library_screen_ppi", Prefix: "prot_scr"},
	{Resource: "small-molecule:design", Type: "boltz_sm_design", Prefix: "sm_des"},
	{Resource: "small-molecule:library-screen", Type: "boltz_sm_screen", Prefix: "sm_scr"},
}

var resources = func() []string {
	out := make([]string, 0, len(resourceDescriptors))
	for _, descriptor := range resourceDescriptors {
		out = append(out, descriptor.Resource)
	}
	return out
}()

var resourceSet = func() map[string]struct{} {
	out := make(map[string]struct{}, len(resources))
	for _, resource := range resources {
		out[resource] = struct{}{}
	}
	return out
}()

var resourceDescriptorByResource = func() map[string]resourceDescriptor {
	out := make(map[string]resourceDescriptor, len(resourceDescriptors))
	for _, descriptor := range resourceDescriptors {
		out[descriptor.Resource] = descriptor
	}
	return out
}()

var resourceDescriptorsByPrefix = func() []resourceDescriptor {
	out := append([]resourceDescriptor(nil), resourceDescriptors...)
	sort.SliceStable(out, func(i, j int) bool {
		return len(out[i].Prefix) > len(out[j].Prefix)
	})
	return out
}()

type estimateRunInput struct {
	Resource    string         `json:"resource" jsonschema:"Boltz CLI resource name, for example predictions:structure-and-binding or small-molecule:design"`
	Payload     map[string]any `json:"payload" jsonschema:"API request body object for the selected resource"`
	Model       string         `json:"model,omitempty" jsonschema:"Optional model flag to pass through, for example boltz-2.1 for structure-and-binding"`
	WorkspaceID string         `json:"workspace_id,omitempty" jsonschema:"Optional Boltz workspace ID"`
}

type submitRunInput struct {
	Resource            string         `json:"resource" jsonschema:"Boltz CLI resource name, for example predictions:structure-and-binding or protein:design"`
	Payload             map[string]any `json:"payload" jsonschema:"API request body object for the selected resource"`
	RunName             string         `json:"run_name" jsonschema:"Short descriptive slug used as both idempotency key and download name"`
	Model               string         `json:"model,omitempty" jsonschema:"Optional model flag to pass through, for example boltz-2.1 for structure-and-binding"`
	WorkspaceID         string         `json:"workspace_id,omitempty" jsonschema:"Optional Boltz workspace ID"`
	OutputDir           string         `json:"output_dir,omitempty" jsonschema:"Optional output directory. Relative paths resolve from the original workspace if PWD is available, otherwise from the server process directory"`
	PollIntervalSeconds int            `json:"poll_interval_seconds,omitempty" jsonschema:"Optional download-results polling interval in seconds"`
}

type listJobsInput struct {
	PerResourceLimit int    `json:"per_resource_limit,omitempty" jsonschema:"Max rows to request and keep per resource; defaults to 20"`
	TotalLimit       int    `json:"total_limit,omitempty" jsonschema:"Max merged rows to return after sorting; defaults to 20"`
	WorkspaceID      string `json:"workspace_id,omitempty" jsonschema:"Optional Boltz workspace ID"`
}

type getJobInput struct {
	ID          string `json:"id" jsonschema:"Boltz job ID, ideally with the standard prefix such as pred_*, prot_des_*, prot_scr_*, sm_des_*, or sm_scr_*"`
	WorkspaceID string `json:"workspace_id,omitempty" jsonschema:"Optional Boltz workspace ID"`
}

type resumeDownloadInput struct {
	ID                  string `json:"id,omitempty" jsonschema:"Optional Boltz job ID. Omit only when the existing run directory already contains .boltz-run.json"`
	RunName             string `json:"run_name" jsonschema:"Existing or new download name / run slug"`
	OutputDir           string `json:"output_dir,omitempty" jsonschema:"Optional output directory. Relative paths resolve from the original workspace if PWD is available, otherwise from the server process directory"`
	PollIntervalSeconds int    `json:"poll_interval_seconds,omitempty" jsonschema:"Optional download-results polling interval in seconds; defaults to 30"`
}

type getLocalRunInput struct {
	RunName      string `json:"run_name" jsonschema:"Run slug used as the local download directory name"`
	OutputDir    string `json:"output_dir,omitempty" jsonschema:"Optional output directory. Relative paths resolve from the original workspace if PWD is available, otherwise from the server process directory"`
	LogTailLines int    `json:"log_tail_lines,omitempty" jsonschema:"How many trailing log lines to return; defaults to 30"`
}

func main() {
	server := mcp.NewServer(&mcp.Implementation{
		Name:    serverName,
		Version: serverVersion,
	}, nil)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "boltz_estimate_run",
		Title:       "Estimate Boltz Run",
		Description: "Estimate Boltz Compute cost for a payload without submitting a job.",
		Annotations: readOnlyExternalTool("Estimate Boltz Run"),
	}, handleEstimateRun)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "boltz_submit_run",
		Title:       "Submit Boltz Run",
		Description: "Submit a Boltz Compute run and start detached download-results polling in the background.",
		Annotations: writeExternalTool("Submit Boltz Run", true),
	}, handleSubmitRun)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "boltz_list_jobs",
		Title:       "List Boltz Jobs",
		Description: "List recent Boltz Compute jobs across all five resources and annotate each row with resource type metadata.",
		Annotations: readOnlyExternalTool("List Boltz Jobs"),
	}, handleListJobs)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "boltz_get_job",
		Title:       "Get Boltz Job",
		Description: "Use the job ID prefix to route to the expected Boltz resource, falling back to the full search only when the prefix is unknown.",
		Annotations: readOnlyExternalTool("Get Boltz Job"),
	}, handleGetJob)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "boltz_resume_download",
		Title:       "Resume Boltz Download",
		Description: "Restart detached download-results polling for an existing Boltz job.",
		Annotations: writeExternalTool("Resume Boltz Download", true),
	}, handleResumeDownload)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "boltz_get_local_run",
		Title:       "Inspect Local Boltz Run",
		Description: "Read local run metadata, download log tail, and .boltz-run.json state from disk; analogous to CLI download-status plus log tail.",
		Annotations: &mcp.ToolAnnotations{
			Title:         "Inspect Local Boltz Run",
			ReadOnlyHint:  true,
			OpenWorldHint: boolPtr(false),
		},
	}, handleGetLocalRun)

	if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Fatal(err)
	}
}

func handleEstimateRun(ctx context.Context, _ *mcp.CallToolRequest, input estimateRunInput) (*mcp.CallToolResult, map[string]any, error) {
	if err := validateResource(input.Resource); err != nil {
		return nil, nil, err
	}

	payloadPath, cleanup, err := writePayloadTemp(input.Payload)
	if err != nil {
		return nil, nil, err
	}
	defer cleanup()

	args := []string{input.Resource, "estimate-cost"}
	args = appendCommonArgs(args, input.Model, input.WorkspaceID)
	args = append(args, "--input", "@json://"+payloadPath)

	baseDir := resolveBaseDir()
	stdout, stderr, err := runBoltzCommand(ctx, baseDir, args)
	if err != nil {
		return nil, nil, err
	}

	parsed, parseErr := parseStructuredText(stdout)
	response := map[string]any{
		"resource":          input.Resource,
		"command":           commandWithBinary(args),
		"working_directory": baseDir,
		"raw_output":        stdout,
	}
	if strings.TrimSpace(stderr) != "" {
		response["stderr"] = stderr
	}
	if parseErr == nil && parsed != nil {
		response["parsed_response"] = parsed
		if estimatedCost, ok := nestedNumber(parsed, "estimated_cost_usd"); ok {
			response["estimated_cost_usd"] = estimatedCost
		}
		if disclaimer, ok := nestedString(parsed, "disclaimer"); ok {
			response["disclaimer"] = disclaimer
		}
	} else if parseErr != nil {
		response["parse_warning"] = parseErr.Error()
	}

	return nil, response, nil
}

func handleSubmitRun(ctx context.Context, _ *mcp.CallToolRequest, input submitRunInput) (*mcp.CallToolResult, map[string]any, error) {
	if err := validateResource(input.Resource); err != nil {
		return nil, nil, err
	}
	if strings.TrimSpace(input.RunName) == "" {
		return nil, nil, errors.New("run_name is required")
	}

	baseDir := resolveBaseDir()
	outputDir, err := resolveOutputDir(input.OutputDir)
	if err != nil {
		return nil, nil, err
	}
	runDir := filepath.Join(outputDir, input.RunName)
	if err := os.MkdirAll(runDir, 0o755); err != nil {
		return nil, nil, fmt.Errorf("create run dir: %w", err)
	}

	requestPath := filepath.Join(runDir, requestFileName)
	if err := writeJSONFile(requestPath, input.Payload); err != nil {
		return nil, nil, err
	}

	args := []string{input.Resource, "start"}
	args = appendCommonArgs(args, input.Model, input.WorkspaceID)
	args = append(args,
		"--idempotency-key", input.RunName,
		"--input", "@json://"+requestPath,
		"--raw-output",
		"--transform", "id",
	)

	stdout, _, err := runBoltzCommand(ctx, baseDir, args)
	if err != nil {
		return nil, nil, err
	}

	jobID := strings.TrimSpace(stdout)
	if jobID == "" {
		return nil, nil, errors.New("boltz-api start returned an empty job id")
	}

	pollInterval := input.PollIntervalSeconds
	if pollInterval <= 0 {
		pollInterval = defaultPollIntervalForResource(input.Resource)
	}

	downloadArgs := downloadResultsArgs(jobID, input.RunName, outputDir, pollInterval)
	logPath := filepath.Join(runDir, logFileName)
	pidPath := filepath.Join(runDir, pidFileName)
	metadataPath := filepath.Join(runDir, metadataFileName)

	pid, err := startDetachedDownload(baseDir, downloadArgs, logPath)
	if err != nil {
		return nil, nil, err
	}
	if err := os.WriteFile(pidPath, []byte(strconv.Itoa(pid)+"\n"), 0o644); err != nil {
		return nil, nil, fmt.Errorf("write pid file: %w", err)
	}

	metadata := map[string]any{
		"resource":               input.Resource,
		"id":                     jobID,
		"run_name":               input.RunName,
		"output_dir":             outputDir,
		"run_dir":                runDir,
		"request_path":           requestPath,
		"log_path":               logPath,
		"pid_file":               pidPath,
		"download_pid":           pid,
		"poll_interval_seconds":  pollInterval,
		"submitted_at":           time.Now().UTC().Format(time.RFC3339),
		"start_command":          commandWithBinary(args),
		"download_command":       commandWithBinary(downloadArgs),
		"working_directory":      baseDir,
		"idempotency_key_source": "run_name",
	}
	if input.Model != "" {
		metadata["model"] = input.Model
	}
	if input.WorkspaceID != "" {
		metadata["workspace_id"] = input.WorkspaceID
	}
	if err := writeJSONFile(metadataPath, metadata); err != nil {
		return nil, nil, err
	}

	return nil, metadata, nil
}

func handleListJobs(ctx context.Context, _ *mcp.CallToolRequest, input listJobsInput) (*mcp.CallToolResult, map[string]any, error) {
	perResourceLimit := input.PerResourceLimit
	if perResourceLimit <= 0 {
		perResourceLimit = defaultListLimit
	}

	totalLimit := input.TotalLimit
	if totalLimit <= 0 {
		totalLimit = defaultTotalLimit
	}

	baseDir := resolveBaseDir()
	merged := make([]map[string]any, 0, len(resources)*perResourceLimit)
	for _, resource := range resources {
		args := []string{resource, "list", "--limit", strconv.Itoa(perResourceLimit), "--format", "jsonl"}
		if input.WorkspaceID != "" {
			args = append(args, "--workspace-id", input.WorkspaceID)
		}

		stdout, _, err := runBoltzCommand(ctx, baseDir, args)
		if err != nil {
			return nil, nil, err
		}

		records, err := parseJSONLines(stdout)
		if err != nil {
			return nil, nil, fmt.Errorf("parse %s list output: %w", resource, err)
		}
		if len(records) > perResourceLimit {
			records = records[:perResourceLimit]
		}
		for _, record := range records {
			merged = append(merged, summarizeRecord(resource, record))
		}
	}

	sort.SliceStable(merged, func(i, j int) bool {
		return createdAt(merged[i]) > createdAt(merged[j])
	})
	if len(merged) > totalLimit {
		merged = merged[:totalLimit]
	}

	return nil, map[string]any{
		"jobs":               merged,
		"per_resource_limit": perResourceLimit,
		"total_limit":        totalLimit,
		"resource_prefixes":  resourcePrefixMap(),
		"working_directory":  baseDir,
	}, nil
}

func handleGetJob(ctx context.Context, _ *mcp.CallToolRequest, input getJobInput) (*mcp.CallToolResult, map[string]any, error) {
	jobID := strings.TrimSpace(input.ID)
	if jobID == "" {
		return nil, nil, errors.New("id is required")
	}

	baseDir := resolveBaseDir()
	resourcesToTry := resources
	routingMode := "fallback_probe"
	if descriptor, ok := inferResourceFromID(jobID); ok {
		resourcesToTry = []string{descriptor.Resource}
		routingMode = "id_prefix"
	}

	var lastErr error
	for _, resource := range resourcesToTry {
		args := []string{resource, "retrieve", "--id", jobID, "--format", "json"}
		if input.WorkspaceID != "" {
			args = append(args, "--workspace-id", input.WorkspaceID)
		}

		stdout, stderr, err := runBoltzCommand(ctx, baseDir, args)
		if err != nil {
			lastErr = err
			if isVersionSurfaceMismatch(stderr) {
				return nil, nil, err
			}
			continue
		}

		parsed, parseErr := parseStructuredText(stdout)
		if parseErr != nil {
			return nil, nil, fmt.Errorf("parse %s retrieve output: %w", resource, parseErr)
		}

		descriptor := describeResource(resource)
		if inferred, ok := inferResourceFromID(jobID); ok {
			descriptor = inferred
		}

		out := map[string]any{
			"resource":              resource,
			"resource_type":         descriptor.Type,
			"resource_prefix":       descriptor.Prefix,
			"resource_routing_mode": routingMode,
			"command":               commandWithBinary(args),
			"working_directory":     baseDir,
			"record":                parsed,
			"raw_output":            stdout,
		}
		if status, ok := nestedString(parsed, "status"); ok {
			out["status"] = status
		}
		if idem, ok := nestedString(parsed, "idempotency_key"); ok {
			out["idempotency_key"] = idem
		}
		if progress, ok := nestedMap(parsed, "progress"); ok {
			out["progress"] = progress
		}
		if jobErr, ok := nestedValue(parsed, "error"); ok {
			out["error"] = jobErr
		}

		return nil, out, nil
	}

	if lastErr != nil {
		return nil, nil, fmt.Errorf("job %q not found across known Boltz resources; last error: %w", jobID, lastErr)
	}
	return nil, nil, fmt.Errorf("job %q not found across known Boltz resources", jobID)
}

func handleResumeDownload(_ context.Context, _ *mcp.CallToolRequest, input resumeDownloadInput) (*mcp.CallToolResult, map[string]any, error) {
	if strings.TrimSpace(input.RunName) == "" {
		return nil, nil, errors.New("run_name is required")
	}

	baseDir := resolveBaseDir()
	outputDir, err := resolveOutputDir(input.OutputDir)
	if err != nil {
		return nil, nil, err
	}
	runDir := filepath.Join(outputDir, input.RunName)
	if err := os.MkdirAll(runDir, 0o755); err != nil {
		return nil, nil, fmt.Errorf("create run dir: %w", err)
	}

	pollInterval := input.PollIntervalSeconds
	if pollInterval <= 0 {
		pollInterval = 30
	}

	args := []string{"download-results"}
	if strings.TrimSpace(input.ID) != "" {
		args = append(args, "--id", input.ID)
	}
	args = append(args,
		"--name", input.RunName,
		"--root-dir", outputDir,
		"--poll-interval-seconds", strconv.Itoa(pollInterval),
		"--progress-format", "jsonl",
	)

	logPath := filepath.Join(runDir, logFileName)
	pidPath := filepath.Join(runDir, pidFileName)
	metadataPath := filepath.Join(runDir, metadataFileName)

	pid, err := startDetachedDownload(baseDir, args, logPath)
	if err != nil {
		return nil, nil, err
	}
	if err := os.WriteFile(pidPath, []byte(strconv.Itoa(pid)+"\n"), 0o644); err != nil {
		return nil, nil, fmt.Errorf("write pid file: %w", err)
	}

	metadata := map[string]any{
		"id":                    strings.TrimSpace(input.ID),
		"run_name":              input.RunName,
		"output_dir":            outputDir,
		"run_dir":               runDir,
		"log_path":              logPath,
		"pid_file":              pidPath,
		"download_pid":          pid,
		"poll_interval_seconds": pollInterval,
		"resumed_at":            time.Now().UTC().Format(time.RFC3339),
		"download_command":      commandWithBinary(args),
		"working_directory":     baseDir,
	}
	if existing, err := readJSONFile(metadataPath); err == nil {
		for key, value := range existing {
			if _, exists := metadata[key]; !exists {
				metadata[key] = value
			}
		}
	}
	if err := writeJSONFile(metadataPath, metadata); err != nil {
		return nil, nil, err
	}

	return nil, metadata, nil
}

func handleGetLocalRun(_ context.Context, _ *mcp.CallToolRequest, input getLocalRunInput) (*mcp.CallToolResult, map[string]any, error) {
	if strings.TrimSpace(input.RunName) == "" {
		return nil, nil, errors.New("run_name is required")
	}

	outputDir, err := resolveOutputDir(input.OutputDir)
	if err != nil {
		return nil, nil, err
	}
	runDir := filepath.Join(outputDir, input.RunName)
	if _, err := os.Stat(runDir); err != nil {
		return nil, nil, fmt.Errorf("run dir %q not found: %w", runDir, err)
	}

	logTailLines := input.LogTailLines
	if logTailLines <= 0 {
		logTailLines = defaultStatusLines
	}

	out := map[string]any{
		"run_name":   input.RunName,
		"output_dir": outputDir,
		"run_dir":    runDir,
	}

	if metadata, err := readJSONFile(filepath.Join(runDir, metadataFileName)); err == nil {
		out["metadata"] = metadata
	}
	if boltzRun, err := readJSONFile(filepath.Join(runDir, boltzRunFileName)); err == nil {
		out["boltz_run"] = boltzRun
	}

	pidPath := filepath.Join(runDir, pidFileName)
	if pidBytes, err := os.ReadFile(pidPath); err == nil {
		pidText := strings.TrimSpace(string(pidBytes))
		if pid, convErr := strconv.Atoi(pidText); convErr == nil {
			out["download_pid"] = pid
			running, runErr := processRunning(pid)
			if runErr == nil {
				out["download_process_running"] = running
			} else {
				out["download_process_check_error"] = runErr.Error()
			}
		}
		out["pid_file"] = pidPath
	}

	logPath := filepath.Join(runDir, logFileName)
	if tail, err := tailFile(logPath, logTailLines); err == nil {
		out["log_path"] = logPath
		out["log_tail"] = tail
	}

	return nil, out, nil
}

func appendCommonArgs(args []string, model string, workspaceID string) []string {
	if strings.TrimSpace(model) != "" {
		args = append(args, "--model", model)
	}
	if strings.TrimSpace(workspaceID) != "" {
		args = append(args, "--workspace-id", workspaceID)
	}
	return args
}

func validateResource(resource string) error {
	if _, ok := resourceSet[resource]; ok {
		return nil
	}
	return fmt.Errorf("unsupported resource %q; expected one of %s", resource, strings.Join(resources, ", "))
}

func writePayloadTemp(payload map[string]any) (string, func(), error) {
	tempFile, err := os.CreateTemp("", "boltz-mcp-payload-*.json")
	if err != nil {
		return "", nil, fmt.Errorf("create temp payload file: %w", err)
	}
	path := tempFile.Name()
	tempFile.Close()

	if err := writeJSONFile(path, payload); err != nil {
		_ = os.Remove(path)
		return "", nil, err
	}

	return path, func() {
		_ = os.Remove(path)
	}, nil
}

func writeJSONFile(path string, payload any) error {
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal json for %s: %w", path, err)
	}
	data = append(data, '\n')
	if err := os.WriteFile(path, data, 0o644); err != nil {
		return fmt.Errorf("write %s: %w", path, err)
	}
	return nil
}

func readJSONFile(path string) (map[string]any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out map[string]any
	if err := json.Unmarshal(data, &out); err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}
	return out, nil
}

func runBoltzCommand(ctx context.Context, baseDir string, args []string) (string, string, error) {
	cmd := exec.CommandContext(ctx, "boltz-api", args...)
	cmd.Dir = baseDir
	cmd.Env = os.Environ()

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	stdoutText := strings.TrimSpace(stdout.String())
	stderrText := strings.TrimSpace(stderr.String())
	if err != nil {
		return stdoutText, stderrText, wrapBoltzError(args, stdoutText, stderrText, err)
	}
	return stdoutText, stderrText, nil
}

func wrapBoltzError(args []string, stdout string, stderr string, err error) error {
	joined := strings.Join(args, " ")
	if isVersionSurfaceMismatch(stdout) || isVersionSurfaceMismatch(stderr) {
		return fmt.Errorf(
			"boltz-api on PATH does not support the v0.7.x command surface this plugin expects. Install the newer CLI documented by this repo and retry. command=%q stderr=%q stdout=%q",
			joined,
			stderr,
			stdout,
		)
	}
	return fmt.Errorf("boltz-api %q failed: %w; stderr=%q; stdout=%q", joined, err, stderr, stdout)
}

func isVersionSurfaceMismatch(text string) bool {
	return strings.Contains(text, "No such command") || strings.Contains(text, "No such option")
}

func parseStructuredText(text string) (any, error) {
	trimmed := strings.TrimSpace(text)
	if trimmed == "" {
		return nil, nil
	}

	var jsonValue any
	if err := json.Unmarshal([]byte(trimmed), &jsonValue); err == nil {
		return jsonValue, nil
	}

	var yamlValue any
	if err := yaml.Unmarshal([]byte(trimmed), &yamlValue); err == nil {
		return normalizeYAMLValue(yamlValue), nil
	}

	return nil, fmt.Errorf("output was neither JSON nor YAML")
}

func normalizeYAMLValue(value any) any {
	switch typed := value.(type) {
	case map[string]any:
		out := make(map[string]any, len(typed))
		for key, child := range typed {
			out[key] = normalizeYAMLValue(child)
		}
		return out
	case map[any]any:
		out := make(map[string]any, len(typed))
		for key, child := range typed {
			out[fmt.Sprint(key)] = normalizeYAMLValue(child)
		}
		return out
	case []any:
		out := make([]any, 0, len(typed))
		for _, child := range typed {
			out = append(out, normalizeYAMLValue(child))
		}
		return out
	default:
		return typed
	}
}

func parseJSONLines(text string) ([]map[string]any, error) {
	scanner := bufio.NewScanner(strings.NewReader(text))
	scanner.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)

	records := make([]map[string]any, 0)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var record map[string]any
		if err := json.Unmarshal([]byte(line), &record); err != nil {
			return nil, fmt.Errorf("parse jsonl line %q: %w", line, err)
		}
		records = append(records, record)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return records, nil
}

func summarizeRecord(resource string, record map[string]any) map[string]any {
	summary := map[string]any{
		"resource": resource,
		"raw":      record,
	}
	if descriptor := describeResource(resource); descriptor.Resource != "" {
		summary["resource_type"] = descriptor.Type
		summary["resource_prefix"] = descriptor.Prefix
	}
	if id, ok := record["id"].(string); ok {
		if inferred, ok := inferResourceFromID(id); ok {
			summary["resource_type"] = inferred.Type
			summary["resource_prefix"] = inferred.Prefix
			summary["resource_from_id"] = inferred.Resource
		}
	}
	copyIfPresent(summary, "id", record)
	copyIfPresent(summary, "status", record)
	copyIfPresent(summary, "created_at", record)
	copyIfPresent(summary, "completed_at", record)
	copyIfPresent(summary, "idempotency_key", record)
	copyIfPresent(summary, "progress", record)
	copyIfPresent(summary, "error", record)
	return summary
}

func describeResource(resource string) resourceDescriptor {
	if descriptor, ok := resourceDescriptorByResource[resource]; ok {
		return descriptor
	}
	return resourceDescriptor{}
}

func inferResourceFromID(id string) (resourceDescriptor, bool) {
	trimmed := strings.TrimSpace(id)
	for _, descriptor := range resourceDescriptorsByPrefix {
		if trimmed == descriptor.Prefix || strings.HasPrefix(trimmed, descriptor.Prefix+"_") {
			return descriptor, true
		}
	}
	return resourceDescriptor{}, false
}

func resourcePrefixMap() map[string]string {
	out := make(map[string]string, len(resourceDescriptors))
	for _, descriptor := range resourceDescriptors {
		out[descriptor.Type] = descriptor.Prefix
	}
	return out
}

func copyIfPresent(dst map[string]any, key string, src map[string]any) {
	if value, ok := src[key]; ok {
		dst[key] = value
	}
}

func createdAt(record map[string]any) string {
	if created, ok := record["created_at"].(string); ok {
		return created
	}
	return ""
}

func nestedValue(root any, key string) (any, bool) {
	record, ok := root.(map[string]any)
	if !ok {
		return nil, false
	}
	value, exists := record[key]
	return value, exists
}

func nestedString(root any, key string) (string, bool) {
	value, ok := nestedValue(root, key)
	if !ok {
		return "", false
	}
	text, ok := value.(string)
	return text, ok
}

func nestedMap(root any, key string) (map[string]any, bool) {
	value, ok := nestedValue(root, key)
	if !ok {
		return nil, false
	}
	record, ok := value.(map[string]any)
	return record, ok
}

func nestedNumber(root any, key string) (float64, bool) {
	value, ok := nestedValue(root, key)
	if !ok {
		return 0, false
	}
	switch typed := value.(type) {
	case float64:
		return typed, true
	case float32:
		return float64(typed), true
	case int:
		return float64(typed), true
	case int64:
		return float64(typed), true
	case json.Number:
		number, err := typed.Float64()
		return number, err == nil
	default:
		return 0, false
	}
}

func resolveBaseDir() string {
	if pwd := os.Getenv("PWD"); pwd != "" {
		if abs, err := filepath.Abs(pwd); err == nil {
			if info, statErr := os.Stat(abs); statErr == nil && info.IsDir() {
				return abs
			}
		}
	}
	if wd, err := os.Getwd(); err == nil {
		return wd
	}
	return "."
}

func resolveOutputDir(explicit string) (string, error) {
	value := strings.TrimSpace(explicit)
	if value == "" {
		value = strings.TrimSpace(os.Getenv("BOLTZ_COMPUTE_OUTPUT_DIR"))
	}
	if value == "" {
		value = defaultOutputDir
	}
	return resolveUserPath(value)
}

func resolveUserPath(path string) (string, error) {
	if filepath.IsAbs(path) {
		return filepath.Clean(path), nil
	}
	return filepath.Abs(filepath.Join(resolveBaseDir(), path))
}

func defaultPollIntervalForResource(resource string) int {
	switch resource {
	case "predictions:structure-and-binding":
		return 10
	default:
		return 60
	}
}

func downloadResultsArgs(id string, runName string, outputDir string, pollInterval int) []string {
	return []string{
		"download-results",
		"--id", id,
		"--name", runName,
		"--root-dir", outputDir,
		"--poll-interval-seconds", strconv.Itoa(pollInterval),
		"--progress-format", "jsonl",
	}
}

func startDetachedDownload(baseDir string, args []string, logPath string) (int, error) {
	if err := os.MkdirAll(filepath.Dir(logPath), 0o755); err != nil {
		return 0, fmt.Errorf("create log dir: %w", err)
	}

	logFile, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return 0, fmt.Errorf("open log file: %w", err)
	}
	defer logFile.Close()

	if _, err := logFile.WriteString("\n=== boltz_resume " + time.Now().UTC().Format(time.RFC3339) + " ===\n"); err != nil {
		return 0, fmt.Errorf("prime log file: %w", err)
	}

	cmd := exec.Command("boltz-api", args...)
	cmd.Dir = baseDir
	cmd.Env = os.Environ()
	cmd.Stdout = logFile
	cmd.Stderr = logFile
	cmd.Stdin = nil
	configureDetachedProcess(cmd)

	if err := cmd.Start(); err != nil {
		return 0, wrapBoltzError(args, "", "", err)
	}

	pid := cmd.Process.Pid
	if err := cmd.Process.Release(); err != nil {
		return 0, fmt.Errorf("release detached process: %w", err)
	}
	return pid, nil
}

func tailFile(path string, maxLines int) ([]string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	lines := strings.Split(strings.ReplaceAll(string(data), "\r\n", "\n"), "\n")
	trimmed := make([]string, 0, len(lines))
	for _, line := range lines {
		line = strings.TrimRight(line, "\r")
		if strings.TrimSpace(line) == "" {
			continue
		}
		trimmed = append(trimmed, line)
	}
	if len(trimmed) > maxLines {
		trimmed = trimmed[len(trimmed)-maxLines:]
	}
	return trimmed, nil
}

func readOnlyExternalTool(title string) *mcp.ToolAnnotations {
	return &mcp.ToolAnnotations{
		Title:         title,
		ReadOnlyHint:  true,
		OpenWorldHint: boolPtr(true),
	}
}

func writeExternalTool(title string, idempotent bool) *mcp.ToolAnnotations {
	return &mcp.ToolAnnotations{
		Title:           title,
		ReadOnlyHint:    false,
		IdempotentHint:  idempotent,
		DestructiveHint: boolPtr(false),
		OpenWorldHint:   boolPtr(true),
	}
}

func boolPtr(value bool) *bool {
	return &value
}

func commandWithBinary(args []string) []string {
	return append([]string{"boltz-api"}, args...)
}
