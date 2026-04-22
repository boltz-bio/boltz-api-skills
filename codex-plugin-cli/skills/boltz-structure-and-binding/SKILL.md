---
name: boltz-structure-and-binding
description: Predict the 3D structure of a protein, RNA, DNA, or ligand complex with the Boltz Compute API and optionally score binding. TRIGGER when the user asks to fold a complex, dock a ligand, predict an interface, generate a CIF or PDB for a defined system, or get structure and binding metrics for one specified complex. Not for screening libraries or designing new molecules.
---

## Workflow

Use this skill for one defined complex, not a library workflow.

1. Normalize the inputs into `entities`: proteins, RNA, DNA, ligand SMILES, or ligand CCD codes. Chain IDs go in entity order (`A`, `B`, `C`, …) unless the user specifies otherwise.
2. If the user wants binding metrics, add a `binding` block and pick the right variant (`ligand_protein_binding` for a single ligand binder chain, otherwise `protein_protein_binding`).
3. Only add `constraints` / `bonds` / `modifications` / `model_options` if the user asks.
4. Author the payload YAML, run `estimate-cost`, show the USD cost, wait for explicit confirmation.
5. `start` to submit (synchronous). Capture the ID.
6. Launch `download-results` with Codex's background/non-blocking command facility so polling + download continue without blocking the Codex session. After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.

## Command Pattern

```bash
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}"
IDEM="sab-<target>-<ligand>-v1"    # short descriptive slug

# 1. estimate
boltz-api predictions:structure-and-binding estimate-cost \
  --model boltz-2.1 \
  --input @yaml://payload.yaml

# 2. confirm with user, then submit
ID=$(boltz-api predictions:structure-and-binding start \
       --model boltz-2.1 \
       --idempotency-key "$IDEM" \
       --input @yaml://payload.yaml \
       --raw-output --transform id)

# 3. Start this command in Codex background/non-blocking mode.
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 10 \
  --verbose
# → $ROOT/$IDEM/outputs/archive.tar.gz, .boltz-run.json
```

## Always Do This

- Use `--input @yaml://payload.yaml` or `@json://payload.json`. Never `@./payload.yaml` or `@file://` — those error opaquely on object-typed flags.
- Residue indices are 0-based wherever the payload asks for residue positions (constraints, modifications, contact tokens).
- For CIF/PDB bytes embedded in `--target` / `structure.data`, use `@data:///absolute/path/file.cif` — it sniffs binary and base64-encodes. Don't use bare `@path` for binary data.
- Use the same slug as both `--idempotency-key` at submit time and `--name` at download time so re-runs are idempotent and resume from `.boltz-run.json`.
- Prefer Codex's background/non-blocking command mode for `download-results`. After the background session starts, do not wait on it or poll it. Report the job ID, run name, output directory, and that Codex should notify when the background command completes.
- If Codex background mode is unavailable or blocks the conversation, use the detached fallback: `nohup boltz-api download-results ... > "$ROOT/$IDEM/download-results.log" 2>&1 < /dev/null &`, then write the PID to `$ROOT/$IDEM/download-results.pid`.
- Only check progress when the user asks. Use the background session notification/output if available, or read `download-results.log` for detached fallback runs. Do not loop `retrieve` yourself.
- Poll interval: keep `--poll-interval-seconds 10` for SAB — predictions usually finish in under a few minutes.

## Escape Hatch

For anything not covered in `references/api.md`:

- Upstream request body reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api predictions:structure-and-binding start --help` (schema details aren't there — just flag names and types)

Read [references/api.md](references/api.md) for entity shapes, binding variants, bonds, constraints, model options, and output metrics.

## Outputs

Under `$ROOT/$IDEM/`:

- `.boltz-run.json` — run metadata, cursor, idempotency key
- `outputs/archive.tar.gz` — unpacks to `prediction/{metrics.json, sample_*_predicted_structure.cif, sample_*_pae.npz}`

Useful metrics in `metrics.json`: `pLDDT`, `pTM`, `ipTM`, `PDE`, `ipDE`, `structure_confidence`, and when `binding` was requested, `binding_confidence` + `optimization_score`. Summarize these for the user and point them at the CIF path.

## SAB 400 validation quirk

If the server rejects the payload with only `{"code": "VALIDATION_ERROR", "message": "Request validation failed"}` and no field-level details, inspect the `entities`, `binding`, and `constraints` blocks carefully — `predictions:structure-and-binding` is the one endpoint that currently omits `details`. The other four endpoints return specific field paths.
