---
name: boltz-structure-and-binding
description: Predict the 3D structure of a protein, RNA, DNA, or ligand complex with the Boltz Compute API and optionally score binding. TRIGGER when the user asks to fold a complex, dock a ligand, predict an interface, generate a CIF or PDB for a defined system, or get structure and binding metrics for one specified complex. Not for screening libraries or designing new molecules.
---

## Workflow

Use this skill for one defined complex, not a library workflow.

1. Normalize the complex inputs into entities: proteins, RNA, DNA, ligand SMILES, or ligand CCD codes.
2. If the user wants binding metrics, identify the binder chain correctly and include a `binding` block.
3. If the user asks for advanced geometry control, add only the requested `constraints`, `bonds`, `modifications`, or `model_options`.
4. Estimate cost first, ask for explicit approval, then run the job.
5. Let the wrapper poll to completion and download the returned artifacts locally.

## Always Do This

- Use the Python SDK wrapper only: `python scripts/query.py ...`.
- Expect authentication through `BOLTZ_API_KEY`; `BOLTZ_COMPUTE_API_KEY` also works.
- Always run `--estimate-only` before submission and ask the user to confirm spend.
- Always send `modifications: []` on every protein, RNA, or DNA entity when there are no modifications. The API currently rejects omitted polymer `modifications`.
- Keep defaults unless the user explicitly asks to change sampling behavior or constraints.
- Remind yourself that residue indices are 0-based anywhere the API asks for residue positions.
- Let the wrapper handle polling and downloading. The user should not need to manage async state manually.

## Input Normalization

- `--protein` accepts a raw sequence, FASTA path, or `.txt` path.
- `--rna`, `--dna`, `--ligand-smiles`, and `--ligand-ccd` accept raw strings.
- Chain IDs are assigned in entity order unless the user supplies a full config.
- Use `--config` for advanced payloads that need bonds, pocket or contact constraints, or custom model options.
- Use `--binding` only when the user wants binding metrics. A single ligand binder chain becomes ligand-protein binding; otherwise it becomes protein-protein binding.
- If this endpoint returns `VALIDATION_ERROR` with only `"Request validation failed"`, explain that `structure-and-binding` currently omits field-level `details` and inspect polymer entities first.

## Read This Reference When Needed

- Read [references/api.md](references/api.md) for:
  - the exact entity shapes
  - binding block semantics
  - bonds, constraints, and model options
  - output metrics and downloaded artifacts

## Command Pattern

Estimate first:

```bash
python scripts/query.py \
  --protein TARGET_FASTA_OR_SEQUENCE \
  --ligand-smiles "SMILES" \
  --binding B \
  --num-samples 1 \
  --estimate-only
```

Submit after confirmation:

```bash
python scripts/query.py \
  --protein TARGET_FASTA_OR_SEQUENCE \
  --ligand-smiles "SMILES" \
  --binding B \
  --num-samples 1
```

## Outputs

- `results.json`
- downloaded structures under `$BOLTZ_OUTPUT_DIR/<job_id>/structures/`
- optional `archive.zip`

Summarize the returned metrics and tell the user where the artifacts were written under `$BOLTZ_OUTPUT_DIR`.
