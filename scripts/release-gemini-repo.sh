#!/usr/bin/env bash
# Mirror surfaces/gemini-cli/ into a public Gemini CLI extension repo as a PR.
#
# The release repo should have gemini-extension.json at its root so users can
# install it with `gemini extensions install <repo-url>`.
#
# Usage:
#   scripts/release-gemini-repo.sh
#   RELEASE_REPO=org/name scripts/release-gemini-repo.sh
#   DRY_RUN=1 scripts/release-gemini-repo.sh
#
# Requirements: git, rsync, jq, gh (authenticated).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$REPO_ROOT/surfaces/gemini-cli"

RELEASE_REPO="${RELEASE_REPO:-boltz-bio/boltz-gemini-cli}"
DRY_RUN="${DRY_RUN:-0}"

for cmd in git rsync jq gh; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing required command: $cmd" >&2; exit 1; }
done

VERSION="$(jq -r .version "$SOURCE/gemini-extension.json")"
SOURCE_SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
BRANCH="sync/v${VERSION}-${SOURCE_SHA}"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/boltz-gemini-release.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

# Register gh as git's credential helper so the later `git push` can
# authenticate using GH_TOKEN in CI.
gh auth setup-git >/dev/null

echo "Cloning $RELEASE_REPO..."
gh repo clone "$RELEASE_REPO" "$WORK_DIR/repo" -- --quiet

cd "$WORK_DIR/repo"
DEFAULT_BRANCH="$(gh repo view "$RELEASE_REPO" --json defaultBranchRef -q .defaultBranchRef.name)"
git checkout -q "$DEFAULT_BRANCH"
branch_exists=0
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  branch_exists=1
  git fetch -q origin "$BRANCH"
  git checkout -q -B "$BRANCH" "origin/$BRANCH"
else
  git checkout -q -B "$BRANCH"
fi

echo "Mirroring Gemini extension from surfaces/gemini-cli/..."
rsync -aL --delete \
  --exclude='.DS_Store' \
  --exclude='.git/' \
  --exclude='.github/' \
  --exclude='LICENSE' \
  "$SOURCE/" "./"

git add -A
if git diff --cached --quiet; then
  if [[ "$branch_exists" != "1" ]]; then
    echo "No changes to publish - release repo already up to date."
    exit 0
  fi
  echo "No file changes on existing $BRANCH; ensuring PR exists."
else
  # Use whatever git identity the caller has configured (the workflow sets
  # the boltz-mcpb-publisher[bot] identity globally; locally git uses your
  # user.name/email). Fall back to a sensible default if nothing is set.
  if ! git config user.name >/dev/null; then
    git config user.name "boltz-gemini-release"
    git config user.email "release@boltz.bio"
  fi
  git commit -q -m "sync: gemini extension v${VERSION} from boltz-api-skills@${SOURCE_SHA}"

  if [[ "$DRY_RUN" == "1" ]]; then
    echo
    echo "DRY_RUN=1 - staged commit at $WORK_DIR/repo on branch $BRANCH"
    echo "Diff summary:"
    git --no-pager show --stat HEAD
    trap - EXIT
    echo
    echo "Working dir preserved: $WORK_DIR/repo"
    exit 0
  fi

  echo "Pushing $BRANCH..."
  git push -q --force-with-lease -u origin "$BRANCH"
fi

PR_TITLE="Sync Gemini extension v${VERSION} (${SOURCE_SHA})"
PR_BODY="Automated sync from \`boltz-bio/boltz-api-skills@${SOURCE_SHA}\`.

This PR mirrors the Gemini CLI extension surface with symlinks dereferenced. The release repo keeps
\`.github/\` and LICENSE managed directly, while extension runtime files are
generated upstream from \`surfaces/gemini-cli/\` and shared \`core/\` skills."

if [[ "$DRY_RUN" == "1" ]]; then
  echo
  echo "DRY_RUN=1 - would open or update PR for $BRANCH"
  trap - EXIT
  echo
  echo "Working dir preserved: $WORK_DIR/repo"
  exit 0
fi

if gh pr view "$BRANCH" --repo "$RELEASE_REPO" >/dev/null 2>&1; then
  echo "PR already exists for $BRANCH - updated branch in place."
  gh pr view "$BRANCH" --repo "$RELEASE_REPO" --json url -q .url
else
  gh pr create \
    --repo "$RELEASE_REPO" \
    --base "$DEFAULT_BRANCH" \
    --head "$BRANCH" \
    --title "$PR_TITLE" \
    --body "$PR_BODY"
fi
