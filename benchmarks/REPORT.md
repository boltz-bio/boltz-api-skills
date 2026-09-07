# Benchmark Report: skill behavior across agent runtimes

**Status**: Not yet run against the capability-based skill prose. Populate
after the matrix in `README.md` completes.

## Setup

| Field | Value |
|---|---|
| Date range | TBD |
| Skills revision (`git rev-parse HEAD`) | TBD |
| `boltz-api` version | TBD |
| Claude Code version / install method | TBD |
| Codex version / install method | TBD |
| Gemini CLI version / install method | TBD |
| Claude Desktop / MCPB version | TBD |
| Other runtimes tested | TBD |
| Host OS | TBD |

## Aggregate results

| Metric | Claude Code | Codex | Gemini CLI | Claude Desktop | Other | Baseline (no skill) |
|---|---|---|---|---|---|---|
| Success rate | TBD | TBD | TBD | TBD | TBD | TBD |
| Cost gate respected | TBD | TBD | TBD | TBD | TBD | TBD |
| Launch mode matched runtime notes | TBD | TBD | TBD | n/a | TBD | n/a |
| Invented tool arguments | TBD | TBD | TBD | n/a | TBD | TBD |
| Checkpoint survived turn end | TBD | TBD | TBD | TBD | TBD | TBD |
| Follow-up claims honest | TBD | TBD | TBD | TBD | TBD | TBD |
| Avg approvals per scenario | TBD | TBD | TBD | TBD | TBD | TBD |
| Avg time to verified artifacts (s) | TBD | TBD | TBD | TBD | TBD | TBD |
| Avg input / output tokens | TBD | TBD | TBD | TBD | TBD | TBD |
| Recovery success (scenario 7) | TBD | TBD | TBD | TBD | TBD | TBD |

## Scenario-by-scenario

### Scenario 1 — Fold a protein+ligand complex

- Claude Code: _observation_
- Codex: _observation_
- Gemini CLI: _observation_
- Claude Desktop: _observation_
- Divergences: _notes_

(repeat for scenarios 2 through 9)

## Launch mode and follow-up findings

_For each runtime, record the mechanism the agent chose for `download-results`,
whether it matched `skills/boltz-cli-setup/references/runtimes.md`, and whether
the agent consulted `boltz-cli-setup` when unsure. Note any invented tool
arguments, shell `&` on a reaping runtime, or claimed follow-ups that do not
exist._

## Recovery behavior (scenario 7)

_Which runtimes preserved `.boltz-run.json` across session death, and whether
the resume reused the original run directory._

## Regression verdict

_Compare against the previous report. State per runtime whether success, cost
gate, launch mode, checkpoint survival, and follow-up honesty held._

## Surprises / follow-ups

_Things we did not expect. Bugs found. Runtime behaviors that should be added to
`runtimes.md`. Features to ask the runtime vendors or the CLI for._
