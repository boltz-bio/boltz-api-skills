# boltz-compute-cli (Codex plugin)

Seven Codex skills that drive the [`boltz-api`](https://docs.boltz.bio/api-reference/api-cli-reference.md) Go CLI for the Boltz Compute API. No Python runtime, no SDK install, no wrapper scripts — workflow skills are prose plus per-endpoint schema references, and `boltz-api-cli` covers CLI setup.

## Prerequisites

- `boltz-api` on `PATH` (the Stainless-generated Go CLI; `boltz-api --version` should report ≥ `0.7.0`)
- Authentication via `boltz-api auth login --device-code`, or `BOLTZ_COMPUTE_API_KEY` exported in the environment
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR` to override where results land. Prefer an absolute path; otherwise skills default to `$PWD/boltz-experiments/` from the command's starting directory.

The skills assume the CLI is already configured. If a command fails because auth is missing or expired, the agent should run `boltz-api auth login --device-code` on the user's behalf before retrying.
If the host sandbox blocks installer temp files or OAuth token access, first run the CLI with workspace-local `HOME`, `TMPDIR`, `BOLTZ_API_INSTALL_DIR`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` as described in `boltz-api-cli`. Request the host sandbox bypass only if workspace-local state still cannot access the network, temp files, credentials, or install path.

Verify the CLI is installed:

```sh
boltz-api --version
```

If `boltz-api` is not installed, install or update it from the official CLI repo:

macOS and Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/boltz-bio/boltz-compute-api-cli/main/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/boltz-bio/boltz-compute-api-cli/main/scripts/install.ps1 | iex
```

The installer updates an existing `boltz-api` on `PATH`. If no binary is found, it installs to `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\Boltz\bin` on Windows. Add that directory to `PATH` if `boltz-api --version` is still not found after install. Set `BOLTZ_API_INSTALL_DIR` before running the installer to choose a different install directory.

Important version note:

- This plugin assumes the newer Boltz CLI surface documented by the repo, including commands like `predictions:structure-and-binding estimate-cost`, merged `--input` payloads, top-level `download-results`, and `download-status`.
- If `boltz-api` reports errors like `No such command 'predictions:structure-and-binding'`, your local CLI is too old or is a different binary.
- OAuth/device-code login requires a newer `boltz-api` with the `auth` command family.

## Skills

| Skill | Use when… |
|---|---|
| `boltz-api-cli` | install, update, verify, or authenticate the `boltz-api` CLI |
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

Or configure in your Codex plugin config. The plugin registers the seven skills; the agent picks the right one based on your request.

## Lifecycle

Each `start`-family skill follows the same flow:

1. Agent normalizes your inputs and authors a YAML or JSON payload.
2. `boltz-api <resource> estimate-cost` — shows you the USD cost.
3. You confirm.
4. Submit with `boltz-api <resource> start --input @yaml:///absolute/path/payload.yaml ...`. For the four design/screen endpoints, prefer one merged `--input` payload and keep `--idempotency-key` / `--workspace-id` top-level. Piping YAML / JSON on stdin still works, but the body must use API field names such as `molecules`, `proteins`, `target`, or `binder_specification`.
5. `boltz-api download-results --id $ID --name $RUN_NAME --root-dir $ROOT ...` — run as a foreground Codex shell command with `yield_time_ms=1000`. If Codex returns a session id, keep it and return to the user; the CLI keeps polling + downloading in that managed session. It emits machine-readable JSONL progress events on stderr by default and checkpoints local state in `.boltz-run.json`.
6. Agent answers "how's it going?" either by polling the saved Codex session for JSONL output or by calling `boltz-api --format json download-status --name $RUN_NAME --root-dir $ROOT` for a local-only checkpoint snapshot.

Do not use shell `&`, terminal backgrounding, or `nohup` for `download-results` in Codex. Those detach mechanisms can be cleaned up by the tool runner before `.boltz-run.json` is fully written. Use Codex's managed long-running shell session instead.

Results land in `$ROOT/$RUN_NAME/` where `$ROOT = ${BOLTZ_COMPUTE_OUTPUT_DIR:-$PWD/boltz-experiments}` and `$RUN_NAME` is a short descriptive slug the agent picks (e.g. `kras-g12d-enamine-v1`). Keep `$ROOT` absolute and do not `cd "$ROOT/$RUN_NAME"` for follow-up commands; pass `--root-dir "$ROOT"` instead. Re-running the same `download-results` command with the same `--name` resumes from where it left off — this is the crash-recovery path for dropped sessions. `boltz-check-status` wraps the recovery flow when you only have the job ID.

## Why use the CLI variant

- The user can inspect and rerun every command the agent used.
- No local server has to be built, launched, or debugged.
- The CLI owns the long-running poll/download behavior, local `.boltz-run.json` checkpoint, JSONL progress stream, and `download-status` view.

## Escape hatch

If an agent hits a schema it doesn't recognize, the canonical upstream refs are:

- Payload shapes: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flags: `boltz-api <resource> start --help` (flag names only — the help text is not a schema source)

## Differences from `codex-plugin-python/`

The Python version shipped a ~300-line `scripts/query.py` wrapper per skill that handled polling, download, and payload assembly via the `boltz-compute` Python SDK. The CLI now does all of that natively, so this plugin drops the wrappers entirely. Frontmatter / descriptions are retained verbatim — the trigger matching is already tuned.
