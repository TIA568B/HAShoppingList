#!/usr/bin/env bash
#
# Cut a HACS release for alexa_shopping_categoriser.
#
# Derives the version from the integration manifest (single source of truth),
# creates a matching annotated tag, pushes it to all remotes, and publishes a
# GitHub release so HACS can see it.
#
# Usage:
#   ./scripts/release.sh            # release the version in manifest.json
#   DRY_RUN=1 ./scripts/release.sh  # print what would happen, change nothing
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$REPO_ROOT/custom_components/alexa_shopping_categoriser/manifest.json"
GH_REPO="TIA568B/HAShoppingList"
BRANCH="main"

cd "$REPO_ROOT"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

run() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '\033[2m[dry-run] %s\033[0m\n' "$*"
  else
    eval "$@"
  fi
}

# --- Preconditions -----------------------------------------------------------

command -v gh >/dev/null 2>&1 || die "gh CLI not found. Install it (brew install gh) and run 'gh auth login'."
gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run 'gh auth login'."

[[ -f "$MANIFEST" ]] || die "manifest not found at $MANIFEST"

# Read version from manifest without extra dependencies.
VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST")"
[[ -n "$VERSION" ]] || die "could not read version from $MANIFEST"
TAG="v$VERSION"

log "Manifest version: $VERSION  ->  tag $TAG"

# Refuse to release from a dirty tree; the tag must reflect committed state.
if [[ -n "$(git status --porcelain)" ]]; then
  die "working tree is not clean. Commit or stash changes before releasing."
fi

# Must be on the release branch and in sync with its upstream.
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$CURRENT_BRANCH" == "$BRANCH" ]] || die "not on '$BRANCH' (on '$CURRENT_BRANCH')."

# Tag must not already exist locally or on GitHub.
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  die "tag $TAG already exists locally. Bump the version in the manifest first."
fi
if git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
  die "tag $TAG already exists on a remote. Bump the version in the manifest first."
fi
if gh release view "$TAG" --repo "$GH_REPO" >/dev/null 2>&1; then
  die "GitHub release $TAG already exists."
fi

# --- Release -----------------------------------------------------------------

log "Pushing $BRANCH (updates Bitbucket + GitHub via dual-push origin)"
run "git push origin $BRANCH"

log "Creating annotated tag $TAG"
run "git tag -a $TAG -m $TAG"

log "Pushing tag $TAG to all remotes"
run "git push origin $TAG"

log "Publishing GitHub release $TAG"
run "gh release create $TAG --repo $GH_REPO --title $TAG --generate-notes"

log "Done. HACS will pick up $TAG from $GH_REPO."
