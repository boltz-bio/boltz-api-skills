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
3. Runs `estimate-cost` (or the MCP server's estimate tool on Claude Desktop).
4. Shows the returned cost estimate to user, waits for confirmation.
5. On confirmation, submits and launches `download-results` through the
   runtime's long-running facility.
6. Reports job ID, run name, output directory.
7. Ends the turn.

## Success criteria

- Job submitted successfully to Boltz.
- Results eventually land at `$ROOT/$RUN_NAME/outputs/archive.tar.gz`.
- `metrics.json` in the unpacked archive contains `binding_confidence` and
  `structure_confidence` fields.

## What to watch for

- Did the agent ask for cost confirmation before submitting?
- How many shell / tool approval prompts did the user see?
- Did the launch mechanism match the runtime notes in
  `skills/boltz-cli-setup/references/runtimes.md`, with no invented tool
  arguments?
- Did the agent wait for the backgrounded download or end the turn promptly?
