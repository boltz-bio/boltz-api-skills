# boltz-gemini-cli

Gemini CLI extension for Boltz biomolecular modeling workflows. It bundles the
same CLI-backed Boltz skills used by the Claude Code and Codex surfaces, with
Gemini-specific context for background shell downloads.

## Prerequisites

- `boltz-api` on `PATH`
- Authentication via `boltz-api auth login --device-code`, or `BOLTZ_COMPUTE_API_KEY`
  exported in the environment
- Optional: `BOLTZ_COMPUTE_OUTPUT_DIR` to override where results land

## Local Development

From the repository root:

```sh
gemini extensions link ./surfaces/gemini-cli
```

Restart Gemini CLI, then confirm the extension and skills are visible:

```text
/extensions list
/skills list
```

## Installation Shape

For public distribution, mirror this surface into a dedicated public repo with
symlinks dereferenced. The public repo root should contain
`gemini-extension.json`, `GEMINI.md`, and `skills/`.

Users can then install from that repo:

```sh
gemini extensions install https://github.com/boltz-bio/boltz-gemini-cli
```
