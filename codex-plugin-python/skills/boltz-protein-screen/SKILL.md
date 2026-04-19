---
name: boltz-protein-screen
description: Score a user-supplied library of protein sequences against a target with the Boltz Compute API and return ranked binding and structure metrics with per-hit complex structures. TRIGGER when the user wants to rank an existing set of proteins, peptides, antibodies, nanobodies, or binders against a target. Not for designing new proteins and not for small molecules.
---

## Workflow

Use this skill when the user already has candidate binders.

1. Normalize the binder library from raw sequences, FASTA, CSV, or text files.
2. Normalize the target as either `structure_template` or `no_template`.
3. Keep target constraints and bonds at defaults unless the user explicitly asks for them.
4. Estimate cost first, show the estimate, and ask for confirmation before starting the screen.
5. Let the wrapper poll, paginate results, rank binders, and download structures locally.

## Always Do This

- Use the Python SDK wrapper only: `python scripts/query.py ...`.
- Expect authentication through `BOLTZ_API_KEY`; `BOLTZ_COMPUTE_API_KEY` also works.
- Always run `--estimate-only` before submission and ask for explicit cost approval.
- Always send `modifications: []` on every protein, RNA, or DNA entity when there are no modifications. The API currently rejects omitted polymer `modifications`.
- Treat all residue indices as 0-based.
- Use `structure_template` only when the user truly has a structure-guided target; otherwise prefer the simpler `no_template` path.
- Expect downloads under `$BOLTZ_OUTPUT_DIR` unless `--output-dir` is explicitly provided.

## Input Normalization

- Candidate binders can come from raw sequence, FASTA, CSV, or plain text depending on the wrapper flags.
- `--target-structure` accepts a local structure path or URL.
- `--target-protein` accepts raw sequence, FASTA, or `.txt`.
- Use `--config` for advanced `chain_selection`, `epitope_residues`, `flexible_residues`, `bonds`, or `constraints`.
- Keep optional filters and constraints untouched unless the user asks for them.

## Read This Reference When Needed

- Read [references/api.md](references/api.md) for:
  - `proteins` payload semantics
  - `structure_template` versus `no_template` target shapes
  - bonds and constraint semantics
  - output metrics and downloaded artifacts

## Command Pattern

Estimate first:

```bash
python scripts/query.py \
  --proteins BINDERS.fasta \
  --target-protein TARGET.fasta \
  --estimate-only
```

Submit after confirmation:

```bash
python scripts/query.py \
  --proteins BINDERS.fasta \
  --target-protein TARGET.fasta
```

## Outputs

- `results.json`
- `results.csv`
- per-binder structures under `$BOLTZ_OUTPUT_DIR/<job_id>/structures/`

Report the best-ranked binders and tell the user where the output files were written under `$BOLTZ_OUTPUT_DIR`.
