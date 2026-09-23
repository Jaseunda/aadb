# aadb changelog

## 0.1.1 — 2026-09-23

Bug fix — `aadb shell` / `aadb scrcpy` crashed with
`TypeError: cannot unpack non-iterable NoneType object` when run with no
remembered devices (or when nothing could be reached).  Device selection
now always returns a consistent `(transport, label, endpoint)` result, so
both commands exit cleanly with a helpful hint instead of a traceback.

- When devices are on the wire but none are remembered, aadb now suggests
  `aadb add NAME HOST[:PORT]` for the live endpoint instead of claiming
  "no device is online".
- `aadb connect NAME` reports a proper non-zero exit code when the device
  could not be reached.

## 0.1.0 — 2026-09-23

Initial release — Advanced ADB.

- Remember wireless adb devices (`aadb add NAME HOST[:PORT]`) in
  `~/.aadb/devices.json` (name, endpoint, serial, model, first/last seen).
- Reconnect remembered devices with one command (`aadb scan` / `aadb connect`);
  a device whose endpoint moved (new DHCP lease) is adopted automatically.
- `aadb shell` and `aadb scrcpy` auto-connect first, so opening a session is
  one word instead of `adb connect` + `adb shell`.
- Device deduplication by hardware serial (`getprop ro.serialno`), so the same
  phone reached over IP and mDNS never shows up twice.
- Device selection mirrors the ULS CLI: single online device auto-picks;
  several devices prompt with a numbered picker.
- Same terminal design language as ULS: dmesg-style dual screen/disk logging,
  16-color ANSI only, `::` / `✓` / `!` / `✗` status symbols.
- Build & release workflow: `make build` (self-contained zipapp),
  `make install`, `make release` (zip + SHA256SUMS), `make publish` (GitHub).
- Pure Python 3 stdlib, no dependencies. License: GPL-3.0-or-later.