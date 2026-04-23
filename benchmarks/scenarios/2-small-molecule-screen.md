# Scenario 2 — Screen 50 SMILES against a target

**Skill**: `boltz-small-molecule-screen`
**Difficulty**: Medium
**Expected wall-clock**: 10–30 minutes (Boltz-side)

## User prompt

```
I want to virtually screen the 50 compounds in benchmarks/scenarios/inputs/50-smiles.csv
against my target protein in benchmarks/scenarios/inputs/target.fasta. Rank the
hits and tell me the top 5.
```

## Required inputs (provide at test time)

- `benchmarks/scenarios/inputs/50-smiles.csv` — 50 SMILES strings, one per line
  (or a CSV with a SMILES column). Use a drug-like subset of Enamine REAL or
  any open library.
- `benchmarks/scenarios/inputs/target.fasta` — any reasonably-sized protein
  target (~100–400 residues). BRD4-BD1 is a good test target.

## Expected behavior

1. Agent reads the CSV, extracts the SMILES column (auto-detect).
2. Reads the FASTA, extracts the sequence.
3. Constructs a `molecules` list and `target.entities` list.
4. Calls cost estimation and quotes the returned `estimated_cost_usd`.
5. Confirms, submits, backgrounds download, ends turn.
6. Later, when results are available, ranks by `binding_confidence` for hit
   discovery and reports top 5 with SMILES + metrics. Include
   `optimization_score` as a secondary metric when present, but do not sort by
   it unless the user asks for lead optimization / binding-strength ranking.

## Success criteria

- Job submits and returns results for all molecules that pass server-side
  default filters. Default filters may reject a subset before scoring.
- Top-5 report includes `external_id` (if provided) or SMILES and correct metrics.

## What to watch for

- Does the agent correctly auto-detect the SMILES column in a CSV?
- Does it respect the "don't add molecule_filters unless asked" guidance?
- Does it avoid assuming `len(results) == len(input molecules)` when default
  filters reject molecules?
