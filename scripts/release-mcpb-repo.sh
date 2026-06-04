#!/usr/bin/env bash
# Mirror plugins/boltz-mcpb/ into the public boltz-mcpb release repo as a PR.
#
# The public repo is the URL referenced in the MCPB submission and in
# manifest.json's repository.url. Development happens here in the private
# monorepo; releases land in the public repo through a reviewable PR.
#
# Usage:
#   scripts/release-mcpb-repo.sh                 # version read from manifest.json
#   RELEASE_REPO=org/name scripts/release-mcpb-repo.sh
#   DRY_RUN=1 scripts/release-mcpb-repo.sh       # stage locally, no push/PR
#
# Requirements: git, rsync, jq, gh (authenticated).
#
# What gets mirrored (runtime + contributor assets):
#   manifest.json, package.json, package-lock.json, icon.png, server/, guidance/, test/, examples/
#
# What is left untouched in the release repo (managed there directly):
#   README.md, LICENSE, .github/, .gitignore, .mcpbignore

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$REPO_ROOT/plugins/boltz-mcpb"

RELEASE_REPO="${RELEASE_REPO:-boltz-bio/boltz-mcpb}"
DRY_RUN="${DRY_RUN:-0}"

for cmd in git rsync jq gh; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing required command: $cmd" >&2; exit 1; }
done

VERSION="$(jq -r .version "$SOURCE/manifest.json")"
SOURCE_SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
BRANCH="sync/v${VERSION}-${SOURCE_SHA}"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/boltz-mcpb-release.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

# Register gh as git's credential helper so the later `git push` can
# authenticate using GH_TOKEN. Locally this is usually a no-op (your
# system git creds work); in CI it's required.
gh auth setup-git >/dev/null

echo "Cloning $RELEASE_REPO..."
gh repo clone "$RELEASE_REPO" "$WORK_DIR/repo" -- --quiet

cd "$WORK_DIR/repo"
DEFAULT_BRANCH="$(gh repo view "$RELEASE_REPO" --json defaultBranchRef -q .defaultBranchRef.name)"
git checkout -q "$DEFAULT_BRANCH"
git checkout -q -B "$BRANCH"

echo "Mirroring runtime assets from plugins/boltz-mcpb/..."
# Sync only the assets we own; preserve repo-local README/LICENSE/.github/etc.
for dir in server guidance; do
  rsync -aL --delete \
    --exclude='.DS_Store' \
    --exclude='node_modules' \
    --exclude='*.mcpb' \
    "$SOURCE/$dir/" "./$dir/"
done

for f in manifest.json package.json package-lock.json icon.png; do
  cp "$SOURCE/$f" "./$f"
done

# test/ and examples/ are useful to contributors; mirror but don't fail if absent.
for dir in test examples; do
  if [[ -d "$SOURCE/$dir" ]]; then
    rsync -aL --delete \
      --exclude='.DS_Store' \
      "$SOURCE/$dir/" "./$dir/"
  fi
done

git add -A
if git diff --cached --quiet; then
  echo "No changes to publish — release repo already up to date."
  exit 0
fi
# Use whatever git identity the caller has configured (the workflow sets
# the boltz-mcpb-publisher[bot] identity globally; locally git uses your
# user.name/email). Fall back to a sensible default if nothing is set.
if ! git config user.name >/dev/null; then
  git config user.name "boltz-mcpb-release"
  git config user.email "release@boltz.bio"
fi
git commit -q -m "sync: mcpb v${VERSION} from boltz-api-skills@${SOURCE_SHA}"

if [[ "$DRY_RUN" == "1" ]]; then
  echo
  echo "DRY_RUN=1 — staged commit at $WORK_DIR/repo on branch $BRANCH"
  echo "Diff summary:"
  git --no-pager show --stat HEAD
  trap - EXIT
  echo
  echo "Working dir preserved: $WORK_DIR/repo"
  exit 0
fi

echo "Pushing $BRANCH..."
git push -q -u origin "$BRANCH"

PR_TITLE="Sync mcpb v${VERSION} (${SOURCE_SHA})"
PR_BODY="Automated sync from \`boltz-bio/boltz-api-skills@${SOURCE_SHA}\`.

This PR mirrors the runtime assets of the MCPB extension. README, LICENSE,
and \`.github/\` are managed directly in this repo and are not touched.

Built bundle for this version is produced by the upstream monorepo and
attached to the GitHub release after merge."

if gh pr view "$BRANCH" --repo "$RELEASE_REPO" >/dev/null 2>&1; then
  echo "PR already exists for $BRANCH — updated branch in place."
  gh pr view "$BRANCH" --repo "$RELEASE_REPO" --json url -q .url
else
  gh pr create \
    --repo "$RELEASE_REPO" \
    --base "$DEFAULT_BRANCH" \
    --head "$BRANCH" \
    --title "$PR_TITLE" \
    --body "$PR_BODY"
fi
