#!/usr/bin/env bash
# Refresh the self-contained Codex plugin copy intended for openai/plugins.
#
# The development surface uses symlinks into core/. The official Codex plugin
# repository expects a real plugins/<dir>/ tree, so this generated copy
# dereferences symlinks.
#
# The output directory is PINNED, not derived from plugin.json's `name`.
# Codex requires plugin.json `name` to equal the marketplace entry name
# (`boltz`, see .agents/plugins/marketplace.json), while the released zip, the
# `codex-plugin/v*` tags and .github/workflows/surface-release.yml all key off
# the directory `plugins/boltz-api-cli`. Deriving TARGET from `name` — as this
# script used to — silently redirects the Codex surface on top of
# plugins/boltz, i.e. overwrites the Claude Code plugin.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$REPO_ROOT/surfaces/codex-cli/"
PLUGIN_DIR="boltz-api-cli"
TARGET="$REPO_ROOT/plugins/$PLUGIN_DIR/"

# Codex resolves `codex plugin add <entry>@<marketplace>` by matching the
# marketplace entry name against plugin.json `name`; a mismatch is a hard error
# ("plugin.json name `X` does not match marketplace plugin name `Y`").
MANIFEST_NAME="$(jq -r .name "$SOURCE/.codex-plugin/plugin.json")"
ENTRY_NAME="$(jq -r --arg d "./plugins/$PLUGIN_DIR" \
  '.plugins[] | select(.source == $d) | .name' \
  "$REPO_ROOT/.agents/plugins/marketplace.json")"

if [[ "$MANIFEST_NAME" != "$ENTRY_NAME" ]]; then
  echo "error: Codex plugin name mismatch." >&2
  echo "  surfaces/codex-cli/.codex-plugin/plugin.json name = $MANIFEST_NAME" >&2
  echo "  .agents/plugins/marketplace.json entry name       = $ENTRY_NAME" >&2
  echo "\`codex plugin add\` will fail with a name-mismatch error." >&2
  exit 1
fi

mkdir -p "$TARGET"
rsync -aLI --delete --delete-excluded \
  --exclude='.DS_Store' \
  --exclude='README.md' \
  --exclude='DESIGN.md' \
  --exclude='GOTCHAS.md' \
  --exclude='GENERATED.md' \
  "$SOURCE" "$TARGET"

echo "Synced $TARGET"
