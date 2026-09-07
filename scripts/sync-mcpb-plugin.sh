#!/usr/bin/env bash
# Refresh the self-contained MCPB plugin source from the development surface.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$REPO_ROOT/surfaces/mcpb/"
PLUGIN_ROOT="${1:-$REPO_ROOT/plugins}"
TARGET="$PLUGIN_ROOT/boltz-mcpb/"

mkdir -p "$TARGET"
rsync -acL --delete --delete-excluded \
  --exclude='.DS_Store' \
  --exclude='node_modules' \
  --exclude='*.mcpb' \
  "$SOURCE" "$TARGET"

mkdir -p "$TARGET/guidance/skills"
rsync -acL --delete \
  --exclude='.DS_Store' \
  --exclude='__pycache__' \
  --exclude='*.py[cod]' \
  "$REPO_ROOT/skills/" "$TARGET/guidance/skills/"

echo "Synced $TARGET"
