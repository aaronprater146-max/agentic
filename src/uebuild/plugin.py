"""Parsing and validation of ``.uplugin`` descriptors."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .engine import EngineInstall
from .errors import PluginError


@dataclass
class PluginModule:
    name: str
    module_type: str = "Runtime"
    loading_phase: str = "Default"
    platform_allowlist: List[str] = field(default_factory=list)
    platform_denylist: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "PluginModule":
        allow = data.get("PlatformAllowList") or data.get("WhitelistPlatforms") or []
        deny = data.get("PlatformDenyList") or data.get("BlacklistPlatforms") or []
        return cls(
            name=str(data.get("Name") or "<unnamed>"),
            module_type=str(data.get("Type") or "Runtime"),
            loading_phase=str(data.get("LoadingPhase") or "Default"),
            platform_allowlist=[str(p) for p in allow],
            platform_denylist=[str(p) for p in deny],
        )


@dataclass
class PluginDescriptor:
    """A parsed ``.uplugin`` file."""

    path: Path
    raw: Dict[str, object]

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def plugin_dir(self) -> Path:
        return self.path.parent

    @property
    def file_version(self) -> int:
        try:
            return int(self.raw.get("FileVersion") or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def friendly_name(self) -> str:
        return str(self.raw.get("FriendlyName") or self.name)

    @property
    def version_name(self) -> str:
        return str(self.raw.get("VersionName") or "")

    @property
    def semantic_version(self) -> str:
        if self.raw.get("VersionName"):
            return self.version_name
        version = self.raw.get("Version")
        return "v%s" % version if version is not None else ""

    @property
    def engine_version(self) -> Optional[str]:
        value = self.raw.get("EngineVersion")
        return str(value) if value else None

    @property
    def description(self) -> str:
        return str(self.raw.get("Description") or "")

    @property
    def can_contain_content(self) -> bool:
        return bool(self.raw.get("CanContainContent"))

    @property
    def is_beta(self) -> bool:
        return bool(self.raw.get("IsBetaVersion"))

    @property
    def is_experimental(self) -> bool:
        return bool(self.raw.get("IsExperimentalVersion"))

    @property
    def supported_target_platforms(self) -> List[str]:
        return [str(p) for p in self.raw.get("SupportedTargetPlatforms") or []]

    @property
    def modules(self) -> List[PluginModule]:
        result = []
        for entry in self.raw.get("Modules") or []:
            if isinstance(entry, dict):
                result.append(PluginModule.from_dict(entry))
        return result

    @property
    def content_only(self) -> bool:
        return not self.modules

    # ------------------------------------------------------------------
    @classmethod
    def from_file(cls, path) -> "PluginDescriptor":
        path = Path(path).expanduser()
        if path.is_dir():
            # Allow passing the plugin folder directly.
            candidates = sorted(path.glob("*.uplugin"))
            if not candidates:
                raise PluginError("no .uplugin file found inside %s" % path)
            path = candidates[0]
        if not path.is_file():
            raise PluginError("plugin descriptor not found: %s" % path)
        if path.suffix.lower() != ".uplugin":
            raise PluginError("expected a .uplugin file, got: %s" % path)
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise PluginError("cannot read %s: %s" % (path, exc)) from exc
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise PluginError("%s is not valid JSON: %s" % (path, exc)) from exc
        if not isinstance(data, dict):
            raise PluginError("%s must contain a JSON object" % path)
        return cls(path=path, raw=data)

    # ------------------------------------------------------------------
    def supports_platform(self, platform: str) -> bool:
        supported = self.supported_target_platforms
        if supported and platform not in supported:
            return False
        for module in self.modules:
            if module.platform_allowlist and platform not in module.platform_allowlist:
                continue  # that module just will not build there
            if platform in module.platform_denylist:
                continue
        return True

    def validate(self, engine: Optional[EngineInstall] = None) -> List[str]:
        """Return human-readable warnings. Raises on fatal problems."""
        warnings: List[str] = []
        if self.file_version == 0:
            warnings.append("FileVersion is missing; assuming descriptor format 3")
        if self.content_only:
            warnings.append(
                "plugin declares no C++ modules (content-only); "
                "BuildPlugin will package it without compiling"
            )
        if self.modules and not (self.plugin_dir / "Source").is_dir():
            warnings.append(
                "plugin declares modules but has no Source/ directory: %s"
                % (self.plugin_dir / "Source")
            )
        if self.is_beta:
            warnings.append("plugin is flagged Beta (IsBetaVersion)")
        if self.is_experimental:
            warnings.append("plugin is flagged Experimental (IsExperimentalVersion)")

        if engine is not None:
            warnings.extend(self._engine_warnings(engine))
        return warnings

    def _engine_warnings(self, engine: EngineInstall) -> List[str]:
        warnings: List[str] = []
        declared = self.engine_version
        if declared:
            parts = [
                "".join(c for c in chunk if c.isdigit())
                for chunk in declared.split(".")
            ]
            nums = [int(p) for p in parts if p][:3]
            if nums:
                gen = nums[0]
                if gen != engine.generation:
                    warnings.append(
                        "descriptor targets UE%d (%s) but the build engine is UE%d %s"
                        % (gen, declared, engine.generation, engine.version_str)
                    )
                elif len(nums) > 1 and nums[1] != engine.minor:
                    warnings.append(
                        "descriptor targets UE %s but the build engine is %s; "
                        "this usually works but recompiles may surface differences"
                        % (declared, engine.version_str)
                    )
        if self.supported_target_platforms:
            unsupported = [
                p
                for p in engine.supported_platforms
                if p not in self.supported_target_platforms
                and p in ("Win64", "Mac", "Linux")
            ]
            if unsupported:
                warnings.append(
                    "SupportedTargetPlatforms does not include: "
                    + ", ".join(unsupported)
                )
        return warnings

    # ------------------------------------------------------------------
    def describe(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "path": str(self.path),
            "friendlyName": self.friendly_name,
            "version": self.semantic_version,
            "engineVersion": self.engine_version,
            "fileVersion": self.file_version,
            "description": self.description,
            "canContainContent": self.can_contain_content,
            "isBeta": self.is_beta,
            "isExperimental": self.is_experimental,
            "contentOnly": self.content_only,
            "modules": [
                {
                    "name": m.name,
                    "type": m.module_type,
                    "loadingPhase": m.loading_phase,
                    "platformAllowList": m.platform_allowlist,
                    "platformDenyList": m.platform_denylist,
                }
                for m in self.modules
            ],
            "supportedTargetPlatforms": self.supported_target_platforms,
        }
