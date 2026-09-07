# Contributing

## Source Of Truth

The public skills live in `skills/`. Vercel Skills discovers this directory
before generated marketplace packages and the legacy variants.

| Path | Role | Edit directly? |
|---|---|---|
| `skills/<name>/` | Public skill, references, scripts, and `agents/openai.yaml` | Yes |
| `surfaces/claude-code-cli/` | Claude marketplace wrapper | Yes, except its `skills` link |
| `surfaces/codex-cli/` | Codex marketplace wrapper and plugin assets | Yes, except its `skills` link |
| `surfaces/gemini-cli/` | Gemini extension and context | Yes, except its `skills` link |
| `surfaces/mcpb/` | Claude Desktop MCP server | Yes |
| `surfaces/partner-cli-skills/` | Partner bundle with distinct host-managed policies | Yes |
| `plugins/` | Self-contained marketplace and MCPB copies | No, generated |
| `tests/` | Distribution and protein-design helper tests | Yes |
| `legacy/` | Historical Python SDK variants | Reference only |

Keep each public skill self-contained. Put references and executable helpers
inside its directory. Keep helper tests under `tests/` so Skills does not
install them. Preserve skill names and existing `agents/openai.yaml` metadata.

The three CLI wrappers each have one `skills` symlink to the canonical tree.
`scripts/generate-surfaces.sh` dereferences those links for marketplace caches.
The MCPB generator copies the tree into `guidance/skills/`, including each
skill's references. The development MCP server reads `skills/` directly.

The partner bundle is separate: its host provides authentication and spending
policy. Do not substitute it for the public skills. Historical SDK variants
remain under `legacy/`; they are not distribution targets.

## Local Workflow

Use Node.js 22.20 or newer for the pinned Skills CLI and distribution tests.
The distribution checks also use Bash, rsync, and jq.
Run from the repository root:

```sh
npm ci
scripts/generate-surfaces.sh
npm test
scripts/verify-generated.sh
```

`npm test` checks canonical references, marketplace package contents, and
Skills installation in temporary projects for Claude Code, Codex, and Gemini
CLI. It checks both copy and symlink installation. It does not require agent
logins or submit Boltz jobs. Run only installer checks with
`npm run test:install`. Update the pinned `skills` development dependency and
lockfile together when adopting a new installer version.

For MCP runtime changes:

```sh
npm ci --prefix surfaces/mcpb
npm test --prefix surfaces/mcpb
```

For protein-design helper changes, use a local virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r skills/boltz-protein-design/scripts/requirements.txt
.venv/bin/python -m unittest discover -s tests/protein-design -v
```

To preview the public skill catalog:

```sh
npx skills add . --list
```

For Claude plugin development without persistent installation:

```sh
claude --plugin-dir ./surfaces/claude-code-cli
```

For Gemini extension development:

```sh
gemini extensions link ./surfaces/gemini-cli
```

## Generated Files

Do not edit `plugins/boltz/`, `plugins/boltz-api-cli/`, or
`plugins/boltz-mcpb/` directly. CI generates temporary copies and fails if their
contents differ from the committed copies. Verification does not modify the
working tree. A branch push workflow also regenerates them and commits the
generated result back to development branches when needed.

## Packaging And Release

Build the distributable artifacts:

```bash
./scripts/package-plugins.sh   # writes Claude/Codex/Gemini zips and
                               # boltz-mcpb-<version>.mcpb into dist/
npm run test:packages          # checks every skill and loads packaged MCP guidance
```

CI (`.github/workflows/release.yml`) runs these on every tagged release and
attaches the artifacts to the GitHub Release.

### Monorepo surface releases

Claude Code and Codex use monorepo-native per-surface releases:

1. A source change lands on `main` under shared CLI skill source
   (`skills/`) or under a Claude/Codex surface.
2. `.github/workflows/surface-auto-bump.yml` opens a release-bump PR using the
   existing `boltz-mcpb-publisher` GitHub App token.
3. The bump PR updates the affected surface manifest version(s), runs
   `scripts/generate-surfaces.sh`, and commits the generated plugin copies.
4. When the bump PR merges, `.github/workflows/surface-release.yml` creates one
   GitHub Release per bumped surface in this repo:

| Surface | Version source | Artifact | Tag format |
|---|---|---|---|
| Claude Code plugin | `surfaces/claude-code-cli/.claude-plugin/plugin.json` | `dist/claude-code-cli-<version>.zip` | `claude-code-plugin/v<version>` |
| Codex plugin | `surfaces/codex-cli/.codex-plugin/plugin.json` | `dist/boltz-api-cli-<version>.zip` | `codex-plugin/v<version>` |

Use workflow dispatch on `surface-auto-bump.yml` for manual patch/minor/major
bumps, or on `surface-release.yml` to recreate a release for the current
manifest version when needed. Include `[skip-surface-bump]` in a merge commit
message to suppress the automatic bump PR for a particular merge.

MCPB and Gemini still have their historical public-repo sync workflows:
`mcpb-public-sync.yml` mirrors to `boltz-bio/boltz-mcpb`, and
`gemini-public-sync.yml` mirrors to `boltz-bio/boltz-gemini-cli`. The same
monorepo pattern can absorb them later by adding their manifest paths and
artifacts to `surface-auto-bump.yml` and `surface-release.yml`, then retiring
the public-repo syncs.

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

### Vercel Skills (primary)

Users install directly from this repository with
`npx skills add boltz-bio/boltz-api-skills`. Shared changes are available from
`main` after merge; they do not wait for a marketplace version-bump PR. The
installer's version is separate from the skill source revision. The existing
Claude Code and Codex marketplaces remain first-class distribution channels.
Keep their manifests, generated packages, validation, and release workflows
working when changing the canonical skills. The Gemini extension also remains
supported.

### Claude Code

The repo root is also a Claude Code marketplace named `boltz-marketplace`,
publishing one installable plugin (`boltz`) backed by `plugins/boltz`. Submit
updates to the Claude Code plugin directory at
<https://claude.ai/settings/plugins/submit>.

### Codex (`openai/plugins`)

The official Codex plugin copy is generated under `plugins/boltz-api-cli/`,
with symlinks dereferenced, matching the layout used by `openai/plugins` entries
such as Netlify and Cloudflare. To submit, copy `plugins/boltz-api-cli/`
into that repo's `plugins/` directory and add the marketplace entry:

```json
{
  "name": "boltz-api-cli",
  "source": {
    "source": "local",
    "path": "./plugins/boltz-api-cli"
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

`legacy/skills-python/` and `legacy/codex-plugin-python/` are historical Python
SDK variants. They remain as references, not as distribution targets.
