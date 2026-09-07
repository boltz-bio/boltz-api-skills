# Boltz Codex plugin

The official **Boltz** Codex plugin ships the eight shared
[Boltz skills](../../skills/) and Codex plugin assets. The skills invoke the
`boltz-api` CLI. This package does not configure a local MCP server.

## Install from the official Codex marketplace (recommended)

Open the plugin directory, search for **Boltz**, and install the official
plugin. In Codex CLI, enter `/plugins` to open the plugin browser. Start a
new session after installing. See [OpenAI's plugin guide](https://learn.chatgpt.com/docs/plugins)
for the supported installation surfaces.

The published package is
[`openai/plugins/plugins/boltz-api-cli`](https://github.com/openai/plugins/tree/main/plugins/boltz-api-cli).
Its plugin ID is `boltz-api-cli`; its display name is **Boltz**.

Install and authenticate `boltz-api` as described in the
[prerequisites](../../README.md#prerequisites), or ask for `boltz-cli-setup`.

## Alternative: direct skill installation

If you need a direct skill installation, use
[Vercel Skills](../../README.md#other-agents-and-direct-skill-installation):

```sh
npx skills add boltz-bio/boltz-api-skills --agent codex
```

Use one installation method per scope to avoid loading duplicate skills.
Existing marketplace users do not need to switch to Skills.

## Marketplace distribution

`plugins/boltz-api-cli/` is the generated, self-contained plugin for Codex
marketplace distribution. It retains the plugin manifest and assets. The
canonical skill directories contain the existing `agents/openai.yaml`
metadata, so direct Skills installations receive it too.

The release workflow builds a versioned ZIP in this repository. Publishing
that GitHub Release does not update the copy in `openai/plugins`. Maintainers
must submit an update to the existing OpenAI plugin separately; see the
[Codex publishing procedure](../../CONTRIBUTING.md#codex-openaiplugins).

## Development

`skills` links to the repository's canonical tree. Edit shared content there.
See [CONTRIBUTING.md](../../CONTRIBUTING.md) for generation, tests, and the
marketplace submission procedure.
