# partner-cli-skills

A self-contained, agent-agnostic skill bundle for the [`boltz-api`](https://api.boltz.bio/docs/api/cli/) CLI. Six workflow skills cover the Boltz Compute API endpoints; each skill is prose plus per-endpoint schema references.

This bundle is intended for partner companies who want to bring Boltz capabilities to their own agent harness. It makes no assumptions about which harness is hosting the skill — there are no Bash-tool-specific or shell-session-specific instructions.

## Audience

Partners running their own agent harness who need a drop-in description of the Boltz workflows. If you are an end user looking for an installable plugin for an off-the-shelf assistant, use the published plugin distributions instead.

## Assumptions

- `boltz-api` is already installed and available on `PATH` for the agent's command-execution environment.
- Authentication is provided via the `BOLTZ_API_KEY` environment variable.
- Cost estimation is not part of the per-run workflow. If the host wants pre-flight cost discovery, call `boltz-api <resource> estimate-cost --input @yaml://...` independently; the skills do not require it before submitting.
- The agent harness has some way to run a long-running command (a background or detached session) for the `download-results` poller. Each skill describes the contract; the harness chooses how to fulfill it.

## Skills

| Skill | Use when… |
|---|---|
| `boltz-structure-and-binding` | fold one defined complex; dock one ligand; get pTM/ipTM/binding_confidence for one system |
| `boltz-small-molecule-screen` | rank an existing SMILES library against a target |
| `boltz-small-molecule-design` | generate novel small-molecule binders for a target (no library yet) |
| `boltz-protein-screen` | rank an existing protein / peptide / antibody library against a target |
| `boltz-protein-design` | generate novel protein / peptide / antibody / nanobody binders for a target |
| `boltz-check-status` | list recent jobs, resume after a dropped session, recover results by job ID |

## Layout

```
partner-cli-skills/
└── skills/
    ├── boltz-structure-and-binding/
    │   ├── SKILL.md
    │   └── references/
    │       ├── api.md
    │       └── results.md
    ├── boltz-small-molecule-screen/
    ├── boltz-small-molecule-design/
    ├── boltz-protein-screen/
    ├── boltz-protein-design/
    └── boltz-check-status/
```

Each skill is self-contained: no symlinks, no shared layer, no plugin manifest. Drop the `skills/` directory into whatever skills directory the host harness expects.

## Authentication

```sh
export BOLTZ_API_KEY=<api-key>
```

Every `boltz-api` command resolves this from the environment. If a command fails with an authentication error, surface the failure to the user; do not attempt to re-authenticate from inside the agent.

## Output layout

Results land in `<output-root>/$RUN_NAME/`, where `<output-root>` is the absolute path passed to `download-results --root-dir`. If `--root-dir` is omitted, the CLI defaults to `boltz-experiments` under the command's starting directory. `$RUN_NAME` is a short descriptive slug the agent picks at submit time and re-uses on `download-results`. Re-running the same `download-results` command with the same `--name` resumes from the local checkpoint.

## Lifecycle

Each `start`-family skill follows the same flow:

1. Agent normalizes the user's inputs and authors a YAML or JSON payload.
2. Submit with `boltz-api <resource> start --input @yaml:///absolute/path/payload.yaml --idempotency-key <run-name> --raw-output --transform id`. The command prints a job ID.
3. Launch `boltz-api download-results --id <job-id> --name <run-name> --root-dir <output-root>` as a long-running command in whatever background/detached mode the host harness provides.
4. Report the job ID, run name, and output directory to the user. Do not poll.
5. If the user later asks for progress, prefer `boltz-api --format json download-status --name <run-name> --root-dir <output-root>` for local checkpoint state, or peek at the host's saved background-session output if it captured the JSONL stderr stream.

## Schema escape hatch

If an agent encounters a payload field not covered in `references/api.md`, the upstream sources of truth are:

- API guides and payload examples: <https://api.boltz.bio/docs>
- Python SDK/API reference: <https://api.boltz.bio/docs/api/python/>
- CLI flags: `boltz-api <resource> start --help` (flag names only — not a schema source)
