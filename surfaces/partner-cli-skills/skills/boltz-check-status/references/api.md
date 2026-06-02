# Check Status — Reference

This skill covers all five Boltz resources via `list`, `retrieve`, and `download-results`:

- `predictions:structure-and-binding`
- `small-molecule:library-screen`
- `small-molecule:design`
- `protein:library-screen`
- `protein:design`

This reference tracks the current CLI surface: unified `--id`, merged-input design/screen commands, `download-results`, and `download-status`.

## Contents

- [`list` mode](#list-mode)
- [`retrieve` mode](#retrieve-mode)
- [`list-results` mode (pipeline endpoints only)](#list-results-mode-pipeline-endpoints-only)
- [`download-status` mode](#download-status-mode)
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
- ID prefixes identify the resource family:
  - `pred_*` → `predictions:structure-and-binding`
  - `prot_des_*` → `protein:design`
  - `prot_scr_*` → `protein:library-screen`
  - `sm_des_*` → `small-molecule:design`
  - `sm_scr_*` → `small-molecule:library-screen`
- `status` — `pending` / `running` / `succeeded` / `failed` / `stopped`
- `created_at`, `started_at`, `completed_at`
- `idempotency_key` — captured from `start`; the slug you can use as `--name` for resume
- resource-specific progress counters (see `retrieve`)

Merge + sort flow:

```bash
# Permission-friendly agents should run these as explicit top-level commands
# instead of generating them from a shell loop. CLI output is streamed, so cap
# each resource with head when you only need recent rows.
boltz-api predictions:structure-and-binding list --limit 20 --format jsonl | head -20
boltz-api small-molecule:library-screen list --limit 20 --format jsonl | head -20
boltz-api small-molecule:design list --limit 20 --format jsonl | head -20
boltz-api protein:library-screen list --limit 20 --format jsonl | head -20
boltz-api protein:design list --limit 20 --format jsonl | head -20
```

## `retrieve` mode

```bash
boltz-api <resource> retrieve --id "<job-id>" --format json
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

### Route from the ID prefix when possible

```bash
# Pick the resource from the ID prefix above, then run one concrete command.
boltz-api protein:design retrieve --id "<job-id>" --format json

# If the prefix is unknown, probe explicitly one command at a time until one succeeds.
boltz-api predictions:structure-and-binding retrieve --id "<job-id>" --format json
boltz-api small-molecule:library-screen retrieve --id "<job-id>" --format json
boltz-api small-molecule:design retrieve --id "<job-id>" --format json
boltz-api protein:library-screen retrieve --id "<job-id>" --format json
boltz-api protein:design retrieve --id "<job-id>" --format json
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
boltz-api <resource> list-results --id "<job-id>" --limit 100
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

## `download-status` mode

Use `download-status` when you want the local checkpoint only, without making an API call:

```bash
boltz-api --format json download-status --name "<run-name>" --root-dir "<output-root>"
```

Selectors:

- `--name <slug>` — look up `<output-root>/<run-name>/`
- `--run-dir <path>` — inspect an explicit run directory
- `--name` and `--run-dir` are mutually exclusive
- `--root-dir` cannot be used with `--run-dir`

Structured fields include:

- `run_dir`, `name`, `run_type`, `run_id`
- `status`, `phase`, `ready`
- `pending_kind`, `pending_count`, `pending_after_id`, `pending_page_last_id`, `pending_result_ids`
- `cursor_after_id`, `latest_result_id`
- `started_at`, `completed_at`, `stopped_at`, `error_code`

## `download-results` resume semantics

```bash
# Launch this command in the host harness's long-running/background mode.
boltz-api download-results \
  --id "<job-id>" --name "<run-name>" \
  --root-dir "<output-root>" \
  --poll-interval-seconds 30
```

Behavior:

- `download-results` itself is a blocking poller. Launch it through the host harness's long-running/background command facility and immediately return to the user; do not wait on or poll the background job unless the user asks.
- It emits machine-readable JSONL progress events on stderr by default. Use `--progress-format text --verbose` only when you explicitly want human-readable logs.
- Writes `<output-root>/<run-name>/.boltz-run.json` containing the cursor (`cursor_after_id`), status, idempotency key, and timing.
- On re-run with the same `--root-dir` + `--name`, reuses `.boltz-run.json` and only pulls results past the recorded cursor. Idempotent.
- If the run dir exists and `.boltz-run.json` has the ID, `--id` can be omitted.
- If `--name` is not passed, the CLI generates a random petname dir — use `--name` for cross-session resume.

### Directory layout

```
<output-root>/<run-name>/
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
  --id "<job-id>" --name "<run-name>" \
  --root-dir "<output-root>"
```

### "My session died — I only have the job ID"

```bash
# 1. Use the ID prefix to pick one retrieve endpoint and get idempotency_key.
boltz-api protein:design retrieve --id "<job-id>" --format json

# 2. Resume with the recovered idempotency_key as the run name.
# If idempotency_key is empty, pick a fresh recovery slug.
boltz-api download-results \
  --id "<job-id>" --name "<run-name-or-recovery-slug>" \
  --root-dir "<output-root>"
```

## Escape hatch

- Python SDK reference: <https://api.boltz.bio/docs/api/python>
- `boltz-api <resource> list --help` / `retrieve --help` / `boltz-api download-results --help` / `boltz-api download-status --help`
