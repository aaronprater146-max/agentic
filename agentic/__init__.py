"""Agentic — UE 5.8.3 Plugin Creation and Build Automation for Antigravity."""

from .builder import PluginBuilder
from .creator import PluginScaffolder
from .engine_locator import EngineInfo, find_engine
from .validator import PluginValidator

__version__ = "1.0.0"
__all__ = [
    "PluginScaffolder",
    "PluginBuilder",
    "PluginValidator",
    "EngineInfo",
    "find_engine",
]
