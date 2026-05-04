#!/usr/bin/env bash
# Generate every checked-in distribution surface from the canonical sources.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/sync-claude-marketplace-plugin.sh"
"$SCRIPT_DIR/sync-codex-openai-plugin.sh"
"$SCRIPT_DIR/sync-mcpb-plugin.sh"
