---
name: boltz-setup
description: Verify the local Boltz Compute Codex plugin environment before running real jobs. TRIGGER when the user wants to install, configure, validate, or troubleshoot the plugin setup, SDK import, API key, or output directory.
---

## Workflow

Use this skill before the first real Boltz job in a new environment and any time the plugin appears misconfigured.

1. Run `python scripts/check_setup.py`.
2. Confirm the Boltz Python SDK imports successfully.
3. Confirm one of `BOLTZ_API_KEY` or `BOLTZ_COMPUTE_API_KEY` is set.
4. Confirm `BOLTZ_OUTPUT_DIR` exists or can be created and is writable.
5. If a check fails, give the user the exact missing prerequisite and the command needed to fix it.

## Always Do This

- Prefer the setup checker over manually inspecting environment variables one by one.
- Treat a missing API key or missing output directory as blocking for real jobs.
- Treat dry-run smoke tests as separate from setup validation. Dry-run only proves payload assembly.
- Explain clearly whether the environment is ready for:
  - dry-run validation only
  - real Boltz job submission

## Command Pattern

```bash
python scripts/check_setup.py
```

Optional JSON output:

```bash
python scripts/check_setup.py --json
```

## Output

Summarize which checks passed, which failed, and what the user must fix before submitting a paid Boltz job.
