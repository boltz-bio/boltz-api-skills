#!/usr/bin/env bash
# Install the Boltz Claude Code plugin from the Boltz marketplace.
#
# Usage:
#   scripts/install-claude-code-plugin.sh
#   BOLTZ_CLAUDE_MARKETPLACE=/path/to/boltz-compute-skills scripts/install-claude-code-plugin.sh
#   BOLTZ_CLAUDE_SCOPE=local scripts/install-claude-code-plugin.sh

set -euo pipefail

MARKETPLACE_NAME="${BOLTZ_CLAUDE_MARKETPLACE_NAME:-boltz-marketplace}"
MARKETPLACE_SOURCE="${BOLTZ_CLAUDE_MARKETPLACE:-boltz-bio/boltz-compute-skills}"
PLUGIN_ID="${BOLTZ_CLAUDE_PLUGIN:-boltz@${MARKETPLACE_NAME}}"
SCOPE="${BOLTZ_CLAUDE_SCOPE:-user}"

if ! command -v claude >/dev/null 2>&1; then
  echo "error: Claude Code is required. Install it with: npm install -g @anthropic-ai/claude-code" >&2
  exit 1
fi

if claude plugin marketplace update "$MARKETPLACE_NAME" >/dev/null 2>&1; then
  echo "Updating Claude marketplace: $MARKETPLACE_NAME"
else
  echo "Adding Claude marketplace: $MARKETPLACE_SOURCE"
  claude plugin marketplace add "$MARKETPLACE_SOURCE"
fi

echo "Installing Claude plugin: $PLUGIN_ID (scope: $SCOPE)"
claude plugin install "$PLUGIN_ID" --scope "$SCOPE"

echo
echo "Installed $PLUGIN_ID. Restart Claude Code before using the Boltz skills."
