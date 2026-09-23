#!/usr/bin/env python3
# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Interactive Arrow-Key Navigation Menu for aadb.

Controls:
  Up / Down Arrow : Navigate items
  Right Arrow / Enter : Select / Proceed
  Left Arrow / Esc / 'q' : Back / Cancel
"""

import os
import sys
import termios
import tty


def _read_key() -> str:
    """Read a single keypress or ANSI escape sequence from stdin."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch1 = sys.stdin.read(1)
        if ch1 == '\x1b':
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'UP'
                elif ch3 == 'B':
                    return 'DOWN'
                elif ch3 == 'C':
                    return 'RIGHT'
                elif ch3 == 'D':
                    return 'LEFT'
                elif ch3 in ('1', '2', '3', '4', '5', '6', '7', '8'):
                    sys.stdin.read(1)
                    return 'ESC'
                return 'ESC'
            elif ch2 == 'O':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'UP'
                elif ch3 == 'B':
                    return 'DOWN'
                elif ch3 == 'C':
                    return 'RIGHT'
                elif ch3 == 'D':
                    return 'LEFT'
                return 'ESC'
            return 'ESC'
        elif ch1 in ('\r', '\n'):
            return 'ENTER'
        elif ch1 in ('\x03',):  # Ctrl+C
            raise KeyboardInterrupt()
        elif ch1 in ('\x04',):  # Ctrl+D
            return 'EOF'
        elif ch1 in ('q', 'Q'):
            return 'BACK'
        return ch1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def select_menu(title: str, items: list, default_index: int = 0, allow_back: bool = True) -> int:
    """
    Renders an interactive selection menu navigated with Up/Down arrow keys.
    Right Arrow or Enter confirms selection.
    Left Arrow or Esc returns -1 (back/cancel).

    items: list of tuples: (label, description/detail) or list of strings
    returns: selected index (0-based) or -1 if cancelled/back
    """
    if not items:
        return -1

    # Fallback to standard input if not a real TTY
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(f"\n  {title}:")
        for i, item in enumerate(items, 1):
            if isinstance(item, (tuple, list)):
                label = item[0]
                detail = f" ({item[1]})" if len(item) > 1 and item[1] else ""
            else:
                label, detail = str(item), ""
            print(f"    {i}) {label}{detail}")
        try:
            raw = input(f"\n  Select [1-{len(items)}, default=1]: ").strip()
            if not raw:
                return default_index if 0 <= default_index < len(items) else 0
            val = int(raw) - 1
            if 0 <= val < len(items):
                return val
        except Exception:
            pass
        return default_index if 0 <= default_index < len(items) else 0

    selected = max(0, min(default_index, len(items) - 1))
    color_enabled = "NO_COLOR" not in os.environ

    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    total_lines = 0

    def render(first=False):
        nonlocal total_lines
        lines = []
        if title:
            lines.append(f"  \033[1m{title}\033[0m" if color_enabled else f"  {title}")
            lines.append(f"  \033[2mUse ↑/↓ to navigate, →/Enter to select" + (", ← to go back" if allow_back else "") + "\033[0m" if color_enabled else "  Use Up/Down to navigate, Right/Enter to select")
            lines.append("")

        for i, item in enumerate(items):
            if isinstance(item, (tuple, list)):
                label = item[0]
                detail = f"  \033[2m{item[1]}\033[0m" if (len(item) > 1 and item[1] and color_enabled) else (f"  {item[1]}" if len(item) > 1 and item[1] else "")
            else:
                label, detail = str(item), ""

            if i == selected:
                pointer = " \033[1;36m➜\033[0m " if color_enabled else " > "
                item_str = f"\033[1;36m{label}\033[0m" if color_enabled else label
                lines.append(f"   {pointer}{item_str}{detail}")
            else:
                pointer = "   "
                item_str = f"\033[2m{label}\033[0m" if color_enabled else label
                lines.append(f"   {pointer}{item_str}{detail}")

        # Clear previously printed lines if not first run
        if not first and total_lines > 0:
            sys.stdout.write(f"\033[{total_lines}A\r\033[J")

        output = "\n".join(lines) + "\n"
        sys.stdout.write(output)
        sys.stdout.flush()
        total_lines = len(lines)

    try:
        render(first=True)
        while True:
            key = _read_key()
            if key == 'UP':
                selected = (selected - 1) % len(items)
                render()
            elif key == 'DOWN':
                selected = (selected + 1) % len(items)
                render()
            elif key in ('ENTER', 'RIGHT'):
                if total_lines > 0:
                    sys.stdout.write(f"\033[{total_lines}A\r\033[J")
                    sys.stdout.flush()
                return selected
            elif key in ('LEFT', 'ESC', 'BACK'):
                if allow_back:
                    if total_lines > 0:
                        sys.stdout.write(f"\033[{total_lines}A\r\033[J")
                        sys.stdout.flush()
                    return -1
            elif key.isdigit():
                val = int(key) - 1
                if 0 <= val < len(items):
                    selected = val
                    if total_lines > 0:
                        sys.stdout.write(f"\033[{total_lines}A\r\033[J")
                        sys.stdout.flush()
                    return selected
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
