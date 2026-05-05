# Contributing

## Source Of Truth

Shared workflow prose and API references live under `core/`. Development plugin
surfaces live under `surfaces/`. Checked-in installable plugin copies live under
`plugins/` and are generated.

| Path | Role | Edit directly? |
|---|---|---|
| `core/skills/cli/` | Shared CLI-backed skill workflows | Yes |
| `core/references/` | Shared API reference docs | Yes |
| `surfaces/claude-code-cli/` | Claude Code CLI development surface and Claude-specific wrapper files | Yes |
| `surfaces/codex-cli/` | Codex plugin development surface and Codex-specific metadata | Yes |
| `surfaces/gemini-cli/` | Gemini CLI development extension and Gemini-specific context | Yes |
| `plugins/boltz/` | Self-contained Claude Code marketplace plugin | No, generated |
| `plugins/boltz-compute-cli/` | Self-contained Codex plugin copy | No, generated |

## Surface Composition

The installable Claude Code plugin is assembled from two layers:

1. Shared core content, exposed through the symlinked development surface at
   `surfaces/claude-code-cli/skills/`.
2. Claude-specific files in `surfaces/claude-code-cli/`, such as
   `.claude-plugin/plugin.json`, README content, and any future Claude-only
   commands, agents, hooks, scripts, settings, or assets.

Run `scripts/generate-surfaces.sh` to copy that complete Claude development
surface into `plugins/boltz/` with symlinks dereferenced. That generated copy is
what local marketplace installs consume.

If a change is useful to every CLI-backed agent, put it in `core/skills/cli/` or
`core/references/`. If a change is only about one host's packaging,
configuration, UX, or host-specific components, put it in that host's
`surfaces/<surface>/` directory.

The Gemini CLI extension is source-only in this repo: `surfaces/gemini-cli/`
contains `gemini-extension.json`, `GEMINI.md`, README content, and symlinked
skills. Packaging and public-repo mirroring dereference that surface directly
into a temporary stage or release repo.

## Local Workflow

After changing shared skill content or surface-specific files:

```bash
scripts/generate-surfaces.sh
scripts/verify-generated.sh
claude plugin validate .
claude plugin validate plugins/boltz
```

For Gemini local-link testing:

```bash
gemini extensions link ./surfaces/gemini-cli
```

For persistent local install testing:

```bash
BOLTZ_CLAUDE_MARKETPLACE="$PWD" scripts/install-claude-code-plugin.sh
```

Restart Claude Code after installing.

## Generated Files

Do not edit `plugins/boltz/` or `plugins/boltz-compute-cli/` directly. CI
regenerates them and fails if the committed copies are stale. A branch push
workflow also regenerates them and commits the generated result back to
development branches when needed.
