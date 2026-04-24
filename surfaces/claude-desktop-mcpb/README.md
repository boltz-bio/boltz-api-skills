# boltz-compute (Claude Desktop MCPB extension)

Local MCP server + bundled `boltz-api` CLI, packaged as a Claude Desktop `.mcpb` extension.

## What's inside the bundle

```
boltz-compute-<version>.mcpb        (ZIP archive)
├── manifest.json
├── icon.png                        # TODO: 512×512 PNG; add to manifest.json once available
└── server/
    ├── boltz-compute-mcp           # Go MCP server (darwin universal or win .exe)
    └── boltz-api                   # Bundled Boltz CLI
```

> **Icon**: the manifest intentionally does not reference an icon yet. `mcpb validate` fails if the manifest references a file that doesn't exist on disk. When the 512×512 PNG is ready, drop `icon.png` in this directory and add `"icon": "icon.png"` back to `manifest.json`.

The MCP server's tools (`boltz_auth_login`, `boltz_auth_complete`, `boltz_auth_status`, `boltz_auth_logout`, `boltz_estimate_run`, `boltz_submit_run`, `boltz_list_jobs`, `boltz_get_job`, `boltz_resume_download`, `boltz_get_local_run`) are auto-discovered by Claude Desktop (`tools_generated: true` in the manifest).

## Skills are NOT bundled here

MCPB extensions don't support skills — skills are a separate Claude Desktop distribution slot. The workflow prose lives in `core/skills/mcp/` and is consumed by the Claude Code MCP plugin.

## Prerequisites for end users

- Claude Desktop (macOS or Windows; see [Anthropic docs](https://claude.com/docs/connectors/building/mcpb)).
- Either OAuth device-code login through the `boltz_auth_login` tool, or a Boltz Compute API key configured at install time via the manifest's `user_config`.

**No separate CLI installation required** — `boltz-api` is bundled.

## OAuth Device-Code Login

When no API key is configured, Claude can call `boltz_auth_login`. The tool returns a verification URL, user code, and `pending_id`; Claude should show those to the user, then immediately call `boltz_auth_complete`. That tool waits for the bundled CLI to finish polling the device flow, returning `success` once tokens are stored locally or `waiting` if its timeout expires first.

## Building the bundle

```bash
# From repo root
scripts/build-mcp-release.sh   # produces dist/bin/<platform>/*
scripts/package-mcpb.sh        # produces dist/boltz-compute-<version>.mcpb
```

The build script:
1. Cross-compiles the Go MCP server for darwin-arm64, darwin-amd64, win-amd64.
2. `lipo`-merges the two darwin MCP server builds into a universal binary.
3. Downloads the pinned `boltz-api` release assets from `boltz-bio/boltz-compute-api-cli`.
4. `lipo`-merges the macOS CLI binaries into a universal `server/boltz-api`.
5. Places artifacts in `server/`.
6. Runs `mcpb pack` to produce the final `.mcpb`.

## Local development

```bash
# Fast inner loop: build the host-platform MCP server into server/
scripts/build-mcp-local.sh

# Distributable bundle (macOS only; requires lipo + mcpb)
scripts/build-mcp-release.sh
scripts/package-mcpb.sh
```

## Distribution

Submit to the Anthropic Software Directory via <https://clau.de/desktop-extention-submission>. Required before submission:

- Privacy policy URL.
- Icon at 512×512 PNG (`icon.png`).
- Screenshots of tools in use.
- Verification that the bundled `boltz-api` binary is distributed under a license compatible with redistribution.
