# Scenario 3 — Design 10 nanobody binders for an epitope

**Skill**: `boltz-protein-design`
**Difficulty**: Medium
**Expected wall-clock**: 30–60 minutes (Boltz-side)

## User prompt

```
Design 10 nanobody binders against this epitope.

Target sequence:
MRKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTLTY

Epitope residues (0-based): 42, 43, 44, 45, 46
```

## Expected behavior

1. Agent constructs `target` with `no_template` variant, provides the sequence
   and `epitope_residues`.
2. Sets `modality: nanobody`, `num_proteins: 10`.
3. Calls cost estimation. Cost = (10 + 1) × $0.025 = $0.275.
4. Confirms, submits, backgrounds.
5. Reports 10 designs ranked by optimization_score when results land.

## Success criteria

- Agent enforces the `num_proteins >= 10` floor (does NOT accept a lower number
  without pushing back).
- Agent correctly quotes the cost formula `(num + 1) × $0.025`, not `num × $0.025`.
- Results come back with 10 designed sequences, each with predicted structure.

## What to watch for

- Does the agent correctly use 0-based residue indices?
- Does it set `modality: nanobody` rather than `peptide` or `custom_protein`?
