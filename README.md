# Boltz Skills

Run Boltz biomolecular workflows — structure prediction, binding, molecular and
protein screening, and de novo design — directly from your AI coding agent.
The skills shell out to the [`boltz-api`](https://install.boltz.bio) CLI to
create inputs, estimate cost, submit jobs, and download results.

📖 **Full guide:** [Agent integrations for the Boltz API](https://api.boltz.bio/docs/guides/agent-integrations/)

## Supported agents

| Agent | How it's delivered |
|---|---|
| **Claude Code** | Plugin (`boltz`) installed from a marketplace |
| **Codex** | Plugin (`boltz`) installed from a marketplace |
| **Gemini CLI / Antigravity** | CLI extension |
| **Claude Desktop** | Local MCP server (`.mcpb` bundle) |

Every surface runs the same workflows through the `boltz-api` CLI.

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

### Claude Code

```bash
claude plugin marketplace add boltz-bio/boltz-api-skills
claude plugin install boltz@boltz-marketplace --scope user
```

### Codex

```bash
codex plugin marketplace add boltz-bio/boltz-api-skills
codex plugin add boltz@boltz-marketplace
```

### Gemini CLI / Antigravity

```bash
gemini extensions install https://github.com/boltz-bio/boltz-gemini-cli
# Antigravity:
agy plugin install https://github.com/boltz-bio/boltz-gemini-cli
```

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

## Local development

Contributions are welcome — outside PRs included. Clone the repo and try the
plugin without a persistent install:

```bash
claude --plugin-dir ./surfaces/claude-code-cli
```

The repo is organized as shared source plus per-agent surfaces:

- `core/` — shared skill workflows (`core/skills/cli/`) and API reference docs
  (`core/references/`), symlinked into each surface. **Edit here** for changes
  that apply to every agent.
- `surfaces/<agent>/` — per-agent packaging and host-specific files
  (`claude-code-cli`, `codex-cli`, `gemini-cli`, `mcpb`). **Edit here** for
  changes specific to one host.
- `plugins/` — self-contained, installable copies. **Generated — do not edit.**

After editing `core/` or a surface, regenerate the installable copies:

```bash
scripts/generate-surfaces.sh
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full development, testing, and
release workflow.

## License

MIT — see [`LICENSE`](LICENSE).
