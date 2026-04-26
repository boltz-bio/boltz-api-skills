# Pre-ship checklist — `boltz-compute-cli`

Things we claimed, documented, or assumed during implementation that are **not verified end-to-end**. Resolve these before shipping to users.

Grouped by severity. Checkbox form so we can work through them.

---

## Blockers — must verify before ship

### - [ ] End-to-end `start` → `download-results` round trip (1 skill)

Send a tiny SAB prediction (one small protein + one ligand) following the exact command pattern in `skills/boltz-structure-and-binding/SKILL.md`. Verify:
- `estimate-cost` returns expected `{estimated_cost_usd, breakdown, disclaimer}`
- `start` with `--idempotency-key $RUN_NAME --raw-output --transform id` returns the ID
- `download-results --id $ID --name $RUN_NAME --root-dir ./test-run` creates `./test-run/$RUN_NAME/.boltz-run.json` and `./test-run/$RUN_NAME/outputs/archive.tar.gz`
- Tarball unpacks to `prediction/{metrics.json, sample_*_predicted_structure.cif, sample_*_pae.npz}`
- Metrics file has the fields we list (`pLDDT`, `pTM`, `ipTM`, `binding_confidence` if `binding` was requested, etc.)

If any of this breaks, the SKILL.md command pattern is wrong and every other skill is suspect.

### - [ ] Cross-session resume via `.boltz-run.json`

- Submit a job, launch `download-results` in the background, `kill -9` the process mid-download.
- Re-run the exact same `download-results --id --name --root-dir` command.
- Verify it reads `.boltz-run.json`, advances from `cursor_after_id`, downloads only new results. Also verify `download-status --name $RUN_NAME --root-dir ... --format json` reflects the interrupted and resumed state cleanly. We haven't personally triggered this on v0.7.0 yet.

### - [ ] `modifications` is actually optional (CLI_USAGE §3)

We removed the `modifications: []` gotcha from the plan and docs based on the CLI changelog line that omitted polymer modifications are fixed. Smoke test:

```yaml
entities:
  - type: protein
    chain_ids: [A]
    value: MKTAYIAKQRQISFVKSHFSRQ
    # NO modifications field
```

Submit via `start` (or just `estimate-cost`) and verify no 400. If this still fails, the `modifications: []` requirement has to come back into the gotcha table of every skill's `SKILL.md` and every `references/api.md`.

### - [ ] `num_proteins >= 10` / `num_molecules >= 10` server enforcement

Submit `small-molecule:design` with `num_molecules: 5` and confirm the server returns the validation error. We claim this limit in the SKILL.md "Always do this" bullets and the cost formula uses it — need to verify it still trips. Same for `protein:design` with `num_proteins: 5`.

### - [ ] `estimate-cost` returns the `(num + 1)` formula we claim

Call `small-molecule:design estimate-cost` with `num_molecules: 10` and verify it reports $0.275, not $0.250. Same for `protein:design`. This is in every design SKILL.md — if wrong, we're quoting wrong prices to users.

---

## Shipping-gate — fix before public release

### - [ ] `.codex-plugin/plugin.json` has `[TODO: ...]` placeholders

Open placeholders in `plugin.json`:
- `author` object (name, email, url)
- `homepage`, `repository`, `license`
- `websiteURL`, `privacyPolicyURL`, `termsOfServiceURL`
- `brandColor`, `composerIcon`, `logo`, `screenshots`

These don't block local testing but will show up in the Codex plugin picker — fill them before a public listing.

### - [ ] docs.boltz.bio escape-hatch URLs actually resolve

Every `references/api.md` footer points at:
- `https://docs.boltz.bio/api-reference/api-input-format.md`
- `https://docs.boltz.bio/api-reference/openapi.json`

We confirmed the `llms.txt` index lists these paths but didn't personally fetch each target to verify content quality for an agent trying to grok an undocumented field. WebFetch each, confirm the schema content is actually useful.

### - [ ] Codex trigger smoke test

Install the plugin in a fresh Codex session and verify natural-language prompts route to the intended skill:

| Prompt | Should select |
|---|---|
| "Fold this complex: <seq> + <smiles>" | `boltz-structure-and-binding` |
| "Screen this SMILES list against my target" | `boltz-small-molecule-screen` |
| "Design small-molecule binders for this protein" | `boltz-small-molecule-design` |
| "Rank these nanobodies against KRAS" | `boltz-protein-screen` |
| "Design a nanobody for this epitope" | `boltz-protein-design` |
| "What Boltz jobs are running?" / "my session died, recover $ID" | `boltz-check-status` |

If any route wrong, tune the `description` frontmatter. The Python plugin's descriptions are tuned for its trigger set — CLI-plugin variants are verbatim lifts, so this is mostly a sanity check.

### - [x] Managed download session works in Codex

Codex supports this flow by running `download-results` as a foreground shell command with `yield_time_ms=1000`. If the command is still running, Codex returns a session id; the agent can later poll it with an empty `write_stdin` or use `download-status` for structured checkpoint state.

Do not use shell `&`, terminal backgrounding, or `nohup` for `download-results` in Codex. A benchmark follow-up reproduced child cleanup before completion: `nohup ... &` could leave only a PID/log or a partial `.boltz-run.json`, while the managed foreground session wrote the checkpoint and downloaded all results.

### - [x] CLI version floor

SKILL.md and `plugin.json` assume the current v0.7.0+ surface: unified `--id`, merged `--input` on design/screen commands, top-level `download-results`, and `download-status`. README now states `boltz-api >= 0.7.0` and calls out the likely "No such command" symptom when an older or wrong binary is installed. The skills still do not preflight every run.

---

## Nice-to-have — not blocking but worth a pass

### - [ ] Live-validate `@data:///abs/path/file.cif` on a real CIF

We claim `@data://` is the correct encoding for binary CIF/PDB bytes (per CLI_USAGE §2.4). Used in protein-screen and protein-design skills for `structure.data`. Submit a protein-screen with a real local CIF and confirm the server parses it. If it doesn't, the skill needs a workaround (explicit base64 in YAML).

### - [ ] Verify `idempotency_key` is actually echoed back in `retrieve` responses

Mode 3b of `boltz-check-status` depends on `retrieve --id $ID` returning `idempotency_key` in the response body, so a crashed-session user can recover the slug. I saw it once in the live smoke test during authoring (`"idempotency_key": "walkthrough-v2"`) but should verify it's populated for all five resources, not just SAB. If a design or screen endpoint omits it, the crash-recovery Mode 3b falls back to the "pick a new slug" fallback — tolerable but worth knowing.

### - [ ] CLI auto-pagination behavior on `list`

During implementation I discovered `--limit` is per-page and the CLI auto-paginates — calling `list --limit 20` streamed 362 records. I updated `boltz-check-status` to pipe through `head -N`. Before shipping, confirm this is still the behavior and that `head` doesn't cause a "broken pipe" message that would spook users / break JSON. If there's a `--max-results` or similar total cap, prefer that.

### - [ ] `--transform` GJSON multi-field silent failure

CLI_USAGE §8.4 warns `--transform '#.{a,b}'` silently returns `{}`. We tell agents to use `jq` for multi-field. Verify this is still the behavior — if the CLI now errors instead, our "silent failure" warning is outdated.

### - [ ] Trailing-newline on `@file` scalar substitution

CLI_USAGE §8.2 notes `@./model.txt` on a scalar flag includes the trailing newline and fails enum validation (`echo 'boltz-2.1' > model.txt; --model @./model.txt` → rejected). We don't use `@./` anywhere (skills use literals for `--model`), so this is only relevant if an agent invents the pattern. Low priority.

### - [ ] `BOLTZ_COMPUTE_OUTPUT_DIR` env var name

We picked `BOLTZ_COMPUTE_OUTPUT_DIR` to match the CLI's `BOLTZ_COMPUTE_*` namespace. The old Python skills used `BOLTZ_OUTPUT_DIR`. If the CLI team has an opinion on the name, align with theirs; this is a one-line grep-and-replace across the plugin.

### - [ ] `results/<pres_*>/files/result/` layout is consistent

We document this layout in every screen/design `api.md` and `SKILL.md`. Verified indirectly via CLI_USAGE §4.3 — should spot-check on a live download that the dir structure actually matches what we claim, especially the `files/result/` vs `files/` distinction.

---

## Won't fix / accepted risk

- **No auth preflight.** User chose this explicitly. If `BOLTZ_COMPUTE_API_KEY` is unset, the first CLI call fails with a readable auth error and the agent relays it. Ship as-is.
- **No `boltz-api` install check.** Same reasoning. If the binary is missing, `command not found` surfaces immediately. Ship as-is.
- **Schema drift.** Every `references/api.md` embeds schema that's canonically in Boltz's OpenAPI spec. It will drift. Mitigation: every `api.md` ends with a link to the upstream docs + `openapi.json` as the source of truth. When we bump CLI versions, skim for schema deltas and update. Acceptable maintenance cost.
