#!/usr/bin/env bash
# Package the Claude Desktop MCPB bundle.
#
# Assumes:
#   - scripts/build-mcp-release.sh has produced dist/bin/*.
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
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/boltz-package-mcpb.XXXXXX")"
BOLTZ_API_REPO="boltz-bio/boltz-compute-api-cli"
BOLTZ_API_VERSION_FILE="$SCRIPT_DIR/boltz-api-version.txt"

VERSION=$(jq -r .version "$MCPB_DIR/manifest.json")

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

if [[ ! -d "$DIST_BIN" ]]; then
  echo "error: $DIST_BIN does not exist. Run scripts/build-mcp-release.sh first." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "error: curl not found on PATH." >&2
  exit 1
fi

if ! command -v unzip >/dev/null 2>&1; then
  echo "error: unzip not found on PATH." >&2
  exit 1
fi

if ! command -v lipo >/dev/null 2>&1; then
  echo "error: lipo not found on PATH. Packaging the MCPB requires macOS to assemble universal binaries." >&2
  exit 1
fi

if ! command -v mcpb >/dev/null 2>&1; then
  echo "error: mcpb not found on PATH. Install with: npm install -g @anthropic-ai/mcpb" >&2
  exit 1
fi

resolve_boltz_api_tag() {
  if [[ -n "${BOLTZ_API_VERSION:-}" ]]; then
    printf '%s\n' "$BOLTZ_API_VERSION"
    return
  fi
  if [[ -f "$BOLTZ_API_VERSION_FILE" ]]; then
    tr -d '[:space:]' < "$BOLTZ_API_VERSION_FILE"
    return
  fi
  echo "error: set BOLTZ_API_VERSION or create $BOLTZ_API_VERSION_FILE" >&2
  exit 1
}

download_release_asset() {
  local tag="$1" asset_name="$2" dest_path="$3"
  local url="https://github.com/$BOLTZ_API_REPO/releases/download/$tag/$asset_name"
  echo "  → $asset_name"
  curl -fsSL -o "$dest_path" "$url"
}

ensure_universal_server_binary() {
  local universal_path="$DIST_BIN/darwin-universal/boltz-compute-mcp"
  if [[ -f "$universal_path" ]]; then
    return
  fi

  local arm64_path="$DIST_BIN/darwin-arm64/boltz-compute-mcp"
  local amd64_path="$DIST_BIN/darwin-amd64/boltz-compute-mcp"
  if [[ ! -f "$arm64_path" || ! -f "$amd64_path" ]]; then
    echo "error: missing darwin-arm64 or darwin-amd64 server binary under $DIST_BIN" >&2
    exit 1
  fi

  echo "Creating universal boltz-compute-mcp..."
  mkdir -p "$DIST_BIN/darwin-universal"
  lipo -create "$arm64_path" "$amd64_path" -output "$universal_path"
  chmod +x "$universal_path"
}

stage_boltz_api_cli() {
  local tag="$1"
  local version_without_v="${tag#v}"
  local downloads_dir="$TMP_ROOT/downloads"
  local extract_dir="$TMP_ROOT/extract"
  mkdir -p "$downloads_dir" "$extract_dir/macos-arm64" "$extract_dir/macos-amd64" "$extract_dir/windows-amd64"

  local macos_arm64_zip="$downloads_dir/boltz-api_${version_without_v}_macos_arm64.zip"
  local macos_amd64_zip="$downloads_dir/boltz-api_${version_without_v}_macos_amd64.zip"
  local windows_amd64_zip="$downloads_dir/boltz-api_${version_without_v}_windows_amd64.zip"

  echo "Downloading boltz-api CLI assets from $BOLTZ_API_REPO@$tag..."
  download_release_asset "$tag" "$(basename "$macos_arm64_zip")" "$macos_arm64_zip"
  download_release_asset "$tag" "$(basename "$macos_amd64_zip")" "$macos_amd64_zip"
  download_release_asset "$tag" "$(basename "$windows_amd64_zip")" "$windows_amd64_zip"

  unzip -j -q "$macos_arm64_zip" boltz-api -d "$extract_dir/macos-arm64"
  unzip -j -q "$macos_amd64_zip" boltz-api -d "$extract_dir/macos-amd64"
  unzip -j -q "$windows_amd64_zip" boltz-api.exe -d "$extract_dir/windows-amd64"

  echo "Creating universal boltz-api..."
  lipo -create \
    "$extract_dir/macos-arm64/boltz-api" \
    "$extract_dir/macos-amd64/boltz-api" \
    -output "$MCPB_DIR/server/boltz-api"
  chmod +x "$MCPB_DIR/server/boltz-api"

  cp "$extract_dir/windows-amd64/boltz-api.exe" "$MCPB_DIR/server/boltz-api.exe"
}

# Populate server/ with the right binaries. Claude Desktop targets darwin + win32
# (per Anthropic docs), so we stage the darwin universal + windows-amd64 builds.
echo "Staging server/ with release binaries..."
rm -f "$MCPB_DIR/server/boltz-compute-mcp" "$MCPB_DIR/server/boltz-compute-mcp.exe"
rm -f "$MCPB_DIR/server/boltz-api" "$MCPB_DIR/server/boltz-api.exe"

ensure_universal_server_binary

DARWIN_SRC="$DIST_BIN/darwin-universal/boltz-compute-mcp"
WINDOWS_SRC="$DIST_BIN/windows-amd64/boltz-compute-mcp.exe"
if [[ ! -f "$WINDOWS_SRC" ]]; then
  echo "error: missing $WINDOWS_SRC. Run scripts/build-mcp-release.sh first." >&2
  exit 1
fi

cp "$DARWIN_SRC" "$MCPB_DIR/server/boltz-compute-mcp"
chmod +x "$MCPB_DIR/server/boltz-compute-mcp"
cp "$WINDOWS_SRC" "$MCPB_DIR/server/boltz-compute-mcp.exe"

BOLTZ_API_TAG="$(resolve_boltz_api_tag)"
stage_boltz_api_cli "$BOLTZ_API_TAG"

echo "Running mcpb pack..."
OUT="$REPO_ROOT/dist/boltz-compute-${VERSION}.mcpb"
mkdir -p "$REPO_ROOT/dist"
find "$REPO_ROOT/dist" -maxdepth 1 -type f -name '*.mcpb' -delete
(cd "$MCPB_DIR" && mcpb pack . "$OUT")

echo
echo "Packed: $OUT"
ls -lh "$OUT"
