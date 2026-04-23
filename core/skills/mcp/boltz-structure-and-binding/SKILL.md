---
name: boltz-structure-and-binding
description: Predict the 3D structure of a protein, RNA, DNA, or ligand complex with the Boltz Compute API and optionally score binding. TRIGGER when the user asks to fold a complex, dock a ligand, predict an interface, generate a CIF or PDB for a defined system, or get structure and binding metrics for one specified complex. Not for screening libraries or designing new molecules.
---

## Workflow

Use this skill for one defined complex, not a library workflow.

1. Normalize the inputs into `entities`. Each entity is **`{type, chain_ids, value}`** — note plural `chain_ids` (an array, even for one chain) and the field is `value`, **not** `sequence`:

   ```json
   {"entities": [{"type": "protein", "chain_ids": ["A"], "value": "MKTAYIAKQRQISFVKSHFSRQ"}]}
   ```

   `type` is one of `protein | rna | dna | ligand_smiles | ligand_ccd`. Chain IDs go in entity order (`A`, `B`, `C`, …) unless the user specifies otherwise. Read `references/api.md` for per-type field variants (`cyclic`, `modifications`, ligand CCD codes, etc.) **before** authoring your first payload — agent guesses like `sequence:` or `chain_id: "A"` (singular) fail with opaque 400s.
2. If the user wants binding metrics, add a `binding` block and pick the right variant (`ligand_protein_binding` for a single ligand binder chain, otherwise `protein_protein_binding`).
3. Only add `constraints` / `bonds` / `modifications` / `model_options` if the user asks.
4. Author the payload object, call `boltz_estimate_run` with `resource="predictions:structure-and-binding"` and `model="boltz-2.1"`, show the USD cost, and wait for explicit confirmation.
5. Call `boltz_submit_run` to submit. It starts detached `download-results` polling internally and returns the job ID, run name, and output directory.
6. After `boltz_submit_run` returns, report the job ID, run name, and output directory, then end the turn immediately. Do not run shell background commands yourself unless you're debugging the MCP server.

## MCP Tool Pattern

```text
ROOT = ${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}
RUN_NAME = "sab-<target>-<ligand>-v1"   # short descriptive slug

1. Estimate
   boltz_estimate_run(
     resource="predictions:structure-and-binding",
     model="boltz-2.1",
     payload=<request body object>
   )

2. Confirm with user, then submit
   boltz_submit_run(
     resource="predictions:structure-and-binding",
     model="boltz-2.1",
     run_name=RUN_NAME,
     output_dir=ROOT,
     poll_interval_seconds=10,
     payload=<same request body object>
   )

`boltz_submit_run` submits synchronously, then starts detached `download-results`
internally and returns `{id, run_name, output_dir, log_path, download_pid}`.
```

## Always Do This

- Keep the payload field names exactly as the API body names shown in `references/api.md`.
- Residue indices are 0-based wherever the payload asks for residue positions (constraints, modifications, contact tokens).
- For CIF/PDB bytes embedded in `--target` / `structure.data`, use `@data:///absolute/path/file.cif` — it sniffs binary and base64-encodes. Don't use bare `@path` for binary data.
- Use the same descriptive slug as `run_name`; the MCP server reuses it as both `--idempotency-key` and `--name`.
- `boltz_submit_run` already starts detached `download-results`. Do not run `boltz-api download-results` yourself from the skill flow.
- Only check progress when the user asks. Use `boltz_get_job` for server-side status and `boltz_get_local_run` for local log / `.boltz-run.json` state.
- If detached download needs to be restarted, use `boltz_resume_download` with the same `run_name`.
- Poll interval: keep `poll_interval_seconds=10` for SAB — predictions usually finish in under a few minutes.

## Escape Hatch

For anything not covered in `references/api.md`:

- Upstream request body reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api predictions:structure-and-binding start --help` (schema details aren't there — just flag names and types)

Read [references/api.md](references/api.md) for entity shapes, binding variants, bonds, constraints, model options, and output metrics.

## Outputs

Under `$ROOT/$RUN_NAME/`:

- `.boltz-run.json` — run metadata, cursor, idempotency key
- `outputs/archive.tar.gz` — unpacks to `prediction/{metrics.json, sample_*_predicted_structure.cif, sample_*_pae.npz}`

Metrics in `metrics.json` are **nested, not flat**:

- `best_sample.metrics` and each `all_sample_results[].metrics` contain nine lowercase keys: `structure_confidence`, `ptm`, `iptm`, `ligand_iptm` (only when ligands present), `protein_iptm` (only for multi-protein complexes), `complex_plddt`, `complex_iplddt`, `complex_pde`, `complex_ipde`.
- `binding_metrics` is a **separate top-level object** present only when `binding` was requested. Shape depends on the binding variant: `ligand_protein_binding` → `{binding_confidence, optimization_score}`; `protein_protein_binding` → `{binding_confidence}` only (no `optimization_score`).

Summarize these for the user and point them at the CIF path.

## SAB 400 validation quirk

If the server rejects the payload with only `{"code": "VALIDATION_ERROR", "message": "Request validation failed"}` and no field-level details, inspect the `entities`, `binding`, and `constraints` blocks carefully — `predictions:structure-and-binding` is the one endpoint that currently omits `details`. The other four endpoints return specific field paths.
