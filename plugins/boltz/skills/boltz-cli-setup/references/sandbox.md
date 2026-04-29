# Sandbox and Browser Login

Read this when a sandbox blocks `boltz-api` installation, temp files, OAuth browser login, credential storage, or later API calls.

## Workspace-Local State

Prefer workspace-local temp, install, config, and cache paths before requesting a sandbox bypass:

```sh
mkdir -p "$PWD/.boltz-cli/bin" "$PWD/.boltz-cli/tmp" "$PWD/.boltz-cli/home"
export BOLTZ_API_INSTALL_DIR="$PWD/.boltz-cli/bin"
export TMPDIR="$PWD/.boltz-cli/tmp"
export HOME="$PWD/.boltz-cli/home"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export PATH="$BOLTZ_API_INSTALL_DIR:$PATH"
```

Run install, auth, and API commands with the same environment so config, session cache, and file-backed token storage all stay inside the workspace.

## When to Request Sandbox Bypass

Only request the host sandbox bypass if workspace-local state still cannot access the network, keychain fallback, temp files, target install path, browser auto-open, OAuth callbacks, or credential storage.

For device-code auth, assume the CLI can auto-open the browser and run:

```sh
boltz-api auth login --device-code
```

Keep the same config/cache/credential environment active for later `boltz-api` calls, because every API command resolves auth from those locations.
