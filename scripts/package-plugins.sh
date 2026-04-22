#!/usr/bin/env bash
# Package the Claude Code and Codex plugin surfaces into zip archives for
# release. Surface contents are staged through a dereferenced copy so the
# published archives are self-contained and do not depend on repo-relative
# symlinks resolving after extraction.
#
# Usage: scripts/package-plugins.sh
#
# Produces:
#   dist/claude-code-cli-<version>.zip
#   dist/claude-code-mcp-<version>-<platform>.zip
#   dist/codex-cli-<version>.zip
#   dist/codex-mcp-<version>-<platform>.zip
#
# Requires:
#   - scripts/build-mcp-release.sh has produced dist/bin/*.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST="$REPO_ROOT/dist"
DIST_BIN="$DIST/bin"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/boltz-package-plugins.XXXXXX")"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

mkdir -p "$DIST"
find "$DIST" -maxdepth 1 -type f -name '*.zip' -delete

if [[ ! -d "$DIST_BIN" ]]; then
  echo "error: $DIST_BIN does not exist. Run scripts/build-mcp-release.sh first." >&2
  exit 1
fi

copy_surface_tree() {
  local surface="$1" stage_dir="$2"
  rsync -aL \
    --exclude='.DS_Store' \
    --exclude='.gitkeep' \
    "$REPO_ROOT/surfaces/$surface/" "$stage_dir/"
}

zip_stage_dir() {
  local stage_dir="$1" out="$2"
  rm -f "$out"
  (cd "$stage_dir" && zip -qr "$out" .)
}

pack_cli_plugin() {
  local surface="$1" manifest_path="$2"
  local version
  version=$(jq -r .version "$REPO_ROOT/surfaces/$surface/$manifest_path")
  local out="$DIST/${surface}-${version}.zip"
  local stage_dir="$TMP_ROOT/${surface}"

  echo "Packing $surface (v$version)..."
  mkdir -p "$stage_dir"
  copy_surface_tree "$surface" "$stage_dir"
  zip_stage_dir "$stage_dir" "$out"
  echo "  → $out"
}

rewrite_windows_command() {
  local mcp_json="$1"
  local tmp_json="$mcp_json.tmp"
  jq '
    .mcpServers.boltzComputeLocal.command |= sub("boltz-compute-mcp$"; "boltz-compute-mcp.exe")
  ' "$mcp_json" > "$tmp_json"
  mv "$tmp_json" "$mcp_json"
}

pack_mcp_plugin() {
  local surface="$1" manifest_path="$2" platform="$3" binary_name="$4"
  local version
  version=$(jq -r .version "$REPO_ROOT/surfaces/$surface/$manifest_path")
  local stage_dir="$TMP_ROOT/${surface}-${platform}"
  local src_bin="$DIST_BIN/$platform/$binary_name"
  local dst_bin="$stage_dir/bin/$binary_name"
  local out="$DIST/${surface}-${version}-${platform}.zip"

  if [[ ! -f "$src_bin" ]]; then
    echo "error: missing $src_bin. Run scripts/build-mcp-release.sh first." >&2
    exit 1
  fi

  echo "Packing $surface (v$version, $platform)..."
  copy_surface_tree "$surface" "$stage_dir"
  rm -rf "$stage_dir/bin"
  mkdir -p "$stage_dir/bin"
  cp "$src_bin" "$dst_bin"
  chmod +x "$dst_bin"
  if [[ "$binary_name" == *.exe ]]; then
    rewrite_windows_command "$stage_dir/.mcp.json"
  fi
  zip_stage_dir "$stage_dir" "$out"
  echo "  → $out"
}

pack_cli_plugin claude-code-cli ".claude-plugin/plugin.json"
pack_cli_plugin codex-cli       ".codex-plugin/plugin.json"

for platform in darwin-arm64 darwin-amd64 linux-amd64; do
  pack_mcp_plugin claude-code-mcp ".claude-plugin/plugin.json" "$platform" "boltz-compute-mcp"
  pack_mcp_plugin codex-mcp       ".codex-plugin/plugin.json"  "$platform" "boltz-compute-mcp"
done

pack_mcp_plugin claude-code-mcp ".claude-plugin/plugin.json" "windows-amd64" "boltz-compute-mcp.exe"
pack_mcp_plugin codex-mcp       ".codex-plugin/plugin.json"  "windows-amd64" "boltz-compute-mcp.exe"

echo
echo "Packaged surfaces:"
ls -lh "$DIST"/*.zip
