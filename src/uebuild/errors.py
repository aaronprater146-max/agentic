"""Shared exception types for uebuild."""
from __future__ import annotations


class UEBuildError(Exception):
    """Base class for all uebuild errors."""


class EngineError(UEBuildError):
    """An engine install could not be found, parsed or resolved."""


class PluginError(UEBuildError):
    """A .uplugin descriptor could not be found or parsed."""


class ConfigError(UEBuildError):
    """A build matrix or registry file is invalid."""


class BuildValidationError(UEBuildError):
    """A build request failed validation before UAT was launched."""
