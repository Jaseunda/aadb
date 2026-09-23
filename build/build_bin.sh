#!/bin/bash
# aadb build — assembles a self-contained `aadb` executable.
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Produces build/bin/aadb as a Python zipapp with a `#!/usr/bin/env python3`
# shebang — one executable file, no install, no dependencies beyond python3.
# The modules are flattened into the archive root so the flat imports
# (``import log``, ``import registry``, …) resolve from inside the zip.
#
# Version is read from _VERSION in aadb.py (override with $AADB_VERSION) and
# stamped into build/version for make_release / publish.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"
BIN_DIR="$BUILD_DIR/bin"
PY="${AADB_PY:-python3}"

VERSION="${AADB_VERSION:-$(sed -n 's/^_VERSION[[:space:]]*=[[:space:]]*"\(.*\)"/\1/p' "$REPO_ROOT/aadb.py" | head -1)}"
: "${VERSION:?could not read _VERSION from aadb.py}"

mkdir -p "$BIN_DIR"
printf '\033[1;36mBuilding aadb v%s\033[0m → %s/aadb\n' "$VERSION" "$BIN_DIR"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

APP="$TMP/app"
mkdir -p "$APP"
cp "$REPO_ROOT/aadb.py"   "$APP/aadb.py"
cp "$REPO_ROOT"/modules/*.py "$APP/"

# Explicit entry point so exit codes propagate — zipapp's generated
# __main__.py would call main() and silently drop its return value.
cat > "$APP/__main__.py" <<'PY'
import sys
from aadb import main
sys.exit(main())
PY

"$PY" -m zipapp "$APP" -p "/usr/bin/env python3" \
    -o "$BIN_DIR/aadb"
chmod 755 "$BIN_DIR/aadb"
if [[ "$(uname -s)" == "Darwin" ]]; then
    # Ad-hoc codesign so macOS (esp. Apple Silicon) runs the fresh file.
    codesign --force --sign - "$BIN_DIR/aadb" >/dev/null 2>&1 || true
fi

echo "$VERSION" > "$BUILD_DIR/version"
printf '\033[1;32m✓ Built aadb v%s\033[0m → %s/aadb\n' "$VERSION" "$BIN_DIR"