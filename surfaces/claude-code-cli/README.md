# boltz (Claude Code plugin)

Seven skills for the Boltz Compute API, executed by shelling out to the `boltz-api` Go CLI directly from Claude Code. Six workflow skills run Boltz Compute jobs, and `boltz-api-cli` covers install/auth guidance.

## Skills

| Skill | What it does |
|---|---|
| `boltz-api-cli` | Install, update, verify, and authenticate the `boltz-api` CLI. |
| `boltz-structure-and-binding` | Predict 3D structure of one defined complex; optionally score binding. |
| `boltz-small-molecule-screen` | Rank a user-supplied SMILES library against a target. |
| `boltz-small-molecule-design` | Generate novel small-molecule binders. |
| `boltz-protein-screen` | Rank user-supplied proteins/peptides/antibodies against a target. |
| `boltz-protein-design` | Generate novel peptide/antibody/nanobody/custom-protein binders. |
| `boltz-check-status` | List jobs, inspect one, recover results after a crashed session. |

## Prerequisites

- `boltz-api` on `PATH`.
- `BOLTZ_COMPUTE_API_KEY` exported in your shell environment.
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR`. Prefer an absolute path; otherwise skills default to `$PWD/boltz-experiments` from the command's starting directory.

If the Claude Code sandbox blocks installer temp files or OAuth token access, first run the CLI with workspace-local `HOME`, `TMPDIR`, `BOLTZ_API_INSTALL_DIR`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` as described in `boltz-api-cli`. Use `dangerouslyDisableSandbox: true` only if workspace-local state still cannot access the network, temp files, credentials, or install path.

Verify the CLI is installed:

```sh
boltz-api --version
```

If `boltz-api` is not installed, install or update it from the official CLI repo:

macOS and Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/boltz-bio/boltz-compute-api-cli/main/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/boltz-bio/boltz-compute-api-cli/main/scripts/install.ps1 | iex
```

The installer updates an existing `boltz-api` on `PATH`. If no binary is found, it installs to `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\Boltz\bin` on Windows. Add that directory to `PATH` if `boltz-api --version` is still not found after install. Set `BOLTZ_API_INSTALL_DIR` before running the installer to choose a different install directory.

## Agent-friendly command style

Claude Code permission prompts are easiest to reuse when Boltz calls are simple top-level commands whose first token is `boltz-api`. The skills therefore prefer patterns like:

```bash
boltz-api protein:design start --idempotency-key "protein-design-nanobody-gfp-v1" --input @yaml://payload.yaml --raw-output --transform id
```

The agent should read the printed job ID from stdout and paste that literal ID into the next `boltz-api download-results ...` command. Prefer concrete arguments over `sh -c`, inline environment assignments, aliases, shell loops, or generated command strings unless the user has already allowed that exact command form. This keeps permission rules such as `boltz-api *` useful while preserving the important practices: explicit cost estimates, stable idempotency keys, merged payload files, and detached/non-blocking result downloads.

## Installation

The repository root is a local Claude Code marketplace named
`boltz-marketplace`; it installs the self-contained copy at `plugins/boltz`.
From the repository root:

```bash
claude plugin marketplace add "$PWD"
claude plugin install boltz@boltz-marketplace --scope user
```

Or run the installer:

```bash
scripts/install-claude-code-plugin.sh
```

For local development without persistent installation, start Claude Code with
`--plugin-dir`:

```bash
claude --plugin-dir <path-to-this-directory>
```

## Repository layout

In `surfaces/claude-code-cli`, skill bodies and schema references are symlinked
from `core/` at the repo root. The marketplace-installable copy under
`plugins/boltz` is generated with real files so Claude Code can cache it
without broken symlinks.

## Shared components

- `core/skills/cli/` — skill workflow prose used by both the Claude Code CLI plugin and the Codex CLI plugin.
- `core/references/` — payload schema documentation shared across all surfaces.
