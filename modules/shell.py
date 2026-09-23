# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
"""``aadb shell`` — jump into an adb shell without typing 'adb connect'."""

import argparse
import os
import shlex

import connect
from log import _c, add_common_args, make_logger
from registry import find as reg_find


def entry(argv: list) -> int:
    ap = argparse.ArgumentParser(
        prog="aadb shell",
        description="Open an adb shell on a device (auto-connects if it was "
                    "offline). Target auto-picks when only one device is "
                    "around.")
    add_common_args(ap)
    a, extras = ap.parse_known_args(argv)
    log = make_logger(a)

    spec = a.device or a.serial
    cmd = list(extras)
    if not spec and cmd and cmd[0] == "--":
        cmd.pop(0)
    if not spec and cmd:
        head = cmd[0]
        # 'aadb shell s24 cmd...' — a leading remembered name/endpoint is the
        # target; anything else is the command for the auto-picked device.
        if ":" in head or reg_find(head):
            spec = cmd.pop(0)
    if cmd and cmd[0] == "--":
        cmd.pop(0)

    transport, label, ep = connect.ensure_online(log, spec=spec)
    if not transport:
        return 1

    if not cmd:
        print(f"\n  {_c('1;36', '::')} Shell on {_c('1;33', label)} "
              f"{_c('2', '(' + ep + ')')} — type 'exit' to leave.\n",
              flush=True)
        os.execvp(connect._ADB, [connect._ADB, "-s", transport, "shell"])

    # Same quoting disposition as the ULS CLI: quote every piece on the Mac
    # side so shell metacharacters survive intact to the device shell.
    remote = " ".join(shlex.quote(c) for c in cmd)
    print(f"\n  {_c('1;36', '::')} {_c('1;33', label)}: $ {_c('1', remote)}\n",
          flush=True)
    os.execvp(connect._ADB, [connect._ADB, "-s", transport, "shell", "-t", remote])
    return 127  # unreachable — exec replaced this process