---
name: boltz-check-status
description: List recent Boltz Compute jobs across all five endpoints, or inspect a single job by ID, and optionally pull its results onto disk. TRIGGER when the user asks what Boltz jobs are running, to check status, whether a screen finished, to resume a prior job, to download results for a job ID, to see how far along a job is, or after a session restart where earlier job IDs were lost.
---

## Workflow

If `boltz-api` is missing from `PATH`, use `boltz-api-cli` for install/update guidance before retrying.
If a command reports missing or expired authentication, use `boltz-api-cli` to start `boltz-api auth login --device-code` before retrying; do not ask permission first.
If the agent host sandbox blocks `boltz-api` install/auth/API calls, use `boltz-api-cli` to set workspace-local `HOME`, `TMPDIR`, `BOLTZ_API_INSTALL_DIR`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` before retrying. Request the host sandbox bypass only if workspace-local state still fails.

Use this skill to recover state across sessions and to inspect or download results for prior Boltz jobs. No payload authoring — this skill only calls `list` / `retrieve` / `download-results` / `download-status`.

Three remote modes, plus one local checkpoint helper:

### Local helper — "what is my downloader doing?" (run name or run dir provided)

Use `download-status` first when the user knows the original slug / run name or local run dir and wants to inspect local progress without burning an API call.

### Mode 1 — "what's running?" (no ID provided)

Enumerate recent jobs across all five resources, merge, and sort by `created_at` descending. Use `--limit 20` per resource and cap the streamed output with `head -20` because the CLI auto-paginates; bump higher if the user asks to see more. Derive `resource_type` / `resource_prefix` from the job ID prefix (empirical — not part of the spec contract; verified 2026-04-23 against live `list --limit 1` on each endpoint):

- `sab_pred_*` → `prediction` (structure-and-binding)
- `prot_des_*` → `protein_design_ppi`
- `prot_scr_*` → `protein_library_screen_ppi`
- `sm_des_*` → `boltz_sm_design`
- `sm_scr_*` → `boltz_sm_screen`

If a returned ID doesn't match any of these prefixes, fall through to the all-resources probe — the mapping is observational, not guaranteed.

### Mode 2 — "how's this job doing?" (ID provided)

Use the job ID prefix to select the right `retrieve` endpoint. Only fall back to probing all five if the prefix is unfamiliar. Report `status`, progress counters for pipeline jobs (`num_molecules_screened` / `num_proteins_generated` / etc.), and the `error` if present. For pipeline endpoints, `stopped` is terminal and means the run was stopped early; partial results may be available. SAB predictions do not use `stopped`. **Capture `idempotency_key` from the response**; you'll need it in Mode 3.

### Mode 3 — "my session died, pull the results"

This is the crash-recovery path. Two sub-cases:

**3a. User knows the original slug** (or the local run directory still exists):

```bash
# Launch this command in the agent runtime's background/non-blocking mode.
# Claude Code: Bash with run_in_background=true.
# Codex: foreground shell command with yield_time_ms=1000; keep the returned session_id if one is provided.
# Do not append "&" or use nohup in Codex.
boltz-api download-results \
  --id "<job-id>" --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments" \
  --poll-interval-seconds 30
```

CLI reuses the existing `.boltz-run.json` and only pulls results past the last recorded cursor. If the run dir exists, `--id` can be omitted because the CLI can read the ID from metadata. Re-run in background mode the same as a fresh submit.

**3b. User has only the job ID:**

Run Mode 2 first to get `idempotency_key` from the retrieve response, then use it as `--name` in the 3a command. If the original submit didn't pass `idempotency_key`, pick a fresh slug and `download-results` from scratch — server-side the job is fine; only incremental-resume is lost.

Never run `start` again "to resume" — that creates a new job.

## Command Pattern

```bash
# Replace placeholders with concrete absolute paths before running.

# Local helper: inspect local checkpoint state without API calls.
boltz-api --format json download-status \
  --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments"

# Mode 1: list recent jobs across all 5 resources.
# NB: the CLI emits one JSON object per record (streamed, no {data:[]} wrapper).
# --limit is per-page and the CLI auto-paginates, so cap each explicit command with head.
boltz-api predictions:structure-and-binding list --limit 20 --format jsonl | head -20
boltz-api small-molecule:library-screen list --limit 20 --format jsonl | head -20
boltz-api small-molecule:design list --limit 20 --format jsonl | head -20
boltz-api protein:library-screen list --limit 20 --format jsonl | head -20
boltz-api protein:design list --limit 20 --format jsonl | head -20

# Mode 2: retrieve by ID. Pick the resource from the ID prefix in the workflow
# notes above. If the prefix is unknown, run these one at a time until one succeeds.
boltz-api predictions:structure-and-binding retrieve --id "<job-id>" --format json
boltz-api small-molecule:library-screen retrieve --id "<job-id>" --format json
boltz-api small-molecule:design retrieve --id "<job-id>" --format json
boltz-api protein:library-screen retrieve --id "<job-id>" --format json
boltz-api protein:design retrieve --id "<job-id>" --format json

# Mode 3: resume download.
# Launch this command in the agent runtime's background/non-blocking mode.
# Claude Code: Bash with run_in_background=true.
# Codex: foreground shell command with yield_time_ms=1000; keep the returned session_id if one is provided.
# Do not append "&" or use nohup in Codex.
boltz-api download-results \
  --id "<job-id>" --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments" \
  --poll-interval-seconds 30
```

## Always Do This

- If the user has a run name / slug or run dir and only wants local downloader state, prefer `download-status` before `retrieve`.
- Use an absolute output root and keep passing it through `--root-dir`. Do not `cd` into the run directory; that makes later relative paths point at the run directory instead of the user's workspace.
- On an unfamiliar job ID, run Mode 2 (retrieve) before Mode 3 (download) so you capture `idempotency_key`.
- Prefer the original run-name slug over the job ID as `--name` — it resumes into the existing dir with cursor.
- In permission-gated agents such as Claude Code, keep each Boltz call as a top-level command that starts with `boltz-api`. Prefer running the five `list` / `retrieve` commands explicitly over generating them from a shell loop; a fixed `| head -20` cap is okay when listing to avoid runaway streamed output.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. In Codex specifically, keep `download-results` in the foreground and set the shell tool yield to 1000 ms; Codex will return a `session_id` if the command is still running. Do not append `&` or use `nohup` in Codex because the tool runner may clean up shell-backgrounded descendants before `.boltz-run.json` is fully written.
- After the background/session starts, do not wait on it or poll it. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- `download-results` now emits machine-readable JSONL progress on stderr by default. Add `--progress-format text --verbose` only when you explicitly want human-readable logs.
- Only check progress when the user asks. Prefer `download-status` for local checkpoint state or, in Codex, poll the saved session with an empty `write_stdin` to read JSONL stderr if the session is still running. Don't loop `retrieve` unless the user wants fresh remote status.
- If `retrieve` surfaces only `{"code":"VALIDATION_ERROR","message":"Request validation failed"}` with no `details`, that's expected for `predictions:structure-and-binding` failures — other endpoints include field paths.
- Never run `start` again on a failed or interrupted job. Fix the payload and submit with a new `idempotency-key`, or just resume with `download-results`.

## Escape Hatch

- Python SDK reference (per-resource `list` / `retrieve` methods): <https://boltz-compute-api.stldocs.app/api/python>
- CLI flag names: `boltz-api <resource> list --help`, `boltz-api <resource> retrieve --help`, `boltz-api download-results --help`, `boltz-api download-status --help`

Read [references/api.md](references/api.md) for per-resource `list` columns, `retrieve` record fields, and `download-results` resume semantics.

## Outputs

- Local helper / Mode 1 / Mode 2 print structured data to stdout; present as a table.
- Mode 3 writes recovered artifacts under `<output-root>/<run-name>/` — same layout as a fresh run: `.boltz-run.json`, `outputs/` (SAB) or `results/<pres_*>/` (screens and designs).
