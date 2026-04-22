#!/usr/bin/env bash
# Package the Claude Code and Codex plugin surfaces into zip archives for
# release. The Claude Code MCP variant includes pre-built binaries; all other
# surfaces are just manifest + skill symlinks and require no binaries.
#
# Usage: scripts/package-plugins.sh
#
# Produces:
#   dist/claude-code-cli-<version>.zip
#   dist/claude-code-mcp-<version>.zip        (per-platform, requires binaries)
#   dist/codex-cli-<version>.zip
#   dist/codex-mcp-<version>.zip

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST="$REPO_ROOT/dist"

mkdir -p "$DIST"

pack_plugin() {
  local surface="$1" manifest_path="$2"
  local version
  version=$(jq -r .version "$REPO_ROOT/surfaces/$surface/$manifest_path")
  local out="$DIST/${surface}-${version}.zip"

  echo "Packing $surface (v$version)..."
  rm -f "$out"

  # zip -y preserves symlinks. The Claude Code docs say symlinks survive the
  # plugin cache, so in principle the zip can include them. For codex surfaces
  # we do the same for consistency.
  (cd "$REPO_ROOT/surfaces/$surface" && zip -ry "$out" . -x '*.DS_Store' '.gitkeep')

  echo "  → $out"
}

pack_plugin claude-code-cli ".claude-plugin/plugin.json"
pack_plugin claude-code-mcp ".claude-plugin/plugin.json"
pack_plugin codex-cli       ".codex-plugin/plugin.json"
pack_plugin codex-mcp       ".codex-plugin/plugin.json"

echo
echo "Packaged surfaces:"
ls -lh "$DIST"/*.zip
