# Scenario 7 — Crash recovery

**Skill**: `boltz-check-status` (recovery mode)
**Difficulty**: Hard
**Expected wall-clock**: 5–10 minutes

## Why this matters

This is the scenario most likely to separate runtimes. Each runtime provides a
different long-running-command facility, and some reap shell-backgrounded
children when a tool call returns. The skills describe the launch by capability
and route to `skills/boltz-cli-setup/references/runtimes.md` for host notes. If
that routing fails, `.boltz-run.json` may never be written, and recovery falls
back to a fresh download.

## Setup

1. Run scenario 2 (library screen; medium-length, ~15 min) to submit a real job.
2. Before killing anything, record the mechanism the agent used to launch
   `download-results` and whether `.boltz-run.json` exists in the run
   directory.
3. After the job is submitted and the agent returns, **kill the agent session**
   (Ctrl+C, close the terminal or app, force-quit). Note the run name / slug and
   job ID first.
4. Start a fresh session on the same runtime with the same install method.

## User prompt (in the fresh session)

```
My last agent session died. I had a Boltz job running — here's the ID: <ID>
(and the slug was <SLUG>). Please pick up the download and give me the results
when they're ready.
```

## Expected behavior

1. Agent recognizes this as a recovery request.
2. Runs `retrieve` (or the MCP server's job lookup on Claude Desktop) to inspect
   the job by ID.
3. Captures `idempotency_key` from the response, or uses the supplied slug.
4. Re-launches `download-results` with the original slug as `--name` and the
   same `--root-dir`, through the runtime's long-running facility.
5. Reports the job ID, run name, and output directory, and ends the turn.

## Success criteria

- The previous session's artifacts are reused: the `.boltz-run.json` cursor
  advances rather than restarting from scratch.
- Final results end up in the same directory the original run targeted.
- Agent does NOT call `start` again to "resume."
- The relaunch used the runtime's documented mechanism, not an invented tool
  argument or a shell `&` on a runtime that reaps children.

## What to watch for

- Did `.boltz-run.json` survive the original session's death? If not, record
  the launch mechanism the first session used; that is a runtime-notes bug.
- Does the agent preserve the existing output directory or create a new one?
- If the job is already terminal, does the agent skip polling and pull the
  final artifacts?
- Did the agent consult `boltz-cli-setup` when unsure how to relaunch, or guess?
