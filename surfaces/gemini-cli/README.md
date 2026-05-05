# boltz-gemini-cli

Gemini CLI extension for Boltz biomolecular modeling workflows. It bundles the
same CLI-backed Boltz skills used by the Claude Code and Codex surfaces, with
Gemini-specific context for background shell downloads.

## Installation

Install the extension from the public distribution repo:

```sh
gemini extensions install https://github.com/boltz-bio/boltz-gemini-cli
```

Restart Gemini CLI, then confirm the extension and skills are visible:

```text
/extensions list
/skills list
```

## Boltz API CLI

This extension uses the `boltz-api` command. Install it from the
[boltz-api-cli repo](https://github.com/boltz-bio/boltz-api-cli), then make sure
it is available on `PATH`.

- `boltz-api` on `PATH`
- Authentication via `boltz-api auth login --device-code`, or `BOLTZ_API_KEY`
  exported in the environment
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR` to override where results land
