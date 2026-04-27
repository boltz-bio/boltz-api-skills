---
name: boltz-protein-design
description: Generate novel protein binders (peptide, antibody, nanobody, or custom protein) for a target with the Boltz Compute API and return ranked designed sequences with predicted complex structures. TRIGGER when the user wants to design, generate, propose, or invent new proteins/peptides/antibodies/nanobodies/binders for a target. Not for screening user-supplied proteins and not for small molecules.
---

## Workflow

If `boltz-api` is missing from `PATH`, use `boltz-api-cli` for install/update guidance before retrying.
If a command reports missing or expired authentication, use `boltz-api-cli` to start `boltz-api auth login --device-code` before retrying; do not ask permission first.

Use this skill when the user wants de novo protein / peptide / antibody / nanobody binders.

1. Normalize the target (same shape as protein-screen): `structure_template` if a CIF/PDB is available, else `no_template`.
2. Pick the `binder_specification` variant:
   - `structure_template` — redesign motifs in an existing binder scaffold (CIF + `design_motifs` with `replacement` / `insertion` segments).
   - `no_template` — generate from the sequence DSL (fixed residues + designed segments like `5..10` or `8`).
3. Pick `modality`: `peptide`, `antibody`, `nanobody`, or `custom_protein`.
4. Pick `num_proteins` — minimum **10**, server rejects lower. If the user says a smaller number, explain the floor and propose 10.
5. Add `rules` only on request (`excluded_amino_acids`, `excluded_sequence_motifs` with `X` wildcards, `max_hydrophobic_fraction`).
6. Author the payload YAML or JSON, run `estimate-cost`, show the USD cost, wait for explicit confirmation. **Cost scales with total complex length** (target + binder), not just `num_proteins`. A small peptide + small target runs ≈$0.025 per design; larger complexes (e.g. GFP + 20-mer binder) run ≈$0.05 per design. Always quote the exact figure from `estimate-cost`.
7. `start` to submit. Capture the ID.
8. Launch `download-results` with the agent runtime's background/non-blocking command facility. In Claude Code, use Bash with `run_in_background: true`. In Codex, run `download-results` as a foreground shell command with `yield_time_ms: 1000`; if Codex returns a `session_id`, keep it for optional later polling. After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.
9. Rank by `binding_confidence` descending (primary). Use `iptm` (higher is better) and `min_interaction_pae` (lower is better) as tiebreakers. `optimization_score` is **not emitted** for `protein:design` — do not sort by it. Report top 5–10 designs with sequence, key metrics, and structure path.

## Command Pattern

```bash
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}"
RUN_NAME="protein-design-<modality>-<target>-v1"

boltz-api protein:design estimate-cost \
  --input @yaml://payload.yaml

ID=$(boltz-api protein:design start \
       --idempotency-key "$RUN_NAME" \
       --input @yaml://payload.yaml \
       --raw-output --transform id)

# Launch this command in the agent runtime's background/non-blocking mode.
# Claude Code: Bash with run_in_background=true.
# Codex: foreground shell command with yield_time_ms=1000; keep the returned session_id if one is provided.
# Do not append "&" or use nohup in Codex.
boltz-api download-results \
  --id "$ID" --name "$RUN_NAME" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 60
```

Payload keys are `num_proteins`, `target`, `binder_specification` — API body field names.

## Always Do This

- Enforce `num_proteins >= 10` before calling `estimate-cost`. Server rejects anything lower.
- Cost scales with total complex length (target + binder). Do not quote a flat `num_proteins * $0.025` formula; always quote `estimated_cost_usd` from `estimate-cost`. Empirically: minimal peptide + small target ≈$0.025/design; GFP-sized target + 20-mer binder ≈$0.05/design.
- Residue indices are 0-based everywhere (`design_motifs.start_index`/`end_index`, `after_residue_index`, `epitope_residues`, `flexible_residues`, bonds, constraints).
- For CIF/PDB bytes, use `@data:///abs/path/file.cif` inside `structure.data`. Don't use bare `@path`.
- Sequence DSL for `designed_protein.value`: uppercase letters = fixed residues; integer `N` = exactly `N` designed residues; `MIN..MAX` = variable-length designed segment. Examples: `"20"`, `"5..10"`, `"ACDE8GHI"`, `"MKTAYI5..10VKSHFSRQ"`.
- Keep payload field names exactly as the API body names shown in `references/api.md`.
- Prefer one merged top-level payload via `--input @yaml://payload.yaml` or `@json://payload.json` for `estimate-cost` and `start`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides, such as `--target @yaml://target.yaml` or `--binder-specification @json://binder.json`. Piped YAML / JSON on stdin also works, but it must use API body field names. Use the same slug for both `--idempotency-key` and `--name`.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. In Codex specifically, keep `download-results` in the foreground and set the shell tool yield to 1000 ms; Codex will return a `session_id` if the command is still running. Do not append `&` or use `nohup` in Codex because the tool runner may clean up shell-backgrounded descendants before `.boltz-run.json` is fully written.
- After the background/session starts, do not wait on it or poll it. Design jobs can take 30 min to several hours — `--poll-interval-seconds 60` is a sensible default. `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- Only check status when the user asks. In Codex, poll the saved session with an empty `write_stdin`, or prefer `boltz-api --format json download-status --name "$RUN_NAME" --root-dir "$ROOT"` for structured local checkpoint state. Never run a manual poll loop.
- If detached download needs to be restarted, re-run `boltz-api download-results` with the same `--name "$RUN_NAME"` and the same `--root-dir`.
- Only add `rules` on explicit user request.

## Escape Hatch

- Payload reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api protein:design start --help`

Read [references/api.md](references/api.md) for both `binder_specification` variants, the motif shapes, the sequence DSL, and the `target` variants.

## Outputs

Under `$ROOT/$RUN_NAME/`:

- `.boltz-run.json`
- `results/<pres_*>/archive.tar.gz` — one dir per generated design
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Per-result fields:

- `id`, `artifacts.{structure, archive}`
- `entities` — the generated designs. **Type-flip gotcha:** the binder entity comes back as `type: "protein"` (not `"designed_protein"`), with the DSL resolved to a real AA sequence in `value`. Select the binder by `chain_ids` (the ID you assigned at submit time), **not** by `type == "designed_protein"`.
- `metrics.binding_confidence` — **primary ranking metric**
- `metrics.structure_confidence`
- `metrics.iptm` (higher is better)
- `metrics.min_interaction_pae` (lower is better)
- `metrics.helix_fraction` / `sheet_fraction` / `loop_fraction`

**No `optimization_score` on this endpoint.** Sorting by it returns an empty list.
