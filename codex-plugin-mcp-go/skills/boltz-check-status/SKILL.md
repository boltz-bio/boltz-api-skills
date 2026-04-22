---
name: boltz-check-status
description: List recent Boltz Compute jobs across all five endpoints, or inspect a single job by ID, and optionally pull its results onto disk. TRIGGER when the user asks what Boltz jobs are running, to check status, whether a screen finished, to resume a prior job, to download results for a job ID, to see how far along a job is, or after a session restart where earlier job IDs were lost.
---

## Workflow

Use this skill to recover state across sessions and to inspect or download results for prior Boltz jobs. No payload authoring — this skill only calls `boltz_list_jobs`, `boltz_get_job`, `boltz_resume_download`, and `boltz_get_local_run`.

Three modes, decided by what the user gives you:

### Mode 1 — "what's running?" (no ID provided)

Call `boltz_list_jobs`, merge across all five resources, and sort by `created_at` descending. Use `per_resource_limit=20` unless the user asks to see more. Each row includes prefix-derived `resource_type` / `resource_prefix` metadata:

- `pred_*` → `prediction`
- `prot_des_*` → `protein_design_ppi`
- `prot_scr_*` → `protein_library_screen_ppi`
- `sm_des_*` → `boltz_sm_design`
- `sm_scr_*` → `boltz_sm_screen`

### Mode 2 — "how's job $ID doing?" (ID provided)

Call `boltz_get_job` — it uses the job ID prefix to route to the correct `retrieve` endpoint, and only falls back to probing all five when the prefix is unfamiliar. Report `status`, progress counters for pipeline jobs (`num_molecules_screened` / `num_proteins_generated` / etc.), and the `error` if present. **Capture `idempotency_key` from the response** — you'll need it in Mode 3.

### Mode 3 — "my session died, pull the results"

This is the crash-recovery path. Two sub-cases:

**3a. User knows the original slug** (or the dir at `$ROOT/$RUN_NAME/` still exists):

Call `boltz_resume_download` with the original `run_name` / slug. The MCP server re-runs `download-results` in detached mode and the CLI reuses the existing `.boltz-run.json`, so only results past the last recorded cursor are pulled. If the run dir already exists, `id` can be omitted because the CLI can read the ID from metadata.

**3b. User has only the `$ID`:**

Run Mode 2 first to get `idempotency_key` from the retrieve response, then use it as `run_name` in Mode 3a. If the original submit didn't pass `idempotency_key`, pick a fresh slug and restart `download-results` from scratch — server-side the job is fine; only incremental-resume is lost.

Never run `start` again "to resume" — that creates a new job.

## MCP Tool Pattern

```text
ROOT = ${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}

Mode 1: what's running?
  boltz_list_jobs(per_resource_limit=20, total_limit=20)

Mode 2: how's job $ID doing?
  boltz_get_job(id=ID)

Mode 3: resume / pull results
  boltz_resume_download(
    id=ID,                      # optional if existing .boltz-run.json already has it
    run_name=RUN_NAME,
    output_dir=ROOT,
    poll_interval_seconds=30
  )

When the user asks for local download state or log output, call:
  boltz_get_local_run(run_name=RUN_NAME, output_dir=ROOT)
```

## Always Do This

- On an unfamiliar `$ID`, run Mode 2 (`boltz_get_job`) before Mode 3 (`boltz_resume_download`) so you capture `idempotency_key`.
- Prefer the original slug as `run_name` over the opaque `$ID` — it resumes into the existing dir with cursor.
- `boltz_resume_download` already starts detached `download-results`. Report the job ID, run name, output directory, and log path it returns; do not shell out yourself.
- The underlying CLI now writes JSONL progress by default and exposes `download-status`; `boltz_get_local_run` is the MCP-side equivalent plus log tail. Use it when the user wants local checkpoint state.
- Only check progress when the user asks. Use `boltz_get_job` for server-side status and `boltz_get_local_run` for local log / `.boltz-run.json` state.
- If `boltz_get_job` surfaces only `{"code":"VALIDATION_ERROR","message":"Request validation failed"}` with no `details`, that's expected for `predictions:structure-and-binding` failures — other endpoints include field paths.
- Never run `start` again on a failed or interrupted job. Fix the payload and submit with a new slug, or just resume with `boltz_resume_download`.

## Escape Hatch

- Upstream reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api <resource> list --help`, `boltz-api <resource> retrieve --help`, `boltz-api download-results --help`

Read [references/api.md](references/api.md) for per-resource `list` columns, `retrieve` record fields, and `download-results` resume semantics.

## Outputs

- Mode 1 / Mode 2 print structured data to stdout; present as a table.
- Mode 3 writes recovered artifacts under `$ROOT/$RUN_NAME/` — same layout as a fresh run: `.boltz-run.json`, `outputs/` (SAB) or `results/<pres_*>/` (screens and designs).
