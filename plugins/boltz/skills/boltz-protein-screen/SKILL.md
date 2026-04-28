---
name: boltz-protein-screen
description: Score a user-supplied library of protein sequences against a target with the Boltz Compute API and return ranked binding and structure metrics with per-hit complex structures. TRIGGER when the user wants to rank an existing set of proteins, peptides, antibodies, nanobodies, or binders against a target. Not for designing new proteins and not for small molecules.
---

## Workflow

If `boltz-api` is missing from `PATH`, use `boltz-api-cli` for install/update guidance before retrying.
If a command reports missing or expired authentication, use `boltz-api-cli` to start `boltz-api auth login --device-code` before retrying; do not ask permission first.
If the agent host sandbox blocks `boltz-api` install/auth/API calls, use `boltz-api-cli` to set workspace-local `HOME`, `TMPDIR`, `BOLTZ_API_INSTALL_DIR`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` before retrying. Request the host sandbox bypass only if workspace-local state still fails.

Use this skill when the user already has candidate proteins / peptides / antibodies / nanobodies.

1. Normalize the binder library into `proteins` — a list of candidate complexes. For a simple sequence library each entry has one protein entity; multi-chain candidates (antibody heavy+light) are also allowed.
2. Pick the target variant:
   - `structure_template` — user has a CIF/PDB file or URL; select which chains are polymer vs ligand, which residues to keep (`crop_residues`), and optionally `epitope_residues` / `flexible_residues`.
   - `no_template` — user has only sequences; pass them as `target.entities` plus optional `epitope_residues`.
3. Don't add `bonds` / `constraints` unless the user asks for geometric steering.
4. Author the payload YAML or JSON, run `estimate-cost`, show the USD cost, wait for explicit confirmation.
5. `start` to submit. Capture the ID.
6. Launch `download-results` with the agent runtime's background/non-blocking command facility. In Claude Code, use Bash with `run_in_background: true`. In Codex, run `download-results` as a foreground shell command with `yield_time_ms: 1000`; if Codex returns a `session_id`, keep it for optional later polling. After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.
7. Rank hits from `<output-root>/<run-name>/results/index.jsonl` by `binding_confidence` descending (primary). Use `iptm` (higher is better) and `min_interaction_pae` (lower is better) as tiebreakers. `optimization_score` is **not emitted** for `protein:library-screen` — do not sort by it. Report top 5–10 with the sequence identifier, key metrics, and structure path.

## Command Pattern

```bash
# Replace placeholders with concrete absolute paths before running.
# Use a short descriptive run name, for example: protein-screen-<target>-<library>-v1

boltz-api protein:library-screen estimate-cost \
  --input @yaml:///absolute/path/payload.yaml

boltz-api protein:library-screen start \
       --idempotency-key "<run-name>" \
       --input @yaml:///absolute/path/payload.yaml \
       --raw-output --transform id

# Copy the printed job ID into this command, then launch it in the agent
# runtime's background/non-blocking mode.
# Claude Code: Bash with run_in_background=true.
# Codex: foreground shell command with yield_time_ms=1000; keep the returned session_id if one is provided.
# Do not append "&" or use nohup in Codex.
boltz-api download-results \
  --id "<job-id-from-start>" --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments" \
  --poll-interval-seconds 30
```

Payload keys are `proteins`, `target` — API body field names.

## Always Do This

- For `structure_template`, embed CIF/PDB bytes with `@data:///abs/path/target.cif` inside the `structure.data` field. Don't use bare `@path` (the auto-sniff once sent CIF as plain text into a base64 field and broke the server parser).
- Residue indices are 0-based. `epitope_residues` and `flexible_residues` must be subsets of `crop_residues`.
- Keep payload field names exactly as the API body names shown in `references/api.md`.
- Use absolute paths for the output root, payload files, and embedded target files. Do not `cd` into the run directory for follow-up commands; pass the same `--root-dir` and use absolute paths so later relative paths do not drift.
- Prefer one merged top-level payload via `--input @yaml:///absolute/path/payload.yaml` or `@json:///absolute/path/payload.json` for `estimate-cost` and `start`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides, such as `--target @yaml:///absolute/path/target.yaml` or repeated `--protein @json:///absolute/path/protein-1.json` entries. Piped YAML / JSON on stdin also works, but it must use API body field names. Never use `@file://` or `@./`.
- Use the same slug as both `--idempotency-key` and `--name`.
- In permission-gated agents such as Claude Code, keep each Boltz call as a top-level command that starts with `boltz-api`. Prefer concrete arguments over `sh -c`, inline environment assignments, aliases, wrapper scripts, loops, or pipelines around the `boltz-api` invocation unless the user already allowed that exact command form. Use `--raw-output --transform id`, read the printed ID, then paste that literal ID into the next `download-results` command.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. In Codex specifically, keep `download-results` in the foreground and set the shell tool yield to 1000 ms; Codex will return a `session_id` if the command is still running. Do not append `&` or use `nohup` in Codex because the tool runner may clean up shell-backgrounded descendants before `.boltz-run.json` is fully written.
- After the background/session starts, do not wait on it or poll it. `--poll-interval-seconds 30` is a reasonable default. `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- Only check status when the user asks. In Codex, poll the saved session with an empty `write_stdin`, or prefer `boltz-api --format json download-status --name "<run-name>" --root-dir "/absolute/path/boltz-experiments"` for structured local checkpoint state. Never run a manual poll loop.
- If detached download needs to be restarted, re-run `boltz-api download-results` with the same `--name "<run-name>"` and the same `--root-dir`.
- Cost scales with total complex length (target + candidate). Typically ≈$0.025 per submitted candidate for small complexes, more for larger ones. Quote the exact figure from `estimate-cost`.

## Escape Hatch

- Payload reference: <https://boltz-compute-api.stldocs.app/api/python/resources/protein/subresources/library_screen/methods/start>
- CLI flag names: `boltz-api protein:library-screen start --help`

Read [references/api.md](references/api.md) for the `proteins` list shape and both `target` variants (structure_template with `chain_selection`, and no_template with epitope hints).

## Outputs

Under `<output-root>/<run-name>/`:

- `.boltz-run.json`
- `run.json` — sanitized remote run record
- `results/index.jsonl` — one scored binder per line, with `external_id`/`entities`, `metrics`, and local `paths`
- `results/<pres_*>/metadata.json` — per-result metadata copied from the list-results record
- `results/<pres_*>/archive.tar.gz` — one dir per scored binder
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Rank from `results/index.jsonl` after `download-results`. Per-result metrics: `binding_confidence` (primary), `structure_confidence`, `iptm` (higher better), `min_interaction_pae` (lower better), `helix_fraction`, `sheet_fraction`, `loop_fraction`. **No `optimization_score`** on this endpoint — sorting by it returns an empty list.
