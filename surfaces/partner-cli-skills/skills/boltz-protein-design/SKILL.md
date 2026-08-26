---
name: boltz-protein-design
description: Design new protein binders, generic proteins, or composite proteins with Boltz. Use when generating protein, peptide, antibody, nanobody, or custom candidates. Not for screening existing proteins or small molecules.
---

## Workflow

If `boltz-api` reports missing or expired authentication, surface the error to the user. Do not attempt to re-authenticate; the host environment must provide `BOLTZ_API_KEY`.

Use this skill when the user wants de novo protein / peptide / antibody / nanobody binders, generic proteins, or composite proteins.

1. Choose the request mode. New requests use the top-level `type: binder` or `type: generic` discriminator; do not author the deprecated `binder_specification` shape for a new integration. Use `binder` for target-binding designs and `generic` for designs without a binding target.
2. For `type: binder`, choose the `binder` definition: an untagged custom specification for one binder, `uniformly_sampled` to sample 1–50 specifications, or a `boltz_curated` family. For `type: generic`, define at least one designed entity and any requested bonds; use a `fusion_protein` entity when ordered protein segments should become one output chain. See [references/api.md](references/api.md) for exact shapes.
3. For antibody or nanobody requests, ask before authoring the payload: "I recommend Boltz's curated antibody/nanobody scaffolds for this. Do you want the curated default, or do you have custom scaffold structures/CDR motifs to use?" If the user picks curated, use a `binder` definition with `type: boltz_curated`; if they want custom scaffold control, use an untagged `binder` custom specification.
4. In binder mode, normalize the target (`target.entities`) and binder entities (`binder.entities`) using `from_template` or `no_template` as appropriate. In generic mode, put designed entities in the top-level `entities`; use `templates`, `global_design_filters`, `design_motifs`, and `bonds` only when needed. A generic `fusion_protein` concatenates at least two non-cyclic protein segments into its `output_chain_id`.
5. Pick `num_proteins` — valid range **10 to 1,000,000**; the server rejects values outside it. If the user says fewer than 10, explain the floor and propose 10.
6. Supported optional features include rules such as excluded amino acids, excluded sequence motifs with `X` wildcards, and max hydrophobic fraction. Add `rules` only on request; read [references/api.md](references/api.md) for exact shapes and examples.
7. Author the payload YAML or JSON.
8. `start` to submit. Capture the ID.
9. Launch `download-results` as a long-running/background command in whatever mode the host agent harness provides. After launching it, schedule the host's available follow-up/notification mechanism, if one exists, to check `download-status` periodically and notify the user when the download reaches a terminal state. Always report the job ID, run name, and output directory. Include the next check cadence if a follow-up was scheduled; otherwise include the `download-status` command.
10. For binder runs, rank from `<output-root>/<run-name>/results/index.jsonl` by `binding_confidence` descending, using `iptm` and `min_interaction_pae` as tiebreakers. Generic runs omit binding-specific metrics; rank them by `structure_confidence` and inspect the secondary-structure fractions. `optimization_score` is not emitted for this endpoint. Read [references/results.md](references/results.md) for output layout and metric details.

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

New payload keys are `type`, `num_proteins`, and `templates`, plus `target` and `binder` for binder mode or `entities` and optional `bonds` for generic mode. These are API body field names. The legacy `target` + `binder_specification` body is still accepted for migration, but new requests must use the type-discriminated shape in [references/api.md](references/api.md).

## Always Do This

- Enforce `10 <= num_proteins <= 1,000,000` before submitting. The server rejects values outside that range.
- For antibody or nanobody design, recommend a `binder` specification with `type: boltz_curated` and ask the user to confirm they do not want custom scaffold/CDR control before building the payload. Use `binder: boltz_antibody` for antibody/Fab requests and `binder: boltz_nanobody` for nanobody/VHH requests.
- When the user wants one campaign to compare multiple concrete binder definitions, use `binder.type: uniformly_sampled` with 1–50 `specifications`; each entry must be an untagged custom specification or a curated family. Do not use the legacy `uniformly_sampled_specifications` wrapper for new requests.
- Residue indices are 0-based everywhere (`design_motifs.start_index`/`end_index`, `after_residue_index`, `epitope_residues`, `flexible_residues`, bonds, constraints).
- For CIF/PDB bytes, use `@data:///abs/path/file.cif` inside `structure.data`. Don't use bare `@path`.
- Sequence DSL for `designed_protein.value`: uppercase letters = fixed residues; integer `N` = exactly `N` designed residues; `MIN..MAX` = variable-length designed segment. Examples: `"20"`, `"5..10"`, `"ACDE8GHI"`, `"MKTAYI5..10VKSHFSRQ"`.
- Keep payload field names exactly as the API body names shown in `references/api.md`.
- Use absolute paths for the output root, payload files, and embedded target files. Do not `cd` into the run directory for follow-up commands; pass the same `--root-dir` and use absolute paths so later relative paths do not drift.
- Prefer one merged top-level payload via `--input @yaml:///absolute/path/payload.yaml` or `@json:///absolute/path/payload.json`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- For a type-discriminated request, keep the complete mode in `--input`; legacy direct object flags such as `--target` and `--binder-specification` remain available for migration. Piped YAML / JSON on stdin also works, but it must use API body field names. Use the same slug for both `--idempotency-key` and `--name`.
- In permission-gated agents, keep each Boltz call as a top-level command that starts with `boltz-api`. Prefer concrete arguments over `sh -c`, inline environment assignments, aliases, wrapper scripts, loops, or pipelines around the `boltz-api` invocation unless the user already allowed that exact command form. Use `--raw-output --transform id`, read the printed ID, then paste that literal ID into the next `download-results` command.
- Run `download-results` through the host harness's long-running/background command facility. After it starts, do not manually wait on it or run ad hoc polling loops. Wall-clock time scales roughly with `num_proteins`: under 100 often finishes in a few minutes, 100-1,000 may take several minutes to tens of minutes, and larger runs can take longer or hours depending on inputs and system load. `--poll-interval-seconds 60` is a sensible downloader default. If the host harness provides a managed follow-up/notification mechanism, schedule it to check `download-status`, notify the user on terminal completion/failure, and stop once terminal. If not, do not claim an automatic next check.
- `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs.
- Prefer `boltz-api --format json download-status --name "<run-name>" --root-dir "/absolute/path/boltz-experiments"` for structured local checkpoint state. When the host provides a managed follow-up mechanism, use it for automatic checks with cadence based on `num_proteins`: under 100 -> every 1-2 minutes; 100-1,000 -> every 5 minutes; over 1,000 -> every 15 minutes. Never run a manual poll loop in the current turn.
- If a detached download needs to be restarted, re-run `boltz-api download-results` with the same `--name "<run-name>"` and the same `--root-dir`.
- Only add `rules` on explicit user request.

## Escape Hatch

- Payload reference: <https://api.boltz.bio/docs/api/resources/protein/subresources/design/methods/start/>
- CLI flag names: `boltz-api protein:design start --help`

Read [references/api.md](references/api.md) for the type-discriminated binder/generic request modes, legacy migration variants, motif shapes, sequence DSL, rules, modalities, and target variants. Read [references/results.md](references/results.md) after download when ranking designed binders or explaining outputs.

## Outputs

Rank from `results/index.jsonl` after `download-results`; use [references/results.md](references/results.md) for local file layout, metric meanings, and the designed-binder entity type gotcha.
