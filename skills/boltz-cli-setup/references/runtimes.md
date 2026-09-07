# Long-Running Commands By Runtime

Read this when a workflow skill tells you to run `boltz-api download-results`
through the runtime's long-running or non-blocking command facility and you are
not sure how this runtime provides one.

The workflow skills describe what to do by capability. This file maps those
capabilities onto specific agent runtimes. If your runtime is not listed, use
the fallback at the end.

## Capabilities the skills rely on

| Capability | What the skills ask for |
|---|---|
| Non-blocking command | Start `download-results` so the turn can end while it keeps polling and downloading. |
| Follow-up scheduling | Optional. A heartbeat, scheduled task, or reminder that runs `download-status` later and reports terminal state. |
| Session handle | Optional. A way to inspect a still-running command when the user asks for progress. |
| Permission gating | Some runtimes prompt per shell command. Keep each Boltz call a top-level `boltz-api ...` command so one allow rule covers the workflow. |

Hazards that apply everywhere:

- Do not invent tool arguments. Use only the background or session options the runtime's shell tool documents.
- Do not detach with shell `&`, `nohup`, `setsid`, or `disown` unless the runtime documents shell backgrounding as its supported mode. Some tool runners reap shell-backgrounded children when the tool call returns, before `.boltz-run.json` is written.
- Never claim an automatic next check the runtime cannot make. When no follow-up mechanism exists, report the job ID, run name, output directory, and the `download-status` command instead.
- `download-status` reads the local checkpoint without an API call. Prefer it over polling `retrieve`, and re-run `download-results` with the same `--name` and `--root-dir` to resume.

## Runtime notes

### Claude Code

- Non-blocking command: run the `boltz-api download-results ...` command with the Bash tool's `run_in_background: true`. Claude Code notifies the session when the background command exits.
- Follow-up scheduling: not assumed. Report the `download-status` command. If the installed version offers scheduled or recurring tasks, they may be used, but do not rely on them.
- Permission gating: yes. Keep calls top-level so a rule such as `boltz-api *` applies. Prefer concrete arguments over `sh -c`, inline environment assignments, aliases, loops, or pipelines around `boltz-api`.

### Codex

- Non-blocking command: run `download-results` as a foreground shell command with the shell tool's yield set to 1000 ms (`yield_time_ms: 1000`). If the command is still running, Codex returns a `session_id`. Keep it as an optional interactive handle; the run directory plus `download-status` remain the durable source of truth.
- Do not append `&` or use `nohup`. Codex may clean up shell-backgrounded descendants when the tool call exits, before `.boltz-run.json` is fully written.
- Session handle: poll the saved `session_id` with an empty `write_stdin` only for interactive, user-requested progress checks.
- Follow-up scheduling: Codex app and desktop runtimes that expose same-thread heartbeat automations can schedule a `download-status` heartbeat. Bare Codex CLI may not; check before claiming one.

### Gemini CLI

- Non-blocking command: Gemini CLI documents shell backgrounding. Call `run_shell_command` with `&` appended to the command. Do not pass an `is_background` argument; the tool does not accept one.
- Follow-up scheduling: none. Report the `download-status` command.

### Claude Desktop (Boltz MCP bundle)

- The Boltz MCP server launches and tracks downloads itself. Use its `boltz_job_status` and `boltz_download_results` tools instead of a shell. The skill text is bundled as guidance only.

### Other runtimes

Runtimes installed through Vercel Skills or a partner harness vary. In order of preference:

1. Use the runtime's documented background or detached-command mode.
2. If the runtime only has a foreground shell with a session handle, start `download-results` in the foreground and let the runtime return the handle.
3. If neither exists, run `download-results` in the foreground for small jobs, or give the user the exact `download-results` command to run in their own terminal and the `download-status` command to check later.
