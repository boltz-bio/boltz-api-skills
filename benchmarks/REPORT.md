# Benchmark Report: claude-code-cli vs. claude-code-mcp

**Status**: Not yet run. Populate after the benchmark matrix completes.

## Setup

- **Date range**: TBD
- **Claude Code version**: TBD
- **Host OS**: TBD
- **Plugin versions**: cli v0.1.0, mcp v0.1.0
- **Boltz CLI version**: TBD
- **MCP server commit**: TBD

## Aggregate results

| Metric | claude-code-cli | claude-code-mcp | Δ |
|---|---|---|---|
| Avg approvals per scenario | TBD | TBD | TBD |
| Avg wall-clock (s) | TBD | TBD | TBD |
| Avg input tokens | TBD | TBD | TBD |
| Avg output tokens | TBD | TBD | TBD |
| Success rate | TBD | TBD | TBD |
| Recovery success (scenario 7) | TBD | TBD | TBD |

## Scenario-by-scenario

### Scenario 1 — Fold a protein+ligand complex

- CLI: _observation_
- MCP: _observation_
- Divergences: _notes_

(repeat for scenarios 2–7)

## Recovery behavior (scenario 7)

_This is expected to be the most important section. Note which variant preserves run state across session death more gracefully._

## Recommendation

_Ship `claude-code-<winner>`. Retire `claude-code-<loser>`. OR: ship both with clear positioning (e.g., "cli for power users who want shell flexibility, mcp for default UX")._

## Surprises / follow-ups

_Things we didn't expect. Bugs found. Features we should ask for._
