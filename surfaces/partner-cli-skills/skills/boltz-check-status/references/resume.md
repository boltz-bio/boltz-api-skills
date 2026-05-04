# Resume and Recovery

Read this when the user wants to resume a dropped session, recover results by job ID, inspect local downloader state, or understand job ID routing.

## Job ID Prefixes

Use these observed prefixes to route `retrieve` calls. If a prefix is unfamiliar, fall back to probing all five resources.

- `sab_pred_*` -> `prediction` (`predictions:structure-and-binding`)
- `prot_des_*` -> `protein_design_ppi`
- `prot_scr_*` -> `protein_library_screen_ppi`
- `sm_des_*` -> `boltz_sm_design`
- `sm_scr_*` -> `boltz_sm_screen`

This mapping is observational, not a guaranteed API contract.

## Local Downloader State

When the user knows the original run name or local run directory, prefer local checkpoint inspection before remote API calls:

```bash
boltz-api --format json download-status \
  --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments"
```

## Resume Download

If the user knows the original slug/run name or local run directory:

```bash
boltz-api download-results \
  --id "<job-id>" --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments" \
  --poll-interval-seconds 30
```

Run this through the host harness's long-running/background command facility. The downloader emits JSONL progress on stderr by default and writes incremental state to `<output-root>/<run-name>/.boltz-run.json` so a re-run resumes from the recorded cursor.

If the run directory exists, `--id` can be omitted because the CLI can read the ID from metadata.

## Only Job ID Is Known

Run `retrieve` first and capture `idempotency_key`, then use that as `--name` for `download-results`. If the original submit did not pass an idempotency key, pick a fresh slug and download from scratch. Server-side the job is fine; only incremental local resume is lost.

Never run `start` again to resume an existing job.
