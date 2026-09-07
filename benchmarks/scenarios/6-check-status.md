# Scenario 6 — Check job status and pull results

**Skill**: `boltz-check-status`
**Difficulty**: Easy
**Expected wall-clock**: under 2 minutes

## Setup

Run scenario 1 first (or any scenario that submits a job) and let it finish
server-side. Keep the job ID handy. Then run this scenario in a **fresh
agent session** (to exercise the cross-session recovery path).

## User prompt

```
Can you check what Boltz jobs I have recently and tell me the status? If the
most recent one is done, please download the results.
```

## Expected behavior

1. Agent calls list across all six resources, merges, sorts by created_at.
2. Presents a table of recent jobs with status, resource, timestamps.
3. Identifies the most recent terminal-status job.
4. If done, launches `download-results` (or the MCP server's download tool on
   Claude Desktop) through the runtime's long-running facility and ends the
   turn. ADME jobs have no download step; their results come from `retrieve`.

## Success criteria

- Agent correctly enumerates all six resource types, including
  `predictions:adme`.
- Identifies the right "most recent" job, not a stale one.
- Successfully kicks off a resume-style download (not a fresh submit).

## What to watch for

- Does the agent try to `start` again on a finished job? (It should not.)
- Does it handle a mix of pending and terminal jobs correctly?
