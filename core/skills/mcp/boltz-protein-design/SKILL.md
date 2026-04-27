---
name: boltz-protein-design
description: Generate novel protein binders (peptide, antibody, nanobody, or custom protein) for a target with the Boltz Compute API and return ranked designed sequences with predicted complex structures. TRIGGER when the user wants to design, generate, propose, or invent new proteins/peptides/antibodies/nanobodies/binders for a target. Not for screening user-supplied proteins and not for small molecules.
---

## Workflow

Use this skill when the user wants de novo protein / peptide / antibody / nanobody binders.

1. Normalize the target (same shape as protein-screen): `structure_template` if a CIF/PDB is available, else `no_template`.
2. Pick the `binder_specification` variant:
   - `structure_template` — redesign motifs in an existing binder scaffold (CIF + `design_motifs` with `replacement` / `insertion` segments).
   - `no_template` — generate from the sequence DSL (fixed residues + designed segments like `5..10` or `8`).
3. Pick `modality` — a **generation-config switch only**, not a scaffold loader. The API will not auto-supply an antibody framework or nanobody scaffold; for `antibody` / `nanobody` you must provide your own scaffold via `binder_specification.structure_template` (or sequence components via `no_template`). Options:
   - `custom_protein` — general de novo protein binder. Cys allowed. Includes a design-folding step and the largest-hydrophobic-patch filter. Use this for `protein-anything`, `protein-small_molecule`, and `protein-redesign` workflows from boltzgen.
   - `peptide` — short / cyclic peptide binder. **No Cys** generated in inverse folding. No design-folding step. No LHP filter. Pair with `cyclic: true` on the designed entity for head-to-tail peptides.
   - `antibody` — designs CDRs only on a Fab framework you supply. Same gen-config as `peptide` (no Cys, no design folding, no LHP filter).
   - `nanobody` — same gen-config as `antibody`, for VHH scaffolds you supply.
4. Pick `num_proteins` — minimum **10**, server rejects lower. If the user says a smaller number, explain the floor and propose 10.
5. Add `rules` only on request (`excluded_amino_acids`, `excluded_sequence_motifs` with `X` wildcards, `max_hydrophobic_fraction`).
6. Author the payload object, call `boltz_estimate_run` with `resource="protein:design"`, show the USD cost, and wait for explicit confirmation. **Cost scales with total complex length** (target + binder), not just `num_proteins`. A small peptide + small target runs ≈$0.025 per design; larger complexes (e.g. GFP + 20-mer binder) run ≈$0.05 per design. Always quote the exact figure returned by `boltz_estimate_run`.
7. Call `boltz_submit_run` to submit. It starts detached `download-results` polling internally and returns the job ID, run name, and output directory.
8. After `boltz_submit_run` returns, report the job ID, run name, and output directory, then end the turn immediately. Do not run shell background commands yourself unless you're debugging the MCP server.
9. Rank by `binding_confidence` descending (primary). Use `iptm` (higher is better) and `min_interaction_pae` (lower is better) as tiebreakers. `optimization_score` is **not emitted** for `protein:design` — do not sort by it. Report top 5–10 designs with sequence, key metrics, and structure path.

## MCP Tool Pattern

```text
ROOT = ${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}
RUN_NAME = "protein-design-<modality>-<target>-v1"

1. Estimate
   boltz_estimate_run(
     resource="protein:design",
     payload=<request body object>
   )

2. Confirm with user, then submit
   boltz_submit_run(
     resource="protein:design",
     run_name=RUN_NAME,
     output_dir=ROOT,
     poll_interval_seconds=60,
     payload=<same request body object>
   )

`boltz_submit_run` submits synchronously, then starts detached `download-results`
internally and returns `{id, run_name, output_dir, log_path, download_pid}`.
```

Payload keys are `num_proteins`, `target`, `binder_specification` — API body field names.

## Always Do This

- Enforce `num_proteins >= 10` before calling `estimate-cost`. Server rejects anything lower.
- Cost scales with total complex length (target + binder). Do not quote a flat `num_proteins * $0.025` formula; always quote the exact figure returned by `boltz_estimate_run`. Empirically: minimal peptide + small target ≈$0.025/design; GFP-sized target + 20-mer binder ≈$0.05/design.
- Residue indices are 0-based everywhere (`design_motifs.start_index`/`end_index`, `after_residue_index`, `epitope_residues`, `flexible_residues`, bonds, constraints).
- For CIF/PDB bytes, use `@data:///abs/path/file.cif` inside `structure.data`. Don't use bare `@path`.
- Sequence DSL for `designed_protein.value`: uppercase letters = fixed residues; integer `N` = exactly `N` designed residues; `MIN..MAX` = variable-length designed segment. Examples: `"20"`, `"5..10"`, `"ACDE8GHI"`, `"MKTAYI5..10VKSHFSRQ"`.
- Keep the payload field names exactly as the API body names shown in `references/api.md`.
- If you drop to raw CLI for debugging, prefer one merged top-level `--input @yaml://payload.yaml` (or `@json://...`) and keep `--idempotency-key` / `--workspace-id` top-level. Direct object flags such as `--target @yaml://target.yaml` or `--binder-specification @json://binder.json` still work as overrides. Piped YAML / JSON on stdin also works, but it must use API body field names.
- Use the same descriptive slug as `run_name`; the MCP server reuses it as both `--idempotency-key` and `--name`.
- `boltz_submit_run` already starts detached `download-results`. Do not run `boltz-api download-results` yourself from the skill flow.
- Only check status when the user asks. Use `boltz_get_job` for server-side status and `boltz_get_local_run` for local log / `.boltz-run.json` state.
- If detached download needs to be restarted, use `boltz_resume_download` with the same `run_name`.
- Only add `rules` on explicit user request.

## Escape Hatch

- Payload reference: <https://boltz-compute-api.stldocs.app/api/python/resources/protein/subresources/design/methods/start>
- CLI flag names: `boltz-api protein:design start --help`

Read [references/api.md](references/api.md) for both `binder_specification` variants, the motif shapes, the sequence DSL, and the `target` variants.

## Outputs

Under `$ROOT/$RUN_NAME/`:

- `.boltz-run.json`
- `results/<pres_*>/archive.tar.gz` — one dir per generated design
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Per-result fields:

- `id`, `artifacts.{structure, archive}`
- `entities` — the generated designs. **Type-flip gotcha:** the binder entity comes back as `type: "protein"` (not `"designed_protein"`), with the DSL resolved to a real AA sequence in `value`. Select the binder by `chain_ids` (the ID you assigned at submit time), **not** by `type == "designed_protein"`.
- `metrics.binding_confidence` — **primary ranking metric**
- `metrics.structure_confidence`
- `metrics.iptm` (higher is better)
- `metrics.min_interaction_pae` (lower is better)
- `metrics.helix_fraction` / `sheet_fraction` / `loop_fraction`

**No `optimization_score` on this endpoint.** Sorting by it returns an empty list.
