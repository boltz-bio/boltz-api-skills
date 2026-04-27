# boltz (Claude Code plugin)

Six skills for the Boltz Compute API, executed by shelling out to the `boltz-api` Go CLI directly from Claude Code.

## Skills

| Skill | What it does |
|---|---|
| `boltz-structure-and-binding` | Predict 3D structure of one defined complex; optionally score binding. |
| `boltz-small-molecule-screen` | Rank a user-supplied SMILES library against a target. |
| `boltz-small-molecule-design` | Generate novel small-molecule binders. |
| `boltz-protein-screen` | Rank user-supplied proteins/peptides/antibodies against a target. |
| `boltz-protein-design` | Generate novel peptide/antibody/nanobody/custom-protein binders. |
| `boltz-check-status` | List jobs, inspect one, recover results after a crashed session. |

## Prerequisites

- `boltz-api` on `PATH`. Install from the [CLI repository](https://github.com/boltz-bio/boltz-compute-api-cli).
- `BOLTZ_COMPUTE_API_KEY` exported in your shell environment.
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR` (defaults to `./boltz-experiments`).

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
