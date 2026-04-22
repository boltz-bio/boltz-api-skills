---
name: boltz-protein-design
description: Generate novel protein binders (peptide, antibody, nanobody, or custom protein) for a target with the Boltz Compute API and return ranked designed sequences with predicted complex structures. TRIGGER when the user wants to design, generate, propose, or invent new proteins/peptides/antibodies/nanobodies/binders for a target. Not for screening user-supplied proteins and not for small molecules.
---

## Workflow

Use this skill when the user wants de novo protein / peptide / antibody / nanobody binders.

1. Normalize the target (same shape as protein-screen): `structure_template` if a CIF/PDB is available, else `no_template`.
2. Pick the `binder_specification` variant:
   - `structure_template` — redesign motifs in an existing binder scaffold (CIF + `design_motifs` with `replacement` / `insertion` segments).
   - `no_template` — generate from the sequence DSL (fixed residues + designed segments like `5..10` or `8`).
3. Pick `modality`: `peptide`, `antibody`, `nanobody`, or `custom_protein`.
4. Pick `num_proteins` — minimum **10**, server rejects lower. If the user says a smaller number, explain the floor and propose 10.
5. Add `rules` only on request (`excluded_amino_acids`, `excluded_sequence_motifs` with `X` wildcards, `max_hydrophobic_fraction`).
6. Author the payload YAML, run `estimate-cost`, show the USD cost, wait for explicit confirmation. **Design cost is `(num_proteins + 1) * $0.025`** — the extra unit is the scheduler iteration.
7. `start` to submit. Capture the ID.
8. Launch `download-results` with the agent runtime's background/non-blocking command facility (Claude Code: `run_in_background: true` on Bash; Codex: background shells). After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.
9. Rank by `optimization_score` (fallback `binding_confidence`). Report top 5–10 designs with sequence, key metrics, and structure path.

## Command Pattern

```bash
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}"
IDEM="protein-design-<modality>-<target>-v1"

boltz-api protein:design estimate-cost \
  --input @yaml://payload.yaml

ID=$(boltz-api protein:design start \
       --idempotency-key "$IDEM" \
       --input @yaml://payload.yaml \
       --raw-output --transform id)

# Launch this command in the agent runtime's background/non-blocking mode (e.g., Claude Code Bash with `run_in_background: true`, Codex background shell).
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 60
```

Payload keys are `num_proteins`, `target`, `binder_specification` — API body field names.

## Always Do This

- Enforce `num_proteins >= 10` before calling `estimate-cost`. Server rejects anything lower.
- Cost formula: `(num_proteins + 1) * $0.025`. A batch of 10 is $0.275. Quote the exact number from `estimate-cost`.
- Residue indices are 0-based everywhere (`design_motifs.start_index`/`end_index`, `after_residue_index`, `epitope_residues`, `flexible_residues`, bonds, constraints).
- For CIF/PDB bytes, use `@data:///abs/path/file.cif` inside `structure.data`. Don't use bare `@path`.
- Sequence DSL for `designed_protein.value`: uppercase letters = fixed residues; integer `N` = exactly `N` designed residues; `MIN..MAX` = variable-length designed segment. Examples: `"20"`, `"5..10"`, `"ACDE8GHI"`, `"MKTAYI5..10VKSHFSRQ"`.
- Prefer one merged top-level payload via `--input @yaml://payload.yaml` for `estimate-cost` and `start`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides, such as `--target @yaml://target.yaml` or `--binder-specification @json://binder.json`. Piped YAML / JSON on stdin also works, but it must use API body field names such as `num_proteins`, `target`, and `binder_specification`. Use the same slug for both `--idempotency-key` and `--name`.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. After the background session starts, do not wait on it or poll it. Design jobs can take 30 min to several hours — `--poll-interval-seconds 60` is a sensible default. `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- If background mode is unavailable or blocks the conversation, use the detached fallback: `nohup boltz-api download-results ... > "$ROOT/$IDEM/download-results.log" 2>&1 < /dev/null &`, then write the PID to `$ROOT/$IDEM/download-results.pid`.
- Only add `rules` on explicit user request.

## Escape Hatch

- Payload reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api protein:design start --help`

Read [references/api.md](references/api.md) for both `binder_specification` variants, the motif shapes, the sequence DSL, and the `target` variants.

## Outputs

Under `$ROOT/$IDEM/`:

- `.boltz-run.json`
- `results/<pres_*>/archive.tar.gz` — one dir per generated design
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Per-result fields: `id`, `entities` (with the generated sequences), `metrics.optimization_score` (primary), `metrics.binding_confidence`, `metrics.structure_confidence`, `metrics.iptm`, `metrics.min_interaction_pae`, `metrics.helix_fraction` / `sheet_fraction` / `loop_fraction`.
