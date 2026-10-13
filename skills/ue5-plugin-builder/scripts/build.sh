#!/usr/bin/env bash
# Antigravity skill helper for building plugins
set -euo pipefail

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
    python3 -m agentic build --help
    exit 0
fi

python3 -m agentic build "$TARGET" "${@:2}"
