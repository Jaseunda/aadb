# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later

.PHONY: help check status devices scan connect shell scrcpy add forget build install release publish

PYTHON ?= python3
ARGS   ?=
AADB_HOME ?= $(HOME)/.aadb

all: help

## Syntax-check every source file
check:
	@$(PYTHON) -m py_compile aadb.py modules/*.py
	@echo "✓ syntax check passed"

## List remembered devices & their current adb state
status:
	@$(PYTHON) aadb.py status $(ARGS)

## Show what adb sees right now (with names & models)
devices:
	@$(PYTHON) aadb.py devices $(ARGS)

## Reconnect every remembered device + discover mDNS devices
scan:
	@$(PYTHON) aadb.py scan $(ARGS)

## Connect a remembered device, or everything remembered
connect:
	@$(PYTHON) aadb.py connect $(ARGS)

## Open an adb shell on a device (auto-connects if offline)
shell:
	@$(PYTHON) aadb.py shell $(ARGS)

## Mirror & control a device with scrcpy (auto-connects if offline)
scrcpy:
	@$(PYTHON) aadb.py scrcpy $(ARGS)

## Remember a device:  make add ARGS="phone 192.168.1.5:5555"
add:
	@$(PYTHON) aadb.py add $(ARGS)

## Drop a device from the registry:  make forget ARGS="phone"
forget:
	@$(PYTHON) aadb.py forget $(ARGS)

## Build self-contained executable (build/bin/aadb) — a zipapp, no dependencies
build:
	@bash build/build_bin.sh
	@echo ""

## Build + install to $(AADB_HOME)/aadb and link into ~/.local/bin/aadb
install: build
	@mkdir -p $(AADB_HOME) $(HOME)/.local/bin
	@rm -f $(AADB_HOME)/aadb
	@cp build/bin/aadb $(AADB_HOME)/aadb
	@chmod 755 $(AADB_HOME)/aadb
	@if [ "$$(uname -s)" = "Darwin" ]; then codesign --force --sign - $(AADB_HOME)/aadb >/dev/null 2>&1 || true; fi
	@ln -sf $(AADB_HOME)/aadb $(HOME)/.local/bin/aadb
	@echo "✓ Installed to $(AADB_HOME)/aadb and linked as $(HOME)/.local/bin/aadb"

## Assemble distributable bundle (releases/aadb-<VERSION>.zip + SHA256SUMS)
release:
	@bash build/build_bin.sh >/dev/null
	@bash build/make_release.sh

## Publish the release bundle to GitHub (requires gh authenticated)
publish: release
	@bash build/publish_release.sh

help:
	@echo ""
	@echo "  \033[1;36m::\033[0m \033[1maadb\033[0m — remember & reconnect wireless adb devices"
	@echo ""
	@echo "  \033[1;33mmake status\033[0m        List remembered devices & connection state"
	@echo "  \033[1;33mmake devices\033[0m       What adb sees right now"
	@echo "  \033[1;33mmake scan\033[0m          Reconnect every remembered device"
	@echo "  \033[1;33mmake connect\033[0m       Connect a NAME or everything remembered"
	@echo "  \033[1;33mmake shell\033[0m         Open an adb shell (auto-connect)"
	@echo "  \033[1;33mmake scrcpy\033[0m        Mirror & control with scrcpy"
	@echo "  \033[1;33mmake add\033[0m           Remember a device: make add ARGS=\"phone 192.168.1.5:5555\""
	@echo "  \033[1;33mmake forget\033[0m        Drop a device from the registry"
	@echo "  \033[1;33mmake build\033[0m           Build self-contained executable (zipapp)"
	@echo "  \033[1;33mmake install\033[0m         Build + install to ~/.aadb and link into PATH"
	@echo "  \033[1;33mmake release\033[0m         Assemble releases/aadb-<VERSION>.zip"
	@echo "  \033[1;33mmake publish\033[0m         Publish release to GitHub (gh)"
	@echo ""
	@echo "  Pass extra flags with ARGS=  e.g.  make shell ARGS=\"--device phone uname -a\""
	@echo "  Version lives in _VERSION at the top of aadb.py — bump before a release."
	@echo ""