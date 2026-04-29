#!/usr/bin/env bash
# Package the Claude Code and Codex CLI plugin surfaces into zip archives for
# release. Surface contents are staged through a dereferenced copy so published
# archives are self-contained and do not depend on repo-relative symlinks
# resolving after extraction.
#
# Usage: scripts/package-plugins.sh
#
# Produces:
#   dist/claude-code-cli-<version>.zip
#   dist/<codex-plugin-name>-<version>.zip

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST="$REPO_ROOT/dist"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/boltz-package-plugins.XXXXXX")"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

mkdir -p "$DIST"
find "$DIST" -maxdepth 1 -type f -name '*.zip' -delete

copy_surface_tree() {
  local surface="$1" stage_dir="$2"
  rsync -aL \
    --exclude='.DS_Store' \
    --exclude='.gitkeep' \
    --exclude='README.md' \
    --exclude='DESIGN.md' \
    --exclude='GOTCHAS.md' \
    --exclude='GENERATED.md' \
    "$REPO_ROOT/surfaces/$surface/" "$stage_dir/"
}

zip_stage_dir() {
  local stage_dir="$1" out="$2"
  rm -f "$out"
  (cd "$stage_dir" && zip -qr "$out" .)
}

pack_cli_plugin() {
  local surface="$1" manifest_path="$2" output_name="${3:-$1}"
  local version
  version=$(jq -r .version "$REPO_ROOT/surfaces/$surface/$manifest_path")
  local out="$DIST/${output_name}-${version}.zip"
  local stage_dir="$TMP_ROOT/${surface}"

  echo "Packing $surface (v$version)..."
  mkdir -p "$stage_dir"
  copy_surface_tree "$surface" "$stage_dir"
  zip_stage_dir "$stage_dir" "$out"
  echo "  → $out"
}

codex_plugin_name="$(jq -r .name "$REPO_ROOT/surfaces/codex-cli/.codex-plugin/plugin.json")"

pack_cli_plugin claude-code-cli ".claude-plugin/plugin.json"
pack_cli_plugin codex-cli       ".codex-plugin/plugin.json" "$codex_plugin_name"

echo
echo "Packaged surfaces:"
ls -lh "$DIST"/*.zip
