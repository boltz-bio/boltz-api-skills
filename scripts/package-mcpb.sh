#!/usr/bin/env bash
# Package the Claude Desktop MCPB bundle.
#
# Assumes:
#   - scripts/build-mcp-release.sh has produced dist/bin/*.
#   - boltz-api binaries are staged in dist/bin/<platform>/boltz-api (see
#     FETCH_BOLTZ_API_CLI below; currently a TODO stub).
#
# Produces:
#   dist/boltz-compute-<version>.mcpb
#
# Requires: @anthropic-ai/mcpb on PATH (`npm install -g @anthropic-ai/mcpb`).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCPB_DIR="$REPO_ROOT/surfaces/claude-desktop-mcpb"
DIST_BIN="$REPO_ROOT/dist/bin"

VERSION=$(jq -r .version "$MCPB_DIR/manifest.json")

if [[ ! -d "$DIST_BIN" ]]; then
  echo "error: $DIST_BIN does not exist. Run scripts/build-mcp-release.sh first." >&2
  exit 1
fi

if ! command -v mcpb >/dev/null 2>&1; then
  echo "error: mcpb not found on PATH. Install with: npm install -g @anthropic-ai/mcpb" >&2
  exit 1
fi

# Populate server/ with the right binaries. Claude Desktop targets darwin + win32
# (per Anthropic docs), so we stage the darwin universal + windows-amd64 builds.
echo "Staging server/ with release binaries..."
rm -f "$MCPB_DIR/server/boltz-compute-mcp" "$MCPB_DIR/server/boltz-compute-mcp.exe"
rm -f "$MCPB_DIR/server/boltz-api" "$MCPB_DIR/server/boltz-api.exe"

DARWIN_SRC="$DIST_BIN/darwin-universal/boltz-compute-mcp"
if [[ ! -f "$DARWIN_SRC" ]]; then
  DARWIN_SRC="$DIST_BIN/darwin-arm64/boltz-compute-mcp"
  echo "  warning: darwin-universal not found, falling back to darwin-arm64" >&2
fi

cp "$DARWIN_SRC" "$MCPB_DIR/server/boltz-compute-mcp"
chmod +x "$MCPB_DIR/server/boltz-compute-mcp"

if [[ -f "$DIST_BIN/windows-amd64/boltz-compute-mcp.exe" ]]; then
  cp "$DIST_BIN/windows-amd64/boltz-compute-mcp.exe" "$MCPB_DIR/server/boltz-compute-mcp.exe"
fi

# TODO: Fetch boltz-api binaries per platform from the CLI release pipeline.
# The URL pattern depends on how the Boltz CLI publishes releases. Adjust once
# that pipeline is live. For now, if a local boltz-api is on PATH, stage it for
# the host platform so local builds can smoke-test the bundle.
if command -v boltz-api >/dev/null 2>&1; then
  echo "Staging host boltz-api into server/ (dev only; CI fetches per-platform)..."
  cp "$(command -v boltz-api)" "$MCPB_DIR/server/boltz-api"
  chmod +x "$MCPB_DIR/server/boltz-api"
else
  echo "  warning: boltz-api not on PATH; the packed .mcpb will not include the CLI." >&2
  echo "  This is fine for manifest validation but the bundle won't work end-to-end." >&2
fi

echo "Running mcpb pack..."
OUT="$REPO_ROOT/dist/boltz-compute-${VERSION}.mcpb"
mkdir -p "$REPO_ROOT/dist"
(cd "$MCPB_DIR" && mcpb pack . "$OUT")

echo
echo "Packed: $OUT"
ls -lh "$OUT"
