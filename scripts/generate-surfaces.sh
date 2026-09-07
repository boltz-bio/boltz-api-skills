#!/usr/bin/env bash
# Generate every checked-in distribution surface from the canonical sources.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${1:-$(cd "$SCRIPT_DIR/.." && pwd)/plugins}"

"$SCRIPT_DIR/sync-claude-marketplace-plugin.sh" "$PLUGIN_ROOT"
"$SCRIPT_DIR/sync-codex-openai-plugin.sh" "$PLUGIN_ROOT"
"$SCRIPT_DIR/sync-mcpb-plugin.sh" "$PLUGIN_ROOT"
