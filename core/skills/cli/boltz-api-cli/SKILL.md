---
name: boltz-api-cli
description: Boltz Compute CLI setup and authentication guidance. Use when the user asks how to install, update, verify, or authenticate the boltz-api CLI, or when a workflow reports that boltz-api is missing from PATH.
---

# Boltz API CLI

Use this skill for `boltz-api` installation, version, PATH, and authentication issues. The workflow skills assume `boltz-api` is already installed.

## Verify Installation

Check that the CLI is available:

```sh
boltz-api --version
```

If `boltz-api` is missing or too old, install or update it from the official CLI repo.

macOS and Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/boltz-bio/boltz-compute-api-cli/main/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/boltz-bio/boltz-compute-api-cli/main/scripts/install.ps1 | iex
```

The installer updates an existing `boltz-api` on `PATH`. If no binary is found, it installs to `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\Boltz\bin` on Windows. Add that directory to `PATH` if `boltz-api --version` is still not found after install. Set `BOLTZ_API_INSTALL_DIR` before running the installer to choose a different install directory.

## Authenticate

Use OAuth for local interactive work:

```sh
boltz-api auth login
```

For automation or headless environments, use an API key:

```sh
export BOLTZ_COMPUTE_API_KEY=<api-key>
```

Check the current auth state with:

```sh
boltz-api auth status
```
