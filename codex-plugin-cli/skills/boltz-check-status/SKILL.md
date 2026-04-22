---
name: boltz-check-status
description: List recent Boltz Compute jobs across all five endpoints, or inspect a single job by ID, and optionally pull its results onto disk. TRIGGER when the user asks what Boltz jobs are running, to check status, whether a screen finished, to resume a prior job, to download results for a job ID, to see how far along a job is, or after a session restart where earlier job IDs were lost.
---

## Workflow

Use this skill to recover state across sessions and to inspect or download results for prior Boltz jobs. No payload authoring — this skill only calls `list` / `retrieve` / `download-results`.

Three modes, decided by what the user gives you:

### Mode 1 — "what's running?" (no ID provided)

Enumerate recent jobs across all five resources, merge, and sort by `created_at` descending. Use `--limit 20` per resource; bump higher if the user asks to see more.

### Mode 2 — "how's job $ID doing?" (ID provided)

Probe all five `retrieve` endpoints — exactly one will return the job. Report `status`, progress counters for pipeline jobs (`num_molecules_screened` / `num_proteins_generated` / etc.), and the `error` if present. **Capture `idempotency_key` from the response** — you'll need it in Mode 3.

### Mode 3 — "my session died, pull the results"

This is the crash-recovery path. Two sub-cases:

**3a. User knows the original slug** (or the dir at `$ROOT/$IDEM/` still exists):

```bash
# Start this command in Codex background/non-blocking mode.
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30 \
  --verbose
```

CLI reuses the existing `.boltz-run.json` and only pulls results past the last recorded cursor. If the run dir exists, `--id` can be omitted — the CLI reads the ID from metadata. Re-run with Codex background/non-blocking mode the same as a fresh submit.

**3b. User has only the `$ID`:**

Run Mode 2 first to get `idempotency_key` from the retrieve response, then use it as `--name` in the 3a command. If the original submit didn't pass `idempotency_key`, pick a fresh slug and `download-results` from scratch — server-side the job is fine; only incremental-resume is lost.

Never run `start` again "to resume" — that creates a new job.

## Command Pattern

```bash
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}"

# Mode 1: list recent jobs across all 5 resources.
# NB: the CLI emits one JSON object per record (streamed, no {data:[]} wrapper).
# --limit is per-page and the CLI auto-paginates, so cap output with head.
for R in predictions:structure-and-binding \
         small-molecule:library-screen small-molecule:design \
         protein:library-screen protein:design; do
  boltz-api "$R" list --limit 20 --format jsonl 2>/dev/null \
    | head -20 \
    | jq -c --arg r "$R" '{id, resource:$r, status, created_at, completed_at, idempotency_key}'
done | jq -s 'sort_by(.created_at) | reverse | .[0:20]'

# Mode 2: probe retrieve across all 5 until one succeeds
for R in predictions:structure-and-binding \
         small-molecule:library-screen small-molecule:design \
         protein:library-screen protein:design; do
  if RECORD=$(boltz-api "$R" retrieve --id "$ID" --format json 2>/dev/null); then
    echo "$RECORD" | jq '{id, status, idempotency_key, progress, error}'
    break
  fi
done

# Mode 3: resume download.
# Start this command in Codex background/non-blocking mode.
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30 \
  --verbose
```

## Always Do This

- On an unfamiliar `$ID`, run Mode 2 (retrieve) before Mode 3 (download) so you capture `idempotency_key`.
- Prefer the original `$IDEM` slug over `$ID` as `--name` — it resumes into the existing dir with cursor.
- Prefer Codex's background/non-blocking command mode for `download-results`. After the background session starts, do not wait on it or poll it. Report the job ID, run name, output directory, and that Codex should notify when the background command completes.
- If Codex background mode is unavailable or blocks the conversation, use the detached fallback: `nohup boltz-api download-results ... > "$ROOT/$IDEM/download-results.log" 2>&1 < /dev/null &`, then write the PID to `$ROOT/$IDEM/download-results.pid`.
- Only check progress when the user asks. Use the background session notification/output if available, or read `download-results.log` for detached fallback runs. Don't loop `retrieve`.
- If `retrieve` surfaces only `{"code":"VALIDATION_ERROR","message":"Request validation failed"}` with no `details`, that's expected for `predictions:structure-and-binding` failures — other endpoints include field paths.
- Never run `start` again on a failed or interrupted job. Fix the payload and submit with a new `idempotency-key`, or just resume with `download-results`.

## Escape Hatch

- Upstream reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api <resource> list --help`, `boltz-api <resource> retrieve --help`, `boltz-api download-results --help`

Read [references/api.md](references/api.md) for per-resource `list` columns, `retrieve` record fields, and `download-results` resume semantics.

## Outputs

- Mode 1 / Mode 2 print structured data to stdout; present as a table.
- Mode 3 writes recovered artifacts under `$ROOT/$IDEM/` — same layout as a fresh run: `.boltz-run.json`, `outputs/` (SAB) or `results/<pres_*>/` (screens and designs).
