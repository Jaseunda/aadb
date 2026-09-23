#!/bin/bash
# aadb release bundler — assembles the distributable bundle in releases/.
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Produces, in releases/:
#     aadb-<VERSION>.zip   (built binary + full source + README + LICENSE
#                           + install.sh + Makefile + VERSION)
#     SHA256SUMS
#
# Usage: bash build/make_release.sh   (normally via `make release`)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$REPO_ROOT/build/bin"
RELEASE_DIR="$REPO_ROOT/releases"
VERSION="$(cat "$REPO_ROOT/build/version" 2>/dev/null || echo 0.0.0)"
DATE="$(date +%Y-%m-%d)"

if [ ! -x "$BIN_DIR/aadb" ]; then
    echo "  ✗ No built binary at $BIN_DIR/aadb — run 'make build' first."
    exit 1
fi

mkdir -p "$RELEASE_DIR"

# --- Assemble the versioned staging folder ---------------------------------
STAGE="$RELEASE_DIR/aadb-$VERSION"
rm -rf "$STAGE"
mkdir -p "$STAGE/modules"

cp "$BIN_DIR/aadb"            "$STAGE/aadb";          chmod 755 "$STAGE/aadb"
cp "$REPO_ROOT/aadb.py"       "$STAGE/aadb.py"
cp "$REPO_ROOT"/modules/*.py  "$STAGE/modules/"
cp "$REPO_ROOT/README.md"     "$STAGE/README.md"
cp "$REPO_ROOT/CHANGELOG.md"  "$STAGE/CHANGELOG.md"
cp "$REPO_ROOT/LICENSE"       "$STAGE/LICENSE"
cp "$REPO_ROOT/install.sh"    "$STAGE/install.sh";    chmod 755 "$STAGE/install.sh"
cp "$REPO_ROOT/Makefile"      "$STAGE/Makefile"
printf 'aadb v%s — %s\n' "$VERSION" "$DATE" > "$STAGE/VERSION"

# --- Zip + checksum ---------------------------------------------------------
ZIP="$RELEASE_DIR/aadb-$VERSION.zip"
rm -f "$ZIP"
(cd "$RELEASE_DIR" && zip -qr "$(basename "$ZIP")" "aadb-$VERSION")
(cd "$RELEASE_DIR" && shasum -a 256 "$(basename "$ZIP")" > SHA256SUMS)
rm -rf "$STAGE"

echo ""
echo "  ✓ Release aadb v${VERSION} → ${RELEASE_DIR}/"
echo "     $(ls -1 "$RELEASE_DIR" | tr '\n' ' ')"
echo ""
echo "  Users unzip aadb-$VERSION.zip and run ./install.sh, or drop the"
echo "  'aadb' executable anywhere on PATH.  Publish via:  make publish"