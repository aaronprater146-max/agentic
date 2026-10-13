#!/usr/bin/env bash
# Antigravity skill helper for creating plugins
set -euo pipefail

NAME="${1:-}"
if [[ -z "$NAME" ]]; then
    python3 -m agentic create --help
    exit 0
fi

python3 -m agentic create "$NAME" "${@:2}"
