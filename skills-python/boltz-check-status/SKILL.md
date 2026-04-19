---
name: boltz-check-status
description: List recent Boltz Compute jobs across all five endpoints, or inspect a single job by ID, and optionally pull its results onto disk. TRIGGER when the user asks "what Boltz jobs are running", "check status", "did my screen finish", "resume my job", "download results for <id>", "how far along is <id>", or after a session restart where earlier job IDs were lost.
---

## What this does

Two modes:

1. **Default (list)**: paginates the 5 list endpoints (`predictions.structure_and_binding`, `small_molecule.design`, `small_molecule.library_screen`, `protein.design`, `protein.library_screen`), merges, sorts by `created_at` desc, and prints a table `id | resource_type | status | created_at | completed_at`.

2. **`--id <job_id>`**: probes each `retrieve()` until one succeeds (catches `NotFoundError`). Dumps the full record JSON (plus paginated results for screens/designs) to stdout. With `--download`, re-downloads artifacts into `./boltz_outputs/<id>/` if missing.

Useful after a session has been interrupted — no need to remember which resource type a job belonged to.

## Prerequisites

- `BOLTZ_COMPUTE_API_KEY` env var
- `pip install boltz-compute`
- Python 3.9+

## SDK surface used

- `client.predictions.structure_and_binding.{list, retrieve}`
- `client.small_molecule.design.{list, retrieve, list_results}`
- `client.small_molecule.library_screen.{list, retrieve, list_results}`
- `client.protein.design.{list, retrieve, list_results}`
- `client.protein.library_screen.{list, retrieve, list_results}`
- `boltz_compute.NotFoundError` — raised by `retrieve()` when the ID does not exist at that resource.

## Inputs (full field reference)

This skill takes no API request body; all parameters map to SDK call arguments or query-level settings.

### List mode (default — no `--id`)

Calls `client.predictions.structure_and_binding.list(...)`, `client.small_molecule.design.list(...)`, `client.small_molecule.library_screen.list(...)`, `client.protein.design.list(...)`, `client.protein.library_screen.list(...)` in parallel.

- **`--limit N`** *(optional, int, default 100)* — per-resource page size passed as `limit=` to each `list()` call. For more than 100 jobs, pagination uses `after_id=` cursor-based iteration (`has_more` / `last_id` fields on the response).
- **`--workspace-id <id>`** *(optional, str)* — admin keys only; passed as `workspace_id=` to each call to target a non-default workspace.
- **`--json`** *(optional, flag)* — emit the merged list as a JSON array instead of a human-readable text table.

Each list response element exposes:
- `id` — job ID; prefix indicates type (`pred_…`, `des_…`, `scr_…`, etc.)
- `status` — `"pending"` | `"running"` | `"succeeded"` | `"failed"` | `"stopped"` (screens/designs) or `"pending"` | `"running"` | `"succeeded"` | `"failed"` (structure-and-binding)
- `created_at` — ISO 8601 timestamp
- `progress` — resource-specific sub-object (absent for structure-and-binding):
  - `small_molecule.library_screen`: `{num_molecules_screened, num_molecules_failed, total_molecules_to_screen, rejection_summary?}`
  - `small_molecule.design`: `{num_molecules_generated, total_molecules_to_generate}`
  - `protein.library_screen`: `{num_proteins_screened, num_proteins_failed, total_proteins_to_screen}`
  - `protein.design`: `{num_proteins_generated, total_proteins_to_generate}`

### Inspect mode (`--id <job_id>`)

Probes each of the 5 `retrieve()` methods in turn, catching `boltz_compute.NotFoundError`, until one returns the record. The first match determines the resource type.

- **`--id <job_id>`** *(str)* — the job ID to look up. Can be any prefix format.
- **`--workspace-id <id>`** *(optional, str)* — admin keys only.
- **`--download`** *(optional, flag)* — after retrieval, re-download artifacts into `./boltz_outputs/<id>/`. For screens and designs, also paginates `list_results()` and writes `results.json` and per-result CIF files.

The retrieved record additionally exposes: `input`, `output` (for structure-and-binding: `all_sample_results`, `best_sample`, `archive`, `binding_metrics`), `error`, `started_at`, `completed_at`, `stopped_at`, `expires_at`, `data_deleted_at`, `engine`, `idempotency_key`.

Screens and designs also support `list_results(id, limit=, after_id=, before_id=)` — paginated iterator over individual molecule/protein results (`data`, `first_id`, `last_id`, `has_more`).

## How to invoke

List all recent jobs:

```
python scripts/query.py
```

Inspect a specific job:

```
python scripts/query.py --id sab_abc123
```

Inspect + re-download artifacts:

```
python scripts/query.py --id sab_abc123 --download
```

## Output

- **List mode**: text table to stdout (or JSON array with `--json`).
- **Detail mode (`--id`)**: JSON `{"id", "found", "resource_type", "record"}` where `record` includes paginated `results` for screens/designs. With `--download`, also writes `./boltz_outputs/<id>/results.json` plus `structures/` and `archive.zip`.

## Examples

### 1. Check all jobs

```
python scripts/query.py
```

### 2. Get full record and download for a specific job

```
python scripts/query.py --id smdesign_xyz --download
```

### 3. JSON output for further piping

```
python scripts/query.py --json | jq '.[] | select(.status=="running")'
```
