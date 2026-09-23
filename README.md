# aadb — Advanced ADB

> **Remember your wireless adb devices. Connect, shell, scrcpy — with no `adb connect` typing every time.**

```
   █████╗  █████╗ ██████╗ ██████╗
  ██╔══██╗██╔══██╗██╔══██╗██╔══██╗
  ███████║███████║██║  ██║██████╔╝
  ██╔══██║██╔══██║██║  ██║██╔══██╗
  ██║  ██║██║  ██║██████╔╝██████╔╝
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═════╝
```

Wireless adb is great until the phone's IP changes, or you reboot it, or you
own more than one device — and suddenly you're typing `adb connect
192.168.x.x:5555` from muscle memory again.

`aadb` is a thin CLI that:

- **remembers** every wireless device you've connected to (name, endpoint,
  serial, model) in `~/.aadb/devices.json`;
- **reconnects** remembered devices with one command — it even tracks when a
  device's endpoint moves (new DHCP lease) and updates it for you;
- **skips the typing**: `aadb shell` and `aadb scrcpy` auto-connect first, so
  opening a session is one word, not `adb connect` + `adb shell`;
- **deduplicates** by hardware serial, so the same phone reached over IP and
  mDNS never shows up twice.

It follows the same terminal design language as the [ULS](https://github.com/Jaseunda/uls)
CLI (dmesg-style logs, 16-color ANSI only, dual screen/disk output).

---

## Requirements

| What | Why |
|---|---|
| `adb` | `brew install android-platform-tools` |
| `scrcpy` *(optional)* | `brew install scrcpy` — only for `aadb scrcpy` |
| Python 3.8+ | macOS ships it (`/usr/bin/python3`) |
| Android 11+ phone | Wireless debugging (developer options → wireless debugging) |

> `aadb` works with any adb endpoint — USB, wired network, or Wi-Fi.

---

## Install

```sh
git clone https://github.com/Jaseunda/aadb.git
cd aadb
./install.sh            # installs to ~/.aadb, links aadb into ~/.local/bin
aadb --version
```

Or run straight from the checkout without installing:

```sh
python3 aadb.py status
```

---

## Quick start

### 1 — Pair once (one-time, from Android)

Developer options → **Wireless debugging** → *Pair device with pairing code*.
Then:

```sh
adb pair 192.168.1.5:38079   # pairing port + code from the phone
```

### 2 — Remember the device

```sh
aadb add phone 192.168.1.5:5555
```

aadb connects, reads the serial + model, and stores it. From now on that's
all you ever type about this device.

### 3 — Use it

```sh
aadb shell phone              # interactive shell (auto-reconnects first)
aadb shell phone uname -a     # one-shot command, quoted safely for you
aadb scrcpy phone             # mirror & control — no cable, no typing
aadb scan                     # bring every remembered device back online
aadb status                   # who's around and what state they're in
```

No `adb connect` anywhere. If the phone moved to a new IP, `aadb add` a new
endpoint or let `aadb shell`/`scan` discover it again — aadb learns and
updates the saved endpoint automatically.

---

## Commands

| Command | What it does |
|---|---|
| `aadb status` | List remembered devices & current state |
| `aadb devices` | Show what adb sees right now, with names & models |
| `aadb scan` | Reconnect every remembered device + list mDNS discoveries |
| `aadb connect [name]` | Connect one device (or everything remembered) |
| `aadb shell [device] [cmd…]` | Open an adb shell (auto-connect; device optional when one is around) |
| `aadb scrcpy [device] [flags…]` | Mirror & control via scrcpy (auto-connect) |
| `aadb add NAME HOST[:PORT] [--note …]` | Remember a device |
| `aadb forget NAME` | Drop a device from the registry |

### Selecting a device

- `aadb shell s24` / `aadb shell --device s24` — that remembered device
- `aadb shell 192.168.1.5:5555` — a raw endpoint, on the fly
- `aadb shell` with no device — auto-picks the single online device, or asks
  when several are around

### Global flags (all commands)

| Flag | Meaning |
|---|---|
| `-d, --device` | Target by remembered name or serial |
| `--serial` | Target by raw endpoint or serial |
| `-T, --wall` | Wall-clock timestamps in the disk log |
| `--wrap` | Don't truncate screen output to terminal width |
| `--log PATH` | Custom log file (default `~/.aadb/aadb.log`) |
| `--no-color` | Disable ANSI colors |

### Makefile (dev)

`make status`, `make scan`, `make shell ARGS="--device phone uname -a"`,
`make scrcpy`, `make add ARGS="phone 192.168.1.5:5555"`, …

---

## How the registry works

The device memory lives in `~/.aadb/devices.json` (plain JSON — it contains
your device names, endpoints, serials and models; treat it as mildly
personal):

```json
{
  "version": 1,
  "devices": [
    {
      "name": "phone",
      "host": "192.168.1.5",
      "port": 5555,
      "serial": "R5CXA0ABCDEF",
      "model": "SM-S928B",
      "first_seen": "2026-09-23T10:00:00",
      "last_seen": "2026-09-23T10:05:00"
    }
  ]
}
```

Every successful connect refreshes `serial` / `model` / `last_seen`. When a
remembered serial appears at a different endpoint, the registry entry is
updated so the next `aadb shell` works without re-adding anything.

---

## Design notes

- Same CLI discipline as the ULS host CLI: dmesg-style `[time] tag message`
  logging, `::` / `✓` / `!` / `✗` status symbols, 16-color ANSI only, screen
  output truncated to terminal width while the disk log stays full-length and
  uncolored.
- No Python dependencies — pure standard library. Run it anywhere Python 3
  exists.
- Adb device discovery is deduplicated by hardware serial (`getprop
  ro.serialno`), so an mDNS advertisement and an IP endpoint for the same
  phone count once.

---

## Related

`aadb` composes well with [ULS](https://github.com/Jaseunda/uls) workflows:
it keeps every device reachable for Wi-Fi SSH/session work. It is not
required by ULS and ULS does not depend on it.

---

## License

**GPL-3.0-or-later** — see [LICENSE](./LICENSE). If you distribute a
modified copy, the source must be made available under the same license.