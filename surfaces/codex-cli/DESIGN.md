# Design notes — boltz-compute-cli plugin

What this plugin is, why it's shaped the way it is, and what we're explicitly giving up.

## One-line summary

A Codex plugin that ships six workflow skills for the Boltz Compute API. Each skill is prose + schema reference. The agent authors a YAML payload and invokes the `boltz-api` Go CLI directly. No Python, no SDK, no wrapper scripts.

## Context

Two prior plugins exist in this repo: `skills-python/` (Claude Code) and `codex-plugin-python/` (Codex). Both used the `boltz-compute` Python SDK and each shipped a ~350-line `scripts/query.py` wrapper per skill (2,149 LOC across six skills) that handled input parsing, payload assembly, polling, and download.

The `boltz-api` Go CLI (v0.7.0, Stainless-generated from the same OpenAPI spec as the Python SDK) now exposes all that machinery natively:
- unified `--id` across retrieve / list-results / stop / delete-data
- merged top-level `--input` payloads for design / screen `estimate-cost` and `start`
- `download-results` with internal poll loop, artifact download, and `.boltz-run.json`-cursor-based resume
- `download-status` for reading the local checkpoint without an API call
- `estimate-cost` on every resource
- `@json://` / `@yaml://` / `@data://` input patterns
- idempotency via `--idempotency-key`

So we drop the Python wrapper entirely. The agent becomes the input parser; the CLI becomes the runtime.

## Design choices + tradeoffs

### 1. CLI-first, no SDK wrapper

**Chose:** agent invokes `boltz-api` subprocess directly.

**Trade:** agents must read schema docs + author YAML rather than calling typed Python functions. **Gain:** zero Python runtime dep, zero install step (assuming CLI is on PATH), and the 2,149 LOC of wrappers disappears. CLI bug fixes land for free; we never need to bump a pinned SDK version.

### 2. Agent authors YAML; no input-parsing helpers

**Chose:** no `scripts/` dir. The agent reads FASTA / CSV / SMI / raw sequences itself and emits a payload YAML.

**Trade:** LLM tokens per invocation are higher (reads `references/api.md`, constructs YAML). **Gain:** the entire input-parsing layer (FASTA detection, CSV SMILES-column autodetect, entity dict construction, chain-ID assignment) — ~100 LOC per skill in the Python version — vanishes. Agents are already very good at parsing structured files; the cost is small.

### 3. Five workflow skills + one status/recovery skill, not one omnibus

**Chose:** six separate `SKILL.md` files with tight per-endpoint `description` triggers (lifted verbatim from the Python plugin — those triggers are tuned).

**Trade:** small prose duplication of the "estimate → confirm → submit → background download" lifecycle across five skills. **Gain:** precise trigger matching (Codex selects the right skill from "design a nanobody" vs "screen these SMILES" without loose overlap); each SKILL.md stays short enough that agents read past the first 30%.

### 4. Three-layer doc model

| Layer | File | When agent hits it |
|---|---|---|
| Workflow | `SKILL.md` (~70 lines) | Every invocation |
| Schema | `references/api.md` (~200 lines) | When authoring payload |
| Upstream | `docs.boltz.bio/api-reference/*.md` + `openapi.json` | Fallback for undocumented fields |

`boltz-api <resource> start --help` exists as a fourth fallback but is not a schema source — we verified live that it only lists flag names and types, nothing about the shape of `--input` / `--target` / `--binder-specification` objects.

**Trade:** the `references/api.md` files duplicate content that's canonically in Boltz's OpenAPI spec and will drift if the API evolves. **Gain:** agents get the schema + known gotchas in one pre-digested file instead of fetching the full spec on every run. Drift is manageable because the upstream docs are one hop away and linked from every `api.md`.

### 5. Idempotency slug as both `--idempotency-key` AND `--name`

**Chose:** agent picks a short descriptive slug (e.g. `kras-g12d-enamine-v1`) at submit time. Same slug passed as `--idempotency-key` on `start` and `--name` on `download-results`.

**Trade:** agent has to pick a slug — small judgment cost. **Gain:**
- Retrying `start` with the same key is a no-op (server dedups).
- `download-results` reuses `.boltz-run.json` at `$ROOT/$IDEM/` and resumes from the cursor — this is the crash-recovery primitive.
- Output dirs are readable (`ls $ROOT` shows project slugs, not `pred_AwcjRFqcDMguILMl4laU/`).

Alternative considered: use the server-assigned job ID as `--name`. Rejected because it's opaque, can only be known post-submit, and loses the "pre-submit dir is predictable" property.

### 6. Output dir: `${BOLTZ_COMPUTE_OUTPUT_DIR:-./boltz-experiments}`

**Chose:** project-local default. Matches the CLI's own default.

**Trade:** artifacts live under whatever CWD the user is in; a user who runs Codex from many project dirs has results scattered. **Gain:** matches the CLI's native default (surprising users less), keeps results inside project repos by default, easily overridden via env var. The env var is resolved by the skill (CLI doesn't honor it natively) and passed as `--root-dir` explicitly.

### 7. Managed `download-results`, never agent-side polling

**Chose:** after `start` returns synchronously, agent kicks off `download-results` through the host runtime's managed long-running command support. In Claude Code that is Bash with `run_in_background: true`. In Codex that is a foreground shell command with `yield_time_ms=1000`; if the command is still running, Codex returns a session id that can be polled later. Progress reporting happens by peeking at the default JSONL stderr or by reading `download-status` — no new API calls.

**Trade:** depends on the agent host having managed long-running shell sessions. If a session dies, the downloader may die with it, but the server-side job continues and the `boltz-check-status` skill handles recovery. **Gain:** no agent-loop polling (cheap, and avoids burning tokens on "still running" responses). One long-running tool call per job, not N. The CLI now emits JSONL progress on stderr by default and exposes `download-status` for local checkpoint reads, so progress can be inspected without a fresh API round-trip.

**Codex warning:** do not use shell `&`, terminal backgrounding, or `nohup` as the detach mechanism. Codex may clean up shell-backgrounded descendants when the initiating tool command exits, before `.boltz-run.json` is fully written. Keep `download-results` in the managed foreground session and let Codex return control after a 1000 ms yield.

### 8. No preflight for install or auth

**Chose:** skills assume `boltz-api` is on PATH and `BOLTZ_COMPUTE_API_KEY` is set. No "command -v boltz-api" check, no "auth status" call before every run.

**Trade:** if the CLI is missing or the key is invalid, the first real command fails. **Gain:** zero ceremony per invocation; errors from the CLI are readable enough for the agent to relay. Matches the user's stated preference ("just assume they're set").

### 9. New `codex-plugin-cli/` directory, not an in-place rewrite

**Chose:** sibling of `codex-plugin-python/`; Python version untouched.

**Trade:** another flavor in a repo that already has six (`skills-python`, `skills-rest`, `skills-rest-hybrid`, `skills-mcp`, `boltz-mcp`, `boltz-compute-mcp`). **Gain:** the Python plugin stays as a reference for anyone wanting the SDK path, and there's zero migration risk for existing installs. If the CLI plugin ships well, deprecating the Python one is a separate commit.

## What survives from the Python plugin

- Every `SKILL.md` frontmatter (`name`, `description`) — verbatim. Trigger matching is already tuned; don't break it.
- Every `references/api.md` payload schema — retouched to drop SDK method signatures and use API body field names (`entities`, `target`, `binder_specification`, `molecule_filters`). The structural content (entity shapes, discriminated unions, motif types, DSL syntax, output metrics tables) is the same.
- `agents/openai.yaml` files — copied unchanged. Four lines of Codex display metadata each.
- The broad workflow ("estimate → confirm → submit → download → rank") — same shape, different verbs (no more `--estimate-only`; it's a separate `estimate-cost` subcommand).

## What's new

- The `boltz-check-status` skill is substantially expanded. In the Python plugin it listed + retrieved across resources. In the CLI plugin it's also the **crash-recovery skill**, with three explicit modes (list / retrieve+capture-slug / download-results-with-resume). This matches the real failure mode we care about: "my Codex session died an hour into a design run — can I get my results?"
- A `DESIGN.md` and `GOTCHAS.md` (this file and its sibling) at the plugin root for institutional memory.

## Numbers

```
Python plugin:   2,149 LOC scripts  +  ~1,080 LOC markdown  =  ~3,230 LOC
CLI plugin:          0 LOC scripts  +  ~1,744 LOC markdown  =  ~1,744 LOC
```

Roughly half the total surface area, none of the Python runtime dependency, and the CLI maintains itself.
