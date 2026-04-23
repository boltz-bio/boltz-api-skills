---
name: boltz-check-status
description: List recent Boltz Compute jobs across all five endpoints, or inspect a single job by ID, and optionally pull its results onto disk. TRIGGER when the user asks what Boltz jobs are running, to check status, whether a screen finished, to resume a prior job, to download results for a job ID, to see how far along a job is, or after a session restart where earlier job IDs were lost.
---

## Workflow

Use this skill to recover state across sessions and to inspect or download results for prior Boltz jobs. No payload authoring — this skill only calls `list` / `retrieve` / `download-results` / `download-status`.

Three remote modes, plus one local checkpoint helper:

### Local helper — "what is my downloader doing?" (run name or run dir provided)

Use `download-status` first when the user knows the original slug / run name or local run dir and wants to inspect local progress without burning an API call.

### Mode 1 — "what's running?" (no ID provided)

Enumerate recent jobs across all five resources, merge, and sort by `created_at` descending. Use `--limit 20` per resource; bump higher if the user asks to see more. Derive `resource_type` from the job ID prefix (empirical — not part of the spec contract; verified 2026-04-23 against live `list --limit 1` on each endpoint):

- `sab_pred_*` → `prediction` (structure-and-binding)
- `prot_des_*` → `protein_design_ppi`
- `prot_scr_*` → `protein_library_screen_ppi`
- `sm_des_*` → `boltz_sm_design`
- `sm_scr_*` → `boltz_sm_screen`

If a returned ID doesn't match any of these prefixes, fall through to the all-resources probe — the mapping is observational, not guaranteed.

### Mode 2 — "how's job $ID doing?" (ID provided)

Use the job ID prefix to select the right `retrieve` endpoint. Only fall back to probing all five if the prefix is unfamiliar. Report `status`, progress counters for pipeline jobs (`num_molecules_screened` / `num_proteins_generated` / etc.), and the `error` if present. For pipeline endpoints, `stopped` is terminal and means the run was stopped early; partial results may be available. SAB predictions do not use `stopped`. **Capture `idempotency_key` from the response**; you'll need it in Mode 3.

### Mode 3 — "my session died, pull the results"

This is the crash-recovery path. Two sub-cases:

**3a. User knows the original slug** (or the dir at `$ROOT/$IDEM/` still exists):

```bash
# Launch this command in the agent runtime's background/non-blocking mode (e.g., Claude Code Bash with `run_in_background: true`, Codex background shell).
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30
```

CLI reuses the existing `.boltz-run.json` and only pulls results past the last recorded cursor. If the run dir exists, `--id` can be omitted — the CLI reads the ID from metadata. Re-run in background mode the same as a fresh submit.

**3b. User has only the `$ID`:**

Run Mode 2 first to get `idempotency_key` from the retrieve response, then use it as `--name` in the 3a command. If the original submit didn't pass `idempotency_key`, pick a fresh slug and `download-results` from scratch — server-side the job is fine; only incremental-resume is lost.

Never run `start` again "to resume" — that creates a new job.

## Command Pattern

```bash
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}"

# Local helper: inspect local checkpoint state without API calls.
boltz-api --format json download-status \
  --name "$IDEM" \
  --root-dir "$ROOT"

# Mode 1: list recent jobs across all 5 resources.
# NB: the CLI emits one JSON object per record (streamed, no {data:[]} wrapper).
# --limit is per-page and the CLI auto-paginates, so cap output with head.
for R in predictions:structure-and-binding \
         small-molecule:library-screen small-molecule:design \
         protein:library-screen protein:design; do
  boltz-api "$R" list --limit 20 --format jsonl 2>/dev/null \
    | head -20 \
    | jq -c --arg r "$R" '
        . as $row
        | ($row.id // "") as $id
        | $row + {
            resource: $r,
            resource_type:
              (if $id | startswith("sab_pred_") then "prediction"
               elif $id | startswith("prot_des_") then "protein_design_ppi"
               elif $id | startswith("prot_scr_") then "protein_library_screen_ppi"
               elif $id | startswith("sm_des_") then "boltz_sm_design"
               elif $id | startswith("sm_scr_") then "boltz_sm_screen"
               else "unknown" end)
          }
        | {id, resource, resource_type, status, created_at, completed_at, idempotency_key}'
done | jq -s 'sort_by(.created_at) | reverse | .[0:20]'

# Mode 2: route retrieve from the ID prefix; probe all 5 only if unknown
case "$ID" in
  sab_pred_*) R="predictions:structure-and-binding" ;;
  prot_des_*) R="protein:design" ;;
  prot_scr_*) R="protein:library-screen" ;;
  sm_des_*)   R="small-molecule:design" ;;
  sm_scr_*)   R="small-molecule:library-screen" ;;
  *)
    for R in predictions:structure-and-binding \
             small-molecule:library-screen small-molecule:design \
             protein:library-screen protein:design; do
      if RECORD=$(boltz-api "$R" retrieve --id "$ID" --format json 2>/dev/null); then
        echo "$RECORD" | jq --arg r "$R" '{id, resource:$r, status, idempotency_key, progress, error}'
        break
      fi
    done
    unset R
    ;;
esac

if [ -n "${R:-}" ]; then
  boltz-api "$R" retrieve --id "$ID" --format json \
    | jq --arg r "$R" '{id, resource:$r, status, idempotency_key, progress, error}'
fi

# Mode 3: resume download.
# Launch this command in the agent runtime's background/non-blocking mode (e.g., Claude Code Bash with `run_in_background: true`, Codex background shell).
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30
```

## Always Do This

- If the user has a run name / slug or run dir and only wants local downloader state, prefer `download-status` before `retrieve`.
- On an unfamiliar `$ID`, run Mode 2 (retrieve) before Mode 3 (download) so you capture `idempotency_key`.
- Prefer the original `$IDEM` slug over `$ID` as `--name` — it resumes into the existing dir with cursor.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. After the background session starts, do not wait on it or poll it. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- If background mode is unavailable or blocks the conversation, use the detached fallback: `nohup boltz-api download-results ... > "$ROOT/$IDEM/download-results.log" 2>&1 < /dev/null &`, then write the PID to `$ROOT/$IDEM/download-results.pid`.
- `download-results` now emits machine-readable JSONL progress on stderr by default. Add `--progress-format text --verbose` only when you explicitly want human-readable logs.
- Only check progress when the user asks. Prefer `download-status` for local checkpoint state or the background session's JSONL stderr if it's still running. Don't loop `retrieve` unless the user wants fresh remote status.
- If `retrieve` surfaces only `{"code":"VALIDATION_ERROR","message":"Request validation failed"}` with no `details`, that's expected for `predictions:structure-and-binding` failures — other endpoints include field paths.
- Never run `start` again on a failed or interrupted job. Fix the payload and submit with a new `idempotency-key`, or just resume with `download-results`.

## Escape Hatch

- Upstream reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api <resource> list --help`, `boltz-api <resource> retrieve --help`, `boltz-api download-results --help`, `boltz-api download-status --help`

Read [references/api.md](references/api.md) for per-resource `list` columns, `retrieve` record fields, and `download-results` resume semantics.

## Outputs

- Local helper / Mode 1 / Mode 2 print structured data to stdout; present as a table.
- Mode 3 writes recovered artifacts under `$ROOT/$IDEM/` — same layout as a fresh run: `.boltz-run.json`, `outputs/` (SAB) or `results/<pres_*>/` (screens and designs).
