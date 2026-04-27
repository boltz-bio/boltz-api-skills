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
rsync -aL --delete \
  --exclude='.DS_Store' \
  "$SOURCE" "$TARGET"

cat > "$TARGET/GENERATED.md" <<'EOF'
# Generated Plugin Copy

This directory is generated from `surfaces/claude-code-cli/`.

Do not edit files under `plugins/boltz/` directly. Update the shared source
under `core/` or the development surface under `surfaces/claude-code-cli/`,
then run:

```bash
scripts/generate-surfaces.sh
```
EOF

echo "Synced $TARGET"
