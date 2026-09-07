# Boltz Claude Code plugin

This official marketplace wrapper ships the canonical [Boltz skills](../../skills/).
For the primary installation path, use [Vercel Skills](../../README.md#install).

## Marketplace installation

```sh
claude plugin marketplace add boltz-bio/boltz-api-skills
claude plugin install boltz@boltz-marketplace --scope user
```

Restart Claude Code after installing. Install and authenticate `boltz-api` as
described in the [prerequisites](../../README.md#prerequisites).

## Development

From the repository root:

```sh
claude --plugin-dir ./surfaces/claude-code-cli
```

`skills` links to the repository's canonical tree. Edit shared content there.
The generated `plugins/boltz/` copy contains real files for marketplace caches.
See [CONTRIBUTING.md](../../CONTRIBUTING.md) for generation and validation.
