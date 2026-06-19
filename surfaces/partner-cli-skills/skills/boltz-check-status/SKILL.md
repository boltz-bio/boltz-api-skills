---
name: boltz-check-status
description: Boltz job status and result recovery. Use when listing jobs, checking progress, resuming downloads, recovering results, or downloading an existing job ID. Not for starting new jobs.
---

## Workflow

If `boltz-api` reports missing or expired authentication, surface the error to the user. Do not attempt to re-authenticate; the host environment must provide `BOLTZ_API_KEY`.

Use this skill to recover state across sessions and to inspect or download results for prior Boltz jobs. No payload authoring — this skill only calls `list` / `retrieve` / `download-results` / `download-status`.

Use four modes:

1. Local progress: if the user knows the run name / run dir, prefer `download-status` before remote API calls.
2. List recent jobs: enumerate all six resources, merge, and sort by `created_at` descending.
3. Retrieve one job: use the job ID prefix when known; otherwise probe resources until one succeeds.
4. Resume/download results: run `download-results` with the original run name when possible. Never run `start` again to resume.

ADME jobs use the prefix `adme_pred_*` and show up in Modes 2-3 (`list` / `retrieve`) like the others. ADME has no `download-results`/archive step, so Mode 4 doesn't apply — recover its scores by re-running `retrieve` (read `output.molecules[]`) or from the local `run.json`.

Read [references/resume.md](references/resume.md) before recovering a dropped session, mapping job ID prefixes, or choosing a run name for `download-results`. Read [references/api.md](references/api.md) for per-resource `list` columns, `retrieve` fields, and result semantics.

## Command Pattern

```bash
# Replace placeholders with concrete absolute paths before running.

# Local helper: inspect local checkpoint state without API calls.
boltz-api --format json download-status \
  --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments"

# Mode 1: list recent jobs across all 6 resources.
# NB: the CLI emits one JSON object per record (streamed, no {data:[]} wrapper).
# --limit is per-page and the CLI auto-paginates, so cap each explicit command with head.
boltz-api predictions:structure-and-binding list --limit 20 --format jsonl | head -20
boltz-api predictions:adme list --limit 20 --format jsonl | head -20
boltz-api small-molecule:library-screen list --limit 20 --format jsonl | head -20
boltz-api small-molecule:design list --limit 20 --format jsonl | head -20
boltz-api protein:library-screen list --limit 20 --format jsonl | head -20
boltz-api protein:design list --limit 20 --format jsonl | head -20

# Mode 2: retrieve by ID. Pick the resource from the ID prefix in the workflow
# notes above. If the prefix is unknown, run these one at a time until one succeeds.
boltz-api predictions:structure-and-binding retrieve --id "<job-id>" --format json
boltz-api predictions:adme retrieve --id "<job-id>" --format json
boltz-api small-molecule:library-screen retrieve --id "<job-id>" --format json
boltz-api small-molecule:design retrieve --id "<job-id>" --format json
boltz-api protein:library-screen retrieve --id "<job-id>" --format json
boltz-api protein:design retrieve --id "<job-id>" --format json

# Mode 3: resume download. Run as a long-running/background command via the host harness.
boltz-api download-results \
  --id "<job-id>" --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments" \
  --poll-interval-seconds 30
```

## Always Do This

- If the user has a run name / slug or run dir and only wants local downloader state, prefer `download-status` before `retrieve`.
- Use an absolute output root and keep passing it through `--root-dir`. Do not `cd` into the run directory; that makes later relative paths point at the run directory instead of the user's workspace.
- On an unfamiliar job ID, run Mode 2 (retrieve) before Mode 3 (download) so you capture `idempotency_key`.
- Prefer the original run-name slug over the job ID as `--name` — it resumes into the existing dir with cursor.
- In permission-gated agents, keep each Boltz call as a top-level command that starts with `boltz-api`. Prefer running the six `list` / `retrieve` commands explicitly over generating them from a shell loop; a fixed `| head -20` cap is okay when listing to avoid runaway streamed output.
- Run `download-results` through the host harness's long-running/background command facility. After it starts, do not manually wait on it or run ad hoc polling loops. Schedule the host's available follow-up/notification mechanism to check `download-status`, notify the user on terminal completion/failure, and stop once terminal.
- `download-results` now emits machine-readable JSONL progress on stderr by default. Add `--progress-format text --verbose` only when you explicitly want human-readable logs.
- Prefer `download-status` for local checkpoint state. Use the host's managed follow-up mechanism for automatic checks. Don't loop `retrieve` unless the user wants fresh remote status.
- If `retrieve` surfaces only `{"code":"VALIDATION_ERROR","message":"Request validation failed"}` with no `details`, that's expected for `predictions:structure-and-binding` failures — other endpoints include field paths.
- Never run `start` again on a failed or interrupted job. Fix the payload and submit with a new `idempotency-key`, or just resume with `download-results`.

## Escape Hatch

- Python SDK reference (per-resource `list` / `retrieve` methods): <https://api.boltz.bio/docs/api/python>
- CLI flag names: `boltz-api <resource> list --help`, `boltz-api <resource> retrieve --help`, `boltz-api download-results --help`, `boltz-api download-status --help`

## Outputs

- Local helper / Mode 1 / Mode 2 print structured data to stdout; present as a table.
- Mode 3 writes recovered artifacts under `<output-root>/<run-name>/` — same layout as a fresh run. Read [references/resume.md](references/resume.md) for resume behavior.
