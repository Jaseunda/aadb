# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
"""``aadb scrcpy`` — mirror & control a device with scrcpy, no typing."""

import argparse
import os
import shutil

import connect
from log import _c, add_common_args, make_logger
from registry import find as reg_find


def entry(argv: list) -> int:
    ap = argparse.ArgumentParser(
        prog="aadb scrcpy",
        description="Mirror & control a device with scrcpy (auto-connects if "
                    "it was offline). Extra flags pass through to scrcpy.")
    add_common_args(ap)
    a, extras = ap.parse_known_args(argv)
    log = make_logger(a)

    spec = a.device or a.serial
    extra = list(extras)
    if not spec and extra and extra[0] == "--":
        extra.pop(0)
    if not spec and extra:
        head = extra[0]
        if ":" in head or reg_find(head):
            spec = extra.pop(0)
    if extra and extra[0] == "--":
        extra.pop(0)

    scrcpy_bin = os.environ.get("SCRCPY") or shutil.which("scrcpy")
    if not scrcpy_bin:
        log("scr scrcpy not found — install it with 'brew install scrcpy'",
            "bad")
        return 1

    res = connect.ensure_online(log, spec=spec)
    if not res or not res[0]:
        return 1
    transport, label, ep = res

    print(f"\n  {_c('1;36', '::')} Mirroring {_c('1;33', label)} "
          f"{_c('2', '(' + ep + ')')}…\n", flush=True)
    os.execvp(scrcpy_bin, [scrcpy_bin, "-s", transport] + extra)
    return 127  # unreachable — exec replaced this process