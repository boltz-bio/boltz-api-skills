# Benchmarks: skill behavior across agent runtimes

The canonical skills in `skills/` are written by runtime capability, not by
host name. This harness checks that they still perform on every supported
agent runtime, and it catches regressions when skill prose changes. Run it
before merging a change to the long-running-command guidance, the cost gate,
or a skill's workflow steps.

## Runtime matrix

| Runtime | Install method under test | Expected long-running mode |
|---|---|---|
| Claude Code | Marketplace plugin `boltz@boltz-marketplace`, or `npx skills add boltz-bio/boltz-api-skills --agent claude-code` | Bash tool with `run_in_background: true` |
| Codex | Official marketplace plugin **Boltz**, or `npx skills add boltz-bio/boltz-api-skills --agent codex` | Foreground shell command with a 1000 ms yield; `session_id` returned |
| Gemini CLI | Extension from `boltz-bio/boltz-gemini-cli`, or `npx skills add boltz-bio/boltz-api-skills --agent gemini-cli` | `run_shell_command` with `&` appended |
| Claude Desktop | `boltz-mcpb-<version>.mcpb` from the GitHub Release | The MCP server owns the download; no shell |
| Other Skills-supported agents | `npx skills add boltz-bio/boltz-api-skills --agent <name>` | Whatever the runtime documents; the fallback path in `skills/boltz-cli-setup/references/runtimes.md` |

Test each runtime with the install method users are steered to first: the
marketplace plugin for Claude Code and Codex, and Skills or the extension for
Gemini CLI. Test the second install method when the change touches packaging.

Run the matrix on the latest stable release of every component. Most users
run latest, and a runtime's shell tool can change between releases. Update
each runtime before a session and check what is current:

```sh
npm view @anthropic-ai/claude-code version
npm view @openai/codex version
npm view @google/gemini-cli version
npm view skills version
gh release view --repo boltz-bio/boltz-api-cli --json tagName -q .tagName
```

Latest stable when this harness was last refreshed (2026-09-07), for
reference only:

| Component | Version |
|---|---|
| Claude Code | 2.1.263 |
| Codex CLI | 0.153.4 |
| Gemini CLI | 0.58.0 |
| Vercel Skills CLI | 1.5.24 |
| `boltz-api` | 0.42.0 |

Record the versions you actually ran in each `metrics.json`; do not rely on
this table. Preview, nightly, or alpha channels are out of scope unless a
scenario says otherwise.

## What we're measuring

| Metric | How | Why |
|---|---|---|
| **Success** | Did the job run on Boltz and land results on disk? | The dominant signal. |
| **Cost gate** | Did the agent run `estimate-cost`, quote the returned figure, and wait for an explicit yes before `start`? | Paid workflows must never submit on an assumed approval. |
| **Launch mode** | Which mechanism launched `download-results`? Did it match the runtime notes in `skills/boltz-cli-setup/references/runtimes.md`? Did the agent invent a tool argument, or use shell `&` on a runtime that reaps children? | This is where capability-based prose can regress against host-specific prose. |
| **Checkpoint survival** | After the turn ends, is `<root>/<run-name>/.boltz-run.json` present, and does its cursor advance on the next `download-status`? | Proves the download outlived the tool call. |
| **Follow-up honesty** | Did the agent claim a scheduled check only when the runtime has one? Did it report the `download-status` command otherwise? | Users act on these claims. |
| **Approvals per run** | Count permission prompts (shell, tool, file write). | Approval friction is the main UX cost of the CLI-backed design. |
| **Wall-clock time** | Agent submit/detach time, server runtime, download runtime, time to verified artifacts. | Separates UX latency from Boltz runtime and download behavior. |
| **Tokens (input / output)** | From the runtime's session usage report when it exposes one. | Long prose costs tokens on every invocation. |
| **Error recovery** | Scenario 7 only. Did the agent resume the crashed run without a fresh `start`? | The crash-recovery path is the one users hit at the worst time. |

## Scenarios

Each `scenarios/<id>-*.md` is one test case with a user prompt, expected
behavior, and gradeable success criteria. Scenarios 1 through 5 and 9 cover
the six paid workflow skills, 6 and 7 cover status and recovery, and 8 covers
the protein-design exploration flow in dry-run mode.

Scenarios 1, 6, 7, and 9 are cheap. Run them on every runtime. Run 2 through 5
and 8 on Claude Code and Codex at minimum, and on any runtime whose launch mode
changed.

## Running a benchmark session

The harness is manual. Automated harnessing through the agent SDKs is a
follow-up.

### Per-scenario, per-runtime procedure

0. Update the runtime and `boltz-api` to the latest stable release, and record
   both versions. A stale local install is the most common way to benchmark
   the wrong thing.
1. Install the skills on the runtime with the install method under test. For a
   development build of the canonical tree, use a local install:
   ```sh
   npx skills add . --skill '*' --agent <agent> --yes
   ```
   For Claude Code plugin development, `claude --plugin-dir ./surfaces/claude-code-cli`
   also works.
2. Prepare the scenario inputs. See `scenarios/inputs/README.md`.
3. Start a fresh session in the runtime. Copy the scenario's **user prompt**
   into it and start a timer.
4. Observe and record:
   - Every permission prompt (type, and the tool or command).
   - The exact mechanism used to launch `download-results`, and whether it
     matches the runtime notes.
   - Any tool argument the agent invented, and any shell `&` or `nohup`.
   - Whether the agent claimed a scheduled follow-up, and whether one exists.
   - Errors and how the agent recovered.
   - Whether the job submitted and results landed on disk.
   - Timing breakouts when available:
     - Agent submit/detach time: prompt submit to job ID plus downloader launched.
     - Server runtime: remote `started_at` to `completed_at`.
     - Download runtime: downloader start to local ready or checkpoint complete.
     - Time to verified artifacts: prompt submit to expected files present.
5. After the turn ends, run `boltz-api --format json download-status --name <run-name> --root-dir <root>`
   twice a minute apart and record whether the cursor advanced.
6. When the agent ends the turn, record tokens from the session usage report
   if the runtime exposes one.
7. Save the session transcript and the results directory under:
   ```
   benchmarks/results/<runtime>/<install-method>/<scenario-id>/<YYYYMMDD-HHmm>/
   ```
8. Fill in `metrics.json` from `benchmarks/metrics-template.json`.

### Baseline

Run each scenario once with no Boltz skills installed. The gap between the
baseline and the skill run is the skill's value, and it is the number to
protect when trimming prose.

### Running the full matrix

Plan: 5 runtimes × 9 scenarios × 2 runs for the cheap scenarios, and 2 runtimes
× 5 scenarios × 2 runs for the expensive ones. Run the same scenario on each
runtime back-to-back for a cleaner comparison.

## Reporting

After the runs land, populate `REPORT.md` with aggregate metrics per runtime,
scenario-by-scenario observations, launch-mode and follow-up findings, and the
recovery behavior from scenario 7.

## Regression rule

A change to skill prose ships when no runtime regresses on success, cost gate,
launch mode, checkpoint survival, or follow-up honesty against the previous
report. Approval counts and tokens may move; note them.
