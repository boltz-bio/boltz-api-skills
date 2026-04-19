# Boltz Compute Skills

This repo contains two parallel agent integrations for Boltz Compute:

| Folder | Description |
|--------|-------------|
| `skills-python/` | Claude Code skills |
| `codex-plugin-python/` | Codex plugin with manifest, marketplace support, and Codex-specific metadata |

## Codex plugin

The Codex plugin lives in `codex-plugin-python/`.

- The repo now includes a workspace-local marketplace file at `.agents/plugins/marketplace.json`.
- If you open this repo in Codex and start a fresh session, the plugin can be discovered from this workspace without any extra scaffolding.
- Detailed install, setup, validation, and smoke-test instructions live in `codex-plugin-python/README.md`.

## Claude Code skills

The Claude Code variant in `skills-python/` keeps the same core workflows but omits Codex-specific packaging.

## Shared behavior

Both implementations follow the same operating model:

1. Normalize the biological or chemistry input into the API payload shape expected by Boltz Compute.
2. Estimate cost first and require explicit approval before spend.
3. Submit the job through the Python SDK wrapper.
4. Poll until completion and download local artifacts when the job succeeds.

This keeps agents out of the business of hand-rolling raw API calls, async polling loops, and result-download plumbing.
