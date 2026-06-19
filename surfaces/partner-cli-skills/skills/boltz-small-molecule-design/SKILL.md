---
name: boltz-small-molecule-design
description: Design new small-molecule binders with Boltz. Use when generating novel ligands or hits for a target without a fixed compound library. Not for screening existing molecules or one-off docking.
---

## Workflow

If `boltz-api` reports missing or expired authentication, surface the error to the user. Do not attempt to re-authenticate; the host environment must provide `BOLTZ_API_KEY`.

Use this skill when the user wants de novo small-molecule binders (no existing library).

1. Normalize the target: one or more protein sequences into `target.entities`, plus optional `pocket_residues` (0-based) and/or `reference_ligands` (known binders to seed pocket detection).
2. Pick `num_molecules` — minimum **10**, server rejects anything lower. If the user says a smaller number, explain the floor and propose 10.
3. Only add `chemical_space` (e.g. `"enamine_real"`) if the user explicitly wants synthesis-aware generation within that library.
4. Supported optional features include `chemical_space` and `molecule_filters`; only add them on explicit request. Read [references/api.md](references/api.md) for exact shapes and filter options.
5. Author the payload YAML or JSON.
6. `start` to submit (synchronous). Capture the ID.
7. Launch `download-results` as a long-running/background command in whatever mode the host agent harness provides; it polls, paginates, downloads per-hit structures, and exits when terminal. After launching it, schedule the host's available follow-up/notification mechanism, if one exists, to check `download-status` periodically and notify the user when the download reaches a terminal state. Always report the job ID, run name, and output directory. Include the next check cadence if a follow-up was scheduled; otherwise include the `download-status` command.
8. Rank hits from `<output-root>/<run-name>/results/index.jsonl` by `binding_confidence` for hit discovery or `optimization_score` for lead optimization. Read [references/results.md](references/results.md) for output layout and metric details.

## Command Pattern

```bash
# Replace placeholders with concrete absolute paths before running.
# Use a short descriptive run name, for example: sm-design-<target>-<batch>-v1

boltz-api small-molecule:design start \
       --idempotency-key "<run-name>" \
       --input @yaml:///absolute/path/payload.yaml \
       --raw-output --transform id

# Copy the printed job ID into this command, then launch it as a
# long-running/background command via the host agent harness.
boltz-api download-results \
  --id "<job-id-from-start>" --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments" \
  --poll-interval-seconds 60
# -> /absolute/path/boltz-experiments/<run-name>/results/<pres_*>/...
```

Payload keys are `num_molecules`, `target`, `chemical_space`, `molecule_filters` — the API body field names.

## Always Do This

- Enforce `num_molecules >= 10` before submitting. The server rejects smaller batches.
- Treat pocket residue indices as 0-based.
- Keep payload field names exactly as the API body names shown in `references/api.md`.
- Use absolute paths for the output root, payload files, and embedded target files. Do not `cd` into the run directory for follow-up commands; pass the same `--root-dir` and use absolute paths so later relative paths do not drift.
- Prefer one merged top-level payload via `--input @yaml:///absolute/path/payload.yaml` or `@json:///absolute/path/payload.json`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides: for example `--target @yaml:///absolute/path/target.yaml` or `--molecule-filters @json:///absolute/path/filters.json`. Piped YAML / JSON on stdin also works, but it must use API body field names. Never use `@file://`.
- Use the same slug as both `--idempotency-key` at submit and `--name` on `download-results`.
- In permission-gated agents, keep each Boltz call as a top-level command that starts with `boltz-api`. Prefer concrete arguments over `sh -c`, inline environment assignments, aliases, wrapper scripts, loops, or pipelines around the `boltz-api` invocation unless the user already allowed that exact command form. Use `--raw-output --transform id`, read the printed ID, then paste that literal ID into the next `download-results` command.
- Run `download-results` through the host harness's long-running/background command facility. After it starts, do not manually wait on it or run ad hoc polling loops. Wall-clock time scales roughly with `num_molecules`: under 100 often finishes in a few minutes, 100-1,000 may take several minutes to tens of minutes, and larger runs can take longer or hours depending on inputs and system load. `--poll-interval-seconds 60` is a sensible downloader default. If the host harness provides a managed follow-up/notification mechanism, schedule it to check `download-status`, notify the user on terminal completion/failure, and stop once terminal. If not, do not claim an automatic next check.
- `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs.
- Prefer `boltz-api --format json download-status --name "<run-name>" --root-dir "/absolute/path/boltz-experiments"` for structured local checkpoint state. When the host provides a managed follow-up mechanism, use it for automatic checks with cadence based on `num_molecules`: under 100 -> every 1-2 minutes; 100-1,000 -> every 5 minutes; over 1,000 -> every 15 minutes. Never run a manual poll loop in the current turn.
- If a detached download needs to be restarted, re-run `boltz-api download-results` with the same `--name "<run-name>"` and the same `--root-dir`.
- Do not invent filters; only add `molecule_filters` on user request.

## Escape Hatch

- Payload reference: <https://api.boltz.bio/docs/api/python/resources/small_molecule/subresources/design/methods/start>
- CLI flag names: `boltz-api small-molecule:design start --help`

Read [references/api.md](references/api.md) for the `target`, `chemical_space`, and `molecule_filters` shapes (filter catalog matches the screen endpoint). Read [references/results.md](references/results.md) after download when ranking generated molecules or explaining outputs.

## Outputs

Rank from `results/index.jsonl` after `download-results`; use [references/results.md](references/results.md) for local file layout and metric meanings.
