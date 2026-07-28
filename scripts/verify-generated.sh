#!/usr/bin/env bash
# Verify checked-in generated distribution surfaces are up to date.
#
# The check is: regenerating from the committed core/ and surfaces/ must produce
# exactly the committed plugins/. We assert the working tree is CLEAN for those
# paths after regeneration — not merely "unchanged", which is what the earlier
# version compared, and which passed while origin/main carried live drift
# (surfaces/codex-cli plugin.json 0.1.1 vs plugins/boltz-api-cli 0.1.0, both
# 1766 bytes — equal size, so rsync's mtime/size quick-check skipped it too).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GENERATED=(plugins/boltz plugins/boltz-api-cli plugins/boltz-mcpb)

dirty() {
  ! git -C "$REPO_ROOT" diff --quiet -- "${GENERATED[@]}" ||
    [[ -n "$(git -C "$REPO_ROOT" ls-files --others --exclude-standard -- "${GENERATED[@]}")" ]]
}

if dirty; then
  echo "error: generated plugin copies have uncommitted changes before verification." >&2
  echo "Commit or stash them first, so any diff can be attributed to generation." >&2
  git -C "$REPO_ROOT" status --short -- "${GENERATED[@]}" >&2
  exit 1
fi

"$SCRIPT_DIR/generate-surfaces.sh"

if dirty; then
  echo "error: generated plugin copies are out of sync." >&2
  echo "Edit core/ or surfaces/<surface>/, then run:" >&2
  echo "  scripts/generate-surfaces.sh" >&2
  echo >&2
  git -C "$REPO_ROOT" diff --stat -- "${GENERATED[@]}" >&2
  git -C "$REPO_ROOT" status --short -- "${GENERATED[@]}" >&2
  exit 1
fi

echo "Generated surfaces are in sync."
