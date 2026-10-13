"""Engine locator module for Unreal Engine 5.8.x installations across Linux, Windows, and macOS."""

from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class EngineInfo:
    root_path: Path
    version_str: str
    major_version: int
    minor_version: int
    patch_version: int
    ubt_path: Optional[Path]
    uat_path: Optional[Path]
    editor_path: Optional[Path]

    @property
    def is_valid(self) -> bool:
        return self.root_path.exists() and (self.root_path / "Engine").is_dir()

    @property
    def is_ue58(self) -> bool:
        return self.major_version == 5 and self.minor_version == 8

    def __str__(self) -> str:
        return f"Unreal Engine {self.version_str} at {self.root_path}"


def _read_build_version(engine_root: Path) -> tuple[int, int, int, str]:
    """Reads Major, Minor, Patch and display string from Engine/Build/Build.version."""
    build_version_file = engine_root / "Engine" / "Build" / "Build.version"
    if build_version_file.exists():
        try:
            with open(build_version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                major = int(data.get("MajorVersion", 5))
                minor = int(data.get("MinorVersion", 8))
                patch = int(data.get("PatchVersion", 3))
                ver_name = data.get("BranchName", f"{major}.{minor}.{patch}")
                return major, minor, patch, f"{major}.{minor}.{patch}"
        except Exception:
            pass

    # Fallback to directory name parsing or default 5.8.3
    name = engine_root.name
    if "5.8" in name:
        return 5, 8, 3, "5.8.3"
    elif "5." in name:
        try:
            parts = name.split("5.")[1].split("-")[0].split(".")[0]
            minor = int(parts)
            return 5, minor, 0, f"5.{minor}.0"
        except Exception:
            pass

    return 5, 8, 3, "5.8.3"


def _find_tool_paths(engine_root: Path) -> tuple[Optional[Path], Optional[Path], Optional[Path]]:
    is_windows = platform.system() == "Windows"
    batch_ext = ".bat" if is_windows else ".sh"
    exe_ext = ".exe" if is_windows else ""

    batch_dir = engine_root / "Engine" / "Build" / "BatchFiles"
    binaries_dir = engine_root / "Engine" / "Binaries"

    # UBT path
    ubt_candidates = [
        batch_dir / f"RunUBT{batch_ext}",
        batch_dir / f"Build{batch_ext}",
    ]
    ubt_path = next((p for p in ubt_candidates if p.exists()), None)

    # UAT path
    uat_candidates = [
        batch_dir / f"RunUAT{batch_ext}",
        batch_dir / "RunUAT.bat",
        batch_dir / "RunUAT.sh",
    ]
    uat_path = next((p for p in uat_candidates if p.exists()), None)

    # Editor binary
    if is_windows:
        editor_path = binaries_dir / "Win64" / "UnrealEditor.exe"
    elif platform.system() == "Darwin":
        editor_path = binaries_dir / "Mac" / "UnrealEditor.app" / "Contents" / "MacOS" / "UnrealEditor"
    else:
        editor_path = binaries_dir / "Linux" / "UnrealEditor"

    if not editor_path.exists():
        editor_path = None

    return ubt_path, uat_path, editor_path


def get_candidate_directories() -> list[Path]:
    """Generates a list of potential Unreal Engine installation directories."""
    candidates: list[Path] = []
    sys_name = platform.system()

    # 1. Environment variables
    env_vars = [
        "UNREAL_INSTALL_DIR",
        "UE5_8_DIR",
        "UE_SDKS_ROOT",
        "ARENA_UE_PATH",
        "ENGINE_ROOT",
        "UE_ENGINE_PATH",
    ]
    for var in env_vars:
        val = os.getenv(var)
        if val:
            candidates.append(Path(val).expanduser())

    # 2. System-specific default locations
    if sys_name == "Linux":
        search_roots = [
            Path.home() / ".local" / "share" / "unreal-engine",
            Path("/opt"),
            Path("/opt/Epic"),
            Path("/opt/unreal-engine"),
            Path("/mnt/unreal"),
        ]
        for root in search_roots:
            if root.exists():
                candidates.extend(sorted(root.glob("*5.8*"), reverse=True))
                candidates.extend(sorted(root.glob("*UE*5*"), reverse=True))
                candidates.append(root)

    elif sys_name == "Windows":
        drives = [os.getenv("SystemDrive", "C:"), "C:", "D:", "E:"]
        for drive in drives:
            epic_root = Path(f"{drive}\\Program Files\\Epic Games")
            if epic_root.exists():
                candidates.extend(sorted(epic_root.glob("UE_5.8*"), reverse=True))
                candidates.extend(sorted(epic_root.glob("UE_5.*"), reverse=True))

        # Windows registry lookup
        try:
            import winreg

            reg_paths = [
                r"SOFTWARE\Epic Games\Unreal Engine",
                r"SOFTWARE\EpicGames\Unreal Engine",
                r"SOFTWARE\Epic Games\Unreal Engine\Builds",
                r"SOFTWARE\EpicGames\Unreal Engine\Builds",
            ]
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for sub in reg_paths:
                    try:
                        with winreg.OpenKey(hive, sub) as key:
                            num_subkeys, _, _ = winreg.QueryInfoKey(key)
                            for i in range(num_subkeys):
                                name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, name) as subkey:
                                    try:
                                        val, _ = winreg.QueryValueEx(subkey, "InstalledDirectory")
                                        if val:
                                            candidates.append(Path(val))
                                    except OSError:
                                        pass
                    except OSError:
                        pass
        except ImportError:
            pass

    elif sys_name == "Darwin":
        search_roots = [
            Path("/Users/Shared/Epic Games"),
            Path("/Applications/Unreal Engine"),
        ]
        for root in search_roots:
            if root.exists():
                candidates.extend(sorted(root.glob("UE_5.8*"), reverse=True))
                candidates.extend(sorted(root.glob("UE_5.*"), reverse=True))

    return candidates


def find_engine(explicit_path: Optional[str | Path] = None) -> Optional[EngineInfo]:
    """Finds the most suitable Unreal Engine 5.8.x installation."""
    if explicit_path:
        p = Path(explicit_path).expanduser().resolve()
        if (p / "Engine").is_dir():
            maj, min_, patch, ver = _read_build_version(p)
            ubt, uat, editor = _find_tool_paths(p)
            return EngineInfo(
                root_path=p,
                version_str=ver,
                major_version=maj,
                minor_version=min_,
                patch_version=patch,
                ubt_path=ubt,
                uat_path=uat,
                editor_path=editor,
            )

    candidates = get_candidate_directories()
    tested = set()

    for cand in candidates:
        cand_res = cand.resolve()
        if cand_res in tested:
            continue
        tested.add(cand_res)

        if (cand_res / "Engine").is_dir():
            maj, min_, patch, ver = _read_build_version(cand_res)
            ubt, uat, editor = _find_tool_paths(cand_res)
            info = EngineInfo(
                root_path=cand_res,
                version_str=ver,
                major_version=maj,
                minor_version=min_,
                patch_version=patch,
                ubt_path=ubt,
                uat_path=uat,
                editor_path=editor,
            )
            # Prefer 5.8 if found
            if info.is_ue58:
                return info

    # If no 5.8 found, return first valid UE5 if any
    for cand in candidates:
        cand_res = cand.resolve()
        if (cand_res / "Engine").is_dir():
            maj, min_, patch, ver = _read_build_version(cand_res)
            ubt, uat, editor = _find_tool_paths(cand_res)
            return EngineInfo(
                root_path=cand_res,
                version_str=ver,
                major_version=maj,
                minor_version=min_,
                patch_version=patch,
                ubt_path=ubt,
                uat_path=uat,
                editor_path=editor,
            )

    return None
