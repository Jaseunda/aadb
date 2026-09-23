#!/bin/sh
# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copies the tool into ~/.aadb and links it into PATH.
#
# Prefers the self-contained build (build/bin/aadb) when present; otherwise
# installs the plain source tree (aadb.py + modules/).  The device registry
# (which adb devices you've connected before) lives in ~/.aadb/devices.json.
set -e

AADB_HOME="${AADB_HOME:-$HOME/.aadb}"
BIN_DIR="${AADB_BIN_DIR:-$HOME/.local/bin}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$AADB_HOME/modules" "$BIN_DIR"

if [ -x "$SRC_DIR/build/bin/aadb" ]; then
    cp "$SRC_DIR/build/bin/aadb" "$AADB_HOME/aadb"     # self-contained zipapp
else
    cp "$SRC_DIR/aadb.py" "$AADB_HOME/aadb"
    cp "$SRC_DIR"/modules/*.py "$AADB_HOME/modules/"
fi
chmod 755 "$AADB_HOME/aadb"
ln -sf "$AADB_HOME/aadb" "$BIN_DIR/aadb"

echo "✓ aadb installed: $AADB_HOME/aadb"
echo "  linked as: $BIN_DIR/aadb"
echo "  device registry: $AADB_HOME/devices.json"
echo "  (ensure $BIN_DIR is on your PATH — e.g. export PATH=\"$BIN_DIR:\$PATH\")"