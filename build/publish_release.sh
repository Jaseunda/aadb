#!/bin/bash
# aadb publish — creates the GitHub release + v<VERSION> tag for the bundle.
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Uses the GitHub CLI (gh).  Title constraint is the same as ULS: the release
# title must be exactly ``v<VERSION>`` (matching the tag) — no extra words.
#
# Usage: bash build/publish_release.sh   (normally via `make publish`)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE_DIR="$REPO_ROOT/releases"
VERSION="$(cat "$REPO_ROOT/build/version" 2>/dev/null || echo 0.0.0)"
REPO="${AADB_REPO:-Jaseunda/aadb}"
ZIP="$RELEASE_DIR/aadb-$VERSION.zip"

[ -f "$ZIP" ] || { echo "  ✗ No bundle — run 'make release' first."; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "  ✗ gh (GitHub CLI) not found — install it."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "  ✗ not authenticated with gh — run 'gh auth login'."; exit 1; }

if gh release view "v$VERSION" --repo "$REPO" >/dev/null 2>&1; then
    echo "  ✗ Release v$VERSION already exists — bump _VERSION in aadb.py or delete it."
    exit 1
fi

NOTE="$(git -C "$REPO_ROOT" log -1 --format='%s' 2>/dev/null || echo 'aadb release')"
gh release create "v$VERSION" "$ZIP" "$RELEASE_DIR/SHA256SUMS" \
    --repo "$REPO" --title "v$VERSION" --notes "$NOTE"

echo "  ✓ Published aadb v$VERSION → https://github.com/$REPO/releases/tag/v$VERSION"