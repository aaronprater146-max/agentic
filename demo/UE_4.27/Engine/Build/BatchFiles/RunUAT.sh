#!/bin/sh
# Fake RunUAT that proxies to the python stub next to it.
exec "$(command -v python3 || command -v python)" "$(dirname "$0")/_fake_uat.py" "$@"
