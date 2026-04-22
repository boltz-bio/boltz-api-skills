# boltz-compute-mcp-go (Codex plugin)

This plugin keeps the same six Boltz Compute skills and the same per-skill reference docs as [`../codex-plugin-cli`](../codex-plugin-cli), but swaps the execution layer to a local Go MCP server.

The comparison target is deliberate:

- Same skill names and trigger language
- Same `references/api.md` payload docs
- Same Boltz CLI v0.7.x command surface underneath
- Different runtime boundary: local MCP tools instead of model-generated shell commands

## Why this variant exists

This plugin is for head-to-head testing against `codex-plugin-cli/` on criteria like:

- approval fatigue
- sandbox / network friction
- correctness and reasoning quality with the same workflow prose
- crash recovery ergonomics for long-running downloads

## What changes vs the CLI plugin

- The agent no longer shells out to `boltz-api` directly from the skill.
- A local Go MCP server exposes a small runtime surface:
  - `boltz_estimate_run`
  - `boltz_submit_run`
  - `boltz_list_jobs`
  - `boltz_get_job`
  - `boltz_resume_download`
  - `boltz_get_local_run`
- `boltz_submit_run` and `boltz_resume_download` spawn detached `download-results` processes and persist local metadata/logs under the run directory.
- Those detached downloads now rely on the CLI's default JSONL progress stream and `.boltz-run.json` / `download-status` checkpoint model.
- `boltz_get_job` routes directly from the job ID prefix when possible, and `boltz_list_jobs` annotates rows with the same `resource_type` / `resource_prefix` mapping.

## Prerequisites

- Go installed and on `PATH`
- `boltz-api` on `PATH`
- `BOLTZ_COMPUTE_API_KEY` exported in the environment
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR`

Important version note:

- This plugin assumes the newer Boltz CLI surface documented by the repo, including commands like `predictions:structure-and-binding estimate-cost` and top-level `download-results`.
- If `boltz-api` reports errors like `No such command 'predictions:structure-and-binding'`, your local CLI is too old or is a different binary.

## Installation

From a Codex session:

```text
/plugins add <path-to-this-directory>
```

Then start a fresh Codex session so the MCP server and skills are both available.

## Local MCP launch

The plugin registers `.mcp.json`, which launches the server with:

```text
go run ./cmd/boltz-compute-mcp
```

That keeps setup simple for local comparison work. If you want faster startup, build the binary first:

```bash
go build -o ./bin/boltz-compute-mcp ./cmd/boltz-compute-mcp
```

and update `.mcp.json` to point at `./bin/boltz-compute-mcp`.

## Notes on output paths

The MCP server resolves relative output paths against the original workspace when `PWD` is available, then falls back to its process working directory. The default remains:

```text
${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}
```

## Development

Build and smoke-test the server:

```bash
go build ./cmd/boltz-compute-mcp
go test ./cmd/boltz-compute-mcp
```
