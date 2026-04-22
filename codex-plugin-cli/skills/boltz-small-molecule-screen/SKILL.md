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
6. Launch `download-results` with Codex's background/non-blocking command facility — it polls, paginates `list-results`, downloads every per-hit structure, and exits when terminal. After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.
7. When done, rank results by `optimization_score` descending (fallback `binding_confidence`), report the top 5–10 hits with `smiles` + key metrics, and point the user at `$ROOT/$IDEM/results/`.

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

# Start this command in Codex background/non-blocking mode.
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30 \
  --verbose
# → $ROOT/$IDEM/results/<pres_*>/...
```

Payload keys in `payload.yaml` are `molecules`, `target`, `molecule_filters` — the API body field names, not the CLI flag names `--molecule` / `--target` / `--molecule-filters`.

## Always Do This

- Use `--input @yaml://` for object bodies; never `@file://` or `@./` (errors opaquely).
- Treat pocket residue indices as 0-based.
- Do not invent medicinal-chemistry filters. Only add `molecule_filters` if the user asks; mention the catalog as an option.
- Use the same slug as both `--idempotency-key` at submit and `--name` on `download-results` so re-runs resume via `.boltz-run.json`.
- Prefer Codex's background/non-blocking command mode for `download-results`. After the background session starts, do not wait on it or poll it. Report the job ID, run name, output directory, and that Codex should notify when the background command completes.
- If Codex background mode is unavailable or blocks the conversation, use the detached fallback: `nohup boltz-api download-results ... > "$ROOT/$IDEM/download-results.log" 2>&1 < /dev/null &`, then write the PID to `$ROOT/$IDEM/download-results.pid`.
- Only check status when the user asks. Use the background session notification/output if available, or read `download-results.log` for detached fallback runs. Never run a manual poll loop.
- Cost is $0.025 per molecule — quote the exact number from `estimate-cost` before submitting.
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

Per-result metrics to rank on: `optimization_score` (primary), `binding_confidence`, `structure_confidence`, `complex_plddt`, `complex_iplddt`, `iptm`, `ptm`. Each result also carries `external_id` (your input `id`) and `smiles`.
