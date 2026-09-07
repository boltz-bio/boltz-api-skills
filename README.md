# Boltz Skills

Run Boltz biomolecular workflows — structure prediction, binding, molecular and
protein screening, and de novo design — directly from your AI coding agent.
The skills shell out to the [`boltz-api`](https://install.boltz.bio) CLI to
create inputs, estimate cost, submit jobs, and download results.

📖 **Full guide:** [Agent integrations for the Boltz API](https://api.boltz.bio/docs/guides/agent-integrations/)

## Supported agents

For Codex and Claude Code, use the official marketplace plugins. Gemini CLI
has a native extension, and Claude Desktop uses the MCPB server.
[Vercel Skills](https://github.com/vercel-labs/skills) provides an additional
way to install the shared skills in Antigravity and other supported agents,
or in environments where you prefer a direct skill installation.

## Skills

| Skill | What it does |
|---|---|
| `boltz-cli-setup` | Install, update, verify, and authenticate the `boltz-api` CLI. |
| `boltz-structure-and-binding` | Predict the 3D structure of a defined complex; optionally score binding. |
| `boltz-small-molecule-screen` | Rank a SMILES library against a target. |
| `boltz-small-molecule-design` | Generate novel small-molecule binders. |
| `boltz-small-molecule-adme` | Estimate Tier-1 ADME (solubility, permeability, logD) from bare SMILES. |
| `boltz-protein-screen` | Rank proteins / peptides / antibodies against a target. |
| `boltz-protein-design` | Generate novel peptide / antibody / nanobody / custom-protein binders. |
| `boltz-check-status` | List and inspect jobs; recover results after an interrupted session. |

## Prerequisites

All surfaces need the `boltz-api` CLI on your `PATH`.

**macOS and Linux:**

```sh
curl -fsSL https://install.boltz.bio/boltz-api/install.sh | sh
```

**Windows PowerShell:**

```powershell
irm https://install.boltz.bio/boltz-api/install.ps1 | iex
```

Verify it:

```sh
boltz-api --version
```

Then authenticate, using either device-code login or an API key:

```sh
boltz-api auth login --device-code
# or
export BOLTZ_API_KEY="your-api-key"
```

Results download to a `boltz-experiments/` directory in your working directory
(created automatically). Point any command at a different location with
`--root-dir`.

## Install

### Codex and Claude Code (recommended: official plugins)

For Codex, open the plugin directory, search for **Boltz**, and install the
official plugin. In Codex CLI, enter `/plugins` to open the plugin browser.
Start a new session after installing. See the
[Codex installation guide](surfaces/codex-cli/README.md) for details.

For Claude Code, follow the
[marketplace installation guide](surfaces/claude-code-cli/README.md).

Both plugins use `boltz-api`; complete the prerequisites above or ask for
`boltz-cli-setup`.

### Other agents and direct skill installation

Use [Vercel Skills](https://github.com/vercel-labs/skills) with Node.js 22.20 or
newer. Select your agents and skills interactively:

```sh
npx skills add boltz-bio/boltz-api-skills
```

For example, install all eight skills for Gemini CLI in the current project:

```sh
npx skills add boltz-bio/boltz-api-skills --skill '*' --agent gemini-cli
```

Add `--global` to make the skills available across projects. Use `--list` to
preview the available skills without installing. Use `--copy` if your host
cannot use symlinks. Skills installation does not install or authenticate the
`boltz-api` CLI; complete the prerequisites above or ask for `boltz-cli-setup`.

Use one installation method per agent and scope to avoid loading the same
skills twice. Direct Skills installation is optional for Codex and Claude
Code; existing marketplace users can keep their plugin installation.

### Gemini extension

Gemini CLI users can also use the
[native extension](surfaces/gemini-cli/README.md).

### Claude Desktop

Download the latest `boltz-mcpb-<version>.mcpb` from
[Releases](https://github.com/boltz-bio/boltz-api-skills/releases) and install it
via **Settings → Extensions → Advanced settings → Install Extension**.

Restart your agent after installing.

## Usage

Once installed and authenticated, just describe what you want in natural
language — the agent picks the right skill, builds the payload, shows you a cost
estimate before submitting, and downloads results when the job finishes. For
example:

> Predict the structure of this protein–ligand complex and score the binding affinity.

> Screen these 200 SMILES against my target and rank them.

See the [full guide](https://api.boltz.bio/docs/guides/agent-integrations/) for
detailed workflows and examples.

## Repository layout

- `skills/<name>/` — canonical public skills with instructions, references,
  optional helper scripts, and agent metadata.
- `surfaces/` — marketplace and extension wrappers and the Claude Desktop MCPB runtime.
  CLI wrappers link to `skills/`; the partner bundle retains its distinct
  host-managed authentication and spending policy.
- `plugins/` — generated, self-contained marketplace and MCPB copies.
- `tests/` — distribution checks and protein-design helper tests.

## Local development

Edit `skills/` for shared workflow changes. Then regenerate and verify the
marketplace and MCPB packages:

```sh
npm ci
scripts/generate-surfaces.sh
npm test
scripts/verify-generated.sh
```

The install tests use the pinned Skills CLI to install into temporary projects
for Claude Code, Codex, and Gemini CLI. They do not install into your agents or
submit Boltz jobs.

See [CONTRIBUTING.md](CONTRIBUTING.md) for runtime tests and release workflows.

## License

MIT — see [`LICENSE`](LICENSE).
