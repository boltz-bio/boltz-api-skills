# Target Exploration — pre-design scouting

Read this when the user **opts into** the target-exploration pass from
`boltz-protein-design`. It scouts a few cheap framings of the target before
committing compute to a full design run, then hands back a chosen framing
(crop + optional binding site) and a recommended `num_proteins` for the full
run. If the user already knows their target, site, and crop, do **not** run this
— go straight back to authoring the full payload.

## Contents

- [Mental model: a grid we sample, not a full grid](#mental-model)
- [Bundled scripts and dependency probe](#bundled-scripts-and-dependency-probe)
- [Indexing contract (read before cropping)](#indexing-contract)
- [Step 1 — trim unresolved N/C termini (always)](#step-1--trim-unresolved-nc-termini-always)
- [Step 2 — choose which axes to scout](#step-2--choose-which-axes-to-scout)
- [Step 3 — scout: 50 designs per config](#step-3--scout-50-designs-per-config)
- [Step 4 — pick the winning config by max binding_confidence](#step-4--pick-the-winning-config)
- [Step 5 — size and submit the full run](#step-5--size-and-submit-the-full-run)
- [Step 6 — post-run yield readout](#step-6--post-run-yield-readout)

## Mental model

The exploration procedure is best understood as a set of **axes** that frame the
same target different ways. Each axis changes which target residues the model sees
and whether the binding site is pinned. We do **not** run the full Cartesian
grid — that is wasteful. We trim termini once, then sample a sensible handful of
framings, scout each cheaply at 50 designs, and let the yield pick the winner.

The axes:

| Axis | What it varies | How |
|---|---|---|
| **Termini** (always) | Drop floppy unmodeled N/C overhang | First/last resolved residue |
| **Disorder cutout** | Remove internal loopy/disordered stretches | `detect_disorder.py` |
| **Crop radius** | Keep only residues near the site | `crop_radius.py` (10/15/25/30/35 Å) |
| **Site specified or not** | Pin the epitope vs let the binder find it | include/omit `epitope_residues` |
| **Domain** | Full target vs one domain at a time | ask the user → LLM fallback |
| **Scan** (large/unknown site) | Discover where binders actually land | `scan_sites.py` |

Why bother: unmodeled terminal residues add floppy overhang that hurts designs;
binders frequently dock off-site and crop/epitope indices are easy to misread,
so testing a few framings cheaply reveals which one yields good binders before
spending on a large run.

## Bundled scripts and dependency probe

The geometry/analysis scripts live in `scripts/` next to this skill and need
`python3` with `gemmi` and `numpy`. **Probe the active interpreter first; only
install if it fails** — many users already have a suitable env.

```bash
# Probe (run from the skill directory; adjust the path to scripts/ as needed)
python3 -c "import gemmi, numpy" && echo DEPS_OK
```

If that prints `DEPS_OK`, run the scripts with `python3` directly. If it errors,
install the bundled pin into a throwaway venv and use that interpreter:

```bash
python3 -m venv /tmp/boltz-explore-venv
/tmp/boltz-explore-venv/bin/pip install -r scripts/requirements.txt
# then call /tmp/boltz-explore-venv/bin/python instead of python3 below
```

## Indexing contract

**Every script emits and consumes 0-based API residue indices** — the same
indices `crop_residues`, `epitope_residues`, and `flexible_residues` use in the
payload. The mapping is `API index = canonical label_seq_id − 1`. The scripts
read `label_seq` from the CIF (not author numbering) so crop lists drop straight
into the payload with no offset arithmetic — do **not** reintroduce auth-number
offsets. When in doubt, spot-check one or two mapped indices against the target
sequence before submitting; viz confirmation is deferred to a later skill, so
this sanity check is your guardrail.

## Step 1 — trim unresolved N/C termini (always)

Never include leading or trailing residues that are unresolved in the
structure — drop any unmodeled residues at each end so the crop starts and ends
at the first and last **resolved** residue. This applies to the baseline and to
every crop variant below. (Internal unresolved residues — disordered loops — are
handled separately in the disorder axis, not here.)

Determine the bounds by reading the CIF: the crop starts at the first resolved
`label_seq` and ends at the last resolved `label_seq`. Express the kept range as
0-based API indices in `crop_residues`. For a large structure you may use
`scripts/terminus.py <target.cif> --chain A` to print the first/last resolved
API index, but reading the CIF directly is fine.

## Step 2 — choose which axes to scout

Pick a small set of framings — not the full grid. Sensible defaults:

1. **Baseline** — full target, termini trimmed, design spec as given.
2. **Disorder cutout** — if the target has internal disordered/loopy regions,
   add a framing that crops them away:
   ```bash
   # predicted target (pLDDT in the B-factor column) — default mode:
   python3 scripts/detect_disorder.py <target.cif> --chain A --min-loop 10
   # experimental target (real B-factors): high B = mobile
   python3 scripts/detect_disorder.py <target.cif> --chain A --mode bfactor
   ```
   It flags internal low-confidence/high-mobility runs longer than `--min-loop`
   (default 10) and prints the kept `crop_residues` (0-based) with those runs
   removed; terminal runs are left to terminus trimming. This is the weakest
   axis — it is a confidence/mobility heuristic, not a true disorder detector —
   so treat the suggestion as a hint and confirm it looks reasonable.
3. **Binding-site crop radius** — if a binding site is known, crop to residues
   within a radius of the site (all-atom). Scout a couple of radii rather than
   all five:
   ```bash
   python3 scripts/crop_radius.py <target.cif> --chain A \
     --site 42,43,44 --radii 15,25,35
   ```
   `--site` takes 0-based API indices. For each radius it prints the kept
   `crop_residues`. Run each radius **twice** as separate configs: once **with**
   the site in `epitope_residues`, once **without** — pinning the site is not
   always better, so let the scout decide.
4. **Domain** — if the site sits in one domain, or there is no site and the
   target is multi-domain, scout individual domains as the target. Ask the user
   for domain boundaries (or a CATH/Pfam reference) first; if they don't know,
   propose boundaries from the target's identity and have them confirm. We do
   not bundle a domain predictor — keep this axis manual.
5. **Scan** — only if the target is **> 300 residues** or the binding site is
   unknown. See [scan](#scan) below.

Keep the config count modest. Each config is 50 designs; at ≈$0.03–0.05/design
that is ≈$1.5–2.5 per config, so 4–6 configs is ≈$6–15 of scouting. Always run
`estimate-cost` on each config, sum the total, and confirm before submitting the
batch.

### scan

For large targets or unknown sites, discover where binders naturally dock:

1. Submit **one 200-design run with no `epitope_residues`** (termini trimmed).
   The scan uses 200 (not the 50 of a normal scout) because its job is to find
   *where* binders dock and cluster those footprints reliably — too few designs
   gives noisy clusters. A no-site full-target run is also the unbiased
   **baseline**, so let this run serve both roles rather than paying for a
   separate 50-design baseline.
2. After download, cluster the top designs' contact footprints into candidate
   sites:
   ```bash
   python3 scripts/scan_sites.py <run-dir> --target-chain A --top 20 --cutoff 6 --jaccard 0.25
   ```
   It computes each top design's all-atom footprint on `--target-chain` (default
   `A`; all other chains are treated as binder), greedily clusters footprints by
   Jaccard > 0.25, and prints a consensus site (0-based API indices) per
   cluster — the residues contacted by ≥2 designs in the cluster.
3. For each discovered site, scout two configs **in parallel**: (a) site
   specified + target cropped to ~35 Å around it, and (b) the same crop
   **without** the site specified. Feed each consensus site back through
   `crop_radius.py`.

## Step 3 — scout: 50 designs per config

Each chosen config is a normal `protein:design` submission with
`num_proteins: 50` and that config's `crop_residues` (and `epitope_residues`
when the config pins the site). Author each payload, `estimate-cost`, confirm
the summed cost, then submit and download per the main skill's **Command
Pattern**. Give each scout run a descriptive name, e.g.
`scout-<target>-<axis>-<variant>` (`scout-PD1-r25-site`, `scout-PD1-r25-nosite`,
`scout-PD1-disorder`, `scout-PD1-baseline`), so the configs live together and
are easy to compare.

**Launch the scout configs in parallel** — do not finish one before starting the
next. Submit each (`start`), then immediately background its `download-results`
(per the main skill's Command Pattern) so every config runs on Boltz at the same
time, and do not block waiting on any of them.

The only ordering constraint is the scan: configs derived from `scan_sites.py`
need the 200-design scan run's results first. So launch every independent config
up front together — baseline, disorder cutout, radius crops, and the scan run
itself — and once the scan downloads, launch its per-site configs in parallel
too. Never run scouts one at a time.

## Step 4 — pick the winning config

Once the scout runs finish, score each config and choose the framing to scale
up. **The selection metric is the maximum `binding_confidence`** across the 50
designs in that config — the best single design a framing can produce is the
signal that the framing is promising.

```bash
python3 scripts/analyze_results.py <scout-run-dir>      # one per config
```

For each config it prints: **max binding_confidence**, the 10th-highest
binding_confidence, and the fraction of designs with bc > 0.01 and > 0.05.
Compare configs by max bc; report the others as supporting context. The winning
config's crop (and site, if it had one) becomes the framing for the full run.

## Step 5 — size and submit the full run

Carry the winning config's `crop_residues`/`epitope_residues` into a full-run
payload, then size it per the main skill's **Run sizing** section (20k / 50k /
100k tiers, default 50k). At ≈$0.03–0.05/design a 50k run is on the order of
thousands of dollars, so always run `estimate-cost`, show the exact
`estimated_cost_usd`, and get explicit confirmation before `start`. Then submit
and download per the main skill.

## Step 6 — post-run yield readout

After the full run downloads, give the standard yield readout with the same
script:

```bash
python3 scripts/analyze_results.py <full-run-dir>
```

Report: max binding_confidence, 10th-highest binding_confidence, and the
fraction of designs with bc > 0.01 and > 0.05. These are the numbers a designer
expects after every run. Then rank and present top designs per the main skill's
**Outputs** section. (Histograms and structure visualization are intentionally
out of scope here — a later visualization skill will add them.)
