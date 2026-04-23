# Benchmarks: claude-code-cli vs. claude-code-mcp

Head-to-head comparison of the two Claude Code variants before picking one for
directory submission. Both surfaces expose the same six skills with identical
trigger descriptions; they differ only in execution layer.

## What we're measuring

| Metric | How | Why |
|---|---|---|
| **Approvals per run** | Count permission prompts (Bash, MCP tool, file write) observed during the run. | The CLI variant invokes Bash N times per workflow; the MCP variant invokes 1 MCP tool. Approval friction is the main UX hypothesis we're testing. |
| **Wall-clock time** | Record agent submit/detach time, server runtime, download runtime, and time to verified artifacts separately. Keep the legacy overall `wall_clock_seconds` field for coarse comparison. | Separates UX latency from Boltz runtime and local artifact download behavior. |
| **Tokens (input / output)** | From the Claude Code session usage report. | CLI variant forces the model to author long bash pipelines; MCP variant uses typed tool params. Expect MCP variant to use fewer output tokens. |
| **Success** | Did the job actually run on Boltz and land results on disk? | If either variant fails more often, that's the dominant signal. |
| **Error recovery** | Scenario 7 only — did the variant successfully resume a crashed run? | The crash-recovery path is where the MCP variant's in-process state management should shine. |

## Scenarios

Each `scenarios/<id>-*.md` is a single test case. See that directory for the
full list; scenarios are numbered and cover all six skills plus a recovery
case.

## Running a benchmark session

The v1 harness is **manual**. Automated harnessing via the Claude Agent SDK is
a v2 task.

### Per-scenario, per-variant procedure

1. Install both plugins in Claude Code:
   ```bash
   # Terminal A (CLI variant)
   claude --plugin-dir ./surfaces/claude-code-cli

   # Terminal B (MCP variant)
   claude --plugin-dir ./surfaces/claude-code-mcp
   ```

2. Prepare the scenario inputs (sequences, SMILES, etc.) — see `scenarios/inputs/`.

3. Copy the scenario's **user prompt** from `scenarios/<id>-*.md` into the
   chosen Claude Code session. Start a timer.

4. Observe and record:
   - Every permission prompt that appears (type + tool or command).
   - Any errors the agent encounters and how it recovers.
   - Whether the job submits successfully and results land on disk.
   - Timing breakouts when available:
     - Agent submit/detach time: prompt submit → job ID + downloader launched.
     - Server runtime: remote `started_at` → `completed_at`.
     - Download runtime: downloader start → local ready/checkpoint complete.
     - Time to verified artifacts: prompt submit → expected files present.

5. When the agent ends the turn, record final tokens from the session footer.

6. Save the session transcript and the results/ artifact directory under:
   ```
   benchmarks/results/<variant>/<scenario-id>/<YYYYMMDD-HHmm>/
   ```

7. Fill in `metrics.json` using the template in `benchmarks/metrics-template.json`.

### Running the full matrix

Plan: 2 variants × 7 scenarios × 3 runs = 42 runs. Allocate 1–2 days. Run the
same scenario on both variants back-to-back for cleaner comparison.

## Reporting

After all runs land, populate `REPORT.md` (template in repo) with:

- Aggregate approvals / tokens / wall-clock per variant.
- Scenario-by-scenario observations, especially divergences.
- Recovery behavior (scenario 7) — expected to be the biggest differentiator.
- Recommendation: ship `claude-code-cli` or `claude-code-mcp`.

## When to stop benchmarking

Stop when either:

- One variant clearly dominates across all metrics (n=3 per scenario should
  reveal this).
- Tradeoffs are real and the choice depends on product direction (e.g., MCP
  wins on approval UX but loses on flexibility for power users) — in that
  case, escalate the decision.
