---
name: boltz-cli-setup
description: Boltz CLI setup, auth, and runtime notes. Use when installing, updating, verifying, or authenticating `boltz-api`, fixing missing CLI, PATH, sandbox, browser login, or auth errors, or when unsure how the current agent runtime runs a long-running `boltz-api` command such as `download-results`.
---

# Boltz CLI Setup

Use this skill for `boltz-api` installation, version, PATH, and authentication issues, and for runtime-specific notes on running long-running `boltz-api` commands. The workflow skills assume `boltz-api` is already installed.

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

The installer updates an existing `boltz-api` on `PATH`. If no binary is found, it installs to a user-local bin directory. Add the installed binary to `PATH` if `boltz-api --version` is still not found after install.

Working around the sandbox is critical because the sandbox can block browser login, OAuth callbacks, temp files, credential storage, and user-wide install paths. If the user asks for a normal install, install or authenticate `boltz-api` in the user's real environment. In a filesystem sandbox, request the host sandbox bypass/escalation needed for the install or auth flow.

Read [references/sandbox.md](references/sandbox.md) when an agent sandbox blocks the installer, browser auto-open, OAuth callback, credential storage, temp files, or global install path.

## Authenticate

Use the same executable, environment, and tenant options as the failing command when checking authentication.

```sh
boltz-api auth status
```

### Unattended jobs and result collection

Inject a workspace API key from the runner's secret store as `BOLTZ_API_KEY` in the process that launches `boltz-api`. A nonempty key takes precedence over a saved OAuth session. Some older instructions use `BOLTZ_COMPUTE_API_KEY`. Check `boltz-api --help` for the variable supported by the installed release.

Before leaving a downloader unattended:

1. Run `boltz-api auth status` in the downloader's environment and check that `effective_mode` is `api_key`. This checks local credential selection. If OAuth is selected, check the variable name and whether the runner passes it to the CLI process.
2. Run `boltz-api auth me` with the same tenant options. Confirm the server reports `principal_type: api_key` and the intended organization. For a dedicated tenant, pass its API endpoint with `--base-url`. If the server rejects the key, check the endpoint, key status, and workspace scope.
For interrupted result collection, use a key scoped to the workspace that owns
the job. Follow `boltz-check-status` to resume with the original job ID and run
directory.

### Interactive OAuth

When the workflow uses OAuth and the CLI needs a session or reports that reauthentication is required, start device-code login on the user's behalf:

```sh
boltz-api auth login --device-code
```

Keep the workflow's tenant options. Share the verification URL and code if the browser flow needs user input, then wait for login to finish before retrying. Follow [references/sandbox.md](references/sandbox.md) if the runtime blocks browser launch, callbacks, or credential storage.

## Version Checks

Do not hard-code expected commands or minimum versions in this skill. Treat the CLI's own update check as the source of truth.

When `boltz-api` reports that an update is available or required, relay that message and the install command it provides. The CLI may get this from a Boltz-hosted version metadata endpoint such as `/cli/version`, returning latest version, minimum supported version, whether an update is required, and platform-appropriate install instructions.

If a user asks why the CLI thinks it is stale, explain the split:

- GitHub Releases define which CLI binaries are available to install.
- The Boltz version endpoint defines API compatibility, including the minimum supported CLI version.

Respect user or CI opt-outs such as `BOLTZ_API_NO_UPDATE_CHECK=1`; do not force update checks when the environment disables them.

## Long-Running Commands

The workflow skills launch `boltz-api download-results` through the runtime's long-running or non-blocking command facility and describe follow-up checks by capability, not by host. Read [references/runtimes.md](references/runtimes.md) when you are unsure how the current runtime provides a non-blocking command, a session handle, or scheduled follow-up checks, or when a workflow skill routes here for that reason.
