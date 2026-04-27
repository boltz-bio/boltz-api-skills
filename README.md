# Boltz Compute Skills

Agent tooling for running Boltz Compute workflows (structure prediction, molecular screening, de novo design) from AI coding assistants and Claude Desktop. Distributed across five surfaces that share a single skill prose source and a single Go MCP server implementation.

## Surfaces

| Surface | Consumer | Execution layer | Status |
|---|---|---|---|
| [`surfaces/claude-code-cli/`](surfaces/claude-code-cli) | Claude Code | Skills shell out to `boltz-api` CLI | Scaffolded |
| [`surfaces/claude-code-mcp/`](surfaces/claude-code-mcp) | Claude Code | Skills invoke bundled local MCP server | Scaffolded |
| [`surfaces/claude-desktop-mcpb/`](surfaces/claude-desktop-mcpb) | Claude Desktop | MCP server + bundled CLI packaged as `.mcpb` | Scaffolded |
| [`surfaces/codex-cli/`](surfaces/codex-cli) | Codex | Skills shell out to `boltz-api` CLI | Ships today |
| [`surfaces/codex-mcp/`](surfaces/codex-mcp) | Codex | Skills invoke local MCP server | Ships today |

The two Claude Code variants exist side-by-side for benchmarking — see [`benchmarks/`](benchmarks/). After benchmarks run, one is chosen for directory submission.

## Shared core

Every surface pulls from [`core/`](core/):

| Directory | Purpose | Consumed by |
|---|---|---|
| `core/mcp-server/` | Go MCP server source (single implementation) | `claude-code-mcp`, `claude-desktop-mcpb`, `codex-mcp` |
| `core/skills/cli/` | CLI-variant skill bodies (shell commands) | `claude-code-cli`, `codex-cli` |
| `core/skills/mcp/` | MCP-variant skill bodies (tool invocations) | `claude-code-mcp`, `codex-mcp` |
| `core/references/` | Payload schema docs (identical across all variants) | All surfaces |

Skill bodies and schema docs are **symlinked** into each surface, so editing in `core/` propagates everywhere. Confirmed working under Claude Code plugin caching.

## Quick start (local development)

```bash
# Build the MCP server for the host platform into every target surface
./scripts/build-mcp-local.sh

# Run Claude Code with either variant
claude --plugin-dir ./surfaces/claude-code-cli
claude --plugin-dir ./surfaces/claude-code-mcp
```

## Claude Code local install

The repo root is also a Claude Code marketplace named `boltz-marketplace`. It
publishes one installable plugin named `boltz`, backed by a self-contained copy
of the CLI-direct Claude Code skills under `plugins/boltz`.

For a local checkout:

```bash
claude plugin marketplace add "$PWD"
claude plugin install boltz@boltz-marketplace --scope user
```

Or use the install script:

```bash
scripts/install-claude-code-plugin.sh
```

To install from a local checkout instead of GitHub, run:

```bash
BOLTZ_CLAUDE_MARKETPLACE="$PWD" scripts/install-claude-code-plugin.sh
```

Restart Claude Code after installing. The installed `boltz` plugin requires
`boltz-api` on `PATH` and either `boltz-api auth login` or
`BOLTZ_COMPUTE_API_KEY`.

When editing the shared skill source under `core/` or Claude-specific files
under `surfaces/claude-code-cli/`, refresh generated distribution surfaces:

```bash
scripts/generate-surfaces.sh
```

Treat `plugins/boltz` as generated output. Make source changes under `core/` or
`surfaces/claude-code-cli/`, then sync. CI verifies the generated copy, and a
branch push workflow auto-commits regenerated `plugins/boltz` changes when a
development branch drifts.

For the full development lifecycle, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Release builds

```bash
./scripts/build-mcp-release.sh       # Cross-platform binaries into dist/bin/
./scripts/package-mcpb.sh            # Produces dist/boltz-compute-<version>.mcpb
./scripts/package-plugins.sh         # Zips every plugin surface into dist/
```

CI (`.github/workflows/release.yml`) runs these on every tagged release and attaches artifacts to the GitHub Release.

## Prerequisites for users

All surfaces need:
- Authentication via either `boltz-api auth login` / MCP `boltz_auth_login` OAuth device-code login, or `BOLTZ_COMPUTE_API_KEY` as an API-key fallback.
- `BOLTZ_COMPUTE_OUTPUT_DIR` optional (defaults to `./boltz-experiments`)

CLI-backed surfaces also need `boltz-api` on `PATH`. The Desktop MCPB bundles `boltz-api` so Desktop users don't need to install it separately.

## Benchmarks

The two Claude Code surfaces compete on:
- Approval friction (permission prompts per workflow)
- Token usage
- Crash recovery robustness (scenario 7 — the hypothesis-testing case)

See [`benchmarks/README.md`](benchmarks/README.md) for the harness procedure and scenarios.

## Directory submissions

Targets:
- Claude Code winner → <https://claude.ai/settings/plugins/submit>
- `claude-desktop-mcpb` → <https://clau.de/desktop-extention-submission>
- `codex-*` → Codex-side plugin directory (if applicable)

Pre-submission checklist (per surface): privacy policy URL, 512×512 icon, screenshots, support contact, verified metadata, license confirmation for any bundled binaries.

## Legacy

[`skills-python/`](skills-python/) and [`codex-plugin-python/`](codex-plugin-python/) are legacy Python-SDK-based variants. They predate the `core/` restructure and remain in the repo as references, not as distribution targets.
