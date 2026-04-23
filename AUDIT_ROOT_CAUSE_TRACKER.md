# Audit v2 normalized tracker and root-cause map

Date: 2026-04-23

Inputs checked:

- Local audit: `AUDIT_REPORT_v2.md`
- Local distribution source: `core/skills/{cli,mcp}` and `core/references`
- Local generated/distribution surfaces: `surfaces/*` symlink to `core`
- Local legacy variants: `skills-python/` and `codex-plugin-python/`
- Local CLI help: `boltz-api` 0.7.1
- Hosted docs: `https://boltz-compute-api.stldocs.app/`

Short version:

- The CLI help/man page is not the source of most schema errors. It is mostly flag-level and does not describe output metrics, entity unions, or ranking fields.
- The hosted API Reference is mostly correct for the audited API shapes and metrics. It also now includes SAB `num_samples` and `model_options` bounds that the audit called absent.
- The hosted Guides are stale in several places and explain many v1 false positives, especially SAB `ligand_binding`, `output.sample_results`, and guide examples that omit `chain_type`.
- Current `core/` skill/reference files already contain many fixes that `AUDIT_REPORT_v2.md` lists as open. A few wording issues remain in `core`, and many stale claims remain in legacy Python variants and benchmarks.

## Surface legend

| Bucket | Meaning |
|---|---|
| `CLI help` | Output from installed `boltz-api --help` and subcommand help. |
| `Hosted API Ref` | API Reference pages under `/api/resources/...`. |
| `Hosted Guides` | Guide pages under `/guides/...`. |
| `Core CLI skill` | `core/skills/cli/.../SKILL.md`. |
| `Core MCP skill` | `core/skills/mcp/.../SKILL.md`. |
| `Core reference` | `core/references/.../api.md`. |
| `Legacy Python` | `skills-python/` and `codex-plugin-python/`; README marks these as legacy references, not distribution targets. |
| `Benchmarks` | `benchmarks/scenarios/*`. |

## Raw audit point tracker

This table tracks every finding or reversal called out in `AUDIT_REPORT_v2.md` before grouping into root causes.

### v1 corrections and false positives

| ID | Audit point | Current verification | Source of confusion | Current status |
|---|---|---|---|---|
| V1-01 | SAB `binding.type: ligand_protein_binding` should not be renamed to `ligand_binding`. | Hosted API Ref `Start` uses `type: "ligand_protein_binding"`; current core skills use it. Hosted Guide still uses stale `type: "ligand_binding"` in prediction examples. | Hosted Guides, not CLI help and not current core skills. | External docs issue: hosted Guide stale; core is correct. |
| V1-02 | SAB `protein_protein_binding` and plural `binder_chain_ids` are real. | Hosted API Ref lists `ProteinProteinBinding` with `binder_chain_ids` and `type: "protein_protein_binding"`. Core skills use this. | Prior audit trusted Guides over API Ref. | Not a core issue. |
| V1-03 | Protein design input `designed_protein.value` is correct, not `sequence`. | Hosted API Ref `protein/design/start` uses `DesignedProteinEntity.value`. Hosted Guide uses examples with `sequence` in protein design. Core references use `value`. | Hosted Guides stale. | External docs issue; core is correct. |
| V1-04 | SAB `ligand_ccd` is covered upstream. | Hosted API Ref lists `LigandCcdEntity`. Core reference documents it. | Prior guide-driven audit missed API Ref union. | Not an issue. |
| V1-05 | Protein screen/design `chain_selection.<id>.chain_type` is real. | Hosted API Ref lists `chain_type: "polymer"` and `chain_type: "ligand"`. Hosted protein guides omit `chain_type` in structure-template examples. Core references include it. | Hosted Guides stale. | External docs issue; core is correct. |
| V1-06 | Protein-screen `target.no_template` `bonds`, `constraints`, and `epitope_ligand_chains` are real. | Hosted API Ref lists these in the target union. Core references include them. | Prior guide-driven audit missed API Ref fields. | Not an issue. |
| V1-07 | `--model boltz-2.1` and SAB `model_options` are real. | CLI help exposes `--model`; Hosted API Ref lists `model_options`. Current core includes defaults. Hosted API Ref now also shows min/max bounds. | Local audit used a stale/static spec snapshot for bounds. | Core under-documents current hosted bounds; not a CLI issue. |
| V1-08 | SAB `num_samples` belongs inside `input`. | Hosted API Ref has `input.num_samples`; current core examples put it in the YAML body. | No current confusion. | Not an issue. |
| V1-09 | SAB `num_samples` range/default. | Hosted Guides and Hosted API Ref now show `num_samples` minimum 1 and maximum 10; Guide says default 1. Current core reference now documents the hosted-ref-backed 1-10 range and avoids asserting a default. | Hosted API Ref appears newer than audit's `/tmp` spec snapshot. | Resolved in core; default remains omitted unless API Ref confirms it. |
| V1-10 | Status-value table is out of scope for payload references. | CLI and hosted guides expose statuses; current check-status reference has status coverage. | Scope decision, not schema error. | No blocker. Minor check-status UX enhancement only. |
| V1-11 | `/stop` endpoints out of scope. | CLI help exposes `stop` for pipeline endpoints and not SAB; hosted API has stop pages. Skills do not use stop in normal submit/download workflows. | Scope decision. | Not a correctness bug. Could be optional workflow enhancement. |
| V1-12 | Presigned `url_expires_at` warning out of scope. | Hosted docs mention expiry; skills rely on `download-results` to fetch/cache. | Scope decision. | Not a core skill bug. |
| V1-13 | `/delete-data` eager deletion out of scope. | CLI help exposes `delete-data`; skills do not call it. | Scope decision. | Not a core skill bug. |
| V1-14 | Pagination `limit` / `after_id` out of scope. | CLI list-results exposes pagination flags; skills normally use `download-results` or list-results for ranking. | Scope decision. | Not a core payload-reference bug. |
| V1-15 | Progress-field section missing. | Check-status skills report progress counters. Hosted Guides show counters but some guide examples use questionable nesting like `screen.output.progress`. | Scope and docs consistency. | Mostly OK in core. Hosted Guide may need progress nesting review. |
| V1-16 | SM filter-level enum list missing from SKILL.md. | Core references list `recommended`, `extra`, `aggressive`, `disabled`; skills route to references. | Skill-vs-reference detail split. | Not an issue. |

### v2 surviving findings by file

| ID | Audit point | Current local state | CLI help? | Hosted docs? | Current status |
|---|---|---|---|---|---|
| F-SAB-01 | `core/skills/cli/boltz-structure-and-binding/SKILL.md` used uppercase/flat SAB metrics. | Fixed in current core CLI skill: nested `best_sample.metrics` / `all_sample_results[].metrics` and top-level `binding_metrics`. | CLI help does not contain metric schema. | Hosted API Ref agrees with fixed core; Hosted Guide still says `output.sample_results`. | Resolved in core; Hosted Guide stale. |
| F-SAB-02 | `core/skills/mcp/boltz-structure-and-binding/SKILL.md` same metric issue. | Fixed in current core MCP skill. | Not a CLI help issue. | Hosted API Ref agrees; Guide stale. | Resolved in core. |
| F-SAB-03 | `core/references/boltz-structure-and-binding/api.md` said `num_samples` 1-10/default. Audit said remove. | Current core documents 1-10 but omits a default. | CLI help does not expose body bounds. | Hosted API Ref now shows min 1/max 10; Hosted Guide says 1-10/default 1. | Resolved in core against current Hosted API Ref. |
| F-SAB-04 | `model_options` ranges in reference. Audit said only defaults are spec-backed. | Current core documents hosted-ref-backed bounds: recycling/sampling min 1 and step_scale 1.3-2. | CLI help does not expose body bounds. | Hosted API Ref shows recycling/sampling min 1, step_scale min 1.3/max 2. | Resolved in core against current Hosted API Ref. |
| F-SAB-05 | SAB binding metrics listed unconditionally. | Fixed in current core reference. | CLI help no metric schema. | Hosted API Ref confirms ligand-protein has `optimization_score`, protein-protein does not. | Resolved in core. |
| F-SAB-06 | SAB metrics list flat/wrong names in reference. | Fixed in current core reference. | CLI help no metric schema. | Hosted API Ref confirms fixed names/nesting. Hosted Guide still uses `sample_results`. | Resolved in core; Hosted Guide stale. |
| F-SM-SCR-01 | SM screen skill says `optimization_score` primary/fallback wording. | Fixed in current core CLI and MCP skills: sort by `binding_confidence` for hit discovery or `optimization_score` for lead optimization. | CLI help no ranking guidance. | Hosted API Ref says binding confidence is hit discovery, optimization score is lead optimization. | Resolved in core. |
| F-SM-SCR-02 | SM screen cost says `$0.025 per molecule`. | Fixed in current core reference and skills: cost is quoted by estimate-cost; numeric rate is approximate only. | CLI help no numeric cost. | Hosted API Ref only returns breakdown. | Resolved in core. |
| F-SM-SCR-03 | SM screen reference hit-vs-lead nuance. | Fixed in current core reference. | Not CLI. | Hosted API Ref has both metrics and descriptions. | Resolved in core. |
| F-SM-DES-01 | SM design skill flat `num_molecules * $0.025` cost. | Fixed in core CLI and MCP: approximate, quote estimate-cost. | CLI help says estimate includes SynFlowNet scheduler charges; no flat formula. | Hosted API Ref only returns breakdown. | Resolved in core. |
| F-SM-DES-02 | SM design skill ranks by `optimization_score` only. | Fixed in core CLI and MCP: binding confidence for hit discovery, optimization score for lead optimization. | Not CLI. | Hosted API Ref confirms descriptions. | Resolved in core. |
| F-SM-DES-03 | SM design reference `num_units: num_molecules + 1` asserted as formula. | Current core no longer documents the `+1` observation; it tells agents to quote `estimate-cost`. | CLI help's SynFlowNet scheduler wording likely seeded this claim. | Hosted API Ref only defines generic `breakdown`; no `+1`. | Resolved in core. |
| F-SM-DES-04 | SM design reference ranks by optimization score only. | Fixed in current core reference. | Not CLI. | Hosted API Ref supports hit-vs-lead distinction. | Resolved in core. |
| F-PROT-SCR-01 | Protein-screen CLI skill ranks by missing `optimization_score`. | Fixed in current core CLI skill. | CLI help no metric schema. | Hosted API Ref confirms no `optimization_score`. | Resolved in core. |
| F-PROT-SCR-02 | Protein-screen CLI output metrics include missing `optimization_score`. | Fixed in current core CLI skill. | Not CLI. | Hosted API Ref confirms no `optimization_score`. | Resolved in core. |
| F-PROT-SCR-03 | Protein-screen CLI cost `$0.025 per submitted protein`. | Fixed/softened in current core CLI skill. | CLI help no numeric cost. | Hosted API Ref only returns breakdown. | Resolved in core. |
| F-PROT-SCR-04 | Protein-screen MCP metrics include missing `optimization_score`. | Fixed in current core MCP skill. | Not CLI. | Hosted API Ref confirms no `optimization_score`. | Resolved in core. |
| F-PROT-SCR-05 | Protein-screen reference includes `optimization_score`. | Fixed in current core reference. | Not CLI. | Hosted API Ref confirms no `optimization_score`. | Resolved in core. |
| F-PROT-SCR-06 | Protein-screen reference says rank by `optimization_score` if present. | Fixed in current core reference. | Not CLI. | Hosted API Ref confirms ranking should use available fields. | Resolved in core. |
| F-PROT-SCR-07 | Protein-screen reference flat cost. | Fixed/softened in current core reference. | CLI help no numeric cost. | Hosted API Ref only returns breakdown. | Resolved in core. |
| F-PROT-DES-01 | Protein-design CLI skill flat `num_proteins * $0.025` cost. | Fixed in current core CLI skill. | CLI help no numeric formula. | Hosted API Ref only returns breakdown. | Resolved in core. |
| F-PROT-DES-02 | Protein-design CLI skill ranks by missing `optimization_score`. | Fixed in current core CLI skill. | Not CLI. | Hosted API Ref confirms no `optimization_score`. | Resolved in core. |
| F-PROT-DES-03 | Protein-design CLI outputs include missing `metrics.optimization_score`. | Fixed in current core CLI skill. | Not CLI. | Hosted API Ref confirms no `optimization_score`. | Resolved in core. |
| F-PROT-DES-04 | Protein-design CLI implies output `designed_protein.value`. | Fixed in current core CLI skill: output binder returns as `type: "protein"`. | Not CLI. | Hosted API Ref confirms output entity union starts with `type: "protein"`. | Resolved in core. |
| F-PROT-DES-05 | Protein-design MCP has same four issues. | Fixed in current core MCP skill. | Not CLI. | Hosted API Ref confirms fixed shape. | Resolved in core. |
| F-PROT-DES-06 | Protein-design reference flat cost formula. | Fixed in current core reference. | CLI help no numeric formula. | Hosted API Ref only returns breakdown. | Resolved in core. |
| F-PROT-DES-07 | Protein-design reference says `end_index` exclusive/ambiguous. | Fixed in current core reference: inclusive. | CLI help no schema detail. | Hosted API Ref says inclusive. | Resolved in core. |
| F-PROT-DES-08 | Protein-design reference includes/ranks by missing `optimization_score`. | Fixed in current core reference. | Not CLI. | Hosted API Ref confirms no `optimization_score`. | Resolved in core. |
| F-PROT-DES-09 | Protein-design reference says output `designed_protein.value`. | Fixed in current core reference: output type is `protein`, select by `chain_ids`. | Not CLI. | Hosted API Ref confirms output `type: "protein"`. | Resolved in core. |
| F-STATUS-01 | Check-status ID prefix table is empirical, not spec contract. | Current core CLI/MCP skills annotate it as empirical and say verified 2026-04-23. | CLI help does not define prefix contract. | Hosted API Ref examples use prefixes but schema is just string. | Resolved as observational caveat. |
| F-STATUS-02 | Progress counters OK. | Current core skills report progress counters. | CLI retrieve returns raw response; no issue. | Hosted API Ref has progress fields. | OK. |

### Cross-cutting and coverage points

| ID | Audit point | Current state | Source/root | Current status |
|---|---|---|---|---|
| X-01 | `optimization_score` on protein endpoints is the highest-impact error. | Fixed in current `core`. Still stale in legacy Python skills/scripts and some benchmark scenarios. | Local instruction drift from copying SM ranking model to protein workflows. | Core resolved; legacy/benchmarks stale. |
| X-02 | SAB metric name/case/nesting mismatch. | Fixed in current `core`. Still stale in some legacy references. Hosted Guide still uses `sample_results`, not `all_sample_results`/`best_sample`. | Hosted Guide and older local reference mismatch. | Core resolved; external guide/legacy stale. |
| X-03 | Flat cost formulas are unsafe. | Fixed/softened in most current core docs. Benchmarks still have flat cost expectations for SM/protein scenarios. | Empirical pricing got promoted to contract; API only exposes estimate response. | Mostly resolved in core; benchmarks stale. |
| X-04 | Protein-design output entity type flips from input `designed_protein` to output `protein`. | Fixed in current `core`. Legacy Python skill text still says the `designed_protein` entity gets realized sequence. | Local instruction drift from input schema to output schema. | Core resolved; legacy stale. |
| X-05 | SM `binding_confidence` vs `optimization_score` is hit-discovery vs lead-optimization, not primary/fallback. | Fixed in current SM design and SM screen core files. | Local instruction simplification, not CLI. | Resolved in core. |
| G-01 | Pipeline `stopped` status should be explained. | Current check-status skills explain that `stopped` is terminal for pipeline endpoints, partial results may be available, and SAB does not use it. Hosted Guides define stopped for pipeline pages. | Coverage gap in skills, not CLI/API mismatch. | Resolved in core. |
| G-02 | SAB `ligand_iptm` and `protein_iptm` conditional presence. | Fixed in current core SAB skills/reference. | Prior local omission. | Resolved in core. |
| G-03 | PPI binding metric asymmetry: no `optimization_score`. | Fixed in current core SAB skills/reference. | Prior flattening of binding metrics. | Resolved in core. |
| G-04 | Protein-screen `proteins[].id` surfaces as `external_id`. | Current core input and output reference documents optional `proteins[].id` and `external_id`. Hosted Guide documents it. | Core reference coverage gap. | Resolved in core. |
| G-05 | Protein-design no-template binder `bonds` residue-index semantics for designed regions. | Current core protein-design reference documents minimum-designed-length indexing for designed-chain bond references. | Coverage gap from API detail. | Resolved in core. |

### Extra issues found while normalizing

| ID | Point | Evidence | Source/root | Current status |
|---|---|---|---|---|
| E-01 | Hosted API Ref estimate-cost examples for SM/protein pages show `application: "structure_and_binding"` in response examples. | Hosted SM design and protein design estimate-cost pages both show generic example response with `application: "structure_and_binding"`. | Hosted API docs generator/example placeholder issue. | External docs issue; not caused by CLI or skills. |
| E-02 | Hosted API Ref now includes SAB bounds that `AUDIT_REPORT_v2.md` says are absent. | Hosted SAB Start page shows `num_samples` min 1/max 10 and `model_options` min/max. | Audit used stale `/tmp/boltz-docs/api` snapshot or docs changed after audit. | Resolved in core reference against current hosted API Ref. |
| E-03 | Hosted Guides show stale SAB output property `output.sample_results`. | Hosted prediction guide says `output.sample_results`; API Ref returns `all_sample_results` and `best_sample`. | Hosted Guides stale. | External docs issue. |
| E-04 | Benchmarks still encode some old expectations. | Scenario 3 and 4 use flat cost and/or rank by `optimization_score`; scenario 2 ranks SM screen by optimization score without hit-vs-lead distinction. | Benchmark drift from old skills. | Benchmark maintenance issue. |

## Root-cause analysis

### RC1: Hosted Guides drifted from the hosted API Reference

The most important upstream source issue is not the API Reference; it is the Guides. The Guides still contain stale examples for:

- SAB binding type: `ligand_binding` instead of `ligand_protein_binding`.
- SAB output: `output.sample_results` instead of the API Ref's `output.all_sample_results` plus `output.best_sample`.
- SAB binding metrics: Guide wording implies `optimization_score` is always present when binding is requested, but API Ref limits it to ligand-protein binding metrics.
- Protein design: guide examples use `sequence` where API Ref uses `value` for `designed_protein`.
- Protein structure-template examples: guides omit `chain_type` even though API Ref requires the discriminant.

This explains why v1 called several correct local skill instructions "invented" or "wrong." It was comparing against stale Guides instead of the API Reference.

Owner/source: hosted docs Guides.

Action: fix Guides or add a docs rule in this repo: API Reference beats Guides when they disagree.

### RC2: Local skills copied one metric/ranking model across endpoints

The high-impact local blocker was not from CLI help. It came from local skill/reference prose assuming all result endpoints have the small-molecule metric set, especially `optimization_score`.

Correct split:

- Small molecule design/screen: `binding_confidence` for hit discovery; `optimization_score` for lead optimization.
- Protein design/screen: no `optimization_score`; rank by `binding_confidence`, with `iptm` high and `min_interaction_pae` low as tiebreakers.
- SAB: sample metrics are nested under sample results; binding metrics are separate and variant-specific.

Current core state: fixed for protein and SAB; SM screen workflow wording still needs cleanup.

Owner/source: local `core/skills/{cli,mcp}` and `core/references`, mostly already corrected.

### RC3: Cost semantics are not a schema contract

The API Reference only promises `estimate-cost` response shape:

- `breakdown.application`
- `breakdown.cost_per_unit_usd`
- `breakdown.num_units`
- `estimated_cost_usd`
- `disclaimer`

Flat formulas such as `num_proteins * $0.025` came from empirical observations and benchmark assumptions. The CLI help contributed one phrase for SM design: "Includes the SynFlowNet generation charges implied by the scheduler iteration cap plus Boltz2 scoring..." That can explain why a local reference mentioned scheduler iterations, but it does not justify a stable formula.

Owner/source: local docs/benchmarks and one CLI-help phrase.

Action: keep "quote estimate-cost" as the instruction everywhere; treat numeric examples as empirical only.

### RC4: Core and generated/legacy copies are out of sync

Current distribution surfaces under `surfaces/*` symlink to `core`, so packaged current surfaces inherit core fixes. However, legacy Python variants and benchmarks still contain older wording and sometimes old scripts:

- Protein scripts still read/sort optional `optimization_score` columns.
- Legacy protein-design skill text still implies output `designed_protein` realization.
- Legacy references still mention optimization-score sorting for protein.
- Benchmark scenarios still expect flat cost and old ranking behavior.

Owner/source: legacy directories and benchmark docs, not active `core`.

Action: either mark legacy clearly as excluded from audits, or update/remove stale legacy and benchmark text so repo-wide greps do not keep rediscovering fixed issues.

### RC5: CLI help is useful for commands, not schema truth

Installed `boltz-api` 0.7.1 help shows:

- Resource names and subcommands.
- Flag names like `--input`, `--model`, `--target`, `--protein`.
- Stop/delete-data/list-results support.
- Some short descriptions, including SM design estimate-cost scheduler wording.

It does not show:

- Output metric schemas.
- Entity union details.
- SAB binding metric variants.
- Protein result metric sets.
- Protein-design output entity type.

So when the issue is a wrong metric name, wrong output nesting, or wrong entity field, it is not coming from the CLI man page. The CLI help can only confirm command availability and broad option names.

Owner/source: not the root of most audited blockers.

Action: keep skills pointing to `references/api.md` or hosted API Ref for schema details; use CLI help only for command/flag availability.

### RC6: The audit's canonical snapshot has drifted from current hosted docs

Two audit findings now disagree with the live hosted API Reference:

- SAB `num_samples` bounds.
- SAB `model_options` bounds.

The audit's `/tmp/boltz-docs/api/*.md` snapshot is not present in this workspace, and the live hosted API Ref currently shows those bounds. The local reference now follows the hosted API Ref for these fields.

Owner/source: audit input snapshot vs live hosted API Ref drift.

Action: pick a single canonical source for future audits. Current core now follows the hosted API Ref for these SAB bounds.

## Current actionable list

Done in active `core` files:

1. Fixed `core/skills/cli/boltz-small-molecule-screen/SKILL.md` workflow step 7 to remove the optimization-score fallback hierarchy.
2. Fixed `core/skills/mcp/boltz-small-molecule-screen/SKILL.md` workflow step 7 the same way.
3. Fixed `core/references/boltz-small-molecule-screen/api.md` so `optimization_score` is lead-optimization ranking, not the primary ranking metric.
4. Restored hosted-API-backed SAB `num_samples` and `model_options` bounds in `core/references/boltz-structure-and-binding/api.md`.
5. Added optional `proteins[].id` / `external_id` guidance to `core/references/boltz-protein-screen/api.md`.
6. Added protein-design no-template bond/index semantics to `core/references/boltz-protein-design/api.md`.
7. Added `stopped` status meaning to both check-status skills.
8. Simplified SM design/screen cost references to prefer `estimate-cost` over hardcoded formulas.

Still open:

1. Decide whether to update or explicitly exclude legacy Python variants and benchmark scenarios from future audits.
2. File hosted docs issues for stale Guides and estimate-cost example responses.
