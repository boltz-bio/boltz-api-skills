---
name: boltz-protein-screen
description: Score a user-supplied library of protein sequences against a target with the Boltz Compute API and return ranked binding and structure metrics with per-hit complex structures. TRIGGER when the user wants to rank an existing set of proteins, peptides, antibodies, nanobodies, or binders against a target. Not for designing new proteins and not for small molecules.
---

## Workflow

Use this skill when the user already has candidate proteins / peptides / antibodies / nanobodies.

1. Normalize the binder library into `proteins` — a list of candidate complexes. For a simple sequence library each entry has one protein entity; multi-chain candidates (antibody heavy+light) are also allowed.
2. Pick the target variant:
   - `structure_template` — user has a CIF/PDB file or URL; select which chains are polymer vs ligand, which residues to keep (`crop_residues`), and optionally `epitope_residues` / `flexible_residues`.
   - `no_template` — user has only sequences; pass them as `target.entities` plus optional `epitope_residues`.
3. Don't add `bonds` / `constraints` unless the user asks for geometric steering.
4. Author the payload object, call `boltz_estimate_run` with `resource="protein:library-screen"`, show the USD cost, and wait for explicit confirmation.
5. Call `boltz_submit_run` to submit. It starts detached `download-results` polling internally and returns the job ID, run name, and output directory.
6. After `boltz_submit_run` returns, report the job ID, run name, and output directory, then end the turn immediately. Do not run shell background commands yourself unless you're debugging the MCP server.
7. Rank hits by `binding_confidence` descending (primary). Use `iptm` (higher is better) and `min_interaction_pae` (lower is better) as tiebreakers. `optimization_score` is **not emitted** for `protein:library-screen` — do not sort by it. Report top 5–10 with the sequence identifier, key metrics, and structure path.

## MCP Tool Pattern

```text
ROOT = ${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}
RUN_NAME = "protein-screen-<target>-<library>-v1"

1. Estimate
   boltz_estimate_run(
     resource="protein:library-screen",
     payload=<request body object>
   )

2. Confirm with user, then submit
   boltz_submit_run(
     resource="protein:library-screen",
     run_name=RUN_NAME,
     output_dir=ROOT,
     poll_interval_seconds=30,
     payload=<same request body object>
   )

`boltz_submit_run` submits synchronously, then starts detached `download-results`
internally and returns `{id, run_name, output_dir, log_path, download_pid}`.
```

Payload keys are `proteins`, `target` — API body field names.

## Always Do This

- For `structure_template`, embed CIF/PDB bytes with `@data:///abs/path/target.cif` inside the `structure.data` field. Don't use bare `@path` (the auto-sniff once sent CIF as plain text into a base64 field and broke the server parser).
- Residue indices are 0-based. `epitope_residues` and `flexible_residues` must be subsets of `crop_residues`.
- Keep the payload field names exactly as the API body names shown in `references/api.md`.
- If you drop to raw CLI for debugging, prefer one merged top-level `--input @yaml://payload.yaml` (or `@json://...`) and keep `--idempotency-key` / `--workspace-id` top-level. Direct object flags such as `--target @yaml://target.yaml` or repeated `--protein @json://protein-1.json` entries still work as overrides. Piped YAML / JSON on stdin also works, but it must use API body field names.
- Use the same descriptive slug as `run_name`; the MCP server reuses it as both `--idempotency-key` and `--name`.
- `boltz_submit_run` already starts detached `download-results`. Do not run `boltz-api download-results` yourself from the skill flow.
- Only check status when the user asks. Use `boltz_get_job` for server-side status and `boltz_get_local_run` for local log / `.boltz-run.json` state.
- If detached download needs to be restarted, use `boltz_resume_download` with the same `run_name`.
- Cost scales with total complex length (target + candidate). Typically ≈$0.025 per submitted candidate for small complexes, more for larger ones. Quote the exact figure from `boltz_estimate_run`.

## Escape Hatch

- Payload reference: <https://boltz-compute-api.stldocs.app/api/python/resources/protein/subresources/library_screen/methods/start>
- CLI flag names: `boltz-api protein:library-screen start --help`

Read [references/api.md](references/api.md) for the `proteins` list shape and both `target` variants (structure_template with `chain_selection`, and no_template with epitope hints).

## Outputs

Under `$ROOT/$RUN_NAME/`:

- `.boltz-run.json`
- `results/<pres_*>/archive.tar.gz` — one dir per scored binder
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Per-result metrics: `binding_confidence` (primary), `structure_confidence`, `iptm` (higher better), `min_interaction_pae` (lower better), `helix_fraction`, `sheet_fraction`, `loop_fraction`. **No `optimization_score`** on this endpoint — sorting by it returns an empty list.
