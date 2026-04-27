#!/usr/bin/env bash
# Verify checked-in generated distribution surfaces are up to date.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

before="$(git -C "$REPO_ROOT" status --porcelain -- plugins/boltz)"

"$SCRIPT_DIR/generate-surfaces.sh"

after="$(git -C "$REPO_ROOT" status --porcelain -- plugins/boltz)"

if [[ "$before" != "$after" ]]; then
  echo "error: generated Claude plugin copy is out of sync." >&2
  echo "Edit core/ or surfaces/claude-code-cli/, then run:" >&2
  echo "  scripts/generate-surfaces.sh" >&2
  echo >&2
  git -C "$REPO_ROOT" diff --stat -- plugins/boltz >&2
  git -C "$REPO_ROOT" status --short -- plugins/boltz >&2
  exit 1
fi

echo "Generated surfaces are in sync."
