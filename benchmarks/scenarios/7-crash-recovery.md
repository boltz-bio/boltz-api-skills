# Scenario 7 — Crash recovery

**Skill**: `boltz-check-status` (recovery mode)
**Difficulty**: Hard
**Expected wall-clock**: 5–10 minutes

## Why this matters

This is the scenario most likely to distinguish the two variants. The CLI
variant relies on the agent's background shell persistence, which dies with the
session. The MCP variant has a dedicated server that detaches `download-results`
as its own process and persists `.boltz-run.json`.

## Setup

1. Run scenario 2 (library screen; medium-length, ~15 min) to submit a real job.
2. After the job is submitted and the agent returns, **kill the Claude Code
   session** (Ctrl+C, close terminal, force-quit — whatever simulates a crash).
   Note the run_name / slug and job ID first.
3. Start a fresh Claude Code session with the same plugin variant.

## User prompt (in the fresh session)

```
My last Claude Code session died. I had a Boltz job running — here's the ID: <ID>
(and the slug was <SLUG>). Please pick up the download and give me the results
when they're ready.
```

## Expected behavior

1. Agent recognizes this as a recovery request.
2. Calls retrieve / `boltz_get_job` to inspect the job by ID.
3. Captures `idempotency_key` from the response (or uses the supplied slug).
4. Initiates `download-results` / `boltz_resume_download` with the original
   slug as `--name` / `run_name`.
5. Reports success and ends the turn.

## Success criteria

- The previous session's artifacts are reused (check `.boltz-run.json` cursor
  advances, not restarts from scratch).
- Final results end up in the same directory the original run targeted.
- Agent does NOT call `start` again to "resume."

## What to watch for

- Does the agent preserve the existing output directory or create a new one?
- If the job is already terminal, does the agent skip polling and just pull the
  final artifacts?
- Which variant handles the detached-process recovery more smoothly — the CLI
  shelling to `nohup` or the MCP server's detached spawn?
