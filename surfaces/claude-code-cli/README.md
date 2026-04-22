# boltz-compute-cli (Claude Code plugin)

Six skills for the Boltz Compute API, executed by shelling out to the `boltz-api` Go CLI directly from Claude Code. This is the **CLI-direct variant** — see [`../claude-code-mcp/`](../claude-code-mcp) for the MCP-backed variant.

Both surfaces expose the same six skills with identical trigger descriptions, differing only in execution layer. They exist side-by-side to support benchmarking before a single Claude Code surface is chosen for directory submission.

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

- `boltz-api` on `PATH`. Install from the [CLI repository](https://github.com/boltz-bio/boltz-api).
- `BOLTZ_COMPUTE_API_KEY` exported in your shell environment.
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR` (defaults to `./boltz-experiments`).

## Installation

From a Claude Code session:

```text
/plugin install <path-to-this-directory>
```

Or for local development, start Claude Code with `--plugin-dir`:

```bash
claude --plugin-dir <path-to-this-directory>
```

## Repository layout

All skill bodies and schema references are symlinked from `core/` at the repo root — this surface is just the Claude Code manifest + the skill index. Editing SKILL.md here edits the shared source.

## Shared components

- `core/skills/cli/` — skill workflow prose used by both the Claude Code CLI plugin and the Codex CLI plugin.
- `core/references/` — payload schema documentation shared across all surfaces.
