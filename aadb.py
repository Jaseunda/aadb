#!/usr/bin/env python3
# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""aadb — Advanced ADB: remember your wireless adb devices.

``aadb <command> [args...]`` routes to a command module. The philosophy is
the same as the ULS host CLI: hide the raw ``adb connect`` + ``adb shell``
incantations behind small named commands, keep the device registry
(``~/.aadb/devices.json``) as the memory of devices that connected before,
and log in the dmesg-style design system (see modules/log.py).
"""

import os
import sys

_me = os.path.dirname(os.path.realpath(__file__))
for _p in (_me, os.path.join(_me, "modules")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from log import _c  # noqa: E402

_VERSION = "0.1.2"


def _banner() -> str:
    art = [
        ("35", "   █████╗  █████╗ ██████╗ ██████╗ "),
        ("35", "  ██╔══██╗██╔══██╗██╔══██╗██╔══██╗"),
        ("36", "  ███████║███████║██║  ██║██████╔╝"),
        ("36", "  ██╔══██║██╔══██║██║  ██║██╔══██╗"),
        ("34", "  ██║  ██║██║  ██║██████╔╝██████╔╝"),
        ("34", "  ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═════╝ "),
    ]
    lines = [_c(f"1;{c}", line) for c, line in art]
    lines += ["",
              _c("1;32", f"  aadb v{_VERSION} — Advanced ADB"),
              _c("2", "  Remember your wireless adb devices. Connect, shell, scrcpy —"),
              _c("2", "  no 'adb connect' typing every time."),
              ""]
    return "\n".join(lines)


_CMDS = [
    ("status",   "list remembered devices & their current state"),
    ("devices",  "show what adb sees right now (with names & models)"),
    ("scan",     "reconnect every remembered device, discover mDNS"),
    ("connect",  "bring a remembered device online (adb connect)"),
    ("shell",    "open an adb shell on a device (auto-connect)"),
    ("scrcpy",   "mirror & control a device via scrcpy (auto-connect)"),
    ("add",      "remember a new device:  aadb add NAME HOST[:PORT]"),
    ("forget",   "drop a device from the registry"),
]
_CMDS_STR = "|".join(c for c, _ in _CMDS)

HELP = "\n".join([
    _banner(),
    _c("1;36", "usage:") + f" aadb <{_c('1', _CMDS_STR)}> [args ...]",
    "",
] + [
    f"  {_c('1;33', c.ljust(12))}{d}" for c, d in _CMDS
] + [
    "",
    _c("2", "Options are passed straight through to the command, e.g.:"),
    f"  {_c('1;33', 'aadb shell s24')}",
    f"  {_c('1;33', 'aadb shell --device s24 uname -a')}",
    f"  {_c('1;33', 'aadb scrcpy --device tab')}",
    f"  {_c('1;33', 'aadb scan --wall')}",
    "",
])


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(HELP)
        return 0 if argv else 2
    if argv[0] in ("-V", "--version", "version"):
        print(f"aadb v{_VERSION}")
        return 0

    cmd = argv.pop(0)
    if cmd in ("ls", "list"):
        cmd = "devices"
    if cmd == "sh":
        cmd = "shell"
    if cmd in ("sc", "mirror"):
        cmd = "scrcpy"

    if cmd in ("status", "devices"):
        import status
        return status.status_entry(argv) if cmd == "status" \
            else status.devices_entry(argv)
    if cmd in ("scan", "connect"):
        import connect
        return connect.entry(argv, scan_mode=(cmd == "scan"))
    if cmd == "add":
        import connect
        return connect.add_entry(argv)
    if cmd == "forget":
        import connect
        return connect.forget_entry(argv)
    if cmd == "shell":
        import shell
        return shell.entry(argv)
    if cmd == "scrcpy":
        import scrcpy
        return scrcpy.entry(argv)

    print(f"aadb: unknown command '{cmd}'. "
          f"Type {_c('1;33', 'aadb')} to see what you can do.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())