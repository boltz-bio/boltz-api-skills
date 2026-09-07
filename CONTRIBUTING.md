# Contributing

## Source Of Truth

The public skills live in `skills/`. Vercel Skills discovers this directory
before generated marketplace packages.

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

Keep each public skill self-contained. Put references and executable helpers
inside its directory. Keep helper tests under `tests/` so Skills does not
install them. Preserve skill names and existing `agents/openai.yaml` metadata.

Follow the [Agent Skills specification](https://agentskills.io/specification).
This open format is the source contract; Vercel Skills is an installer and
test dependency. Keep the skill content usable by other compatible clients.
The frontmatter name must match the directory name. Keep descriptions specific
about when to use the skill, and keep `SKILL.md` below 500 lines. Put detailed
schemas and result interpretation in references that the skill links to.
Document helper dependencies beside the scripts. Keep host-specific plugin
configuration in `surfaces/`; the portable skills must not require it.

The three CLI wrappers each have one `skills` symlink to the canonical tree.
`scripts/generate-surfaces.sh` dereferences those links for marketplace caches.
The MCPB generator copies the tree into `guidance/skills/`, including each
skill's references. The development MCP server reads `skills/` directly.

The partner bundle is separate: its host provides authentication and spending
policy. Do not substitute it for the public skills.

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

`npm test` checks required skill metadata, canonical references, marketplace package contents, and
Skills installation in temporary projects for Claude Code, Codex, and Gemini
CLI. It checks preview, selective installation, and both copy and symlink
installation. It does not require agent
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

### Channel priorities

Recommend the official OpenAI marketplace plugin for Codex and the Claude
Code marketplace plugin for Claude Code. Boltz maintains these partner
distribution channels alongside the shared skill source. Keep their
manifests, generated packages, validation, and release workflows working.
The Gemini extension and Claude Desktop MCPB remain separate packages.

### Vercel Skills (additional distribution)

Users install directly from this repository with
`npx skills add boltz-bio/boltz-api-skills`. Shared changes are available from
`main` after merge; they do not wait for a marketplace version-bump PR. The
installer's version is separate from the skill source revision. Use this
route for other supported agents or optional direct skill installations.
Do not direct existing Codex or Claude Code marketplace users to switch.

### Claude Code

The repo root is also a Claude Code marketplace named `boltz-marketplace`,
publishing one installable plugin (`boltz`) backed by `plugins/boltz`. Submit
updates to the Claude Code plugin directory at
<https://claude.ai/settings/plugins/submit>.

### Codex (`openai/plugins`)

Boltz already has a published plugin at
[`openai/plugins/plugins/boltz-api-cli`](https://github.com/openai/plugins/tree/main/plugins/boltz-api-cli)
and an entry in that repository's
[marketplace catalog](https://github.com/openai/plugins/blob/main/.agents/plugins/marketplace.json).
The display name is **Boltz**. Preserve the plugin ID `boltz-api-cli`.

The source wrapper is `surfaces/codex-cli/`. The generated, self-contained
copy is `plugins/boltz-api-cli/`, with symlinks dereferenced. It contains
CLI-backed skills and assets; it does not configure an MCP server.

To publish an update:

1. Merge the source changes and the Codex version-bump PR described above.
2. Confirm the `codex-plugin/v<version>` GitHub Release contains
   `boltz-api-cli-<version>.zip` and its checksum.
3. Use `plugins/boltz-api-cli/` from that release revision to prepare an
   update to the existing `plugins/boltz-api-cli/` directory in `openai/plugins`.
   Review differences against the published copy, including any
   marketplace-specific metadata and assets.
4. Preserve the existing catalog entry, installation and authentication
   policies, and reviewed category. Do not create a second Boltz entry.
5. Submit the update through the OpenAI partner publishing process. Verify
   the published version and installation after the update is accepted.

This repository automates generation and GitHub Releases. It does not
automatically submit or publish updates to `openai/plugins`. A merge here
can update direct Skills installs before the marketplace update is accepted.

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
