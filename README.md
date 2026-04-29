# Boltz Compute Skills

Agent tooling for running Boltz Compute workflows (structure prediction, molecular screening, de novo design) from AI coding assistants. Distributed as CLI-backed Claude Code and Codex plugins that share one skill prose source.

## Surfaces

| Surface | Consumer | Execution layer | Status |
|---|---|---|---|
| [`surfaces/claude-code-cli/`](surfaces/claude-code-cli) | Claude Code | Skills shell out to `boltz-api` CLI | Active |
| [`surfaces/codex-cli/`](surfaces/codex-cli) | Codex | Skills shell out to `boltz-api` CLI | Ships today |

MCP-backed surfaces were removed for now so development can focus on one CLI-backed distribution path.

## Shared core

Every surface pulls from [`core/`](core/):

| Directory | Purpose | Consumed by |
|---|---|---|
| `core/skills/cli/` | CLI-variant skill bodies (shell commands) | `claude-code-cli`, `codex-cli` |
| `core/references/` | Payload schema docs | All surfaces |

Skill bodies and schema docs are **symlinked** into each surface, so editing in `core/` propagates everywhere. Confirmed working under Claude Code plugin caching.

## Quick start (local development)

```bash
# Run Claude Code with the development surface
claude --plugin-dir ./surfaces/claude-code-cli
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
`boltz-api` on `PATH` and either device-code auth via
`boltz-api auth login --device-code` or `BOLTZ_COMPUTE_API_KEY`.

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
./scripts/package-plugins.sh         # Zips the Claude Code and Codex CLI plugin surfaces into dist/
```

CI (`.github/workflows/release.yml`) runs these on every tagged release and attaches artifacts to the GitHub Release.

## Prerequisites for users

All surfaces need:
- Authentication via either `boltz-api auth login --device-code` or `BOLTZ_COMPUTE_API_KEY` as an API-key fallback.
- `BOLTZ_COMPUTE_OUTPUT_DIR` optional. Prefer an absolute path; otherwise skills default to `$PWD/boltz-experiments` from the command's starting directory.
- `boltz-api` on `PATH`

If an agent sandbox blocks installer temp files or OAuth token access, first run the CLI with workspace-local `HOME`, `TMPDIR`, `BOLTZ_API_INSTALL_DIR`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` as described in `boltz-api-cli`. Request the host sandbox bypass only if workspace-local state still cannot access the network, temp files, credentials, or install path.

Verify the CLI is installed:

```sh
boltz-api --version
```

If `boltz-api` is not installed, install or update it from the official CLI repo:

macOS and Linux:

```sh
curl -fsSL https://install.boltz.bio/boltz-api/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://install.boltz.bio/boltz-api/install.ps1 | iex
```

## Directory submissions

Targets:
- Claude Code `boltz` plugin → <https://claude.ai/settings/plugins/submit>
- `codex-*` → Codex-side plugin directory (if applicable)

Pre-submission checklist (per surface): privacy policy URL, 512×512 icon, screenshots, support contact, verified metadata, license confirmation for any bundled binaries.

## Legacy

[`skills-python/`](skills-python/) and [`codex-plugin-python/`](codex-plugin-python/) are legacy Python-SDK-based variants. They predate the `core/` restructure and remain in the repo as references, not as distribution targets.
