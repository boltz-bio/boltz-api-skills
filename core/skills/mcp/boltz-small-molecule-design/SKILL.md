---
name: boltz-small-molecule-design
description: Generate novel small-molecule binders for a protein target with the Boltz Compute API and return ranked candidate SMILES with predicted complex structures. TRIGGER when the user wants to design, generate, or propose new ligands or hits for a target and does not already have a compound library. Not for screening user-supplied molecules.
---

## Workflow

Use this skill when the user wants de novo small-molecule binders (no existing library).

1. Normalize the target: one or more protein sequences into `target.entities`, plus optional `pocket_residues` (0-based) and/or `reference_ligands` (known binders to seed pocket detection).
2. Pick `num_molecules` — minimum **10**, server rejects anything lower. If the user says a smaller number, explain the floor and propose 10.
3. Only add `chemical_space` (e.g. `"enamine_real"`) if the user explicitly wants synthesis-aware generation within that library.
4. Only add `molecule_filters` on explicit request — the default filtering is usually fine.
5. Author the payload object, call `boltz_estimate_run` with `resource="small-molecule:design"`, show the USD cost, and wait for explicit confirmation. Cost is approximately $0.025 per molecule for small targets (may scale with complex size); always quote `estimated_cost_usd` from the response rather than a hardcoded formula.
6. Call `boltz_submit_run` to submit. It starts detached `download-results` polling internally and returns the job ID, run name, and output directory.
7. After `boltz_submit_run` returns, report the job ID, run name, and output directory, then end the turn immediately. Do not run shell background commands yourself unless you're debugging the MCP server.
8. Rank hits by `binding_confidence` (for **hit discovery**) or `optimization_score` (for **lead optimization**, binding strength) — these are parallel intents, not a primary/fallback hierarchy. Sort by whichever matches the user's goal. Report top 5–10 with `smiles`, the chosen ranking metric, and structure path.

## MCP Tool Pattern

```text
ROOT = ${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}
RUN_NAME = "sm-design-<target>-<batch>-v1"

1. Estimate
   boltz_estimate_run(
     resource="small-molecule:design",
     payload=<request body object>
   )

2. Confirm with user, then submit
   boltz_submit_run(
     resource="small-molecule:design",
     run_name=RUN_NAME,
     output_dir=ROOT,
     poll_interval_seconds=60,
     payload=<same request body object>
   )

`boltz_submit_run` submits synchronously, then starts detached `download-results`
internally and returns `{id, run_name, output_dir, log_path, download_pid}`.
```

Payload keys are `num_molecules`, `target`, `chemical_space`, `molecule_filters` — the API body field names.

## Always Do This

- Enforce `num_molecules >= 10` before calling `estimate-cost`. The server rejects smaller batches.
- Cost is approximately $0.025 per molecule for small targets (may scale with complex size). Always quote `estimated_cost_usd` from `boltz_estimate_run` rather than a hardcoded per-molecule rate.
- Treat pocket residue indices as 0-based.
- Keep the payload field names exactly as the API body names shown in `references/api.md`.
- If you drop to raw CLI for debugging, prefer one merged top-level `--input @yaml://payload.yaml` (or `@json://...`) and keep `--idempotency-key` / `--workspace-id` top-level. Direct object flags such as `--target @yaml://target.yaml` or `--molecule-filters @json://filters.json` still work as overrides. Piped YAML / JSON on stdin also works, but it must use API body field names.
- Use the same descriptive slug as `run_name`; the MCP server reuses it as both `--idempotency-key` and `--name`.
- `boltz_submit_run` already starts detached `download-results`. Do not run `boltz-api download-results` yourself from the skill flow.
- Only check status when the user asks. Use `boltz_get_job` for server-side status and `boltz_get_local_run` for local log / `.boltz-run.json` state.
- If detached download needs to be restarted, use `boltz_resume_download` with the same `run_name`.
- Do not invent filters; only add `molecule_filters` on user request.

## Escape Hatch

- Payload reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api small-molecule:design start --help`

Read [references/api.md](references/api.md) for the `target`, `chemical_space`, and `molecule_filters` shapes (filter catalog matches the screen endpoint).

## Outputs

Under `$ROOT/$RUN_NAME/`:

- `.boltz-run.json`
- `results/<pres_*>/archive.tar.gz` — one dir per generated candidate
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Per-result fields: `smiles`, `metrics.binding_confidence` (primary for **hit discovery**), `metrics.optimization_score` (for **lead optimization**, binding strength — parallel intent, not fallback), `metrics.structure_confidence`, `metrics.complex_plddt`, `metrics.complex_iplddt`, `metrics.iptm`, `metrics.ptm`.
