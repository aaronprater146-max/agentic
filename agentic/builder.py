"""Build orchestrator for compiling and packaging Unreal Engine 5.8.3 plugins."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .engine_locator import EngineInfo, find_engine
from .validator import PluginValidator, ValidationReport


@dataclass
class BuildResult:
    plugin_name: str
    success: bool
    exit_code: int
    mode: str
    commands_executed: list[list[str]]
    output_path: Optional[Path] = None
    log_tail: Optional[str] = None
    dry_run: bool = False


class PluginBuilder:
    def __init__(
        self,
        engine_path: Optional[str | Path] = None,
        scratch_root: Optional[str | Path] = None,
    ):
        self.engine_info: Optional[EngineInfo] = find_engine(engine_path)
        self.scratch_root = Path(scratch_root) if scratch_root else Path.cwd() / ".build"

    def _resolve_plugin_dir(self, plugin_path_or_name: str | Path) -> Path:
        p = Path(plugin_path_or_name).resolve()
        if p.is_dir() and list(p.glob("*.uplugin")):
            return p

        # Check inside Plugins/ or workspace root
        for candidate in [Path.cwd() / p, Path.cwd() / "Plugins" / p]:
            if candidate.is_dir() and list(candidate.glob("*.uplugin")):
                return candidate.resolve()

        # If file provided
        if p.is_file() and p.suffix == ".uplugin":
            return p.parent.resolve()

        return p

    def build_ubt(
        self,
        plugin_target: str | Path,
        target_platform: Optional[str] = None,
        configuration: str = "Development",
        dry_run: bool = False,
    ) -> BuildResult:
        """Fast incremental build via scratch host project and UnrealBuildTool."""
        plugin_dir = self._resolve_plugin_dir(plugin_target)
        uplugins = list(plugin_dir.glob("*.uplugin"))
        if not uplugins:
            return BuildResult(
                plugin_name=plugin_dir.name,
                success=False,
                exit_code=1,
                mode="ubt",
                commands_executed=[],
                log_tail=f"Error: No .uplugin found in '{plugin_dir}'",
            )

        uplugin_file = uplugins[0]
        plugin_name = uplugin_file.stem

        # Determine target platform
        sys_name = platform.system()
        if target_platform:
            plat = target_platform
        elif sys_name == "Windows":
            plat = "Win64"
        elif sys_name == "Darwin":
            plat = "Mac"
        else:
            plat = "Linux"

        # Setup scratch project
        scratch_dir = self.scratch_root / f"scratch_{plugin_name}"
        scratch_name = f"{plugin_name}Host"
        self._prepare_scratch_project(scratch_dir, scratch_name, plugin_dir, plugin_name)

        scratch_uproject = scratch_dir / f"{scratch_name}.uproject"
        target_name = f"{scratch_name}Editor"

        # Determine UBT command
        if self.engine_info and self.engine_info.ubt_path:
            ubt_cmd = str(self.engine_info.ubt_path)
        else:
            ubt_cmd = "RunUBT.bat" if sys_name == "Windows" else "RunUBT.sh"

        cmd = [
            ubt_cmd,
            target_name,
            plat,
            configuration,
            f"-Project={scratch_uproject}",
        ]
        if sys_name == "Windows":
            cmd.append("-WaitMutex")

        if dry_run or not (self.engine_info and self.engine_info.ubt_path and self.engine_info.ubt_path.exists()):
            log = (
                f"[Dry-Run / Preview Mode]\n"
                f"Plugin: {plugin_name} ({plugin_dir})\n"
                f"Scratch Host: {scratch_uproject}\n"
                f"Target Platform: {plat} | Config: {configuration}\n"
                f"Command: {' '.join(cmd)}\n"
            )
            if not (self.engine_info and self.engine_info.is_valid):
                log += "\nNotice: Unreal Engine 5.8 was not found in local system paths. Running in dry-run mode."
            return BuildResult(
                plugin_name=plugin_name,
                success=True,
                exit_code=0,
                mode="ubt",
                commands_executed=[cmd],
                output_path=scratch_dir,
                log_tail=log,
                dry_run=True,
            )

        # Execute build
        print(f"==> Compiling {plugin_name} with UBT ({plat} {configuration})...")
        proc = subprocess.run(cmd, cwd=str(scratch_dir), capture_output=True, text=True)
        log = proc.stdout + "\n" + proc.stderr
        return BuildResult(
            plugin_name=plugin_name,
            success=proc.returncode == 0,
            exit_code=proc.returncode,
            mode="ubt",
            commands_executed=[cmd],
            output_path=scratch_dir,
            log_tail=log[-2000:] if len(log) > 2000 else log,
        )

    def package_uat(
        self,
        plugin_target: str | Path,
        output_dir: Optional[str | Path] = None,
        target_platforms: Optional[list[str]] = None,
        dry_run: bool = False,
    ) -> BuildResult:
        """Official standalone plugin packaging via RunUAT BuildPlugin."""
        plugin_dir = self._resolve_plugin_dir(plugin_target)
        uplugins = list(plugin_dir.glob("*.uplugin"))
        if not uplugins:
            return BuildResult(
                plugin_name=plugin_dir.name,
                success=False,
                exit_code=1,
                mode="uat",
                commands_executed=[],
                log_tail=f"Error: No .uplugin found in '{plugin_dir}'",
            )

        uplugin_file = uplugins[0]
        plugin_name = uplugin_file.stem

        out_path = Path(output_dir) if output_dir else self.scratch_root / "packaged" / plugin_name
        out_path.mkdir(parents=True, exist_ok=True)

        sys_name = platform.system()
        default_platform = "Win64" if sys_name == "Windows" else ("Mac" if sys_name == "Darwin" else "Linux")
        plat_str = "+".join(target_platforms) if target_platforms else default_platform

        if self.engine_info and self.engine_info.uat_path:
            uat_cmd = str(self.engine_info.uat_path)
        else:
            uat_cmd = "RunUAT.bat" if sys_name == "Windows" else "RunUAT.sh"

        cmd = [
            uat_cmd,
            "BuildPlugin",
            f"-Plugin={uplugin_file}",
            f"-Package={out_path}",
            "-Rocket",
            f"-TargetPlatforms={plat_str}",
        ]

        if dry_run or not (self.engine_info and self.engine_info.uat_path and self.engine_info.uat_path.exists()):
            log = (
                f"[Dry-Run / Package Preview]\n"
                f"Plugin: {plugin_name} ({uplugin_file})\n"
                f"Target Platforms: {plat_str}\n"
                f"Package Output: {out_path}\n"
                f"Command: {' '.join(cmd)}\n"
            )
            if not (self.engine_info and self.engine_info.is_valid):
                log += "\nNotice: Unreal Engine 5.8 was not found in local system paths. Running in dry-run mode."
            return BuildResult(
                plugin_name=plugin_name,
                success=True,
                exit_code=0,
                mode="uat",
                commands_executed=[cmd],
                output_path=out_path,
                log_tail=log,
                dry_run=True,
            )

        print(f"==> Packaging {plugin_name} with RunUAT ({plat_str})...")
        proc = subprocess.run(cmd, cwd=str(plugin_dir), capture_output=True, text=True)
        log = proc.stdout + "\n" + proc.stderr
        return BuildResult(
            plugin_name=plugin_name,
            success=proc.returncode == 0,
            exit_code=proc.returncode,
            mode="uat",
            commands_executed=[cmd],
            output_path=out_path,
            log_tail=log[-2000:] if len(log) > 2000 else log,
        )

    def _prepare_scratch_project(
        self,
        scratch_dir: Path,
        scratch_name: str,
        plugin_dir: Path,
        plugin_name: str,
    ) -> None:
        """Prepares a lightweight host .uproject with Target.cs files for UBT."""
        scratch_dir.mkdir(parents=True, exist_ok=True)

        engine_assoc = self.engine_info.version_str if self.engine_info else "5.8"

        # 1. Host .uproject
        uproject_content = f"""{{
    "FileVersion": 3,
    "EngineAssociation": "{engine_assoc}",
    "Category": "",
    "Description": "Automated Scratch Host for building {plugin_name}",
    "Modules": [
        {{
            "Name": "{scratch_name}",
            "Type": "Runtime",
            "LoadingPhase": "Default"
        }}
    ],
    "Plugins": [
        {{
            "Name": "{plugin_name}",
            "Enabled": true
        }}
    ]
}}
"""
        (scratch_dir / f"{scratch_name}.uproject").write_text(uproject_content, encoding="utf-8")

        # 2. Source/Target files
        src_dir = scratch_dir / "Source" / scratch_name
        src_dir.mkdir(parents=True, exist_ok=True)

        target_cs = f"""using UnrealBuildTool;

public class {scratch_name}Target : TargetRules
{{
    public {scratch_name}Target(TargetInfo Target) : base(Target)
    {{
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("{scratch_name}");
    }}
}}
"""
        (scratch_dir / "Source" / f"{scratch_name}.Target.cs").write_text(target_cs, encoding="utf-8")

        editor_target_cs = f"""using UnrealBuildTool;

public class {scratch_name}EditorTarget : TargetRules
{{
    public {scratch_name}EditorTarget(TargetInfo Target) : base(Target)
    {{
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("{scratch_name}");
    }}
}}
"""
        (scratch_dir / "Source" / f"{scratch_name}Editor.Target.cs").write_text(editor_target_cs, encoding="utf-8")

        # Minimal host module
        build_cs = f"""using UnrealBuildTool;

public class {scratch_name} : ModuleRules
{{
    public {scratch_name}(ReadOnlyTargetRules Target) : base(Target)
    {{
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        CppStandard = CppStandardVersion.Cpp20;
        PublicDependencyModuleNames.AddRange(new string[] {{ "Core", "CoreUObject", "Engine" }});
    }}
}}
"""
        (src_dir / f"{scratch_name}.Build.cs").write_text(build_cs, encoding="utf-8")
        (src_dir / f"{scratch_name}.cpp").write_text(
            f'#include "Modules/ModuleManager.h"\nIMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, {scratch_name}, "{scratch_name}");\n',
            encoding="utf-8",
        )

        # 3. Link or copy plugin into <scratch_dir>/Plugins/<PluginName>
        plugins_dest = scratch_dir / "Plugins" / plugin_name
        plugins_dest.parent.mkdir(parents=True, exist_ok=True)

        if plugins_dest.exists() or plugins_dest.is_symlink():
            if plugins_dest.is_symlink():
                plugins_dest.unlink()
            elif plugins_dest.is_dir():
                shutil.rmtree(plugins_dest)

        # Attempt symlink first; fall back to copy if symlinks not supported
        try:
            plugins_dest.symlink_to(plugin_dir.resolve(), target_is_directory=True)
        except OSError:
            shutil.copytree(plugin_dir, plugins_dest, dirs_exist_ok=True)
