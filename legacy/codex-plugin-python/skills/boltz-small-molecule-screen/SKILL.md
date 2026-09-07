---
name: boltz-small-molecule-screen
description: Score a user-supplied SMILES library against a protein target with the Boltz Compute API and return ranked binding and structure metrics with per-hit structures. TRIGGER when the user wants to virtually screen, dock, or rank an existing compound library against a target. Not for designing new molecules and not for a single one-off docking pose.
---

## Workflow

Use this skill when the user already has candidate molecules.

1. Normalize the molecule library from raw SMILES, `.csv`, `.smi`, or `.txt`.
2. Normalize the target from one or more protein sequences, plus optional pocket residues or reference ligands.
3. Keep default server-side filtering unless the user explicitly asks for custom filters.
4. Estimate cost first, show the user the estimate, and get confirmation before starting the screen.
5. Let the wrapper poll, paginate results, rank hits, and download per-hit structures locally.

## Always Do This

- Use the Python SDK wrapper only: `python scripts/query.py ...`.
- Expect authentication through `BOLTZ_API_KEY`; `BOLTZ_COMPUTE_API_KEY` also works.
- Always run `--estimate-only` before submission and ask for explicit spend confirmation.
- Always send `modifications: []` on every target protein entity when there are no modifications. The API currently rejects omitted polymer `modifications`.
- Do not invent medicinal chemistry filters. Mention them as options and apply them only on request.
- Treat residue indices as 0-based when pocket residues are supplied.
- Expect downloads under `$BOLTZ_OUTPUT_DIR` unless `--output-dir` is explicitly provided.

## Input Normalization

- `--molecules` accepts:
  - raw SMILES
  - `.csv` with an auto-detected SMILES column and optional identifier column
  - `.smi`
  - `.txt`
- `--target-protein` accepts raw sequence, FASTA, or `.txt`.
- Multiple `--molecules` flags merge libraries.
- Multiple `--target-protein` flags create multiple chains.
- Use `--config` for advanced filters or target settings.

## Read This Reference When Needed

- Read [references/api.md](references/api.md) for:
  - exact `molecules`, `target`, and `molecule_filters` shapes
  - available Lipinski, RDKit, SMARTS catalog, custom SMARTS, and regex filters
  - output metrics and downloaded files

## Command Pattern

Estimate first:

```bash
python scripts/query.py \
  --molecules LIBRARY.smi \
  --target-protein TARGET.fasta \
  --estimate-only
```

Submit after confirmation:

```bash
python scripts/query.py \
  --molecules LIBRARY.smi \
  --target-protein TARGET.fasta
```

## Outputs

- `results.json`
- `results.csv`
- per-hit structures under `$BOLTZ_OUTPUT_DIR/<job_id>/structures/`

Report the top-ranked hits and tell the user where the files were written under `$BOLTZ_OUTPUT_DIR`.
