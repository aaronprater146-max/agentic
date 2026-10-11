"""uebuild -- headless plugin build tool for Unreal Engine 4 and Unreal Engine 5.

Wraps Epic's UnrealAutomationTool command ``BuildPlugin`` (``RunUAT``) so that
plugins can be compiled and packaged from CI machines and terminals with no
editor UI. Pure standard library; Python 3.9+.
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
