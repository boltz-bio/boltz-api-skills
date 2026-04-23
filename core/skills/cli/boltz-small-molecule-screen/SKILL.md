---
name: boltz-small-molecule-screen
description: Score a user-supplied SMILES library against a protein target with the Boltz Compute API and return ranked binding and structure metrics with per-hit structures. TRIGGER when the user wants to virtually screen, dock, or rank an existing compound library against a target. Not for designing new molecules and not for a single one-off docking pose.
---

## Workflow

Use this skill when the user already has candidate molecules.

1. Normalize the library from raw SMILES, a CSV (auto-detect the SMILES column), `.smi`, or `.txt` into the `molecules` list. Each entry is `{smiles, id?}`; the optional `id` is echoed back as `external_id` on each result.
2. Normalize the target: one or more protein sequences into `target.entities`, plus optional `pocket_residues` (0-based) and/or `reference_ligands` (SMILES of known binders to seed pocket detection).
3. Keep default server-side filtering unless the user asks for custom filters — only add `molecule_filters` on explicit request.
4. Author the payload YAML, run `estimate-cost`, show the user the USD cost, wait for explicit confirmation.
5. `start` to submit (synchronous). Capture the ID.
6. Launch `download-results` with the agent runtime's background/non-blocking command facility (Claude Code: `run_in_background: true` on Bash; Codex: background shells) — it polls, paginates `list-results`, downloads every per-hit structure, and exits when terminal. After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.
7. When done, rank via `boltz-api small-molecule:library-screen list-results --id "$ID" --format jsonl`. **Do not** try to rank from the per-hit `metrics.json` files on disk: they currently carry `external_id: null` / `smiles: null`, so you can't map scores back to your input library from disk alone. `list-results` returns `external_id`, `smiles`, and metrics together per hit. Sort by `binding_confidence` for hit discovery or `optimization_score` for lead optimization; these are parallel intents, not a fallback hierarchy. Report the top 5-10 hits with `smiles`, the chosen ranking metric, and key confidence metrics, then point the user at `$ROOT/$IDEM/results/`.

**Heads-up: the `results/<pres_*>/` directory count is usually less than `len(molecules)`.** Default server-side `molecule_filters` (SMARTS catalog at level `recommended`) silently drops candidates — the drop is not logged in `.boltz-run.json` or surfaced as a progress counter. Typical drop rate is 20–30% on generic drug libraries. `list-results` is the authoritative filtered list; if the user needs to know which input IDs were dropped, compute `input_ids - seen(external_id)` from the list-results output.

## Command Pattern

```bash
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}"
IDEM="sm-screen-<target>-<library>-v1"

boltz-api small-molecule:library-screen estimate-cost \
  --input @yaml://payload.yaml

ID=$(boltz-api small-molecule:library-screen start \
       --idempotency-key "$IDEM" \
       --input @yaml://payload.yaml \
       --raw-output --transform id)

# Launch this command in the agent runtime's background/non-blocking mode (e.g., Claude Code Bash with `run_in_background: true`, Codex background shell).
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30
# → $ROOT/$IDEM/results/<pres_*>/...
```

Payload keys in `payload.yaml` are `molecules`, `target`, `molecule_filters` — the API body field names, not the direct CLI flag names `--molecule` / `--target` / `--molecule-filters`.

## Always Do This

- Prefer one merged top-level payload via `--input @yaml://payload.yaml` for `estimate-cost` and `start`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides, such as `--target @yaml://target.yaml`, `--molecule-filters @json://filters.json`, or repeated `--molecule @json://mol-1.json` entries. Piped YAML / JSON on stdin also works, but it must use API body field names such as `molecules`, `target`, and `molecule_filters`. Never use `@file://` or `@./`.
- Treat pocket residue indices as 0-based.
- Do not invent medicinal-chemistry filters. Only add `molecule_filters` if the user asks; mention the catalog as an option.
- Use the same slug as both `--idempotency-key` at submit and `--name` on `download-results` so re-runs resume via `.boltz-run.json`.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. After the background session starts, do not wait on it or poll it. `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- If background mode is unavailable or blocks the conversation, use the detached fallback: `nohup boltz-api download-results ... > "$ROOT/$IDEM/download-results.log" 2>&1 < /dev/null &`, then write the PID to `$ROOT/$IDEM/download-results.pid`.
- Only check status when the user asks. Use the background session notification/output if available, or read `download-results.log` for detached fallback runs. Never run a manual poll loop.
- Cost is approximately $0.025 per molecule for small targets (may scale with complex size). `estimate-cost` returns the authoritative quote — always use it.
- Poll interval: `--poll-interval-seconds 30` is a reasonable default; libraries can run 10–60 min depending on size.

## Escape Hatch

- Upstream payload reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api small-molecule:library-screen start --help`

Read [references/api.md](references/api.md) for the `molecules`, `target`, and `molecule_filters` shapes, including the catalog of built-in SMARTS filters and RDKit descriptor ranges.

## Outputs

Under `$ROOT/$IDEM/`:

- `.boltz-run.json` — run metadata
- `results/<pres_*>/archive.tar.gz` and `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}` — one per scored molecule

Rank via `boltz-api small-molecule:library-screen list-results --id "$ID" --format jsonl` — it returns `external_id`, `smiles`, and metrics together per hit. The per-hit `metrics.json` files on disk have `external_id: null` / `smiles: null`, so ranking from on-disk files alone loses the input-library mapping (tracked as a CLI bug — see CLI_BUG_REPORT.md §7).

Per-result metrics (all 7 always present for sm:library-screen): `binding_confidence` — primary metric for **hit discovery**; `optimization_score` — for **lead-optimization** ranking (binding strength). These are parallel intents, not a primary/fallback hierarchy. Sort by whichever matches the user's goal. Also available: `structure_confidence`, `complex_plddt`, `complex_iplddt`, `iptm`, `ptm`.
