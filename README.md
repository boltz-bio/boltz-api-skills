# Boltz Skills

Agent tooling for running Boltz workflows (structure prediction, molecular screening, de novo design) from AI coding assistants. Distributed as CLI-backed Claude Code, Codex, and Gemini CLI surfaces that share one skill prose source.

## Surfaces

| Surface | Consumer | Execution layer | Status |
|---|---|---|---|
| [`surfaces/claude-code-cli/`](surfaces/claude-code-cli) | Claude Code | Skills shell out to `boltz-api` CLI | Active |
| [`surfaces/codex-cli/`](surfaces/codex-cli) | Codex | Skills shell out to `boltz-api` CLI | Ships today |
| [`surfaces/gemini-cli/`](surfaces/gemini-cli) | Gemini CLI | Skills shell out to `boltz-api` CLI | Local surface |

MCP-backed surfaces were removed for now so development can focus on one CLI-backed distribution path.

## Shared core

Every surface pulls from [`core/`](core/):

| Directory | Purpose | Consumed by |
|---|---|---|
| `core/skills/cli/` | CLI-variant skill bodies (shell commands) | `claude-code-cli`, `codex-cli`, `gemini-cli` |
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
branch push workflow auto-commits regenerated plugin-copy changes when a
development branch drifts.

## Codex official plugin submission

The official Codex plugin copy is generated under
[`plugins/boltz-compute-cli/`](plugins/boltz-compute-cli). Its directory name
matches `.codex-plugin/plugin.json` and its symlinked skill sources are
dereferenced, matching the layout used by `openai/plugins` entries such as
Netlify and Cloudflare.

For a zip artifact:

```bash
./scripts/package-plugins.sh         # writes dist/boltz-compute-cli-<version>.zip
```

For an `openai/plugins` PR, copy `plugins/boltz-compute-cli/` into that repo's
`plugins/` directory and add the marketplace entry:

```json
{
  "name": "boltz-compute-cli",
  "source": {
    "source": "local",
    "path": "./plugins/boltz-compute-cli"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Science"
}
```

For the full development lifecycle, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Gemini CLI extension

The Gemini CLI extension source lives under
[`surfaces/gemini-cli/`](surfaces/gemini-cli). It bundles the same shared
CLI-backed skills with a `gemini-extension.json` manifest and a concise
`GEMINI.md` context file for Gemini-specific shell behavior.

For local development:

```bash
gemini extensions link ./surfaces/gemini-cli
```

Restart Gemini CLI after linking, then verify with `/extensions list` and
`/skills list`.

For public distribution, mirror `surfaces/gemini-cli/` into a dedicated public
install repo with symlinks dereferenced. In that repo, `gemini-extension.json`
must live at the repo root.

To open a sync PR against the public release repo:

```bash
RELEASE_REPO=boltz-bio/boltz-gemini-cli scripts/release-gemini-repo.sh
```

## Release builds

```bash
./scripts/package-plugins.sh         # Zips the Claude Code, Codex CLI, and Gemini CLI surfaces into dist/
```

CI (`.github/workflows/release.yml`) runs these on every tagged release and attaches artifacts to the GitHub Release.

## Prerequisites for users

All surfaces need:
- Authentication via either `boltz-api auth login --device-code` or `BOLTZ_COMPUTE_API_KEY` as an API-key fallback.
- `BOLTZ_COMPUTE_OUTPUT_DIR` optional. Prefer an absolute path; otherwise skills default to `$PWD/boltz-experiments` from the command's starting directory.
- `boltz-api` on `PATH`

If an agent sandbox blocks installer temp files, OAuth browser login, credential storage, or the user-wide install path, request the host sandbox bypass/escalation needed to install and authenticate `boltz-api` in the user's real environment.

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
- `boltz-gemini-cli` → public Gemini CLI extension repo with `gemini-extension.json` at root

Pre-submission checklist (per surface): privacy policy URL, 512×512 icon, screenshots, support contact, verified metadata, license confirmation for any bundled binaries.

## Legacy

[`skills-python/`](skills-python/) and [`codex-plugin-python/`](codex-plugin-python/) are legacy Python-SDK-based variants. They predate the `core/` restructure and remain in the repo as references, not as distribution targets.
