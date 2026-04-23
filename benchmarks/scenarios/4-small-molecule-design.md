# Scenario 4 — Design 10 novel small-molecule ligands

**Skill**: `boltz-small-molecule-design`
**Difficulty**: Medium
**Expected wall-clock**: 30–90 minutes (Boltz-side)

## User prompt

```
I don't have any candidate compounds yet. Please design 10 novel ligands for
this target protein, prioritizing synthesizable molecules.

Target: benchmarks/scenarios/inputs/target.fasta

Pocket residues (0-based): 78, 79, 80, 81, 82, 83, 145, 146, 147
```

## Required inputs

- `benchmarks/scenarios/inputs/target.fasta` (same as scenario 2).

## Expected behavior

1. Agent constructs `target` with `no_template` variant, sequence from fasta,
   `pocket_residues` (0-based).
2. Sets `num_molecules: 10`. Optionally adds `chemical_space: enamine_real`
   because user said "synthesizable" — good agents do this; it's not strictly
   required.
3. Calls cost estimation and quotes the returned `estimated_cost_usd`.
4. Confirms, submits, backgrounds, reports top designs when ranked.

## Success criteria

- `num_molecules >= 10` enforced.
- Cost estimate quoted from `estimate-cost`, not a hardcoded
  `num_molecules × $0.025` formula.
- Output ranked by the metric matching user intent: `binding_confidence` for
  hit discovery / novel-hit design, or `optimization_score` when the user asks
  for lead optimization / binding-strength ranking.

## What to watch for

- Did the agent add `chemical_space: enamine_real` for "synthesizable"? (Bonus
  for yes; not wrong if no.)
- Does it offer filters but not silently add them?
- Does it explain the chosen ranking metric rather than treating
  `binding_confidence` and `optimization_score` as a fallback hierarchy?
