#!/usr/bin/env bash
# Refresh the self-contained MCPB plugin source from the development surface.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$REPO_ROOT/surfaces/mcpb/"
TARGET="$REPO_ROOT/plugins/boltz-mcpb/"

mkdir -p "$TARGET"
rsync -aL --delete --delete-excluded \
  --exclude='.DS_Store' \
  --exclude='node_modules' \
  --exclude='*.mcpb' \
  "$SOURCE" "$TARGET"

echo "Synced $TARGET"
