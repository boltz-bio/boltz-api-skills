---
name: boltz-protein-design
description: Generate novel protein binders such as peptides, antibodies, nanobodies, or custom proteins for a target with the Boltz Compute API and return ranked designed sequences with predicted complex structures. TRIGGER when the user wants to design or invent new binders for a target. Not for screening user-supplied proteins and not for small molecules.
---

## Workflow

Use this skill when the user wants novel binder generation.

1. Normalize the target as `structure_template` or `no_template`.
2. Normalize the binder specification as either `structure_template` redesign or `no_template` sequence-DSL design.
3. Keep rules and motif constraints at defaults unless the user explicitly asks for them.
4. Estimate cost first, show the estimate, and run without asking only when `estimated_cost_usd` is less than $1.00; ask for confirmation at $1.00 or more.
5. Let the wrapper poll, paginate designs, rank outputs, and download structures locally.

## Always Do This

- Use the Python SDK wrapper only: `python scripts/query.py ...`.
- Expect authentication through `BOLTZ_API_KEY`; `BOLTZ_COMPUTE_API_KEY` also works.
- Always run `--estimate-only` before submission. Submit without asking only when `estimated_cost_usd` is less than $1.00; ask for explicit cost approval at $1.00 or more.
- Always send `modifications: []` on every protein, RNA, or DNA entity when there are no modifications. The API currently rejects omitted polymer `modifications`.
- Treat `--num-proteins 10` as the minimum valid request size. Smaller values currently fail server-side.
- Treat all residue indices as 0-based.
- Be careful with the sequence DSL for `designed_protein` entities. Fixed residues stay literal; numeric spans represent designed segments.
- Mention optional amino-acid and motif rules to the user, but apply them only on request.
- Expect downloads under `$BOLTZ_OUTPUT_DIR` unless `--output-dir` is explicitly provided.

## Input Normalization

- `--binder-sequence` is the simplest no-template path for designed binders.
- `--binder-structure` plus `--binder-chain-selection` is the structure-template redesign path.
- `--target-protein` accepts raw sequence, FASTA, or `.txt`.
- `--target-structure` accepts a local structure path or URL.
- Use `--config` for advanced motif layouts, rules, target epitope definitions, bonds, or constraints.

## Read This Reference When Needed

- Read [references/api.md](references/api.md) for:
  - binder specification variants
  - sequence DSL semantics
  - redesign motif semantics
  - target variants and rule fields
  - returned metrics and downloaded artifacts

## Command Pattern

Estimate first:

```bash
python scripts/query.py \
  --num-proteins 50 \
  --modality peptide \
  --binder-sequence "8..15" \
  --target-protein TARGET.fasta \
  --estimate-only
```

Submit after confirmation when the estimate is $1.00 or more:

```bash
python scripts/query.py \
  --num-proteins 50 \
  --modality peptide \
  --binder-sequence "8..15" \
  --target-protein TARGET.fasta
```

## Outputs

- `results.json`
- `results.csv`
- per-design structures under `$BOLTZ_OUTPUT_DIR/<job_id>/structures/`

Report the strongest designs and tell the user where the artifacts were written under `$BOLTZ_OUTPUT_DIR`.
