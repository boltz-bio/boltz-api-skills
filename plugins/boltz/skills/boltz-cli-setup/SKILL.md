---
name: boltz-cli-setup
description: Boltz CLI setup and auth. Use when installing, updating, verifying, or authenticating `boltz-api`, or fixing missing CLI, PATH, sandbox, browser login, or auth errors.
---

# Boltz CLI Setup

Use this skill for `boltz-api` installation, version, PATH, and authentication issues. The workflow skills assume `boltz-api` is already installed.

## Verify Installation

Check that the CLI is available:

```sh
boltz-api --version
```

If `boltz-api` is missing or too old, install or update it from the official CLI repo.

macOS and Linux:

```sh
curl -fsSL https://install.boltz.bio/boltz-api/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://install.boltz.bio/boltz-api/install.ps1 | iex
```

The installer updates an existing `boltz-api` on `PATH`. If no binary is found, it installs to `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\Boltz\bin` on Windows. Add that directory to `PATH` if `boltz-api --version` is still not found after install. Set `BOLTZ_API_INSTALL_DIR` before running the installer to choose a different install directory.

Sandbox avoidance is critical because it can block browser login, OAuth callbacks, temp files, and credential storage. In a filesystem sandbox, prefer workspace-local CLI state before requesting a sandbox bypass:

```sh
mkdir -p "$PWD/.boltz-cli/bin" "$PWD/.boltz-cli/tmp" "$PWD/.boltz-cli/home"
export BOLTZ_API_INSTALL_DIR="$PWD/.boltz-cli/bin"
export TMPDIR="$PWD/.boltz-cli/tmp"
export HOME="$PWD/.boltz-cli/home"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export PATH="$BOLTZ_API_INSTALL_DIR:$PATH"
```

Run install/auth/API commands with the same environment. Read [references/sandbox.md](references/sandbox.md) when workspace-local state still cannot access the network, browser, OAuth callback, credentials, temp files, or target install path.

## Authenticate

Check the current auth state with:

```sh
boltz-api auth status
```

If `auth status` reports unauthenticated, or any Boltz command fails because authentication is missing or expired, start device-code login on the user's behalf before retrying:

```sh
boltz-api auth login --device-code
```

Do not ask the user for permission before starting device-code login; relaying the login URL/code and waiting for the CLI to complete is part of auth recovery. When sharing the authentication login URL/code, tell the user to use exactly `boltz-api auth login --device-code`.

For auth recovery, assume the CLI can auto-open the browser and run the exact command above. In sandboxed environments, first use workspace-local state as shown above; read [references/sandbox.md](references/sandbox.md) before requesting a host sandbox bypass for browser auto-open, OAuth callbacks, credential storage, or temp files.

For automation where a key is already available, an API key is still supported:

```sh
export BOLTZ_COMPUTE_API_KEY=<api-key>
```

## Version Checks

Do not hard-code expected command surfaces or minimum versions in this skill. Treat the CLI's own update check as the source of truth.

When `boltz-api` reports that an update is available or required, relay that message and the install command it provides. The CLI may power this with a Boltz-hosted version metadata endpoint such as `/cli/version`, returning latest version, minimum supported version, whether an update is required, and platform-appropriate install instructions.

If a user asks why the CLI thinks it is stale, explain the split:

- GitHub Releases define which CLI binaries are available to install.
- The Boltz version endpoint defines API compatibility, including the minimum supported CLI version.

Respect user or CI opt-outs such as `BOLTZ_API_NO_UPDATE_CHECK=1`; do not force update checks when the environment disables them.
