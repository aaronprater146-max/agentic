"""Small platform / formatting helpers shared across uebuild."""
from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import Optional, TextIO

APP_NAME = "uebuild"


def host_os() -> str:
    """Return ``windows``, ``macos`` or ``linux`` (everything else)."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def host_editor_platform() -> str:
    """Unreal's name for this machine as an editor target platform."""
    return {"windows": "Win64", "macos": "Mac", "linux": "Linux"}[host_os()]


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_STYLES = {
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "grey": "90",
    "bold": "1",
    "dim": "2",
}


def supports_color(stream: Optional[TextIO] = None) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("UEBUILD_FORCE_COLOR"):
        return True
    stream = stream if stream is not None else sys.stderr
    return bool(getattr(stream, "isatty", lambda: False)())


def colorize(text: str, *styles: str, enabled: bool = True) -> str:
    if not enabled:
        return text
    codes = [s for s in (_STYLES.get(x) for x in styles) if s]
    if not codes:
        return text
    return "\033[%sm%s\033[0m" % (";".join(codes), text)


# ---------------------------------------------------------------------------
# Config directory
# ---------------------------------------------------------------------------

def config_dir() -> Path:
    """Where uebuild keeps the engine registry and other user state.

    Honour ``UEBUILD_CONFIG_DIR`` first so tests and CI can isolate state.
    """
    override = os.environ.get("UEBUILD_CONFIG_DIR")
    if override:
        return Path(override)
    os_name = host_os()
    if os_name == "windows":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    if os_name == "macos":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else Path.home() / ".config") / APP_NAME


# ---------------------------------------------------------------------------
# Misc formatting
# ---------------------------------------------------------------------------

def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def human_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return "%dh %02dm %02ds" % (hours, minutes, secs)
    if minutes:
        return "%dm %02ds" % (minutes, secs)
    return "%ds" % secs


def sanitize_filename(text: str) -> str:
    keep = []
    for ch in text:
        keep.append(ch if (ch.isalnum() or ch in "-._") else "-")
    return "".join(keep).strip("-.") or "build"
