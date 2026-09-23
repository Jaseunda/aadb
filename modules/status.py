# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
"""``aadb status`` / ``aadb devices`` — see what you have and what's online."""

import argparse

import connect
from log import _c, add_common_args, make_logger
from registry import devices, endpoint_of, find as reg_find


def _mark(state: str) -> str:
    if state == "device":
        return _c("1;32", "✓")
    if state == "offline":
        return _c("1;31", "✗")
    return _c("1;33", "!")


def status_entry(argv: list) -> int:
    ap = argparse.ArgumentParser(
        prog="aadb status",
        description="List remembered devices and their current adb state.")
    add_common_args(ap)
    a, _ = ap.parse_known_args(argv)
    log = make_logger(a)

    rc, out, _ = connect.run(["devices", "-l"])
    if rc == 127:
        log("adb adb not found on PATH (brew install android-platform-tools)",
            "bad")
        return 1
    conn = {ep: st for ep, st, _ in connect.adb_devices_l()}

    rows = []
    for d in devices():
        name = (d.get("name") or "?").strip()
        ep = endpoint_of(d) or "?"
        serial = d.get("serial") or ""
        model = d.get("model") or ""
        state = conn.get(ep, "offline")
        if state != "device" and d.get("serial"):
            for e, st in conn.items():
                if st == "device" and connect.resolve_serial(e) == d["serial"]:
                    state = "device"
                    break
        rows.append((name, ep, serial, model, state))

    unused = [ep for ep, st in conn.items() if st == "device"]
    unused = [ep for ep in unused if not any(ep == e for _, e, _, _, _ in rows)]

    print()
    if rows:
        cols = ["NAME", "ENDPOINT", "SERIAL", "MODEL"]
        widths = [len(c) for c in cols]
        for name, ep, serial, model, _ in rows:
            widths[0] = max(widths[0], len(name))
            widths[1] = max(widths[1], len(ep))
            widths[2] = max(widths[2], len(serial))
            widths[3] = max(widths[3], len(model))
        print(f"  {_c('2', cols[0].ljust(widths[0]))}  "
              f"{_c('2', cols[1].ljust(widths[1]))}  "
              f"{_c('2', cols[2].ljust(widths[2]))}  "
              f"{_c('2', cols[3].ljust(widths[3]))}  {_c('2', 'STATE')}")
        for name, ep, serial, model, state in rows:
            print(f"  {_c('1;36', name.ljust(widths[0]))}  "
                  f"{_c('2', ep.ljust(widths[1]))}  "
                  f"{ serial.ljust(widths[2]) if serial else '—'.ljust(widths[2]) }  "
                  f"{ model.ljust(widths[3]) if model else '—'.ljust(widths[3]) }  "
                  f"{_mark(state)} {_c('2', state)}")
        print()
    for ep in unused:
        serial = connect.resolve_serial(ep) or ""
        d = reg_find(serial) if serial else reg_find(ep)
        name = (d.get("name") or "?") if d else "—"
        print(f"  {_c('1;36', name.ljust(widths[0] if rows else 7))}  "
              f"{_c('2', ep)}  {_c('1;32', '✓')} {_c('2', 'device (not in registry)')}")

    online = sum(1 for *_rest, st in rows if st == "device") + len(unused)
    log(f"adb {len(rows)} remembered, {online} online now",
        "ok" if online else "dim")
    return 0


def devices_entry(argv: list) -> int:
    ap = argparse.ArgumentParser(
        prog="aadb devices",
        description="Show what adb sees right now, with names & models.")
    add_common_args(ap)
    a, _ = ap.parse_known_args(argv)
    log = make_logger(a)

    rows = connect.adb_devices_l()
    if not rows:
        log("adb no devices attached", "dim")
        return 0
    print()
    shown = []
    for ep, state, attrs in rows:
        serial = connect.resolve_serial(ep) if state == "device" else ""
        d = reg_find(serial) if serial else None
        name = (d.get("name") or "—") if d else (attrs.get("model") or "")
        model = attrs.get("model") or (d.get("model") if d else "")
        shown.append((ep, state, name or "—", model or ""))
    w_ep = max(len(e) for e, *_ in shown)
    w_n = max(len(n) for _, _, n, _ in shown)
    print(f"  {_c('2', 'ENDPOINT'.ljust(w_ep))}  "
          f"{_c('2', 'STATE'.ljust(10))}  {_c('2', 'NAME'.ljust(w_n))}  "
          f"{_c('2', 'MODEL')}")
    for ep, state, name, model in shown:
        print(f"  {_c('1;36', ep.ljust(w_ep))}  {state.ljust(10)}  "
              f"{_c('1;33', name.ljust(w_n))}  {_c('2', model)}")
    print()
    return 0