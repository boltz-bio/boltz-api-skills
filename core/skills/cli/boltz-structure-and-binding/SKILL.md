---
name: boltz-structure-and-binding
description: Predict the 3D structure of a protein, RNA, DNA, or ligand complex with the Boltz Compute API and optionally score binding. TRIGGER when the user asks to fold a complex, dock a ligand, predict an interface, generate a CIF or PDB for a defined system, or get structure and binding metrics for one specified complex. Not for screening libraries or designing new molecules.
---

## Workflow

If `boltz-api` is missing from `PATH`, use `boltz-api-cli` for install/update guidance before retrying.
If a command reports missing or expired authentication, use `boltz-api-cli` to start `boltz-api auth login --device-code` before retrying; do not ask permission first.
If the agent host sandbox blocks `boltz-api` install/auth/API calls, use `boltz-api-cli` to set workspace-local `HOME`, `TMPDIR`, `BOLTZ_API_INSTALL_DIR`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` before retrying. Request the host sandbox bypass only if workspace-local state still fails.

Use this skill for one defined complex, not a library workflow.

1. Normalize the inputs into `entities`. Each entity is **`{type, chain_ids, value}`** — note plural `chain_ids` (an array, even for one chain) and the field is `value`, **not** `sequence`:

   ```json
   {"entities": [{"type": "protein", "chain_ids": ["A"], "value": "MKTAYIAKQRQISFVKSHFSRQ"}]}
   ```

   `type` is one of `protein | rna | dna | ligand_smiles | ligand_ccd`. Chain IDs go in entity order (`A`, `B`, `C`, …) unless the user specifies otherwise. Read `references/api.md` for per-type field variants (`cyclic`, `modifications`, ligand CCD codes, etc.) **before** authoring your first payload — agent guesses like `sequence:` or `chain_id: "A"` (singular) fail with opaque 400s.
2. If the user wants binding metrics, add a flat `binding` block with an explicit `type` field. For ligand-protein binding use:

   ```yaml
   binding:
     type: ligand_protein_binding
     binder_chain_id: B
   ```

   For protein-protein binding use:

   ```yaml
   binding:
     type: protein_protein_binding
     binder_chain_ids: [B]
   ```

   Do not nest the variant name under `binding` (for example, no `binding.ligand_protein_binding` object).
3. Only add `constraints` / `bonds` / `modifications` / `model_options` if the user asks.
4. Author the payload YAML or JSON, run `estimate-cost`, show the USD cost, wait for explicit confirmation.
5. `start` to submit (synchronous). Capture the ID.
6. Launch `download-results` with the agent runtime's background/non-blocking command facility so polling + download continue without blocking the agent session. In Claude Code, use Bash with `run_in_background: true`. In Codex, run `download-results` as a foreground shell command with `yield_time_ms: 1000`; if Codex returns a `session_id`, keep it for optional later polling. After launching it, report the job ID, run name, and output directory, then end the turn immediately. Do not wait on the background session unless the user explicitly asks for progress.

## Command Pattern

```bash
WORKDIR="$(pwd)"
ROOT="${BOLTZ_COMPUTE_OUTPUT_DIR:-$WORKDIR/boltz-experiments}"
RUN_NAME="sab-<target>-<ligand>-v1"    # short descriptive slug
PAYLOAD="$WORKDIR/payload.yaml"

# 1. estimate
boltz-api predictions:structure-and-binding estimate-cost \
  --model boltz-2.1 \
  --input "@yaml://$PAYLOAD"

# 2. confirm with user, then submit
ID=$(boltz-api predictions:structure-and-binding start \
       --model boltz-2.1 \
       --idempotency-key "$RUN_NAME" \
       --input "@yaml://$PAYLOAD" \
       --raw-output --transform id)

# 3. Launch this command in the agent runtime's background/non-blocking mode.
# Claude Code: Bash with run_in_background=true.
# Codex: foreground shell command with yield_time_ms=1000; keep the returned session_id if one is provided.
# Do not append "&" or use nohup in Codex.
boltz-api download-results \
  --id "$ID" --name "$RUN_NAME" \
  --root-dir "$ROOT" \
  --poll-interval-seconds 10
# → $ROOT/$RUN_NAME/outputs/archive.tar.gz, .boltz-run.json
```

## Always Do This

- Keep payload field names exactly as the API body names shown in `references/api.md`; then pass the merged payload with `--input @yaml:///absolute/path/payload.yaml` or `@json:///absolute/path/payload.json`. Never use `@./payload.yaml` or `@file://` for object-typed payloads.
- Use absolute paths for `ROOT`, payload files, and embedded structure files. Do not `cd "$ROOT/$RUN_NAME"` for follow-up commands; pass `--root-dir "$ROOT"` and use absolute paths so later relative paths do not drift.
- Residue indices are 0-based wherever the payload asks for residue positions (constraints, modifications, contact tokens).
- For CIF/PDB bytes embedded in `--target` / `structure.data`, use `@data:///absolute/path/file.cif` — it sniffs binary and base64-encodes. Don't use bare `@path` for binary data.
- Use the same slug as both `--idempotency-key` at submit time and `--name` at download time so re-runs are idempotent and resume from `.boltz-run.json`.
- Prefer the agent runtime's background/non-blocking command mode for `download-results`. In Codex specifically, keep `download-results` in the foreground and set the shell tool yield to 1000 ms; Codex will return a `session_id` if the command is still running. Do not append `&` or use `nohup` in Codex because the tool runner may clean up shell-backgrounded descendants before `.boltz-run.json` is fully written.
- After the background/session starts, do not wait on it or poll it. `download-results` emits JSONL progress on stderr by default; add `--progress-format text --verbose` only when you explicitly want human-readable logs. Report the job ID, run name, output directory, and that the runtime should notify when the background command completes.
- Only check progress when the user asks. In Codex, poll the saved session with an empty `write_stdin`, or prefer `boltz-api --format json download-status --name "$RUN_NAME" --root-dir "$ROOT"` for structured local checkpoint state. Do not loop `retrieve` yourself.
- If detached download needs to be restarted, re-run `boltz-api download-results` with the same `--name "$RUN_NAME"` and the same `--root-dir`.
- Poll interval: keep `--poll-interval-seconds 10` for SAB — predictions usually finish in under a few minutes.

## Escape Hatch

For anything not covered in `references/api.md`:

- Upstream request body reference: <https://docs.boltz.bio/api-reference/api-input-format.md>
- Full spec: <https://docs.boltz.bio/api-reference/openapi.json>
- CLI flag names: `boltz-api predictions:structure-and-binding start --help` (schema details aren't there — just flag names and types)

Read [references/api.md](references/api.md) for entity shapes, binding variants, bonds, constraints, model options, and output metrics.

## Outputs

Under `$ROOT/$RUN_NAME/`:

- `.boltz-run.json` — run metadata, cursor, idempotency key
- `outputs/archive.tar.gz` — unpacks to `prediction/{metrics.json, sample_*_predicted_structure.cif, sample_*_pae.npz}`

Metrics in `metrics.json` are **nested, not flat**:

- `best_sample.metrics` and each `all_sample_results[].metrics` contain nine lowercase keys: `structure_confidence`, `ptm`, `iptm`, `ligand_iptm` (only when ligands present), `protein_iptm` (only for multi-protein complexes), `complex_plddt`, `complex_iplddt`, `complex_pde`, `complex_ipde`.
- `binding_metrics` is a **separate top-level object** present only when `binding` was requested. Shape depends on the binding variant: `ligand_protein_binding` → `{binding_confidence, optimization_score}`; `protein_protein_binding` → `{binding_confidence}` only (no `optimization_score`).

Summarize these for the user and point them at the CIF path.

## SAB 400 validation quirk

If the server rejects the payload with only `{"code": "VALIDATION_ERROR", "message": "Request validation failed"}` and no field-level details, inspect the `entities`, `binding`, and `constraints` blocks carefully — `predictions:structure-and-binding` is the one endpoint that currently omits `details`. The other four endpoints return specific field paths.
