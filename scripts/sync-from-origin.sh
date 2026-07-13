#!/usr/bin/env bash
# Sync this working tree with origin BEFORE starting any commit work.
#
# Two-machine workflow (MacBook Air + Mac Studio, git-synced). The other machine
# may have pushed commits this one hasn't seen. Run this before building on top
# of anything.
#
# Usage:  ./scripts/sync-from-origin.sh
#         (run from the repo root, or it will cd there itself)
#
# Safe: never force-pushes, never switches accounts, never auto-resolves real
# conflicts (it stops and reports instead). Stashes .DS_Store noise if it blocks.
set -euo pipefail

# Locate the repo root (this script lives in scripts/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

BRANCH="cursor/founding-state-claimdesk247"
REMOTE="origin"

echo "=== two-machine sync: $(basename "$(pwd)") @ $(hostname -s) ==="
echo ""

# 1. Identity guard — never push with the wrong account on a 3-business Mac.
echo "--- active gh account ---"
GH_USER="$(gh api /user --jq '.login' 2>/dev/null || echo "NOT-LOGGED-IN")"
echo "  $GH_USER"
if [ "$GH_USER" != "CTO-goldmanglobal" ]; then
  echo "  ⚠️  Active gh user is '$GH_USER', not CTO-goldmanglobal."
  echo "     This Mac runs 3 businesses. Stopping — do NOT push or switch accounts"
  echo "     autonomously. Ask the user to run: gh auth switch -u CTO-goldmanglobal"
  exit 1
fi
echo ""

# 2. Fetch remote state.
echo "--- fetching $REMOTE ---"
git fetch "$REMOTE" 2>&1 | sed 's/^/  /' | head -8 || true
echo ""

LOCAL="$(git rev-parse HEAD)"
REMOTE_REF="$(git rev-parse "$REMOTE/$BRANCH" 2>/dev/null || echo "")"
BASE="$(git merge-base "$LOCAL" "${REMOTE_REF:-HEAD}" 2>/dev/null || echo "$LOCAL")"

# 3. Report divergence.
echo "--- divergence ---"
if [ "$LOCAL" = "$REMOTE_REF" ]; then
  echo "  up to date — local matches origin/$BRANCH"
  echo "  HEAD: $(git log -1 --format='%h %s')"
  exit 0
elif [ "$LOCAL" = "$BASE" ]; then
  echo "  local is BEHIND origin by $(git rev-list --count "$LOCAL..$REMOTE_REF") commit(s)."
elif [ "$REMOTE_REF" = "$BASE" ]; then
  echo "  local is AHEAD of origin by $(git rev-list --count "$REMOTE_REF..$LOCAL") unpushed commit(s)."
  echo "  (nothing to pull — consider pushing your local work)"
  exit 0
else
  echo "  ⚠️  DIVERGED. Local and origin have divergent commits."
  echo "  local-only :"
  git log --oneline "$REMOTE_REF..$LOCAL" | sed 's/^/    /' | head -10
  echo "  origin-only:"
  git log --oneline "$LOCAL..$REMOTE_REF" | sed 's/^/    /' | head -10
  echo ""
  echo "  Stopping. Do NOT auto-resolve. Show the user this divergence."
  exit 1
fi
echo ""

# 4. Stash noise (.DS_Store) if it blocks the pull.
STASHED=0
if ! git diff --quiet -- .DS_Store 2>/dev/null; then
  echo "--- stashing .DS_Store noise ---"
  git stash push -m "sync: ds-store noise" -- .DS_Store >/dev/null 2>&1
  STASHED=1
  echo "  stashed"
fi

# 5. Pull with rebase (linear history).
echo "--- pulling (rebase) ---"
git pull --rebase "$REMOTE" "$BRANCH" 2>&1 | sed 's/^/  /' | tail -10
echo ""

# 6. Sync submodule.
echo "--- submodule sync ---"
git submodule update --recursive 2>&1 | sed 's/^/  /' | head -3 || true
echo ""

# 7. Drop the stash if we made one.
if [ "$STASHED" = "1" ]; then
  echo "--- dropping .DS_Store stash ---"
  git stash drop >/dev/null 2>&1 && echo "  dropped" || echo "  (stash already gone)"
fi

# 8. Report new state.
echo "--- synced ==="
echo "  HEAD: $(git log -1 --format='%h %s')"
echo "  new commits since last sync:"
git log --oneline "$LOCAL..HEAD" 2>/dev/null | sed 's/^/    /' | head -10
echo ""
echo "  next: run the health check —"
echo "    cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py"
echo "    cd ../stage-2.5 && PYTHONPATH=. python3 tests/run_acceptance.py"
echo "    cd .. && python3 stage-4/scripts/sign_rule_trees.py --verify"
