#!/usr/bin/env bash
# Play the latest pyRL from GitHub without touching your local branch.
#
# Nothing is checked out or merged: `git fetch` only moves remote-tracking
# refs, then the pyRL/ tree is exported to a temp dir, played, and deleted.
# Your branch, working tree, and untracked files are never touched.
#
# Usage: ./play-pyrl.sh [branch]   (defaults to pyRL-dev)
set -euo pipefail

BRANCH="${1:-pyRL-dev}"

# Resolve the repo relative to this script (script lives in <repo>/pyRL).
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$SCRIPT_DIR/.." && pwd)

# Fresh temp dir every run — cleared up front, and again on exit.
TMP="${TMPDIR:-/tmp}/pyrl-play"
rm -rf "$TMP"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

# Grab the newest commits (updates origin/* refs only — not your branch).
git -C "$REPO" fetch origin "$BRANCH"

# Export just the game into the temp dir.
git -C "$REPO" archive "origin/$BRANCH" pyRL | tar -x -C "$TMP"

# Play. The temp dir is removed automatically when the game exits.
cd "$TMP/pyRL"
python3 main.py
