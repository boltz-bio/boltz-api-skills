---
name: boltz-small-molecule-screen
description: Screen existing small-molecule libraries with Boltz. Use when docking, scoring, or ranking a supplied SMILES or compound library against a target. Not for de novo molecule design or one-off docking.
---

## Workflow

If `boltz-api` reports missing or expired authentication, surface the error to the user. Do not attempt to re-authenticate; the host environment must provide `BOLTZ_API_KEY`.

Use this skill when the user already has candidate molecules.

1. Normalize the library from raw SMILES, a CSV (auto-detect the SMILES column), `.smi`, or `.txt` into the `molecules` list. Each entry is `{smiles, id?}`; the optional `id` is echoed back as `external_id` on each result.
2. Normalize the target: one or more protein sequences into `target.entities`, plus optional `pocket_residues` (0-based) and/or `reference_ligands` (SMILES of known binders to seed pocket detection).
3. Keep default server-side filtering unless the user asks for custom filters — only add `molecule_filters` on explicit request.
4. Author the payload YAML or JSON.
5. `start` to submit (synchronous). Capture the ID.
6. Launch `download-results` as a long-running/background command in whatever mode the host agent harness provides — it polls, paginates `list-results`, downloads every per-hit structure, and exits when terminal. After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background job unless the user explicitly asks for progress.
7. When done, rank from `<output-root>/<run-name>/results/index.jsonl`. Sort by `binding_confidence` for hit discovery or `optimization_score` for lead optimization; these are parallel intents, not a fallback hierarchy. Report the top 5-10 hits with `smiles`, the chosen ranking metric, key confidence metrics, and structure path. Read [references/results.md](references/results.md) for output layout, metrics, and filtered-input accounting.

## Command Pattern

```bash
# Replace placeholders with concrete absolute paths before running.
# Use a short descriptive run name, for example: sm-screen-<target>-<library>-v1

boltz-api small-molecule:library-screen start \
       --idempotency-key "<run-name>" \
       --input @yaml:///absolute/path/payload.yaml \
       --raw-output --transform id

# Copy the printed job ID into this command, then launch it as a
# long-running/background command via the host agent harness.
boltz-api download-results \
  --id "<job-id-from-start>" --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments" \
  --poll-interval-seconds 30
# -> /absolute/path/boltz-experiments/<run-name>/results/<pres_*>/...
```

Payload keys are `molecules`, `target`, `molecule_filters` — the API body field names, not the direct CLI flag names `--molecule` / `--target` / `--molecule-filters`.

## Always Do This

- Keep payload field names exactly as the API body names shown in `references/api.md`.
- Use absolute paths for the output root, payload files, and embedded target files. Do not `cd` into the run directory for follow-up commands; pass the same `--root-dir` and use absolute paths so later relative paths do not drift.
- Prefer one merged top-level payload via `--input @yaml:///absolute/path/payload.yaml` or `@json:///absolute/path/payload.json`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides, such as `--target @yaml:///absolute/path/target.yaml`, `--molecule-filters @json:///absolute/path/filters.json`, or repeated `--molecule @json:///absolute/path/mol-1.json` entries. Piped YAML / JSON on stdin also works, but it must use API body field names. Never use `@file://` or `@./`.
- Treat pocket residue indices as 0-based.
- Do not invent medicinal-chemistry filters. Only add `molecule_filters` if the user asks; mention the catalog as an option.
- Use the same slug as both `--idempotency-key` at submit and `--name` on `download-results` so re-runs resume via `.boltz-run.json`.
- In permission-gated agents, keep each Boltz call as a top-level command that starts with `boltz-api`. Prefer concrete arguments over `sh -c`, inline environment assignments, aliases, wrapper scripts, loops, or pipelines around the `boltz-api` invocation unless the user already allowed that exact command form. Use `--raw-output --transform id`, read the printed ID, then paste that literal ID into the next `download-results` command.
- Run `download-results` through the host harness's long-running/background command facility. After it starts, do not wait on or poll it. Report the job ID, run name, and output directory and let the harness notify the user when the background command completes.
- `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs.
- Only check status when the user asks. Prefer `boltz-api --format json download-status --name "<run-name>" --root-dir "/absolute/path/boltz-experiments"` for structured local checkpoint state. Never run a manual poll loop.
- If a detached download needs to be restarted, re-run `boltz-api download-results` with the same `--name "<run-name>"` and the same `--root-dir`.
- Poll interval: `--poll-interval-seconds 30` is a reasonable default; libraries can run 10–60 min depending on size.

## Escape Hatch

- Payload reference: <https://api.boltz.bio/docs/api/python/resources/small_molecule/subresources/library_screen/methods/start>
- CLI flag names: `boltz-api small-molecule:library-screen start --help`

Read [references/api.md](references/api.md) for the `molecules`, `target`, and `molecule_filters` shapes, including the built-in SMARTS filters and RDKit descriptor ranges. Read [references/results.md](references/results.md) after download when ranking hits or explaining missing/filtered inputs.

## Outputs

Rank from `results/index.jsonl` after `download-results`; use [references/results.md](references/results.md) for the local file layout, metric meanings, and filtered-input accounting.
