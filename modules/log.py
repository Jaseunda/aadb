# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
"""Terminal design-system logger for aadb.

Screen output is colorized, truncated to the terminal width and readable in
any theme (16-color ANSI only); the disk log is plain, full-length and
timestamped in dmesg style. Adapted from the ULS design-system reference
implementation (see docs/DESIGN.md in the ULS repository).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time

# Semantic styles (standard 16-color ANSI SGR — never TrueColor).
SGR = {
    "ok": "32",    # green: success / online / exit 0
    "bad": "31",   # red: failure / offline / unreachable
    "warn": "33",  # yellow: retries / degraded / confirmation
    "hdr": "1",    # bold: headings / executed commands
    "dim": "2",    # dim: secondary metadata
    "": "",
}

# Subsystem tags (exactly 3 chars -> ANSI color) per the design system.
TAGS = {
    "sys": "37",   # white: supervisor / lifecycle
    "adb": "35",   # magenta: adb bridge
    "net": "36",   # cyan: network / transport
    "shl": "36",   # cyan: shell sessions
    "scr": "36",   # cyan: scrcpy mirror sessions
}


def _use_color() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, text: str) -> str:
    """ANSI highlight; stripped when stdout isn't a TTY or NO_COLOR is set."""
    return f"\033[{code}m{text}\033[0m" if _use_color() else text


class TerminalLogger:
    """Dual-target (screen + disk) dmesg-style logger."""

    def __init__(self, log_path=None, color=None, wall=False, trunc=True):
        self.color = _use_color() if color is None else bool(color)
        self.wall = wall
        self.trunc = trunc
        self.t0 = time.monotonic()
        self.lock = threading.Lock()
        self.fh = None
        if log_path:
            try:
                self.fh = open(log_path, "a", buffering=1, encoding="utf-8")
            except OSError:
                self.fh = None

    def __call__(self, msg: str, kind: str = ""):
        t = (time.strftime("%Y-%m-%d %H:%M:%S") if self.wall
             else f"{time.monotonic() - self.t0:12.6f}")
        full = f"[{t}] {msg}"
        with self.lock:
            try:
                print(self._render(t, msg, kind), flush=True)
            except BrokenPipeError:
                sys.exit(0)
            if self.fh:
                try:
                    self.fh.write(full + "\n")
                except OSError:
                    pass

    def _render(self, t: str, msg: str, kind: str) -> str:
        shown = msg
        if self.trunc:
            cols = shutil.get_terminal_size((80, 24)).columns
            room = cols - len(t) - 4
            if room > 1 and len(shown) > room:
                shown = shown[:room - 1] + "…"
        if not self.color:
            return f"[{t}] {shown}"
        tag = shown[:3] if (shown[:3] in TAGS and shown[3:4] in (" ", ":")) else ""
        rest = shown[len(tag):]
        head = f"\033[1;{TAGS[tag]}m{tag}\033[0m" if tag else ""
        body = (f"\033[{SGR.get(kind, '')}m{rest}\033[0m"
                if SGR.get(kind) and rest else rest)
        return f"\033[2m[{t}]\033[0m {head}{body}"

    def run_job(self, name: str, cmd: list, busy_event: threading.Event):
        """Stream a child's output, debouncing carriage-return progress bars."""
        def worker():
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     start_new_session=True)
                buf, last_cr = b"", 0.0
                while True:
                    data = os.read(p.stdout.fileno(), 4096)
                    if not data:
                        break
                    buf += data
                    while m := re.search(rb"\r\n|\r|\n", buf):
                        line, sep, buf = buf[:m.start()], m.group(), buf[m.end():]
                        text = line.decode(errors="replace").strip()
                        if not text:
                            continue
                        if sep == b"\r" and time.monotonic() - last_cr < 1.0:
                            continue
                        last_cr = time.monotonic()
                        self(f"{name}: {text}")
                if buf.strip():
                    self(f"{name}: {buf.decode(errors='replace').strip()}")
                rc = p.wait()
                self(f"{name}: exited with status {rc}",
                     "ok" if rc == 0 else "bad")
            except Exception as e:  # pragma: no cover
                self(f"{name}: execution failed: {e}", "bad")
            finally:
                busy_event.clear()

        busy_event.set()
        self(f"{name}: $ {' '.join(cmd)}", "hdr")
        threading.Thread(target=worker, daemon=True).start()


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Flags shared by every aadb command (same surface as the ULS CLI)."""
    parser.add_argument("-d", "--device", default=None,
                        help="target remembered device (name or serial)")
    parser.add_argument("--serial", default=None,
                        help="target raw adb endpoint (host:port or serial)")
    parser.add_argument("-T", "--wall", action="store_true",
                        help="wall-clock timestamps in the disk log")
    parser.add_argument("--wrap", action="store_true",
                        help="do not truncate screen output to terminal width")
    parser.add_argument("--log", default=None,
                        help="log file path (default: ~/.aadb/aadb.log)")
    parser.add_argument("--no-color", action="store_true",
                        help="disable ANSI colors")


def make_logger(args: argparse.Namespace) -> TerminalLogger:
    from config import log_path
    return TerminalLogger(
        log_path=args.log or log_path(),
        color=not args.no_color,
        wall=args.wall,
        trunc=not args.wrap,
    )