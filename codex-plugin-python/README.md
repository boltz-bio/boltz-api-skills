# Boltz Compute Codex Plugin

This plugin exposes Boltz Compute workflows to Codex through Python SDK-backed skills.

## Included skills

- `boltz-setup`: validate local prerequisites before running paid jobs
- `boltz-structure-and-binding`: predict one complex and optional binding metrics
- `boltz-small-molecule-screen`: rank an existing SMILES library
- `boltz-small-molecule-design`: generate novel ligands for a target
- `boltz-protein-screen`: rank an existing protein binder library
- `boltz-protein-design`: generate novel binders
- `boltz-check-status`: inspect jobs and recover outputs

## Workspace-local install

This repo already ships `.agents/plugins/marketplace.json` pointing at `./codex-plugin-python`.

1. Clone the repo.
2. Open the repo in Codex.
3. Start a fresh Codex session.
4. Open `/plugins` and install `boltz-compute-python` from the workspace marketplace.

This is the recommended development setup because the plugin travels with the repo and versioned changes stay visible in git.

## Runtime prerequisites

The plugin wrappers assume a Python environment with the official SDK installed:

```bash
python -m pip install boltz-compute
```

Set the runtime environment before real jobs:

```bash
export BOLTZ_API_KEY=your_api_key
export BOLTZ_OUTPUT_DIR="$PWD/.boltz-output"
```

`BOLTZ_COMPUTE_API_KEY` also works if you prefer that variable name.

## Validation and smoke tests

Validate the package structure:

```bash
python scripts/validate_plugin.py
```

Validate local runtime setup:

```bash
python skills/boltz-setup/scripts/check_setup.py
```

Run dry-run smoke tests for every skill wrapper:

```bash
python scripts/smoke_test.py
```

The smoke tests do not require the SDK, API key, or output directory. They only verify that each CLI can construct a valid payload in `--dry-run` mode.

## Real workflow loop

For day-to-day iteration, use this loop:

1. Edit the skill or wrapper.
2. Run `python scripts/validate_plugin.py`.
3. Run `python scripts/smoke_test.py`.
4. Start a fresh Codex session in this repo and confirm the plugin still appears in `/plugins`.
5. Exercise one real endpoint with `--estimate-only` before submitting a paid job.

Example:

```bash
python skills/boltz-structure-and-binding/scripts/query.py \
  --protein MSEQNNTEMTFQIQRIYTKDISFEAPNAPHVFQKDW \
  --estimate-only
```
