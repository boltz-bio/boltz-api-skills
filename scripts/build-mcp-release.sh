#!/usr/bin/env bash
# Cross-compile the Go MCP server for all release platforms and produce the
# per-platform binaries ready for packaging.
#
# Usage: scripts/build-mcp-release.sh
#
# Produces:
#   dist/bin/darwin-arm64/boltz-compute-mcp
#   dist/bin/darwin-amd64/boltz-compute-mcp
#   dist/bin/darwin-universal/boltz-compute-mcp   (lipo-merged; macOS only)
#   dist/bin/linux-amd64/boltz-compute-mcp
#   dist/bin/windows-amd64/boltz-compute-mcp.exe

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$REPO_ROOT/core/mcp-server"
DIST_DIR="$REPO_ROOT/dist/bin"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

build() {
  local goos="$1" goarch="$2" ext="${3:-}"
  local platform_dir="$DIST_DIR/${goos}-${goarch}"
  local bin_path="$platform_dir/boltz-compute-mcp${ext}"
  mkdir -p "$platform_dir"
  echo "Building ${goos}/${goarch}..."
  (cd "$SRC_DIR" && GOOS="$goos" GOARCH="$goarch" CGO_ENABLED=0 \
    go build -ldflags="-s -w" -o "$bin_path" ./cmd/boltz-compute-mcp)
}

build darwin arm64
build darwin amd64
build linux amd64
build windows amd64 .exe

# lipo-merge the two darwin builds into one universal binary (macOS host only).
if [[ "$(uname)" == "Darwin" ]] && command -v lipo >/dev/null 2>&1; then
  echo "Creating darwin universal binary..."
  mkdir -p "$DIST_DIR/darwin-universal"
  lipo -create \
    "$DIST_DIR/darwin-arm64/boltz-compute-mcp" \
    "$DIST_DIR/darwin-amd64/boltz-compute-mcp" \
    -output "$DIST_DIR/darwin-universal/boltz-compute-mcp"
else
  echo "Skipping darwin universal binary (lipo not available on this host)."
fi

echo
echo "Built binaries:"
find "$DIST_DIR" -type f | sort
