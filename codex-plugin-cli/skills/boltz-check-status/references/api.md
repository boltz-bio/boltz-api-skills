# Check Status — Reference

This skill covers all five Boltz Compute resources via `list`, `retrieve`, and `download-results`:

- `predictions:structure-and-binding`
- `small-molecule:library-screen`
- `small-molecule:design`
- `protein:library-screen`
- `protein:design`

All subcommands use the unified `--id` flag as of CLI v0.5.4 (the pre-0.5.0 `--screen-id` / `--run-id` flags are gone).

## Contents

- [`list` mode](#list-mode)
- [`retrieve` mode](#retrieve-mode)
- [`list-results` mode (pipeline endpoints only)](#list-results-mode-pipeline-endpoints-only)
- [`download-results` resume semantics](#download-results-resume-semantics)
- [Common recovery recipes](#common-recovery-recipes)
- [Escape hatch](#escape-hatch)

## `list` mode

```bash
boltz-api <resource> list --limit 20 --format json
```

Parameters:

- `--limit N` — **per-page** size. The CLI auto-paginates beyond this, so expect the stream to keep going after N records. To cap total output, pipe through `head -N`.
- `--workspace-id <id>` — admin-only.
- `--format json|yaml|pretty|jsonl` — serialization. Both `json` and `jsonl` emit one record per object with no `{data:[]}` wrapper.
- `--transform <gjson>` — single-field projection per row (don't use `#.{a,b}` multi-field — it silently returns `{}`; use `jq` for that).

Common columns across resources:

- `id` — the job ID
- `status` — `pending` / `running` / `succeeded` / `failed` / `stopped`
- `created_at`, `started_at`, `completed_at`
- `idempotency_key` — captured from `start`; the slug you can use as `--name` for resume
- resource-specific progress counters (see `retrieve`)

Merge + sort flow:

```bash
# CLI emits one JSON object per record (streamed, no {data:[]} wrapper) and
# auto-paginates, so cap per-resource output with head after --limit.
for R in predictions:structure-and-binding \
         small-molecule:library-screen small-molecule:design \
         protein:library-screen protein:design; do
  boltz-api "$R" list --limit 20 --format jsonl 2>/dev/null \
    | head -20 \
    | jq -c --arg r "$R" '{id, resource:$r, status, created_at, completed_at, idempotency_key}'
done | jq -s 'sort_by(.created_at) | reverse | .[0:20]'
```

## `retrieve` mode

```bash
boltz-api <resource> retrieve --id "$ID" --format json
```

Returns the full job record. Key fields:

- `id`, `status`, `error`
- `started_at`, `completed_at`, `stopped_at`, `expires_at`, `data_deleted_at`
- `idempotency_key` — **capture this for resume** (use as `--name` on `download-results`)
- `input` — the original submitted payload
- `output` — full output (SAB only; pipeline endpoints stream per-item via `list-results` instead)
- `engine` — engine metadata

### Progress fields by resource

| Resource | Progress fields |
|---|---|
| `predictions:structure-and-binding` | `status`; no per-item progress |
| `small-molecule:library-screen` | `num_molecules_screened`, `num_molecules_failed`, `total_molecules_to_screen`, optional `rejection_summary` |
| `small-molecule:design` | `num_molecules_generated`, `total_molecules_to_generate` |
| `protein:library-screen` | `num_proteins_screened`, `num_proteins_failed`, `total_proteins_to_screen` |
| `protein:design` | `num_proteins_generated`, `total_proteins_to_generate` |

### Probe an unknown-resource-type ID

```bash
for R in predictions:structure-and-binding \
         small-molecule:library-screen small-molecule:design \
         protein:library-screen protein:design; do
  if RECORD=$(boltz-api "$R" retrieve --id "$ID" --format json 2>/dev/null); then
    echo "Resource: $R"
    echo "$RECORD" | jq '{status, idempotency_key, error}'
    break
  fi
done
```

### `predictions:structure-and-binding` 400 quirk

Failed SAB jobs may expose only:

```json
{"code": "VALIDATION_ERROR", "message": "Request validation failed"}
```

with no `details`. The other four endpoints include field paths. If you see the bare message, inspect the `input.entities` and `input.constraints` by hand.

## `list-results` mode (pipeline endpoints only)

Applies to the four pipeline resources (not SAB, which has a single `output`):

```bash
boltz-api <resource> list-results --id "$ID" --limit 100
```

Each row:

- `id` — server-assigned `pres_*` result ID
- `external_id` — client-supplied `id` from the original `molecules[]` / `proteins[]` entry
- `smiles` (SM) or `entities` (protein)
- `metrics.*` — same fields documented in each start-family skill's `references/api.md`
- `artifacts.structure.url`, `artifacts.archive.url` — presigned, short-lived; refetch via re-`retrieve` or re-`list-results` if expired
- `warnings` — any per-item server warnings

Pagination:

- `--limit N` — per-page size. CLI auto-paginates, streaming records one per object.
- `--after-id <pres_*>` / `--before-id <pres_*>` — cursor.
- The CLI emits one JSON record per object (no `{data:[]}` wrapper); `--transform` applies per-row. Pipe through `head -N` to cap total.

## `download-results` resume semantics

```bash
# Start this command in Codex background/non-blocking mode.
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30 \
  --verbose
```

Behavior:

- `download-results` itself is a blocking poller. In Codex, launch it through the background/non-blocking command facility and immediately return to the user; do not wait on or poll the background session unless the user asks.
- Writes `$ROOT/$NAME/.boltz-run.json` containing the cursor (`cursor_after_id`), status, idempotency key, and timing.
- On re-run with the same `--root-dir` + `--name`, reuses `.boltz-run.json` and only pulls results past the recorded cursor. Idempotent.
- If the run dir exists and `.boltz-run.json` has the ID, `--id` can be omitted.
- If `--name` is not passed, the CLI generates a random petname dir — use `--name` for cross-session resume.
- If Codex background mode is unavailable or blocks the conversation, use detached fallback: `nohup boltz-api download-results ... > "$ROOT/$NAME/download-results.log" 2>&1 < /dev/null &` and write the PID to `$ROOT/$NAME/download-results.pid`.

### Directory layout

```
$ROOT/$NAME/
├── .boltz-run.json                       # cursor, status, idem key, timing
├── outputs/                              # SAB only
│   └── archive.tar.gz                    # unpacks to prediction/{metrics.json, *.cif, *.pae.npz}
└── results/                              # screens and designs only
    ├── pres_55p3z0ew50xt7uitsMnU/
    │   ├── archive.tar.gz
    │   └── files/result/
    │       ├── metrics.json
    │       ├── predicted_structure.cif
    │       └── pae.npz
    └── pres_...                           # one dir per per-item result, keyed by server ID
```

## Common recovery recipes

### "My session died during the download — same slug available"

```bash
# just re-run; CLI reads .boltz-run.json and resumes
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" --verbose
```

### "My session died — I only have the job ID"

```bash
# 1. retrieve across resources to find the right endpoint and get the slug
for R in predictions:structure-and-binding \
         small-molecule:library-screen small-molecule:design \
         protein:library-screen protein:design; do
  RECORD=$(boltz-api "$R" retrieve --id "$ID" --format json 2>/dev/null) && break
done
IDEM=$(echo "$RECORD" | jq -r '.idempotency_key // empty')

# 2. resume with the recovered slug (or pick a fresh one if IDEM is empty)
IDEM="${IDEM:-recover-$ID}"
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" --verbose
```

## Escape hatch

- Upstream: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- `boltz-api <resource> list --help` / `retrieve --help` / `boltz-api download-results --help`
