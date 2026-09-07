#!/usr/bin/env bash
# Verify checked-in generated distribution surfaces are up to date.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/boltz-verify-generated.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

"$SCRIPT_DIR/generate-surfaces.sh" "$TMP_ROOT"

stale=0
for plugin in boltz boltz-api-cli boltz-mcpb; do
  if ! diff -qr -x node_modules -x __pycache__ -x '*.pyc' -x .DS_Store \
    "$REPO_ROOT/plugins/$plugin" "$TMP_ROOT/$plugin"; then
    stale=1
  fi
done

if [[ "$stale" == 1 ]]; then
  echo "error: generated plugin copies are out of sync." >&2
  echo "Edit skills/ or surfaces/<surface>/, then run:" >&2
  echo "  scripts/generate-surfaces.sh" >&2
  exit 1
fi

echo "Generated surfaces are in sync."
