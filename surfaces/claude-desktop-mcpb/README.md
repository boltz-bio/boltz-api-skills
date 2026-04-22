# boltz-compute (Claude Desktop MCPB extension)

Local MCP server + bundled `boltz-api` CLI, packaged as a Claude Desktop `.mcpb` extension.

## What's inside the bundle

```
boltz-compute-<version>.mcpb        (ZIP archive)
├── manifest.json
├── icon.png
└── server/
    ├── boltz-compute-mcp           # Go MCP server (darwin universal or win .exe)
    └── boltz-api                   # Bundled Boltz CLI
```

The MCP server's tools (`boltz_estimate_run`, `boltz_submit_run`, `boltz_list_jobs`, `boltz_get_job`, `boltz_resume_download`, `boltz_get_local_run`) are auto-discovered by Claude Desktop (`tools_generated: true` in the manifest).

## Skills are NOT bundled here

MCPB extensions don't support skills — skills are a separate Claude Desktop distribution slot. The workflow prose lives in `core/skills/mcp/` and is consumed by the Claude Code MCP plugin. For Desktop users, progressive disclosure happens via MCP Resources served by the bundled Go server (payload schemas from `core/references/`).

## Prerequisites for end users

- Claude Desktop (macOS or Windows; see [Anthropic docs](https://claude.com/docs/connectors/building/mcpb)).
- A Boltz Compute API key — requested at install time via the manifest's `user_config`.

**No separate CLI installation required** — `boltz-api` is bundled.

## Building the bundle

```bash
# From repo root
scripts/build-mcpb.sh          # produces dist/boltz-compute-<version>.mcpb
```

The build script:
1. Cross-compiles the Go MCP server for darwin-arm64, darwin-amd64, win-amd64.
2. `lipo`-merges the two darwin builds into a universal binary.
3. Fetches `boltz-api` per platform (TODO: source URL from CLI release pipeline).
4. Places artifacts in `server/`.
5. Runs `mcpb pack` to produce the final `.mcpb`.

## Local development

```bash
# Build just the host-platform MCP server binary into server/
scripts/build-mcp-local.sh

# Then test-install into Claude Desktop by dragging the resulting .mcpb
# or pointing Claude Desktop at this directory via Settings > Extensions.
```

## Distribution

Submit to the Anthropic Software Directory via <https://clau.de/desktop-extention-submission>. Required before submission:

- Privacy policy URL.
- Icon at 512×512 PNG (`icon.png`).
- Screenshots of tools in use.
- Verification that the bundled `boltz-api` binary is distributed under a license compatible with redistribution.
