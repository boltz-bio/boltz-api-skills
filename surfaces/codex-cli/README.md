# boltz-compute-cli (Codex plugin)

Six Codex skills that drive the [`boltz-api`](https://docs.boltz.bio/api-reference/api-cli-reference.md) Go CLI for the Boltz Compute API. No Python runtime, no SDK install, no wrapper scripts — each skill is workflow prose plus a per-endpoint schema reference. The agent authors a YAML payload and calls `boltz-api` directly.

## Prerequisites

- `boltz-api` on `PATH` (the Stainless-generated Go CLI; `boltz-api --version` should report ≥ `0.7.0`)
- `BOLTZ_COMPUTE_API_KEY` exported in the environment
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR` to override where results land (default: `./boltz-experiments/`)

The skills assume these are already configured and do not preflight-check them. If the CLI is missing or the key is invalid, `boltz-api` will error readably and the agent will relay the message.

## Skills

| Skill | Use when… |
|---|---|
| `boltz-structure-and-binding` | fold one defined complex; dock one ligand; get pTM/ipTM/binding_confidence for one system |
| `boltz-small-molecule-screen` | rank an existing SMILES library against a target |
| `boltz-small-molecule-design` | generate novel small-molecule binders for a target (no library yet) |
| `boltz-protein-screen` | rank an existing protein / peptide / antibody library against a target |
| `boltz-protein-design` | generate novel protein / peptide / antibody / nanobody binders for a target |
| `boltz-check-status` | list recent jobs, resume after a crashed session, recover results by ID |

## Installation

From a Codex session:

```
/plugins add <path-to-this-directory>
```

Or configure in your Codex plugin config. The plugin registers the six skills; the agent picks the right one based on your request.

## Lifecycle

Each `start`-family skill follows the same flow:

1. Agent normalizes your inputs and authors a YAML payload.
2. `boltz-api <resource> estimate-cost` — shows you the USD cost.
3. You confirm.
4. Submit with `boltz-api <resource> start --input @yaml://payload.yaml ...`. For the four design/screen endpoints, prefer one merged `--input` payload and keep `--idempotency-key` / `--workspace-id` top-level. Piping YAML / JSON on stdin still works, but the body must use API field names such as `molecules`, `proteins`, `target`, or `binder_specification`.
5. `boltz-api download-results --id $ID --name $IDEM --root-dir $ROOT ...` — runs in the background; polls + downloads. It now emits machine-readable JSONL progress events on stderr by default and checkpoints local state in `.boltz-run.json`.
6. Agent answers "how's it going?" either by peeking those JSONL progress events or by calling `boltz-api --format json download-status --name $IDEM --root-dir $ROOT` for a local-only checkpoint snapshot.

Results land in `$ROOT/$IDEM/` where `$ROOT = ${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}` and `$IDEM` is a short descriptive slug the agent picks (e.g. `kras-g12d-enamine-v1`). Re-running the same `download-results` command with the same `--name` resumes from where it left off — this is the crash-recovery path for dropped sessions. `boltz-check-status` wraps the recovery flow when you only have the job ID.

## Escape hatch

If an agent hits a schema it doesn't recognize, the canonical upstream refs are:

- Payload shapes: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flags: `boltz-api <resource> start --help` (flag names only — the help text is not a schema source)

## Differences from `codex-plugin-python/`

The Python version shipped a ~300-line `scripts/query.py` wrapper per skill that handled polling, download, and payload assembly via the `boltz-compute` Python SDK. The CLI now does all of that natively, so this plugin drops the wrappers entirely. Frontmatter / descriptions are retained verbatim — the trigger matching is already tuned.
