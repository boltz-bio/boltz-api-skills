---
name: boltz-small-molecule-screen
description: Score a user-supplied SMILES library against a protein target with the Boltz Compute API and return ranked binding and structure metrics with per-hit structures. TRIGGER when the user wants to virtually screen, dock, or rank an existing compound library against a target. Not for designing new molecules and not for a single one-off docking pose.
---

## Workflow

If `boltz-api` is missing from `PATH`, use `boltz-api-cli` for install/update guidance before retrying.
If a command reports missing or expired authentication, use `boltz-api-cli` to start `boltz-api auth login --device-code` before retrying; do not ask permission first.
If the agent host sandbox blocks `boltz-api` install/auth/API calls, use `boltz-api-cli` to set workspace-local `HOME`, `TMPDIR`, `BOLTZ_API_INSTALL_DIR`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` before retrying. Request the host sandbox bypass only if workspace-local state still fails.

Use this skill when the user already has candidate molecules.

1. Normalize the library from raw SMILES, a CSV (auto-detect the SMILES column), `.smi`, or `.txt` into the `molecules` list. Each entry is `{smiles, id?}`; the optional `id` is echoed back as `external_id` on each result.
2. Normalize the target: one or more protein sequences into `target.entities`, plus optional `pocket_residues` (0-based) and/or `reference_ligands` (SMILES of known binders to seed pocket detection).
3. Keep default server-side filtering unless the user asks for custom filters — only add `molecule_filters` on explicit request.
4. Author the payload YAML or JSON, run `estimate-cost`, show the user the USD cost, wait for explicit confirmation.
5. `start` to submit (synchronous). Capture the ID.
6. Launch `download-results` with the agent runtime's background/non-blocking command facility — it polls, paginates `list-results`, downloads every per-hit structure, and exits when terminal. In Claude Code, use Bash with `run_in_background: true`. In Codex, run `download-results` as a foreground shell command with `yield_time_ms: 1000`; if Codex returns a `session_id`, keep it for optional later polling. After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.
7. When done, rank from `$ROOT/$RUN_NAME/results/index.jsonl`. `download-results` builds this local manifest from `list-results` and adds local artifact paths, so it has `external_id`, `smiles`, `metrics`, and `paths` together per scored molecule. Sort by `binding_confidence` for hit discovery or `optimization_score` for lead optimization; these are parallel intents, not a fallback hierarchy. Report the top 5-10 hits with `smiles`, the chosen ranking metric, key confidence metrics, and structure path. Use `boltz-api small-molecule:library-screen list-results --id "$ID" --format jsonl` only when no local download manifest is available or the user asks for fresh remote results.

**Heads-up: the `results/<pres_*>/` directory count is usually less than `len(molecules)`.** Default server-side `molecule_filters` (SMARTS catalog at level `recommended`) can drop candidates before scoring. The drop is not logged in `.boltz-run.json` or surfaced by `download-status`; `run.json` may include `progress.rejection_summary` after `download-results` refreshes remote run metadata. `results/index.jsonl` is the authoritative local scored list after download; if the user needs to know which input IDs were dropped, compute `input_ids - seen(external_id)` from that manifest.

## Command Pattern

```bash
WORKDIR="$(pwd)"
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-$WORKDIR/boltz-experiments}"
RUN_NAME="sm-screen-<target>-<library>-v1"
PAYLOAD="$WORKDIR/payload.yaml"

boltz-api small-molecule:library-screen estimate-cost \
  --input "@yaml://$PAYLOAD"

ID=$(boltz-api small-molecule:library-screen start \
       --idempotency-key "$RUN_NAME" \
       --input "@yaml://$PAYLOAD" \
       --raw-output --transform id)

# Launch this command in the agent runtime's background/non-blocking mode.
# Claude Code: Bash with run_in_background=true.
# Codex: foreground shell command with yield_time_ms=1000; keep the returned session_id if one is provided.
# Do not append "&" or use nohup in Codex.
boltz-api download-results \
  --id "$ID" --name "$RUN_NAME" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30
# → $ROOT/$RUN_NAME/results/<pres_*>/...
```

Payload keys are `molecules`, `target`, `molecule_filters` — the API body field names, not the direct CLI flag names `--molecule` / `--target` / `--molecule-filters`.

## Always Do This

- Keep payload field names exactly as the API body names shown in `references/api.md`.
- Use absolute paths for `ROOT`, payload files, and embedded target files. Do not `cd "$ROOT/$RUN_NAME"` for follow-up commands; pass `--root-dir "$ROOT"` and use absolute paths so later relative paths do not drift.
- Prefer one merged top-level payload via `--input @yaml:///absolute/path/payload.yaml` or `@json:///absolute/path/payload.json` for `estimate-cost` and `start`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides, such as `--target @yaml:///absolute/path/target.yaml`, `--molecule-filters @json:///absolute/path/filters.json`, or repeated `--molecule @json:///absolute/path/mol-1.json` entries. Piped YAML / JSON on stdin also works, but it must use API body field names. Never use `@file://` or `@./`.
- Treat pocket residue indices as 0-based.
- Do not invent medicinal-chemistry filters. Only add `molecule_filters` if the user asks; mention the catalog as an option.
- Use the same slug as both `--idempotency-key` at submit and `--name` on `download-results` so re-runs resume via `.boltz-run.json`.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. In Codex specifically, keep `download-results` in the foreground and set the shell tool yield to 1000 ms; Codex will return a `session_id` if the command is still running. Do not append `&` or use `nohup` in Codex because the tool runner may clean up shell-backgrounded descendants before `.boltz-run.json` is fully written.
- After the background/session starts, do not wait on it or poll it. `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- Only check status when the user asks. In Codex, poll the saved session with an empty `write_stdin`, or prefer `boltz-api --format json download-status --name "$RUN_NAME" --root-dir "$ROOT"` for structured local checkpoint state. Never run a manual poll loop.
- If detached download needs to be restarted, re-run `boltz-api download-results` with the same `--name "$RUN_NAME"` and the same `--root-dir`.
- Cost is approximately $0.025 per molecule for small targets (may scale with complex size). `estimate-cost` returns the authoritative quote — always use it.
- Poll interval: `--poll-interval-seconds 30` is a reasonable default; libraries can run 10–60 min depending on size.

## Escape Hatch

- Upstream payload reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api small-molecule:library-screen start --help`

Read [references/api.md](references/api.md) for the `molecules`, `target`, and `molecule_filters` shapes, including the catalog of built-in SMARTS filters and RDKit descriptor ranges.

## Outputs

Under `$ROOT/$RUN_NAME/`:

- `.boltz-run.json` — run metadata
- `run.json` — sanitized remote run record; check `progress.rejection_summary` for filtered/invalid counts when present
- `results/index.jsonl` — one scored molecule per line, with `external_id`, `smiles`, `metrics`, and local `paths`
- `results/<pres_*>/metadata.json` — per-result metadata copied from the list-results record
- `results/<pres_*>/archive.tar.gz` and `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}` — per-scored-molecule artifacts

Rank from `results/index.jsonl` after `download-results`. The extracted per-hit `files/result/metrics.json` files are engine metrics only and do not include input-library mapping fields; use `results/index.jsonl` or `results/<pres_*>/metadata.json` for `external_id` and `smiles`.

Per-result metrics (all 7 always present for sm:library-screen): `binding_confidence` — primary metric for **hit discovery**; `optimization_score` — for **lead-optimization** ranking (binding strength). These are parallel intents, not a primary/fallback hierarchy. Sort by whichever matches the user's goal. Also available: `structure_confidence`, `complex_plddt`, `complex_iplddt`, `iptm`, `ptm`.
