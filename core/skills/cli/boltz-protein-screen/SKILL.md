---
name: boltz-protein-screen
description: Score a user-supplied library of protein sequences against a target with the Boltz Compute API and return ranked binding and structure metrics with per-hit complex structures. TRIGGER when the user wants to rank an existing set of proteins, peptides, antibodies, nanobodies, or binders against a target. Not for designing new proteins and not for small molecules.
---

## Workflow

Use this skill when the user already has candidate proteins / peptides / antibodies / nanobodies.

1. Normalize the binder library into `proteins` — a list of candidate complexes. For a simple sequence library each entry has one protein entity; multi-chain candidates (antibody heavy+light) are also allowed.
2. Pick the target variant:
   - `structure_template` — user has a CIF/PDB file or URL; select which chains are polymer vs ligand, which residues to keep (`crop_residues`), and optionally `epitope_residues` / `flexible_residues`.
   - `no_template` — user has only sequences; pass them as `target.entities` plus optional `epitope_residues`.
3. Don't add `bonds` / `constraints` unless the user asks for geometric steering.
4. Author the payload YAML, run `estimate-cost`, show the USD cost, wait for explicit confirmation.
5. `start` to submit. Capture the ID.
6. Launch `download-results` with the agent runtime's background/non-blocking command facility (Claude Code: `run_in_background: true` on Bash; Codex: background shells). After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.
7. Rank hits by `optimization_score` descending (fallback `binding_confidence`). Report top 5–10 with the sequence identifier, key metrics, and structure path.

## Command Pattern

```bash
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}"
IDEM="protein-screen-<target>-<library>-v1"

boltz-api protein:library-screen estimate-cost \
  --input @yaml://payload.yaml

ID=$(boltz-api protein:library-screen start \
       --idempotency-key "$IDEM" \
       --input @yaml://payload.yaml \
       --raw-output --transform id)

# Launch this command in the agent runtime's background/non-blocking mode (e.g., Claude Code Bash with `run_in_background: true`, Codex background shell).
# Do not wait on the returned background session.
boltz-api download-results \
  --id "$ID" --name "$IDEM" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 30
```

Payload keys are `proteins`, `target` — API body field names.

## Always Do This

- For `structure_template`, embed CIF/PDB bytes with `@data:///abs/path/target.cif` inside the `structure.data` field. Don't use bare `@path` (the auto-sniff once sent CIF as plain text into a base64 field and broke the server parser).
- Residue indices are 0-based. `epitope_residues` and `flexible_residues` must be subsets of `crop_residues`.
- Prefer one merged top-level payload via `--input @yaml://payload.yaml` for `estimate-cost` and `start`. Keep `--idempotency-key` and `--workspace-id` top-level; if they also appear inside `--input`, the top-level flags win.
- Direct object flags still work as overrides, such as `--target @yaml://target.yaml` or repeated `--protein @json://protein-1.json` entries. Piped YAML / JSON on stdin also works, but it must use API body field names such as `proteins` and `target`. Never use `@file://` or `@./`.
- Use the same slug as both `--idempotency-key` and `--name`.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. After the background session starts, do not wait on it or poll it. `--poll-interval-seconds 30` is a reasonable default. `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- If background mode is unavailable or blocks the conversation, use the detached fallback: `nohup boltz-api download-results ... > "$ROOT/$IDEM/download-results.log" 2>&1 < /dev/null &`, then write the PID to `$ROOT/$IDEM/download-results.pid`.
- Cost is $0.025 per submitted protein — quote the exact number from `estimate-cost` before submitting.

## Escape Hatch

- Payload reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api protein:library-screen start --help`

Read [references/api.md](references/api.md) for the `proteins` list shape and both `target` variants (structure_template with `chain_selection`, and no_template with epitope hints).

## Outputs

Under `$ROOT/$IDEM/`:

- `.boltz-run.json`
- `results/<pres_*>/archive.tar.gz` — one dir per scored binder
- `results/<pres_*>/files/result/{metrics.json, predicted_structure.cif, pae.npz}`

Per-result metrics: `optimization_score` (primary, if present), `binding_confidence`, `structure_confidence`, `iptm`, `min_interaction_pae`, `helix_fraction`, `sheet_fraction`, `loop_fraction`.
