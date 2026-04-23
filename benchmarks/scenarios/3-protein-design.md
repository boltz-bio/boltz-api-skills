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
3. Calls cost estimation and quotes the returned `estimated_cost_usd`.
4. Confirms, submits, backgrounds.
5. Reports 10 designs ranked by `binding_confidence` when results land, with
   `iptm` (higher is better) and `min_interaction_pae` (lower is better) as
   tiebreakers.

## Success criteria

- Agent enforces the `num_proteins >= 10` floor (does NOT accept a lower number
  without pushing back).
- Agent quotes the exact cost estimate returned by `estimate-cost`, not a
  hardcoded `num_proteins × $0.025` formula.
- Results come back with 10 designed sequences, each with predicted structure.

## What to watch for

- Does the agent correctly use 0-based residue indices?
- Does it set `modality: nanobody` rather than `peptide` or `custom_protein`?
- Does it avoid sorting by `optimization_score`? `protein:design` does not emit
  that metric.
