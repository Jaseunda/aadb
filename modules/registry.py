# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
"""Persistent device registry (``~/.aadb/devices.json``).

This is aadb's memory of "devices that connected before": a small JSON list
keyed by a short name you choose, with the wireless endpoint (host:port),
the hardware serial and model. Everything else (scan, connect, shell,
scrcpy) reads from here so you never type ``adb connect IP:PORT`` again.
"""

import json
import os
import time

from config import ensure_dirs, registry_path


def _defaults() -> dict:
    return {"version": 1, "devices": []}


def load() -> dict:
    try:
        with open(registry_path(), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return _defaults()
    if not isinstance(data, dict) or not isinstance(data.get("devices"), list):
        data = _defaults()
    data["devices"] = [d for d in data["devices"] if isinstance(d, dict)]
    return data


def save(data: dict) -> None:
    ensure_dirs()
    p = registry_path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    os.replace(tmp, p)


def devices() -> list:
    return load()["devices"]


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def new_record(name: str, host: str, port: int = 5555, serial: str = "",
               model: str = "", note: str = "") -> dict:
    now = now_iso()
    return {"name": name, "host": host, "port": int(port),
            "serial": serial or "", "model": model or "", "note": note or "",
            "first_seen": now, "last_seen": now}


def endpoint_of(dev: dict):
    """'host:port' string for a record, or None if the record is unusable."""
    host = (dev.get("host") or "").strip()
    if not host:
        return None
    port = dev.get("port") or 5555
    return f"{host}:{int(port)}"


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def find(spec: str):
    """Resolve a name / serial / 'host:port' to a device record or None."""
    if not spec:
        return None
    s = _norm(spec)
    for d in devices():
        if _norm(d.get("name")) == s:
            return d
    for d in devices():
        if _norm(d.get("serial")) and _norm(d.get("serial")) == s:
            return d
    for d in devices():
        ep = endpoint_of(d)
        if ep and _norm(ep) == s:
            return d
    return None


def upsert(rec: dict) -> dict:
    """Insert rec, or merge into the record with the same name."""
    data = load()
    name = _norm(rec.get("name"))
    for i, d in enumerate(data["devices"]):
        if _norm(d.get("name")) == name:
            merged = dict(d)
            merged.update(rec)
            data["devices"][i] = merged
            save(data)
            return merged
    data["devices"].append(rec)
    save(data)
    return rec


def touch(dev: dict, serial: str = None, model: str = None) -> None:
    """Refresh last-seen (and optional serial/model), persisting the change."""
    dev["last_seen"] = now_iso()
    if serial:
        dev["serial"] = serial
    if model:
        dev["model"] = model
    upsert(dev)


def remove(spec: str) -> bool:
    """Forget a device by name, serial or endpoint. True if something went."""
    data = load()
    before = len(data["devices"])
    s = _norm(spec)
    kept = []
    for d in data["devices"]:
        if _norm(d.get("name")) == s or _norm(d.get("serial")) == s:
            continue
        ep = endpoint_of(d)
        if ep and _norm(ep) == s:
            continue
        kept.append(d)
    if len(kept) != before:
        data["devices"] = kept
        save(data)
        return True
    return False