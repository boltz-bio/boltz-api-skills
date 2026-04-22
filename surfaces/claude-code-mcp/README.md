# boltz-compute-mcp (Claude Code plugin)

Six skills for the Boltz Compute API, executed via a bundled local MCP server. This is the **MCP-backed variant** — see [`../claude-code-cli/`](../claude-code-cli) for the direct-CLI variant.

Both surfaces expose the same six skills with identical trigger descriptions, differing only in execution layer. They exist side-by-side for benchmarking before a single Claude Code surface is chosen for directory submission.

## Skills

Identical trigger names and descriptions to `claude-code-cli`. The skill bodies differ: this variant calls MCP tools (`boltz_estimate_run`, `boltz_submit_run`, `boltz_list_jobs`, `boltz_get_job`, `boltz_resume_download`, `boltz_get_local_run`) instead of shelling out to `boltz-api`.

## Prerequisites

- `boltz-api` on `PATH`. The MCP server shells out to it internally. Install from the [CLI repository](https://github.com/boltz-bio/boltz-compute-api-cli).
- `BOLTZ_COMPUTE_API_KEY` exported in your shell environment.
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR` (defaults to `./boltz-experiments`).
- A pre-built MCP server binary in `./bin/boltz-compute-mcp`. Build it with:

```bash
# From repo root
scripts/build-mcp-local.sh
```

This produces `surfaces/claude-code-mcp/bin/boltz-compute-mcp` (and its MCPB sibling) for the host platform.

## Installation

From a Claude Code session:

```text
/plugin install <path-to-this-directory>
```

Or for local development:

```bash
claude --plugin-dir <path-to-this-directory>
```

## Repository layout

- `.claude-plugin/plugin.json` — manifest.
- `.mcp.json` — launches the bundled Go MCP server at `${CLAUDE_PLUGIN_ROOT}/bin/boltz-compute-mcp`.
- `bin/` — built binaries (gitignored locally; release zips bundle one binary per target platform).
- `skills/` — symlinked from `core/skills/mcp/` and `core/references/` at the repo root.

## Shared components

- `core/mcp-server/` — Go source for the MCP server.
- `core/skills/mcp/` — MCP-variant skill prose, shared with Codex MCP plugin.
- `core/references/` — payload schema documentation shared across all surfaces.
