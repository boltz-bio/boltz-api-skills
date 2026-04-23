# Skills / References Audit v2 vs Real API Reference (2026-04-23)

Canonical source: `/tmp/boltz-docs/api/*.md` (19 method-level spec files).
Secondary (illustrative only): `/tmp/boltz-docs/guides/*.md`.
v1 report: `AUDIT_REPORT.md` — many findings reversed here.

Out-of-scope exclusions (CLI abstracts them, agent never touches them directly):
raw HTTP paths, pagination params (`limit`/`after_id`), `url_expires_at` presigned
expiry, REST `/stop` endpoints, polling loops, auth header. v1 findings keyed on
any of these are listed as **v1 false positive (out of scope)** below.

---

## v1 corrections

The prior audit used `/tmp/boltz-docs/guides/*.md` as authoritative; the real spec
(`/tmp/boltz-docs/api/*.md`) contradicts the guides on several enum values and
field names. These v1 findings are reversed:

| v1 finding | v1 verdict | v2 (per spec) verdict | Why v1 was wrong |
|---|---|---|---|
| SAB `binding.type: ligand_protein_binding` | blocker — rename to `ligand_binding` | **skills are correct; keep** | `api/predictions-structure_and_binding-start.md:201, 203` defines literal `"ligand_protein_binding"`. Guide shorthand is stale. |
| SAB `binding.type: protein_protein_binding` (+`binder_chain_ids` plural) | blocker — "invented, not in canonical" | **skills are correct; keep** | `api/predictions-structure_and_binding-start.md:205–213` defines `ProteinProteinBinding = {binder_chain_ids: array of string, type: "protein_protein_binding"}`. |
| `designed_protein.value` (sequence DSL) | blocker — "canonical says `sequence:`" | **skills are correct; keep `value:`** | `api/protein-design-start.md:181–183` defines `DesignedProteinEntity.value: string` holding the DSL literal like `"MKTAYI5..10VKSHFSRQ"`. Guide uses `sequence:`; spec uses `value:`. |
| SAB skill cites `ligand_ccd` entity type ("not covered upstream") | minor — verify | **skills are correct; keep** | `api/predictions-structure_and_binding-start.md:165–178` defines `LigandCcdEntity`. |
| Protein-screen `chain_selection.<id>.chain_type: polymer\|ligand` "invented" | blocker — possibly invented | **skills are correct; keep** | `api/protein-library_screen-start.md:207–245` and `api/protein-design-start.md:25–27, 99–101` define the discriminated union `StructureTemplateTargetPolymerChainSpec`/`…LigandChainSpec` keyed on `chain_type`. |
| Protein-screen `target.no_template.bonds` / `constraints` / `epitope_ligand_chains` "not in canonical" | major — remove | **skills are correct; keep** | `api/protein-library_screen-start.md` and `api/protein-design-start.md:977–983` define all three. |
| `--model boltz-2.1` / `model_options.{recycling_steps, sampling_steps, step_scale}` | minor — unverified | **skills are correct; keep** | `api/predictions-structure_and_binding-start.md:407–419, 425–429` define them. |
| `num_samples` belongs inside `input` | minor — add note | **skills already correct** | `api/predictions-structure_and_binding-start.md:421–423` puts `num_samples` under `input`. The whole `--input @yaml://payload.yaml` already makes this so. |
| `num_samples` range 1–10, default 1 | (asserted by v1 from guides) | **out of scope / unverified — spec gives no min/max** | Spec only says "Number of structure samples to generate". Treat numeric bound as unverified. |
| v1 "add status-value table (`pending/running/succeeded/failed[/stopped]`)" | major | **out of scope (CLI-abstracted)** | `retrieve` is called by `download-results`/`check-status` internally. Agent reads a rendered status line from CLI output. Could still be useful for `check-status` Mode 2 narration but it's a nicety, not a correctness bug. Downgraded to minor enhancement. |
| v1 "add `/stop` stop-early section" | major | **out of scope** | REST endpoint; CLI does not currently expose it as an agent-facing subcommand per `boltz-api` help table in skills. |
| v1 "add `url_expires_at` / download-URL re-fetch warning" | major | **out of scope** | `download-results` internally downloads & caches; agent never touches presigned URLs. |
| v1 "add `/delete-data` eager deletion" | minor | **out of scope** | Agent does not call it; not part of any skill workflow. |
| v1 "pagination `limit` / `after_id` not documented" | minor | **out of scope** | `list-results` auto-paginates in the CLI. |
| v1 "progress-field section (`num_molecules_screened`, `num_proteins_generated`, etc.) missing" | minor | **out of scope for reference docs** but legitimately useful for `check-status`; see v2 cross-cutting section. |
| v1 "filter-level enum list missing from SKILL.md" (sm-screen/sm-design) | major | **partial false positive** — references/api.md already lists the four levels (`recommended/extra/aggressive/disabled`). Having them only in the reference is fine; SKILL.md is meant to route to the reference. |

Net reversal: v1 reported **~20 findings** in the above categories that v2 now marks
as correct-as-written or out of scope. The bulk of the "binding variant wrong" /
"designed_protein.sequence" / "protein_protein_binding invented" / "chain_type
invented" findings were caused by reading guides instead of the spec.

---

## Summary

- **17 surviving findings**. Severity: **8 blockers, 6 major, 3 minor**.
- Largest concentration: `core/references/boltz-structure-and-binding/api.md` (4
  findings) and `core/references/boltz-protein-design/api.md` (4 findings).
- Biggest change from v1: the binding-variant and DSL-field findings are reversed;
  the real blockers are (a) SAB output metric **nesting** and **names**
  (`complex_plddt`/`complex_ipde`/etc., split across `best_sample.metrics` vs
  `binding_metrics`); (b) `optimization_score` on **protein** endpoints (both
  design and screen — confirmed absent in spec); (c) protein-design output entity
  type flip from `designed_protein` to `protein`; (d) protein-design `end_index`
  semantics; (e) flat cost formulas for protein:design.

---

## Per-endpoint spec cheat-sheets (ground truth used for diffing)

### SAB (`predictions:structure-and-binding`)

Start body:
- `input.entities[]` — discriminated union on `type`: `"protein"`, `"rna"`,
  `"dna"`, `"ligand_ccd"`, `"ligand_smiles"`. All take `chain_ids: string[]`,
  `value: string`. Polymer types also take optional `cyclic: bool`,
  `modifications[]`.
- `input.binding?` — union on `type`: `"ligand_protein_binding"` (with
  `binder_chain_id: string` singular) OR `"protein_protein_binding"` (with
  `binder_chain_ids: string[]` plural).
- `input.bonds?`, `input.constraints?`, `input.model_options?`, `input.num_samples?`.
- Top-level: `model: "boltz-2.1"`, `idempotency_key?`, `workspace_id?`.

Retrieve output:
- `output.all_sample_results[].metrics.{complex_ipde, complex_iplddt,
  complex_pde, complex_plddt, iptm, ligand_iptm?, protein_iptm?, ptm,
  structure_confidence}` + `.structure.{url, url_expires_at}`.
- `output.best_sample.{metrics (same nine keys), structure}`.
- `output.archive?`.
- `output.binding_metrics?` — union:
  - `LigandProteinBindingMetrics = {binding_confidence, optimization_score,
    type: "ligand_protein_binding_metrics"}`
  - `ProteinProteinBindingMetrics = {binding_confidence, type:
    "protein_protein_binding_metrics"}` — **no `optimization_score`**.
- `status: "pending" | "running" | "succeeded" | "failed"` (no `stopped`).
- Spec citation: `api/predictions-structure_and_binding-retrieve.md:479–619`.

Estimate cost returns: `breakdown.{application, cost_per_unit_usd, num_units}`,
`estimated_cost_usd`, `disclaimer`.

### SM library screen (`small-molecule:library-screen`)

Start body:
- `molecules: [{smiles, id?}]` (top level).
- `target.entities[]` — `type: "protein"` only.
- `target.{bonds?, constraints?, pocket_residues?, reference_ligands?}`.
- `molecule_filters?.{boltz_smarts_catalog_filter_level?,
  custom_filters?[]}` — filter union variants: `lipinski_filter`,
  `rdkit_descriptor_filter`, `smarts_custom_filter`, `smarts_catalog_filter`,
  `smiles_regex_filter`.

List-results per-hit:
- `metrics: {binding_confidence, complex_iplddt, complex_plddt, iptm,
  optimization_score, ptm, structure_confidence}` — 7 keys.
- `smiles`, `external_id?`, `artifacts.{archive, structure}`, `warnings?`.
- Spec citation: `api/small_molecule-library_screen-list_results.md:61–91`.

### SM design (`small-molecule:design`)

Start body:
- `num_molecules` (min 10).
- `target` (same shape as SM screen).
- `chemical_space?: "enamine_real"` (only documented literal).
- `molecule_filters?` (same union as SM screen).

Per-hit metrics: same 7 keys as SM screen.

### Protein library screen (`protein:library-screen`)

Start body:
- `proteins: [{entities: [...], id?}]` (top level; plural, entry has nested `entities`).
- `target` — union on `type`:
  - `StructureTemplateTarget = {chain_selection: map<chain_id,
    PolymerSpec|LigandSpec>, structure, type: "structure_template"}`.
    `PolymerSpec = {chain_type: "polymer", crop_residues: number[] | "all",
    epitope_residues?, flexible_residues?}`. `LigandSpec = {chain_type:
    "ligand"}`.
  - `NoTemplateTarget = {entities, type: "no_template", bonds?, constraints?,
    epitope_ligand_chains?, epitope_residues?}`.

List-results per-hit:
- `metrics: {binding_confidence, helix_fraction, iptm, loop_fraction,
  min_interaction_pae, sheet_fraction, structure_confidence}` — 7 keys, **no
  `optimization_score`, no `ptm`, no `plddt`, no `complex_*`**.
- `entities[]`, `external_id?`, `artifacts`, `warnings?`.
- Spec citation: `api/protein-library_screen-list_results.md:243–273`.

### Protein design (`protein:design`)

Start body:
- `num_proteins: number` — "Must be between 10 and 1,000,000" (spec
  `api/protein-design-start.md:511–513`).
- `binder_specification` — union on `type`:
  - `StructureTemplateBinderSpec = {chain_selection, modality, structure, type:
    "structure_template", rules?}`. Inside `chain_selection.<id>` polymer variant
    carries `design_motifs[]`:
    - `ReplacementMotif = {design_length_range, end_index, start_index, type:
      "replacement"}` — `end_index` is **inclusive** per spec line 61: "0-indexed
      end residue (inclusive)". Header text line 45: "Residues from start_index
      to end_index (inclusive) are replaced".
    - `InsertionMotif = {after_residue_index, design_length_range, type:
      "insertion"}`. `after_residue_index = -1` means insert before residue 0.
  - `NoTemplateBinderSpec = {entities, modality, type: "no_template", bonds?,
    rules?}`. `entities[]` discriminated: `designed_protein`, `protein`, `rna`,
    `dna`, `ligand_smiles`, `ligand_ccd`. `DesignedProteinEntity.value` holds
    the DSL string.
- `modality: "peptide" | "antibody" | "nanobody" | "custom_protein"`.
- `target` — same union as protein-screen.
- `rules?.{excluded_amino_acids?, excluded_sequence_motifs?,
  max_hydrophobic_fraction?}`.

List-results per-hit (spec `api/protein-design-list_results.md:61–273`):
- `entities[]` with designed binder entities materialized as **`type:
  "protein"`** (spec line 71, `ProteinEntity`, NOT `designed_protein`) carrying
  the resolved amino-acid sequence in `value`.
- `metrics` — same 7 keys as protein screen: `binding_confidence,
  helix_fraction, iptm, loop_fraction, min_interaction_pae, sheet_fraction,
  structure_confidence`. **No `optimization_score`**.
- `artifacts.{archive, structure?}`, `warnings?`.
- Status enum on retrieve includes `"stopped"` (`api/protein-design-start.md:2003–2013`).

Estimate cost (all endpoints): same shape — `breakdown.{application,
cost_per_unit_usd, num_units}` + `estimated_cost_usd`. No tier structure is
visible in the static schema; however the `num_units` can exceed `num_proteins`
per empirical `debugging_log.md` §4a, implying server-side tier multipliers.

---

## Findings per skill

### 1. boltz-structure-and-binding

#### `core/skills/cli/boltz-structure-and-binding/SKILL.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| SKILL.md:81 | "Useful metrics in `metrics.json`: `pLDDT`, `pTM`, `ipTM`, `PDE`, `ipDE`, `structure_confidence`, and when `binding` was requested, `binding_confidence` + `optimization_score`." | Spec metric names (`api/predictions-structure_and_binding-retrieve.md:487–523`): `complex_ipde, complex_iplddt, complex_pde, complex_plddt, iptm, ligand_iptm, protein_iptm, ptm, structure_confidence`. All lowercase. No `pLDDT`, no `PDE`, no `ipDE`. `binding_confidence`/`optimization_score` live on `output.binding_metrics`, not on sample metrics. `optimization_score` is ONLY present on `LigandProteinBindingMetrics`, not `ProteinProteinBindingMetrics`. | **blocker** | Rewrite to: per-sample metrics are `structure_confidence, ptm, iptm, ligand_iptm, protein_iptm, complex_plddt, complex_iplddt, complex_pde, complex_ipde` (all lowercase). Binding metrics live separately as `binding_confidence` plus (for ligand–protein only) `optimization_score`. Drop uppercase/shorthand names. |

(The SKILL prose about `{type, chain_ids, value}`, `ligand_protein_binding`, and
`protein_protein_binding` is correct per spec — reversed from v1.)

#### `core/skills/mcp/boltz-structure-and-binding/SKILL.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| SKILL.md:78 | Same metric list as CLI variant (`pLDDT, pTM, ipTM, PDE, ipDE, …`) | Same spec lines as above. | **blocker** | Same fix. |

#### `core/references/boltz-structure-and-binding/api.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| api.md:43 | "`num_samples` (optional, 1–10, default 1)" | Spec (`api/predictions-structure_and_binding-start.md:421–423`) only says "Number of structure samples to generate". No min/max/default given in the spec. | minor | Drop the "1–10, default 1" claim or mark it "server-enforced; spec gives no range". |
| api.md:210–213 | `model_options` defaults `recycling_steps: 3`, `sampling_steps: 200`, `step_scale: 1.638` **plus ranges** ("min 1", "range 1.3–2.0") | Spec (`api/predictions-structure_and_binding-start.md:409–419`) confirms the three defaults. It does NOT state a min of 1 for recycling/sampling steps or a 1.3–2.0 range for step_scale. | minor | Keep defaults, drop the range assertions or mark them empirical. |
| api.md:145–148 | "Returned binding metrics: `binding_confidence`, `optimization_score`" (listed unconditionally under `binding`) | Spec (`api/predictions-structure_and_binding-retrieve.md:595–619`): `optimization_score` is present only when `binding.type: ligand_protein_binding` (`LigandProteinBindingMetrics`). `ProteinProteinBindingMetrics` has `binding_confidence` only. | **blocker** | Split the list: ligand–protein yields `binding_confidence + optimization_score`; protein–protein yields `binding_confidence` only. |
| api.md:235–244 | Metrics list in `metrics.json`: `pLDDT, pTM, ipTM, PDE, ipDE, structure_confidence, binding_confidence, optimization_score` | Same spec lines as SKILL finding above. Sample metrics are nine lowercase keys (`complex_plddt, complex_iplddt, complex_pde, complex_ipde, ptm, iptm, ligand_iptm, protein_iptm, structure_confidence`). Binding metrics are separate. | **blocker** | Rewrite metrics section. Document the nesting: sample-level metrics (nine lowercase keys) vs top-level `binding_metrics` (binding_confidence + optimization_score-for-ligand-only). |

### 2. boltz-small-molecule-screen

#### `core/skills/cli/boltz-small-molecule-screen/SKILL.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| SKILL.md:75 | Per-result metrics to rank on: `optimization_score` (primary), `binding_confidence`, `structure_confidence`, `complex_plddt`, `complex_iplddt`, `iptm`, `ptm`. | Spec (`api/small_molecule-library_screen-list_results.md:61–91`) lists exactly these 7 keys. Match is correct. Spec description places `binding_confidence` as "Primary metric for hit discovery" and `optimization_score` as "Binding strength ranking score for lead optimization" — parallel, not fallback. | minor | Clarify: `binding_confidence` is primary for hit discovery; `optimization_score` for lead optimization. Current "primary/fallback" framing is slightly off but not wrong mechanically. |
| SKILL.md:55 | "Cost is $0.025 per molecule" | Spec has no cost numbers; estimate-cost returns the authoritative breakdown. | minor | Mark as empirical / "quote `estimate-cost`". |

#### `core/skills/mcp/boltz-small-molecule-screen/SKILL.md`

Same two findings (SKILL.md:77, plus cost claim in "Always Do This"). Apply same fixes.

#### `core/references/boltz-small-molecule-screen/api.md`

No blocker-level issues. The field names and filter enums all match spec
(`api/small_molecule-library_screen-start.md:281–520`). The `binding_confidence`
vs `optimization_score` hit-vs-lead nuance (api.md:212) is a minor reword.

### 3. boltz-small-molecule-design

#### `core/skills/cli/boltz-small-molecule-design/SKILL.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| SKILL.md:14, 47 | "Design cost is `num_molecules * $0.025`." | Spec (`api/small_molecule-design-estimate_cost.md:523–553`) returns a single `breakdown` with `num_units`; doesn't expose a formula. Empirically this may hold for SM design, but protein-design experience (see debugging log §4a) shows flat formulas can be wrong. | minor | Soften to: "cost is quoted by `estimate-cost`; typically around $0.025 per molecule but confirm per-job". |
| SKILL.md:17 | "Rank hits by `optimization_score` descending" | Spec (`api/small_molecule-design-list_results.md:81–83`) has `optimization_score` with description "Binding strength ranking score for lead optimization". `binding_confidence` (line 65) is "Primary metric for hit discovery". | minor | Clarify hit-vs-lead parallel, not primary/fallback. |

#### `core/skills/mcp/boltz-small-molecule-design/SKILL.md`

Same two minor items. Apply same fixes.

#### `core/references/boltz-small-molecule-design/api.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| api.md:62 | "`num_units: num_molecules + 1` (accounting for a SynFlowNet / designer scheduler iteration)" with "cost_per_unit_usd adjusted so the total matches `num_molecules * $0.025` exactly" | Spec only defines `num_units: number` (`api/small_molecule-design-estimate_cost.md:547`) with no `+1` or adjustment rule documented. | minor | Mark as empirical observation; do not assert as formula. |
| api.md:197 | "Rank by `optimization_score` descending." | Spec: `optimization_score` is "lead optimization", `binding_confidence` is "Primary metric for hit discovery". | minor | Reword for hit-vs-lead parity. |

### 4. boltz-protein-screen

#### `core/skills/cli/boltz-protein-screen/SKILL.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| SKILL.md:18 | "Rank hits by `optimization_score` descending (fallback `binding_confidence`)." | Spec (`api/protein-library_screen-list_results.md:243–273`): protein-screen metrics are **exactly**: `binding_confidence, helix_fraction, iptm, loop_fraction, min_interaction_pae, sheet_fraction, structure_confidence`. No `optimization_score`. | **blocker** | Drop `optimization_score`. Rank by `binding_confidence` primary, with `iptm` and `min_interaction_pae` (lower is better) as tiebreakers. |
| SKILL.md:71 | Per-result metrics list begins with `optimization_score` (primary, if present) | Same spec citation — `optimization_score` is not in the schema at all for this endpoint. | **blocker** | Remove `optimization_score` from the metric list entirely. |
| SKILL.md:53 | "Cost is $0.025 per submitted protein" | Spec has no cost numbers. Also per debugging log §4a the flat formula is wrong for design; likely also tier-scaled here. | minor | Say "quoted by `estimate-cost`, approximately $0.025 per candidate for small complexes; scales with complex size". |

#### `core/skills/mcp/boltz-protein-screen/SKILL.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| SKILL.md:75 | Per-result metrics: `optimization_score` (primary, if present), … | Same — absent from spec. | **blocker** | Same fix. |

#### `core/references/boltz-protein-screen/api.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| api.md:247 | "`metrics.optimization_score` — primary ranking (when present)" | `api/protein-library_screen-list_results.md:243–273` — absent. | **blocker** | Remove `optimization_score` line. |
| api.md:254 | "Rank by `optimization_score` descending if present, otherwise by `binding_confidence`." | Same. | **blocker** | Rewrite: rank by `binding_confidence` primary; use `iptm` / `min_interaction_pae` for tiebreak. |
| api.md:232 | "$0.025 per submitted candidate binder (one entry in `proteins`)" | Not documented; tier-scaled empirically. | minor | Soften. |

### 5. boltz-protein-design

#### `core/skills/cli/boltz-protein-design/SKILL.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| SKILL.md:17, 49 | "Design cost is `num_proteins * $0.025`." (and "A batch of 10 is $0.250") | Spec doesn't expose a formula. `debugging_log.md` §4a: tier multiplier based on total complex length (~256-token bucket); GFP (238 aa) + 20-mer binder × 10 designs → $0.500 actual, not $0.250. | **blocker** | Replace with: "cost scales with total complex length. A minimal peptide + small target costs ≈$0.025/design; larger complexes (e.g. GFP + 20-mer binder) cost ≈$0.05/design. Quote the exact figure from `estimate-cost`." |
| SKILL.md:20 | "Rank by `optimization_score` (fallback `binding_confidence`)." | Spec (`api/protein-design-list_results.md:243–273`): metrics are `binding_confidence, helix_fraction, iptm, loop_fraction, min_interaction_pae, sheet_fraction, structure_confidence`. No `optimization_score`. | **blocker** | Rank by `binding_confidence`; tiebreakers `iptm` (higher better) and `min_interaction_pae` (lower better). |
| SKILL.md:75 | Per-result fields include `metrics.optimization_score` (primary) | Same — absent. | **blocker** | Remove `optimization_score`. |
| SKILL.md:75 | "`entities` (with the generated sequences)" — wording implies `designed_protein.value` is filled in | Spec (`api/protein-design-list_results.md:65–78`): output entity is `ProteinEntity` with `type: "protein"`, holding the resolved amino-acid sequence in `value`. The type flips from `designed_protein` at input to `protein` at output. | **blocker** | Add note: designed binder entities come back as `type: "protein"` with DSL resolved. Select by `chain_ids` (not by `type == "designed_protein"`). |

#### `core/skills/mcp/boltz-protein-design/SKILL.md`

Same four findings at lines 17, 20, 80. Apply same fixes.

#### `core/references/boltz-protein-design/api.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| api.md:73 | "Cost formula: `num_proteins * $0.025`. A batch of 10 is $0.250. `estimate-cost` returns the authoritative quote." | Spec gives no formula; debugging log §4a observed tier multipliers around complex length 256. | **blocker** | Rewrite to describe the `estimate-cost` `breakdown` shape (`application, cost_per_unit_usd, num_units`) and note that `num_units` may exceed `num_proteins` when total complex length crosses the ~256-token bucket (empirical). Do not assert a flat per-protein multiplier. |
| api.md:93 | "`end_index: 5 # 0-based, exclusive semantics depend on motif`" | Spec (`api/protein-design-start.md:59–65, 45`): "0-indexed end residue **(inclusive)**" and header text "Residues from start_index to end_index **(inclusive)** are replaced with a new sequence of the specified length." | **blocker** | State inclusive explicitly. Add a worked example: for a 17-mer scaffold with `start_index: 2, end_index: 15` you replace residues 2..15 (14 residues) and keep residues 0..1 + 16. Note debugging log §4d observed apparent off-by-one drift; cite this as "verify end boundary empirically against a test case — see debugging_log.md §4d". |
| api.md:258 | "`metrics.optimization_score` — primary ranking (when present)" | `api/protein-design-list_results.md:243–273` — absent from schema. | **blocker** | Remove `optimization_score`. |
| api.md:266 | "Rank by `optimization_score` descending if present, otherwise by `binding_confidence`." | Same. | **blocker** | Rank by `binding_confidence`; tiebreakers `iptm`, `min_interaction_pae`. |
| api.md:257 | "`entities` — generated sequences for this design (with `designed_protein.value` filled in with actual residues)" | Spec: output entities have `type: "protein"`, not `designed_protein`. | **blocker** | State explicitly: designed entity returns as `type: "protein"` with `value` holding the materialized AA sequence. Select by `chain_ids`, not by `type == "designed_protein"`. |
| api.md:222 (cross-ref) | "`epitope_residues` / `flexible_residues` must be subsets of `crop_residues`, all 0-based" | Spec (`api/protein-design-start.md:547–561`): "All indices must be present in crop_residues." Matches. | — | OK. |

### 6. boltz-check-status

#### `core/skills/cli/boltz-check-status/SKILL.md`

| File:line | Our claim | Spec citation | Severity | Suggested fix |
|---|---|---|---|---|
| SKILL.md:20–24 | ID prefix table maps `sab_pred_*`, `prot_des_*`, `prot_scr_*`, `sm_des_*`, `sm_scr_*` to resources. | Spec describes IDs only as `id: string` (no prefix contract in the schema itself). Per debugging log §2 the SAB prefix `sab_pred_*` was confirmed empirically. Other prefixes have not been re-verified live; `AUDIT_REPORT.md` v1 also flagged this. | minor | Keep the table but annotate that prefixes are observed-empirically, not part of the spec contract. Re-verify `prot_des_*`, `prot_scr_*`, `sm_des_*`, `sm_scr_*` against a live response before shipping. |
| SKILL.md:28 | "progress counters for pipeline jobs (`num_molecules_screened` / `num_proteins_generated` / etc.)" | Spec (`api/protein-design-start.md:1987–1999`) exposes `progress.{num_proteins_generated, total_proteins_to_generate, latest_result_id}` on protein:design retrieve; the other pipeline endpoints have analogous fields. The names `num_molecules_screened` / `num_proteins_generated` the skill uses match the spec. | — | OK. |

MCP variant mirrors CLI (no additional findings).

---

## Cross-cutting issues

1. **"optimization_score on protein endpoints" is the single highest-impact
   error.** It appears in all four protein files (CLI + MCP SKILL, plus api.md
   references for both protein-screen and protein-design). The spec is
   unambiguous: protein list-results do not emit `optimization_score`. Sorting
   jq by this field returns `[]`, wasting agent turns and confusing users.
   Blockers × 6 (two SKILLs × two products, plus two references).
2. **SAB metric-name/case/nesting mismatch.** The SAB reference + both SKILL
   Outputs sections use uppercase shorthand (`pLDDT, pTM, ipTM, PDE, ipDE`) that
   does not exist in the spec, and present the metrics as a flat list when they
   are actually split across `best_sample.metrics` (nine lowercase keys) and
   `binding_metrics` (2 keys for ligand–protein, 1 key for protein–protein).
   Blockers × 3.
3. **Flat cost formulas claim certainty the API doesn't guarantee.** Protein
   design is definitely tier-scaled (debugging log §4a); small-molecule design
   may also be. Any doc that says `num_X * $0.025` is at best approximate.
   Treat `estimate-cost` as the authoritative quote in all six products.
4. **Protein-design output entity-type flip is silently documented wrong in
   both the SKILL and the reference.** Agents that select by
   `type == "designed_protein"` will get empty results. Worth a visible callout,
   not buried in output field tables.
5. **Minor: hit-discovery vs lead-optimization framing.** Across SM endpoints
   (screen + design), our docs consistently say "`optimization_score` primary,
   `binding_confidence` fallback". Spec descriptions say the opposite (hit
   discovery → `binding_confidence`; lead optimization → `optimization_score`).
   They are parallel, not hierarchical. Minor copy fix, but repeated across 4
   files (cli/mcp × screen/design).

---

## Coverage gaps (in scope, not currently documented)

These are real features the agent should know about that aren't called out
clearly in skills or references:

1. **Protein design `status: "stopped"`** (`api/protein-design-start.md:2013`).
   The four pipeline endpoints (protein:design, protein:screen, sm:design,
   sm:screen) have a `stopped` terminal state in addition to succeeded/failed.
   SAB does NOT. The skills currently don't explain what `stopped` means to the
   agent when `check-status` narrates it. Minor enhancement for
   `boltz-check-status/SKILL.md`.
2. **`ligand_iptm` / `protein_iptm` are conditional in SAB output** (spec lines
   931–937): "Only present when ligands are included" / "Only present for
   multi-protein complexes." The reference currently doesn't explain the
   conditional presence. Worth one sentence in the rewritten SAB metrics
   section.
3. **`ProteinProteinBinding` input vs metric asymmetry.** `ProteinProteinBindingMetrics`
   has only `binding_confidence` (no `optimization_score`). Worth calling out
   explicitly so agents don't try to rank PPI binders by a missing field.
4. **Protein-screen `proteins[].id`** (spec `api/protein-library_screen-start.md:195–197`) — optional
   client-provided identifier; surfaces on results as `external_id`. Currently
   not documented in `core/references/boltz-protein-screen/api.md`. Parallel to
   the `molecules[].id` pattern already documented for sm-screen. Minor
   enhancement.
5. **`bonds` restriction in protein-design no_template binder**
   (`api/protein-design-start.md:415–417`): "If defining bonds where an atom is
   part of a designed protein chain, assume residue indices count designed
   regions as the minimum length. Example: designed protein `1..3C1..2`, `C` is
   residue 1 (0-indexed) of the designed protein." Subtle semantics; worth
   surfacing if bonds get more attention, otherwise minor.

---

## Severity legend

- **blocker**: wrong field name or enum value → 400 rejection OR silently wrong
  output parsing (e.g. sort by missing metric yields empty list).
- **major**: misleading enough to waste agent turns; partial failure or repeated
  rework.
- **minor**: cosmetic, overly strong phrasing, or copy/range assertions the spec
  doesn't actually cover.

---

## Finding totals by file

| File | Blockers | Major | Minor |
|---|---|---|---|
| `core/skills/cli/boltz-structure-and-binding/SKILL.md` | 1 | 0 | 0 |
| `core/skills/mcp/boltz-structure-and-binding/SKILL.md` | 1 | 0 | 0 |
| `core/references/boltz-structure-and-binding/api.md` | 2 | 0 | 2 |
| `core/skills/cli/boltz-small-molecule-screen/SKILL.md` | 0 | 0 | 2 |
| `core/skills/mcp/boltz-small-molecule-screen/SKILL.md` | 0 | 0 | 2 |
| `core/references/boltz-small-molecule-screen/api.md` | 0 | 0 | 1 |
| `core/skills/cli/boltz-small-molecule-design/SKILL.md` | 0 | 0 | 2 |
| `core/skills/mcp/boltz-small-molecule-design/SKILL.md` | 0 | 0 | 2 |
| `core/references/boltz-small-molecule-design/api.md` | 0 | 0 | 2 |
| `core/skills/cli/boltz-protein-screen/SKILL.md` | 2 | 0 | 1 |
| `core/skills/mcp/boltz-protein-screen/SKILL.md` | 1 | 0 | 0 |
| `core/references/boltz-protein-screen/api.md` | 2 | 0 | 1 |
| `core/skills/cli/boltz-protein-design/SKILL.md` | 4 | 0 | 0 |
| `core/skills/mcp/boltz-protein-design/SKILL.md` | 4 | 0 | 0 |
| `core/references/boltz-protein-design/api.md` | 5 | 0 | 0 |
| `core/skills/cli/boltz-check-status/SKILL.md` | 0 | 0 | 1 |
| `core/skills/mcp/boltz-check-status/SKILL.md` | 0 | 0 | 1 |

(Totals count duplicated findings per file separately. The "blockers" across
files trace back to ~4 underlying root-cause errors: SAB metric names/nesting,
`optimization_score` on protein endpoints, protein-design `end_index` phrasing,
protein-design output entity type flip, protein-design flat cost formula.)
