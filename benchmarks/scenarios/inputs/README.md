# Scenario inputs

Populate this directory before running benchmarks. The specific files referenced by scenarios:

- `target.fasta` — used by scenarios 2, 4, 5. A ~100–400 residue protein target. Suggestion: BRD4-BD1 (UniProt O60885, residues 44–168).
- `50-smiles.csv` — used by scenario 2. 50 SMILES strings, drug-like. A random subset of Enamine REAL works well.
- `20-peptides.fasta` — used by scenario 5. 20 peptides (12–20 residues each), multi-record FASTA format.

All inputs are gitignored; check in the scenarios' prompts, not the inputs themselves (to keep the repo light and to avoid licensing concerns with third-party libraries).
