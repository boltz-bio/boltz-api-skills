#!/usr/bin/env bash
# Build the Boltz Compute Go MCP server for the current host platform and copy
# the binary into every surface directory that needs it.
#
# Usage: scripts/build-mcp-local.sh
#
# Produces (only for the host platform):
#   surfaces/claude-code-mcp/bin/boltz-compute-mcp
#   surfaces/claude-desktop-mcpb/server/boltz-compute-mcp
#   surfaces/codex-mcp/bin/boltz-compute-mcp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$REPO_ROOT/core/mcp-server"

BIN_NAME="boltz-compute-mcp"
if [[ "${OS:-}" == "Windows_NT" ]]; then
  BIN_NAME="boltz-compute-mcp.exe"
fi

echo "Building $BIN_NAME (host platform)..."
(cd "$SRC_DIR" && go build -o "/tmp/$BIN_NAME" ./cmd/boltz-compute-mcp)

TARGETS=(
  "$REPO_ROOT/surfaces/claude-code-mcp/bin"
  "$REPO_ROOT/surfaces/claude-desktop-mcpb/server"
  "$REPO_ROOT/surfaces/codex-mcp/bin"
)

for target in "${TARGETS[@]}"; do
  mkdir -p "$target"
  cp "/tmp/$BIN_NAME" "$target/$BIN_NAME"
  chmod +x "$target/$BIN_NAME"
  echo "  → $target/$BIN_NAME"
done

rm -f "/tmp/$BIN_NAME"
echo "Done."
