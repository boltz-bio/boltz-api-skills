#!/usr/bin/env bash
# Refresh the self-contained Claude Code marketplace plugin from the CLI surface.
#
# The development surface uses symlinks into core/. Claude marketplace installs
# copy plugins into a cache, so the published local plugin must contain real
# files instead of repo-relative symlinks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$REPO_ROOT/surfaces/claude-code-cli/"
TARGET="$REPO_ROOT/plugins/boltz/"

mkdir -p "$TARGET"
rsync -aL --delete --delete-excluded \
  --exclude='.DS_Store' \
  --exclude='README.md' \
  --exclude='DESIGN.md' \
  --exclude='GOTCHAS.md' \
  --exclude='GENERATED.md' \
  "$SOURCE" "$TARGET"

echo "Synced $TARGET"
