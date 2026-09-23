# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
"""ADB discovery, reconnection and target selection.

The job of this module is the whole point of aadb: instead of typing
``adb connect 192.168.x.x:5555`` every session, aadb remembers devices in the
registry and re-establishes their wireless connection on demand (or on
``scan``). Device selection auto-picks the single online device and asks
interactively when several are around — the same UX as the ULS CLI.
"""

import argparse
import os
import re
import subprocess
import sys

from config import log_path
from log import _c, add_common_args, make_logger
from registry import (devices, endpoint_of, find as reg_find, new_record,
                      remove as reg_remove, touch as reg_touch, upsert)

_ADB = os.environ.get("AADB_ADB") or "adb"
DEFAULT_PORT = 5555


# ---------------------------------------------------------------- low level

def run(args: list, timeout: int = 10):
    """Run an adb subcommand, returning (rc, stdout, stderr) strings."""
    try:
        p = subprocess.run([_ADB] + args, capture_output=True, text=True,
                           timeout=timeout)
    except FileNotFoundError:
        return 127, "", "adb not found on PATH (brew install android-platform-tools)"
    except subprocess.TimeoutExpired:
        return 124, "", "command timed out"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def adb_devices_l(timeout: int = 8) -> list:
    """Parse ``adb devices -l`` -> [(endpoint, state, attrs), ...]."""
    rc, out, _ = run(["devices", "-l"], timeout=timeout)
    rows = []
    if rc != 0:
        return rows
    for ln in out.splitlines():
        parts = ln.split()
        if len(parts) < 2 or parts[0] == "List":
            continue
        endpoint, state = parts[0], parts[1]
        attrs = {}
        for tok in parts[2:]:
            if ":" in tok:
                k, _, v = tok.partition(":")
                attrs[k] = v
        rows.append((endpoint, state, attrs))
    return rows


def connected_endpoints(timeout: int = 8) -> list:
    """Endpoints currently in the authorized ``device`` state."""
    return [ep for ep, state, _ in adb_devices_l(timeout=timeout)
            if state == "device"]


def resolve_serial(endpoint: str, timeout: int = 8):
    """Hardware serial for an endpoint (getprop, with mDNS-name fallback)."""
    rc, hw, _ = run(["-s", endpoint, "shell", "getprop ro.serialno"],
                    timeout=timeout)
    hw = hw.strip()
    if hw:
        return hw
    m = re.search(r"adb-([^-]+)-", endpoint)  # adb-<serial>-<nonce>._adb-tls-connect._tcp
    return m.group(1) if m else None


def resolve_model(endpoint: str, timeout: int = 8) -> str:
    rc, model, _ = run(["-s", endpoint, "shell", "getprop ro.product.model"],
                       timeout=timeout)
    return model.strip() or ""


def connect_endpoint(host: str, port: int = DEFAULT_PORT, timeout: int = 15):
    """``adb connect host:port`` -> (ok, display_endpoint, detail)."""
    ep = f"{host}:{int(port)}"
    rc, out, err = run(["connect", ep], timeout=timeout)
    ok = rc == 0 and "connected" in out
    return ok, ep, (out or err or "")


def discover_mdns(timeout: int = 8) -> list:
    """Best-effort: wireless-debugging services advertising on the LAN."""
    rc, out, _ = run(["mdns", "services"], timeout=timeout)
    if rc != 0 or not out:
        return []
    return re.findall(r"\b([A-Za-z0-9._-]+\._adb-tls-connect\._tcp)\b", out)


def _serial_map(endpoints: list) -> dict:
    """{hardware serial: representative endpoint} for a set of endpoints."""
    mapping = {}
    for ep in endpoints:
        s = resolve_serial(ep)
        if s:
            mapping.setdefault(s, ep)
    return mapping


def _is_online(dev: dict, conn: list) -> bool:
    ep = endpoint_of(dev)
    if ep and ep in conn:
        return True
    serial = dev.get("serial")
    if serial:
        return any(resolve_serial(e) == serial for e in conn)
    return False


def _adopt(host: str, port: int, serial: str, model: str) -> None:
    """Learn a reachable serial: update its endpoint if already remembered."""
    if not serial:
        return
    for d in devices():
        if d.get("serial") == serial:
            old = endpoint_of(d)
            new = f"{host}:{int(port)}"
            if old and new != old:
                d["host"] = host
                d["port"] = int(port)
            if model:
                d["model"] = model
            reg_touch(d, serial=serial, model=model or None)
            return
    # Brand-new device seen on the wire — remember it (no name yet).
    upsert(new_record(serial, host, int(port), serial=serial, model=model))


# ------------------------------------------------------------ scan

def scan_registry(log, discover: bool = True):
    """Reconnect every remembered device. Returns (ok_count, total)."""
    conn = connected_endpoints()
    ok_count = total = 0
    for d in devices():
        ep = endpoint_of(d)
        host = d.get("host") or ""
        port = int(d.get("port") or DEFAULT_PORT)
        name = d.get("name") or ep or "?"
        if not ep or not host:
            continue
        total += 1
        if _is_online(d, conn):
            reg_touch(d, serial=d.get("serial") or resolve_serial(ep))
            log(f"adb {name}: online ({_c('2', ep)})", "ok")
            ok_count += 1
            continue
        ok, ep, detail = connect_endpoint(host, port)
        if ok:
            serial = resolve_serial(ep) or d.get("serial")
            model = resolve_model(ep) or d.get("model")
            reg_touch(d, serial=serial, model=model)
            log(f"adb {name}: reconnected ({_c('2', ep)})", "ok")
            ok_count += 1
        else:
            log(f"adb {name}: {detail.strip() or 'unreachable'} ({_c('2', ep)})",
                "bad")
    if discover:
        services = discover_mdns()
        if services:
            log(f"net {len(services)} wireless device(s) advertising on the LAN:",
                "dim")
            for s in services:
                log(f"net   {s}", "dim")
    return ok_count, total


# ------------------------------------------------------------ selection

def _online_ready() -> list:
    """[(device_record, endpoint)] for remembered devices currently online."""
    conn = connected_endpoints()
    on = _serial_map(conn)
    result, seen = [], set()
    for d in devices():
        serial = d.get("serial") or ""
        ep = endpoint_of(d)
        match = on.get(serial) if serial else None
        if match and match not in seen:
            result.append((d, match))
            seen.add(match)
            continue
        if ep and ep in conn and ep not in seen:
            result.append((d, ep))
            seen.add(ep)
    return result


def _picker(log, options: list, prompt: str):
    """Numbered picker (same shape as the ULS device picker).
    ``options`` = [(key, display_string)]. Returns the chosen key."""
    print()
    for i, (_, display) in enumerate(options, 1):
        print(f"    {i}) {display}")
    while True:
        try:
            raw = input(f"\n  {_c('1;36', '::')} {prompt} "
                        f"[1-{len(options)}, Enter=1]: ").strip()
        except EOFError:
            raw = ""
        if not raw:
            return options[0][0]
        try:
            idx = int(raw)
        except ValueError:
            print(f"\n  {_c('1;31', '✗')} enter a number (1-{len(options)})")
            continue
        if 1 <= idx <= len(options):
            return options[idx - 1][0]
        print(f"\n  {_c('1;31', '✗')} pick 1-{len(options)}")


def _target_explicit(log, spec: str):
    """Connect/verify a specific device.
    Returns (transport, label, endpoint) where transport is the token
    ``adb -s`` accepts (endpoint/mDNS name for wireless, serial for USB).
    All three are None when nothing could be reached."""
    dev = reg_find(spec)
    conn = connected_endpoints()
    if dev:
        ep = endpoint_of(dev)
        host = dev.get("host") or ""
        port = int(dev.get("port") or DEFAULT_PORT)
        label = (dev.get("name") or "").strip() or spec
        if ep and ep in conn:
            serial = resolve_serial(ep) or dev.get("serial") or ""
            model = resolve_model(ep) or dev.get("model") or ""
            reg_touch(dev, serial=serial, model=model or None)
            log(f"adb {label}: online ({_c('2', ep)})", "ok")
            return ep, label, ep
        serial = dev.get("serial") or ""
        if serial:
            for e in conn:
                if resolve_serial(e) == serial:
                    model = resolve_model(e) or dev.get("model") or ""
                    reg_touch(dev, serial=serial, model=model or None)
                    log(f"adb {label}: online via {_c('2', e)}", "ok")
                    return e, label, e
        ok, ep, detail = connect_endpoint(host, port)
        if ok:
            serial = resolve_serial(ep) or serial
            model = resolve_model(ep) or dev.get("model") or ""
            reg_touch(dev, serial=serial, model=model or None)
            log(f"adb {label}: reconnected ({_c('2', ep)})", "ok")
            return ep, label, ep
        log(f"adb {label}: {detail.strip() or 'could not connect'} "
            f"({_c('2', ep)})", "bad")
        return None, None, None
    if ":" in spec:
        host, _, port = spec.partition(":")
        port = int(port) if port.isdigit() else DEFAULT_PORT
        ok, ep, detail = connect_endpoint(host, port)
        if not ok:
            log(f"adb {spec}: {detail.strip() or 'could not connect'}", "bad")
            return None, None, None
        serial = resolve_serial(ep)
        model = resolve_model(ep)
        log(f"adb {spec}: connected ({_c('2', ep)})", "ok")
        if serial:
            _adopt(host, port, serial, model)
        return ep, spec, ep
    # A raw serial of something already attached (e.g. USB) — adb -s accepts it.
    for e in conn:
        if resolve_serial(e) == spec:
            return e, spec, e
    log(f"adb {spec}: not a remembered device, endpoint, or connected serial",
        "bad")
    return None, None, None


def _target_auto(log, prompt: str):
    """No explicit target: auto-pick, reconnect as needed, else ask.
    Returns (transport, label, endpoint) or None."""
    def use(d, ep):
        serial = d.get("serial") or resolve_serial(ep) or ep
        label = (d.get("name") or "").strip() or ep
        reg_touch(d, serial=serial)
        return ep, label, ep

    def finish(ready):
        if len(ready) == 1:
            return use(*ready[0])
        if len(ready) > 1:
            options = [(d.get("name") or ep,
                        f"{_c('1;36', d.get('name') or ep)}  "
                        f"{_c('2', endpoint_of(d) or '?')}")]
            for d, ep in ready:
                pick = _picker(log, options, f"{prompt}")
                for d2, ep2 in ready:
                    if (d2.get("name") or ep2) == pick:
                        return use(d2, ep2)
        return None, None, None

    ready = _online_ready()
    if ready:
        return finish(ready)
    log("adb no remembered device is online — reconnecting "
        "your saved devices…", "warn")
    scan_registry(log, discover=False)
    ready = _online_ready()
    if ready:
        return finish(ready)
    remembered = devices()
    if remembered:
        log(f"sys {len(remembered)} remembered device(s), none reachable yet",
            "bad")
        log("sys is your phone on the same Wi-Fi, with wireless debugging on?",
            "dim")
        options = [(d.get("name") or ep,
                    f"{_c('1;36', d.get('name') or ep)}  "
                    f"{_c('2', endpoint_of(d) or '?')}  {_c('1;31', 'offline')}")
                   for d in remembered if (ep := endpoint_of(d))]
        if options:
            pick = _picker(log, options, "force a connection attempt on")
            return _target_explicit(log, pick)
        return None, None, None
    log("sys no remembered devices — run 'aadb add NAME HOST:PORT' first",
        "dim")
    live = connected_endpoints()
    if live:
        hint = live[0]
        log(f"net {len(live)} device(s) are online but not remembered — "
            f"e.g. 'aadb add NAME {hint}'", "dim")
    return None, None, None


def ensure_online(log, spec: str = None, prompt: str = "connect to"):
    """Pick a device and guarantee it is connected.
    Returns (transport, label, endpoint) — all None when nothing was
    reachable, so callers can unpack unconditionally."""
    if spec:
        return _target_explicit(log, spec)
    return _target_auto(log, prompt)


# ------------------------------------------------------------ commands

def entry(argv: list, scan_mode: bool = False) -> int:
    ap = argparse.ArgumentParser(
        prog="aadb connect",
        description="Connect one remembered device, or reconnect everything "
                    "you have saved.")
    add_common_args(ap)
    a, extras = ap.parse_known_args(argv)
    log = make_logger(a)
    spec = a.device or a.serial or (extras[0] if extras else None)

    if scan_mode and spec:
        log("sys 'scan' reconnects every remembered device "
            "(use 'aadb connect NAME' for a single one).", "dim")

    if spec and not scan_mode:
        res = ensure_online(log, spec=spec)
        return 0 if res and res[0] else 1

    ok, total = scan_registry(log, discover=True)
    log(f"sys reconnect: {ok}/{total} device(s) online now",
        "ok" if ok else "bad")
    return 0


def add_entry(argv: list) -> int:
    ap = argparse.ArgumentParser(
        prog="aadb add",
        description="Remember a wireless device so aadb can reconnect it "
                    "without you typing 'adb connect' again.")
    add_common_args(ap)
    ap.add_argument("name", help="short name for this device (e.g. phone, tab)")
    ap.add_argument("endpoint", help="HOST[:PORT] — default port 5555")
    ap.add_argument("--note", default="", help="optional annotation")
    a = ap.parse_args(argv)
    log = make_logger(a)

    host, _, port = a.endpoint.rpartition(":")
    if not host:                       # bare host, no colon
        host, port = a.endpoint, ""
    if not port:
        port = str(DEFAULT_PORT)
    elif not port.isdigit():
        print(f"\n  {_c('1;31', '✗')} invalid port in '{a.endpoint}' — "
              f"use HOST[:PORT]\n")
        return 1

    ok, ep, detail = connect_endpoint(host, int(port))
    serial = resolve_serial(ep) if ok else ""
    model = resolve_model(ep) if ok else ""
    rec = new_record(a.name, host, int(port), serial=serial, model=model,
                     note=a.note)
    upsert(rec)
    if ok:
        log(f"adb {a.name}: connected & remembered ({_c('2', ep)})", "ok")
    else:
        log(f"adb {a.name}: remembered but unreachable right now "
            f"({_c('2', ep)}) — {detail.strip() or 'is the phone awake?'}",
            "warn")
    return 0


def forget_entry(argv: list) -> int:
    ap = argparse.ArgumentParser(
        prog="aadb forget",
        description="Drop a device from the registry.")
    add_common_args(ap)
    ap.add_argument("name", help="device name or serial to forget")
    a = ap.parse_args(argv)
    log = make_logger(a)
    if reg_remove(a.name):
        log(f"sys forgot '{a.name}'", "ok")
        return 0
    log(f"sys no device named '{a.name}' in the registry", "bad")
    return 1