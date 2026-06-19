---
name: boltz-protein-design
description: Design new protein binders with Boltz. Use when generating protein, peptide, antibody, nanobody, or custom binder candidates for a target. Not for screening existing proteins or small molecules.
---

## Workflow

If `boltz-api` reports missing or expired authentication, surface the error to the user. Do not attempt to re-authenticate; the host environment must provide `BOLTZ_API_KEY`.

Use this skill when the user wants de novo protein / peptide / antibody / nanobody binders.

1. Normalize the target (same shape as protein-screen): `structure_template` if a CIF/PDB is available, else `no_template`.
2. Pick the `binder_specification` variant. Supported variants include:
   - `boltz_curated` — recommended default for antibody and nanobody design. Boltz selects from maintained scaffold/template lists (`binder: boltz_antibody` or `boltz_nanobody`).
   - `structure_template` — redesign motifs in an existing binder scaffold (CIF + `design_motifs` with `replacement` / `insertion` segments).
   - `no_template` — generate from the sequence DSL (fixed residues + designed segments like `5..10` or `8`).
3. For antibody or nanobody requests, ask before authoring the payload: "I recommend Boltz's curated antibody/nanobody scaffolds for this. Do you want the curated default, or do you have custom scaffold structures/CDR motifs to use?" If the user picks curated, use `type: boltz_curated`; if they want custom scaffold control, use `type: structure_template`.
4. Pick `modality`: `peptide`, `antibody`, `nanobody`, or `custom_protein` for `structure_template` and `no_template`. Do not include `modality` on `boltz_curated`; use `binder` instead.
5. Pick `num_proteins` — minimum **10**, server rejects lower. If the user says a smaller number, explain the floor and propose 10.
6. Supported optional features include rules such as excluded amino acids, excluded sequence motifs with `X` wildcards, and max hydrophobic fraction. Add `rules` only on request; read [references/api.md](references/api.md) for exact shapes and examples.
7. Author the payload YAML or JSON.
8. `start` to submit. Capture the ID.
9. Launch `download-results` as a long-running/background command in whatever mode the host agent harness provides. After launching it, schedule the host's available follow-up/notification mechanism to check `download-status` periodically and notify the user when the download reaches a terminal state. Report the job ID, run name, output directory, and next check cadence.
10. Rank from `<output-root>/<run-name>/results/index.jsonl` by `binding_confidence` descending. Use `iptm` and `min_interaction_pae` as tiebreakers. `optimization_score` is not emitted for this endpoint. Read [references/results.md](references/results.md) for output layout and metric details.

## Command Pattern

```bash
# Replace placeholders with concrete absolute paths before running.
# Use a short descriptive run name, for example: protein-design-<modality>-<target>-v1

boltz-api protein:design start \
       --idempotency-key "<run-name>" \
       --input @yaml:///absolute/path/payload.yaml \
       --raw-output --transform id

# Copy the printed job ID into this command, then launch it as a
# long-running/background command via the host agent harness.
boltz-api download-results \
  --id "<job-id-from-start>" --name "<run-name>" \
  --root-dir "/absolute/path/boltz-experiments" \
  --poll-interval-seconds 60
```

Payload keys are `num_proteins`, `target`, `binder_specification` — API body field names.

## Always Do This

- Enforce `num_proteins >= 10` before submitting. Server rejects anything lower.
- For antibody or nanobody design, recommend `binder_specification.type: boltz_curated` and ask the user to confirm they do not want custom scaffold/CDR control before building the payload. Use `binder: boltz_antibody` for antibody/Fab requests and `binder: boltz_nanobody` for nanobody/VHH requests.
- Residue indices are 0-based everywhere (`design_motifs.start_index`/`end_index`, `after_residue_index`, `epitope_residues`, `flexible_residues`, bonds, constraints).
- For CIF/PDB bytes, use `@data:///abs/path/file.cif` inside `structure.data`. Don't use bare `@path`.
- Sequence DSL for `designed_protein.value`: uppercase letters = fixed residues; integer `N` = exactly `N` designed residues; `MIN..MAX` = variable-length designed segment. Examples: `"20"`, `"5..10"`, `"ACDE8GHI"`, `"MKTAYI5..10VKSHFSRQ"`.
- Keep payload field names exactly as the API body names shown in `references/api.md`.
- Use absolute paths for the output root, payload files, and embedded target files. Do not `cd` into the run directory for follow-up commands; pass the same `--root-dir` and use absolute paths so later relative paths do not drift.
- Prefer one merged top-level payload via `--input @yaml:///absolute/path/payload.yaml` or `@json:///absolute/path/payload.json`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides, such as `--target @yaml:///absolute/path/target.yaml` or `--binder-specification @json:///absolute/path/binder.json`. Piped YAML / JSON on stdin also works, but it must use API body field names. Use the same slug for both `--idempotency-key` and `--name`.
- In permission-gated agents, keep each Boltz call as a top-level command that starts with `boltz-api`. Prefer concrete arguments over `sh -c`, inline environment assignments, aliases, wrapper scripts, loops, or pipelines around the `boltz-api` invocation unless the user already allowed that exact command form. Use `--raw-output --transform id`, read the printed ID, then paste that literal ID into the next `download-results` command.
- Run `download-results` through the host harness's long-running/background command facility. After it starts, do not manually wait on it or run ad hoc polling loops. Design jobs can take 30 min to several hours — `--poll-interval-seconds 60` is a sensible default. Schedule the host's available follow-up/notification mechanism to check `download-status`, notify the user on terminal completion/failure, and stop once terminal.
- `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs.
- Prefer `boltz-api --format json download-status --name "<run-name>" --root-dir "/absolute/path/boltz-experiments"` for structured local checkpoint state. Use the host's managed follow-up mechanism for automatic checks. Never run a manual poll loop in the current turn.
- If a detached download needs to be restarted, re-run `boltz-api download-results` with the same `--name "<run-name>"` and the same `--root-dir`.
- Only add `rules` on explicit user request.

## Escape Hatch

- Payload reference: <https://api.boltz.bio/docs/api/resources/protein/subresources/design/methods/start/>
- CLI flag names: `boltz-api protein:design start --help`

Read [references/api.md](references/api.md) for all `binder_specification` variants, motif shapes, sequence DSL, rules, modalities, and `target` variants. Read [references/results.md](references/results.md) after download when ranking designed binders or explaining outputs.

## Outputs

Rank from `results/index.jsonl` after `download-results`; use [references/results.md](references/results.md) for local file layout, metric meanings, and the designed-binder entity type gotcha.
