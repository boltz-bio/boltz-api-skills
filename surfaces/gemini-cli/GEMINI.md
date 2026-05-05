# Boltz Gemini CLI Extension

Use this extension for Boltz biomolecular modeling workflows through the `boltz-api` CLI.

## Skill Routing

Use the bundled `boltz-*` skills for workflow details:

- `boltz-cli-setup`: install, update, verify, or authenticate `boltz-api`.
- `boltz-structure-and-binding`: predict one defined complex or dock one ligand.
- `boltz-small-molecule-screen`: rank an existing SMILES library against a target.
- `boltz-small-molecule-design`: generate novel small-molecule binders.
- `boltz-protein-screen`: rank an existing protein, peptide, antibody, or nanobody library.
- `boltz-protein-design`: design novel protein, peptide, antibody, or nanobody binders.
- `boltz-check-status`: list jobs, inspect progress, resume downloads, or recover results.

## Operating Rules

- Paid workflows must run `estimate-cost` first and wait for explicit user confirmation before `start`.
- Use `boltz-cli-setup` for missing CLI, old CLI, PATH, auth, browser-login, or sandbox failures.
- Prefer `boltz-api auth login --device-code` for interactive auth; `BOLTZ_API_KEY` is the API-key fallback.
- Keep payloads, embedded input files, and output roots on absolute paths.
- Use the same slug as `--idempotency-key` on `start` and `--name` on `download-results`.
- When a skill says to use the agent runtime's background or non-blocking mode, start `boltz-api download-results` through Gemini CLI's documented shell syntax: call `run_shell_command(command="... &", description="...", directory="...")` with `&` at the end of the command. Do not pass an `is_background` argument.
- After starting a background download, report the job ID, run name, and output directory. Do not poll again unless the user asks.
- For progress checks, prefer `boltz-api --format json download-status --name "<run-name>" --root-dir "<absolute-root>"` before remote API calls.
