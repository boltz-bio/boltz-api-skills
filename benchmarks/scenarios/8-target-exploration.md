# Scenario 8 — Target exploration before a design campaign

**Skill**: `boltz-protein-design` (opt-in `references/target-exploration.md`)
**Difficulty**: Hard
**Expected wall-clock**: scouting is 50-design runs (minutes–tens of minutes
Boltz-side per config); the eval below is **dry-run** and submits nothing.

This scenario tests the *behavior* of the exploration flow — whether the agent
offers scouting at the right time, follows the procedure when opted in, respects
the user when they decline, and uses the bundled scripts with correct 0-based
indexing. It is gradeable **without** submitting real Boltz jobs: run each case
in dry-run (produce payloads, commands, and local script output; stop before
`start`/`estimate-cost` against the server).

## Case 8a — new target, unknown site (should offer → scout)

### User prompt
```
I want to design protein binders against my target. The structure is at
<target.cif> (chain A, ~308 residues). I don't know where on the target they
should bind. Help me set this up.
```

### Expected behavior
1. **Offers** the target-exploration pass (new target, nothing pinned).
2. On opt-in, reads `references/target-exploration.md` and follows it.
3. Trims unresolved N/C termini before any crop.
4. Recognizes target > 300 aa with unknown site → uses the **scan** path:
   a no-site ~200-design run, then `scan_sites.py` to cluster footprints into
   candidate sites, then per-site crop configs via `crop_radius.py`.
5. Scouts each config at **50 designs**.
6. Probes deps first (`python3 -c "import gemmi, numpy"`) and uses the bundled
   scripts rather than hand-rolling geometry.
7. Selects the winning config by **max binding_confidence** (`analyze_results.py`).
8. Recommends a full-run size with the 20k/50k/100k tiers, defaulting to **50k**.

### Success criteria (gradeable)
- [ ] Offered exploration (did not silently jump to a full run).
- [ ] Trimmed unresolved termini.
- [ ] Chose the scan path for the large/unknown-site target.
- [ ] Ran ≥1 bundled script (`scan_sites` / `crop_radius` / `detect_disorder`).
- [ ] Scout size = 50 designs per config.
- [ ] Selection metric = max binding_confidence.
- [ ] Full-run recommendation cites tiers and defaults to 50k.
- [ ] All crop/epitope indices are **0-based** API indices.

## Case 8b — user already knows their setup (should NOT push scouting)

### User prompt
```
Design binders against my target at <target.cif>, chain A. I've already settled
on my crop and want to bind the patch around residues 277-285. Just set up a
50,000-design run, I don't need any scouting.
```

### Expected behavior
1. **Does not** push the exploration procedure — the user opted out.
2. Sets up the full run directly: `num_proteins: 50000`,
   `epitope_residues: [277..285]` (0-based) on the chain.
3. Still gates on `estimate-cost` + explicit confirmation before `start`
   (a 50k run is costly).

### Success criteria (gradeable)
- [ ] Did not force exploration after the user declined it.
- [ ] `num_proteins == 50000`.
- [ ] Binding site set via `epitope_residues`, 0-based, on the correct chain.
- [ ] Quotes `estimate-cost` and waits for confirmation before submitting.

## What to watch for
- Pushing the full procedure on a user who declined (8b) is as much a failure as
  skipping it when it would help (8a).
- Off-by-one: `epitope_residues`/`crop_residues` must be 0-based API indices
  (`label_seq − 1`), not author numbering.
- Hand-rolled geometry instead of the bundled scripts (re-invents footprints /
  crop math every run, and is where indexing bugs creep in).
- Quoting a hardcoded per-design cost instead of the `estimate-cost` figure.

## Baseline contrast
Run the same prompts with no skill. A baseline agent typically authors a single
design payload with no termini trim, no scouting, no scan, no size-tier
guidance, and no bundled-script usage — that gap is the skill's value.
