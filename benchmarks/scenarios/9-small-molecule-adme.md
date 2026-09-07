# Scenario 9 — ADME triage on a compound list

**Skill**: `boltz-small-molecule-adme`
**Difficulty**: Easy
**Expected wall-clock**: under 2 minutes (ADME is synchronous)

## User prompt

```
Predict solubility, permeability, and logD for the compounds in
benchmarks/scenarios/inputs/50-smiles.csv. No target, I just want ADME triage.
Flag anything that looks poorly soluble.
```

## Required inputs

- `benchmarks/scenarios/inputs/50-smiles.csv` (same as scenario 2).

## Expected behavior

1. Agent picks `boltz-small-molecule-adme`, not `boltz-small-molecule-screen`,
   because no target is involved.
2. Reads the CSV, extracts the SMILES column, and builds a `molecules` list of
   `{smiles, id?}` entries. 50 molecules fit in one request under the 128 cap.
3. Runs `estimate-cost` with `--model adme-v1` and quotes the returned
   `estimated_cost_usd`, then waits for confirmation.
4. Runs `predictions:adme run` with `--model adme-v1` as a normal foreground
   command. No background or non-blocking mode, no `download-results`.
5. Reports from `<root>/<run-name>/run.json` → `output.molecules[]`:
   `external_id` or SMILES, `solubility`, `permeability`, `lipophilicity`, and
   flags low-solubility molecules and any `status: failed` entries.

## Success criteria

- Did not ask for or invent a protein target.
- Passed `--model adme-v1` on both `estimate-cost` and `run`.
- Quoted the `estimate-cost` figure rather than `50 × $0.01`.
- Ran `run` in the foreground and did not launch `download-results`.
- Reported all three ADME values per molecule and called out failures without
  failing the batch.

## What to watch for

- Routing: a screen skill triggered by "compounds" is a failure.
- A background launch or a claimed follow-up check for a synchronous command.
- Silent dropping of molecules with invalid SMILES instead of reporting them.
- Any `chunking` when the list is under 128; chunking is only correct above it.
