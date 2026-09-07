# Boltz Codex plugin

This official marketplace wrapper ships the canonical [Boltz skills](../../skills/)
and Codex plugin assets. For the primary installation path, use
[Vercel Skills](../../README.md#install):

```sh
npx skills add boltz-bio/boltz-api-skills --agent codex
```

Install and authenticate `boltz-api` as described in the
[prerequisites](../../README.md#prerequisites).

## Marketplace distribution

`plugins/boltz-api-cli/` is the generated, self-contained plugin for Codex
marketplace distribution. It retains the plugin manifest and assets. The
canonical skill directories contain the existing `agents/openai.yaml`
metadata, so direct Skills installations receive it too.

## Development

`skills` links to the repository's canonical tree. Edit shared content there.
See [CONTRIBUTING.md](../../CONTRIBUTING.md) for generation, tests, and the
marketplace submission procedure.
