# Small-Molecule Design Results

Read this after `download-results` completes, when ranking generated molecules or summarizing output files.

## Local Layout

Under `<output-root>/<run-name>/`:

- `.boltz-run.json`
- `run.json` - sanitized remote run record
- `results/index.jsonl` - one generated candidate per line, with `smiles`, `metrics`, and local `paths`
- `results/<pres_*>/metadata.json` - per-result metadata copied from the list-results record
- `results/<pres_*>/archive.tar.gz`
- `results/<pres_*>/files/result/{metrics.json, <pres_*>_predicted.cif, pae.npz}` (use the `paths.structure` field from `index.jsonl` rather than assuming a fixed CIF filename)

## Ranking

Sort by the metric matching the user's goal:

- `binding_confidence` for hit discovery
- `optimization_score` for lead optimization / binding strength

These are parallel intents, not fallback metrics. Also available: `structure_confidence`, `complex_plddt`, `complex_iplddt`, `iptm`, and `ptm`. Generated molecules also include a free Tier-1 `adme` block as a sibling of `metrics`.
