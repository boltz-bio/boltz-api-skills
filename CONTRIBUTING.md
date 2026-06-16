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
| `surfaces/mcpb/` | Claude Desktop MCPB development surface | Yes |
| `surfaces/partner-cli-skills/` | Partner self-contained skill bundle | Yes |
| `plugins/boltz/` | Self-contained Claude Code marketplace plugin | No, generated |
| `plugins/boltz-compute-cli/` | Self-contained Codex plugin copy | No, generated |
| `plugins/boltz-mcpb/` | Self-contained MCPB plugin copy | No, generated |

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

The MCPB surface has both a development tree under `surfaces/mcpb/` and a
generated copy under `plugins/boltz-mcpb/` because the MCPB packer consumes a
self-contained runtime tree.

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

Do not edit `plugins/boltz/`, `plugins/boltz-compute-cli/`, or
`plugins/boltz-mcpb/` directly. CI regenerates them and fails if the committed
copies are stale. A branch push workflow also regenerates them and commits the
generated result back to development branches when needed.

## Packaging And Release

Build the distributable artifacts:

```bash
./scripts/package-plugins.sh   # writes Claude/Codex/Gemini zips and
                               # boltz-mcpb-<version>.mcpb into dist/
```

CI (`.github/workflows/release.yml`) runs these on every tagged release and
attaches the artifacts to the GitHub Release.

For the Claude Desktop MCPB surface, run its tests before packaging:

```bash
cd surfaces/mcpb
npm install
npm test
cd ../..
scripts/generate-surfaces.sh
scripts/package-plugins.sh
```

## Distribution

### Claude Code

The repo root is also a Claude Code marketplace named `boltz-marketplace`,
publishing one installable plugin (`boltz`) backed by `plugins/boltz`. Submit
updates to the Claude Code plugin directory at
<https://claude.ai/settings/plugins/submit>.

### Codex (`openai/plugins`)

The official Codex plugin copy is generated under `plugins/boltz-compute-cli/`,
with symlinks dereferenced, matching the layout used by `openai/plugins` entries
such as Netlify and Cloudflare. To submit, copy `plugins/boltz-compute-cli/`
into that repo's `plugins/` directory and add the marketplace entry:

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

### Gemini CLI

`surfaces/gemini-cli/` is source-only here. For public distribution it is
mirrored into a dedicated install repo with symlinks dereferenced and
`gemini-extension.json` at the repo root:

```bash
RELEASE_REPO=boltz-bio/boltz-gemini-cli scripts/release-gemini-repo.sh
```

### Pre-submission checklist (per surface)

Privacy policy URL, 512×512 icon, screenshots, support contact, verified
metadata, and license confirmation for any bundled binaries.

## Legacy

`skills-python/` and `codex-plugin-python/` are legacy Python-SDK-based variants.
They predate the `core/` restructure and remain as references, not as
distribution targets.
