#!/usr/bin/env bash
# Refresh the self-contained Codex plugin copy intended for openai/plugins.
#
# The development surface uses symlinks into skills/. The official Codex plugin
# repository expects a real plugins/<name>/ tree, so this generated copy
# dereferences symlinks and keeps the directory name aligned with plugin.json.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$REPO_ROOT/surfaces/codex-cli/"
PLUGIN_NAME="$(jq -r .name "$SOURCE/.codex-plugin/plugin.json")"
PLUGIN_ROOT="${1:-$REPO_ROOT/plugins}"
TARGET="$PLUGIN_ROOT/$PLUGIN_NAME/"

mkdir -p "$TARGET"
rsync -acL --delete --delete-excluded \
  --exclude='.DS_Store' \
  --exclude='__pycache__' \
  --exclude='*.py[cod]' \
  --exclude='README.md' \
  --exclude='DESIGN.md' \
  --exclude='GOTCHAS.md' \
  --exclude='GENERATED.md' \
  "$SOURCE" "$TARGET"

echo "Synced $TARGET"
