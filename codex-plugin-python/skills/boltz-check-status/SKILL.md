---
name: boltz-check-status
description: List recent Boltz Compute jobs across all five endpoints, or inspect a single job by ID, and optionally pull its results onto disk. TRIGGER when the user asks what Boltz jobs are running, to check status, whether a screen finished, to resume a prior job, to download results for a job ID, to see how far along a job is, or after a session restart where earlier job IDs were lost.
---

## Workflow

Use this skill to recover state across sessions and to inspect or download results for prior Boltz jobs.

1. If the user does not provide a job ID, list recent jobs across all five Boltz resource types and summarize the most relevant rows.
2. If the user provides a job ID, inspect that job, report the resource type and current status, and include progress or error details when present.
3. If the user asks to recover outputs, run the query wrapper with `--download` so results and structures are written locally.

## Always Do This

- Use the Python SDK wrapper only: `python scripts/query.py ...`.
- Expect authentication through `BOLTZ_API_KEY`; `BOLTZ_COMPUTE_API_KEY` also works.
- Prefer the default list mode first when the user has lost track of IDs or resource types.
- When inspecting a specific job, explain whether it is still running, succeeded, failed, or stopped.
- When a failed `structure_and_binding` job shows only `VALIDATION_ERROR` / `Request validation failed`, explain that this endpoint currently omits field-level `details` and point the user first to missing polymer `modifications: []`.
- When `--download` is used, tell the user where files were written under `$BOLTZ_OUTPUT_DIR/<job_id>/`.

## Input Normalization

- Use the Boltz ID prefix to infer the resource type when present:
  - `pred_*` → `prediction`
  - `prot_des_*` → `protein_design_ppi`
  - `prot_scr_*` → `protein_library_screen_ppi`
  - `sm_des_*` → `boltz_sm_design`
  - `sm_scr_*` → `boltz_sm_screen`
- If the prefix is unfamiliar, the wrapper falls back to probing all supported resources.
- Use `--workspace-id` only when the user explicitly needs a non-default workspace and has the right key scope.
- Use `--json` only when structured machine-readable output is more useful than the default text table.

## Read This Reference When Needed

- Read [references/api.md](references/api.md) for:
  - the exact SDK methods covered by this status skill
  - list mode parameters and returned columns
  - inspect mode behavior, downloadable artifacts, and result pagination
  - details about which resources expose `list_results()`

## Command Pattern

List recent jobs:

```bash
python scripts/query.py
```

Inspect one job:

```bash
python scripts/query.py --id JOB_ID
```

Inspect and recover outputs:

```bash
python scripts/query.py --id JOB_ID --download
```

## Outputs

- Default mode prints a merged recent-job view.
- Inspect mode prints JSON for the located job.
- Download mode writes recovered artifacts under `$BOLTZ_OUTPUT_DIR/<job_id>/`.
