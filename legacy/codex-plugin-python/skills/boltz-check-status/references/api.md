# Boltz Check Status Reference

## Scope

This skill covers five Boltz Compute resource families through the Python SDK:

- `predictions.structure_and_binding`
- `small_molecule.design`
- `small_molecule.library_screen`
- `protein.design`
- `protein.library_screen`

The wrapper uses:

- `list()` to enumerate recent jobs
- `retrieve()` to inspect a specific job
- `list_results()` for screen and design jobs
- job ID prefixes to route to the expected resource type, with `NotFoundError` fallback only for unknown prefixes

## Authentication

- Prefer `BOLTZ_API_KEY`
- `BOLTZ_COMPUTE_API_KEY` also works
- `workspace_id` is only for admin-capable flows

## List Mode

Default mode calls each `list()` endpoint, merges the rows, sorts by `created_at` descending, and prints:

- `id`
- `resource_type`
- `resource_prefix`
- `status`
- `created_at`
- `completed_at`

ID prefix map:

- `pred_*` → `prediction`
- `prot_des_*` → `protein_design_ppi`
- `prot_scr_*` → `protein_library_screen_ppi`
- `sm_des_*` → `boltz_sm_design`
- `sm_scr_*` → `boltz_sm_screen`

Parameters:

- `--limit N`: per-resource list limit, default `100`
- `--workspace-id ID`: optional admin-only workspace targeting
- `--json`: emit JSON instead of a text table

Relevant progress fields by resource:

- `small_molecule.library_screen`: `num_molecules_screened`, `num_molecules_failed`, `total_molecules_to_screen`, optional `rejection_summary`
- `small_molecule.design`: `num_molecules_generated`, `total_molecules_to_generate`
- `protein.library_screen`: `num_proteins_screened`, `num_proteins_failed`, `total_proteins_to_screen`
- `protein.design`: `num_proteins_generated`, `total_proteins_to_generate`

## Inspect Mode

`--id JOB_ID` uses the prefix to pick the expected `retrieve()` method first. If the prefix is unknown, the wrapper probes the supported resource types in turn until one succeeds.

Use inspect mode when:

- the user already has a job ID
- the user wants the full record
- the user wants to recover outputs from an interrupted session

Returned record fields can include:

- `status`
- `input`
- `output`
- `error`
- `started_at`
- `completed_at`
- `stopped_at`
- `expires_at`
- `data_deleted_at`
- `engine`
- `idempotency_key`

Validation caveat:

- Failed `predictions.structure_and_binding` jobs may expose only `{"code":"VALIDATION_ERROR","message":"Request validation failed"}` with no field-level `details`.
- Failed design and screening jobs usually return more specific validation messages, often including the offending field path.

For screens and designs, the wrapper also paginates `list_results()` and appends those rows to the record payload.

## Download Behavior

With `--download`, outputs are written to `./boltz_outputs/<job_id>/`.

For `structure_and_binding`, the wrapper may download:

- `archive.zip`
- `structures/best.cif` or `best.pdb`
- `structures/sample_<i>.cif` or `.pdb`

For design and screen jobs, the wrapper may download:

- `results.json`
- `structures/<result_id>.cif` or `.pdb`

## Command Examples

List all recent jobs:

```bash
python scripts/query.py
```

Inspect one job:

```bash
python scripts/query.py --id JOB_ID
```

Inspect and redownload outputs:

```bash
python scripts/query.py --id JOB_ID --download
```
