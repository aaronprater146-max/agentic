#!/usr/bin/env bash
# Builds the ArenaAgent plugin against your Unreal Engine 5.8 installation.
# Cross-platform runner for Linux, macOS, and WSL.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$PLUGIN_ROOT/.." && pwd)"

# Use python-based agentic builder if available
if command -v python3 >/dev/null 2>&1; then
    exec python3 -m agentic build "$PLUGIN_ROOT" "$@"
fi

echo "Error: python3 is required to run the agentic build runner." >&2
exit 1
