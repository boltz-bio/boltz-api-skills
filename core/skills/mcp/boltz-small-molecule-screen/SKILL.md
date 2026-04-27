---
name: boltz-small-molecule-screen
description: Score a user-supplied SMILES library against a protein target with the Boltz Compute API and return ranked binding and structure metrics with per-hit structures. TRIGGER when the user wants to virtually screen, dock, or rank an existing compound library against a target. Not for designing new molecules and not for a single one-off docking pose.
---

## Workflow

Use this skill when the user already has candidate molecules.

1. Normalize the library from raw SMILES, a CSV (auto-detect the SMILES column), `.smi`, or `.txt` into the `molecules` list. Each entry is `{smiles, id?}`; the optional `id` is echoed back as `external_id` on each result.
2. Normalize the target: one or more protein sequences into `target.entities`, plus optional `pocket_residues` (0-based) and/or `reference_ligands` (SMILES of known binders to seed pocket detection).
3. Keep default server-side filtering unless the user asks for custom filters — only add `molecule_filters` on explicit request.
4. Author the payload object, call `boltz_estimate_run` with `resource="small-molecule:library-screen"`, show the user the USD cost, and wait for explicit confirmation.
5. Call `boltz_submit_run` to submit. It starts detached `download-results` polling internally and returns the job ID, run name, and output directory.
6. After `boltz_submit_run` returns, report the job ID, run name, and output directory, then end the turn immediately. Do not run shell background commands yourself unless you're debugging the MCP server.
7. When done, rank via `list-results` (currently not exposed as a dedicated MCP tool; shell out with `boltz-api small-molecule:library-screen list-results --id "$JOB_ID" --format jsonl`). **Do not** rank from the per-hit `metrics.json` files on disk: they carry `external_id: null` / `smiles: null`, so you can't map scores back to your input library without `list-results`. Sort by `binding_confidence` for hit discovery or `optimization_score` for lead optimization; these are parallel intents, not a fallback hierarchy. Report the top 5-10 hits with `smiles`, the chosen ranking metric, and key confidence metrics, then point the user at `$ROOT/$RUN_NAME/results/`.

**Heads-up: the `results/<pres_*>/` directory count is usually less than `len(molecules)`.** Default server-side `molecule_filters` (SMARTS catalog at level `recommended`) silently drops candidates — the drop is not logged in `.boltz-run.json` or surfaced by `boltz_get_local_run`. Typical drop rate is 20–30% on generic drug libraries. `list-results` is the authoritative filtered list.

## MCP Tool Pattern

```text
ROOT = ${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}
RUN_NAME = "sm-screen-<target>-<library>-v1"

1. Estimate
   boltz_estimate_run(
     resource="small-molecule:library-screen",
     payload=<request body object>
   )

2. Confirm with user, then submit
   boltz_submit_run(
     resource="small-molecule:library-screen",
     run_name=RUN_NAME,
     output_dir=ROOT,
     poll_interval_seconds=30,
     payload=<same request body object>
   )

`boltz_submit_run` submits synchronously, then starts detached `download-results`
internally and returns `{id, run_name, output_dir, log_path, download_pid}`.
```

Payload keys in the request body are `molecules`, `target`, `molecule_filters` — the API body field names, not the CLI flag names `--molecule` / `--target` / `--molecule-filters`.

## Always Do This

- Keep the payload field names exactly as the API body names shown in `references/api.md`.
- If you drop to raw CLI for debugging, prefer one merged top-level `--input @yaml://payload.yaml` (or `@json://...`) and keep `--idempotency-key` / `--workspace-id` top-level. Direct object flags such as `--target @yaml://target.yaml`, `--molecule-filters @json://filters.json`, or repeated `--molecule @json://mol-1.json` entries still work as overrides. Piped YAML / JSON on stdin also works, but it must use API body field names.
- Treat pocket residue indices as 0-based.
- Do not invent medicinal-chemistry filters. Only add `molecule_filters` if the user asks; mention the catalog as an option.
- Use the same descriptive slug as `run_name`; the MCP server reuses it as both `--idempotency-key` and `--name`.
- `boltz_submit_run` already starts detached `download-results`. Do not run `boltz-api download-results` yourself from the skill flow.
- Only check status when the user asks. Use `boltz_get_job` for server-side status and `boltz_get_local_run` for local log / `.boltz-run.json` state.
- If detached download needs to be restarted, use `boltz_resume_download` with the same `run_name`.
- Cost is approximately $0.025 per molecule for small targets (may scale with complex size). `boltz_estimate_run` returns the authoritative quote — always use it.
- Poll interval: `poll_interval_seconds=30` is a reasonable default; libraries can run 10–60 min depending on size.

## Escape Hatch

- Payload reference: <https://boltz-compute-api.stldocs.app/api/python/resources/small_molecule/subresources/library_screen/methods/start>
- CLI flag names: `boltz-api small-molecule:library-screen start --help`

Read [references/api.md](references/api.md) for the `molecules`, `target`, and `molecule_filters` shapes, including the catalog of built-in SMARTS filters and RDKit descriptor ranges.

## Outputs

Under `$ROOT/$RUN_NAME/`:

- `.boltz-run.json` — run metadata
- `results/<pres_*>/archive.tar.gz` and `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}` — one per scored molecule

Rank via `list-results` (shell out to `boltz-api small-molecule:library-screen list-results --id "$JOB_ID" --format jsonl` — not yet a dedicated MCP tool). It returns `external_id`, `smiles`, and metrics together per hit. The per-hit `metrics.json` files on disk have `external_id: null` / `smiles: null`, so ranking from on-disk files alone loses the input-library mapping (tracked as a CLI bug — see CLI_BUG_REPORT.md §7).

Per-result metrics (all 7 always present for sm:library-screen): `binding_confidence` — primary metric for **hit discovery**; `optimization_score` — for **lead-optimization** ranking (binding strength). These are parallel intents, not a primary/fallback hierarchy. Sort by whichever matches the user's goal. Also available: `structure_confidence`, `complex_plddt`, `complex_iplddt`, `iptm`, `ptm`.
