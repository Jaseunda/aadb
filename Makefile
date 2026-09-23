# aadb — Advanced ADB
#
# Copyright (C) 2026 Jaseunda
# SPDX-License-Identifier: GPL-3.0-or-later

.PHONY: help status devices scan connect shell scrcpy add forget

PYTHON ?= python3
ARGS   ?=

all: help

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
	@echo ""
	@echo "  Pass extra flags with ARGS=  e.g.  make shell ARGS=\"--device phone uname -a\""
	@echo ""