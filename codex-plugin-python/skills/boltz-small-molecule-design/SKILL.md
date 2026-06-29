---
name: boltz-small-molecule-design
description: Generate novel small-molecule binders for a protein target with the Boltz Compute API and return ranked candidate SMILES with predicted complex structures. TRIGGER when the user wants to design, generate, or propose new ligands or hits for a target and does not already have a compound library. Not for screening user-supplied molecules.
---

## Workflow

Use this skill when the user wants novel ligand generation rather than ranking an existing library.

1. Normalize the protein target and any optional pocket-guidance inputs.
2. Keep default filter behavior unless the user explicitly asks for chemical-space or filter constraints.
3. Estimate cost first, show the estimate, and submit without asking only when `estimated_cost_usd` is less than $1.00; ask for confirmation before submission at $1.00 or more.
4. Let the wrapper submit, poll, paginate results, rank outputs, and download structures locally.

## Always Do This

- Use the Python SDK wrapper only: `python scripts/query.py ...`.
- Expect authentication through `BOLTZ_API_KEY`; `BOLTZ_COMPUTE_API_KEY` also works.
- Always run `--estimate-only` before submission. Submit without asking only when `estimated_cost_usd` is less than $1.00; ask for explicit cost approval at $1.00 or more.
- Always send `modifications: []` on every target protein entity when there are no modifications. The API currently rejects omitted polymer `modifications`.
- Treat `--num-molecules 10` as the minimum valid request size. Smaller values currently fail server-side.
- Keep the default filtering and unconstrained design setup unless the user asks for constraints such as Enamine REAL or custom filter rules.
- Treat residue indices as 0-based for pocket residues.
- Expect downloads under `$BOLTZ_OUTPUT_DIR` unless `--output-dir` is explicitly provided.

## Input Normalization

- `--target-protein` accepts raw sequence, FASTA, or `.txt`.
- Multiple `--target-protein` flags create multiple protein chains.
- `--reference-ligands` accepts comma-separated SMILES for pocket seeding.
- `--chemical-space` should be used only when the user explicitly wants constrained synthesis-aware generation.
- Use `--config` for advanced `target` or `molecule_filters` payloads.

## Read This Reference When Needed

- Read [references/api.md](references/api.md) for:
  - exact `target`, `chemical_space`, and `molecule_filters` semantics
  - supported filter families and what they mean
  - returned metrics and downloaded artifacts

## Command Pattern

Estimate first:

```bash
python scripts/query.py \
  --num-molecules 100 \
  --target-protein TARGET.fasta \
  --estimate-only
```

Submit after confirmation when the estimate is $1.00 or more:

```bash
python scripts/query.py \
  --num-molecules 100 \
  --target-protein TARGET.fasta
```

## Outputs

- `results.json`
- `results.csv`
- per-design structures under `$BOLTZ_OUTPUT_DIR/<job_id>/structures/`

Summarize the top candidates and tell the user where results were written under `$BOLTZ_OUTPUT_DIR`.
