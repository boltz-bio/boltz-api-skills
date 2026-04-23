# Scenario 5 — Screen 20 peptides against a target

**Skill**: `boltz-protein-screen`
**Difficulty**: Medium
**Expected wall-clock**: 15–40 minutes (Boltz-side)

## User prompt

```
Rank these 20 peptides against my target. Give me the top 5 binders.

Target sequence in benchmarks/scenarios/inputs/target.fasta
Peptide library in benchmarks/scenarios/inputs/20-peptides.fasta (one peptide
per record)
```

## Required inputs

- `benchmarks/scenarios/inputs/target.fasta`
- `benchmarks/scenarios/inputs/20-peptides.fasta` — 20 peptide sequences, each
  12–20 residues.

## Expected behavior

1. Agent parses multi-record FASTA into a `proteins` list (each entry a
   single-entity protein).
2. Constructs `target.no_template` with the target sequence.
3. Calls cost estimation and quotes the returned `estimated_cost_usd`.
4. Confirms, submits, backgrounds, reports ranked top 5.

## Success criteria

- All 20 peptides scored.
- Ranking by `binding_confidence` descending, with `iptm` (higher is better) and
  `min_interaction_pae` (lower is better) as tiebreakers, plus structure
  metrics.

## What to watch for

- Does the agent correctly split a multi-record FASTA into individual `proteins`
  entries (not one long concatenated entity)?
- Does it avoid sorting by `optimization_score`? `protein:library-screen` does
  not emit that metric.
