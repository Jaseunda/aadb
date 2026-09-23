# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
"""Paths & base-directory helpers.

aadb keeps the registry of previously-connected devices and its log under
``~/.aadb`` (override with ``AADB_HOME`` — useful for testing).
"""

import os

_BASE = os.environ.get("AADB_HOME") or os.path.join(
    os.path.expanduser("~"), ".aadb")


def base_dir() -> str:
    return _BASE


def registry_path() -> str:
    return os.path.join(_BASE, "devices.json")


def log_path() -> str:
    return os.path.join(_BASE, "aadb.log")


def ensure_dirs() -> None:
    os.makedirs(_BASE, exist_ok=True)