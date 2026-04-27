# Contributing

## Source Of Truth

Shared workflow prose, API references, and MCP code live under `core/`.
Development plugin surfaces live under `surfaces/`. Checked-in installable
plugin copies live under `plugins/` and are generated.

| Path | Role | Edit directly? |
|---|---|---|
| `core/skills/cli/` | Shared CLI-backed skill workflows | Yes |
| `core/skills/mcp/` | Shared MCP-backed skill workflows | Yes |
| `core/references/` | Shared API reference docs | Yes |
| `surfaces/claude-code-cli/` | Claude Code CLI development surface and Claude-specific wrapper files | Yes |
| `plugins/boltz/` | Self-contained Claude Code marketplace plugin | No, generated |

## Claude Plugin Composition

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
`core/references/`. If a change is only about Claude Code packaging,
configuration, UX, or future Claude-only components, put it in
`surfaces/claude-code-cli/`.

## Local Workflow

After changing shared skill content or Claude-specific surface files:

```bash
scripts/generate-surfaces.sh
scripts/verify-generated.sh
claude plugin validate .
claude plugin validate plugins/boltz
```

For persistent local install testing:

```bash
BOLTZ_CLAUDE_MARKETPLACE="$PWD" scripts/install-claude-code-plugin.sh
```

Restart Claude Code after installing.

## Generated Files

Do not edit `plugins/boltz/` directly. CI regenerates it and fails if the
committed copy is stale. A branch push workflow also regenerates it and commits
the generated result back to development branches when needed.
