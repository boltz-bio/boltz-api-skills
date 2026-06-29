# Scenario 1 — Fold a protein+ligand complex with binding metrics

**Skill**: `boltz-structure-and-binding`
**Difficulty**: Easy
**Expected wall-clock**: 3–8 minutes (Boltz-side)

## User prompt

```
I have this protein sequence: MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEK

I want to check if ethanol (SMILES: CCO) binds to it. Please run a Boltz
structure and binding prediction with one sample, give me the binding
confidence, and save the structure.
```

## Expected behavior

1. Agent constructs an entities list: protein (chain A) + ligand_smiles (chain B).
2. Adds a `binding` block with `type: ligand_protein_binding` and `binder_chain_id: B`.
3. Calls `estimate-cost` (CLI) or `boltz_estimate_run` (MCP).
4. Shows the returned cost estimate to user and applies the $1 spend gate.
5. Submits after confirmation when the estimate is $1.00 or more, or immediately when it is less than $1.00, then starts a backgrounded download.
6. Reports job ID, run name, output directory.
7. Ends the turn.

## Success criteria

- Job submitted successfully to Boltz.
- Results eventually land at `$ROOT/$RUN_NAME/outputs/archive.tar.gz`.
- `metrics.json` in the unpacked archive contains `binding_confidence` and
  `structure_confidence` fields.

## What to watch for

- Did the agent apply the $1 spend gate correctly before submitting?
- How many Bash / MCP tool approval prompts did the user see?
- Did the agent wait for the backgrounded download or end the turn promptly?
