"""Unreal Engine installation discovery, version detection and registry.

An *engine install* is any directory that contains ``Engine/Build/Build.version``
(with a launchable ``Engine/Build/BatchFiles/RunUAT``), for example::

    C:\\Program Files\\Epic Games\\UE_5.3        (Windows launcher install)
    /Users/Shared/Epic Games/UE_4.27             (macOS launcher install)
    ~/UnrealEngine                               (Linux source build)

Version information comes from ``Engine/Build/Build.version`` which both the
Epic launcher and source builds ship, so detection is uniform for UE4 and UE5.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import util
from .errors import EngineError

BUILD_VERSION_REL = Path("Engine") / "Build" / "Build.version"
UAT_BATCH_DIR = Path("Engine") / "Build" / "BatchFiles"

#: Target platforms BuildPlugin can usually compile for on any host that has
#: the matching toolchains installed (no platform SDK / NDA required).
PLATFORMS_UE4 = ["Win64", "Mac", "Linux", "Android", "IOS", "HTML5", "HoloLens"]
PLATFORMS_UE5 = [
    "Win64",
    "Mac",
    "Linux",
    "LinuxArm64",
    "Android",
    "IOS",
    "TVOS",
    "VisionOS",
]

#: Console platforms. BuildPlugin *can* target these but only with the
#: platform holder's SDK and credentials, so they need explicit opt-in.
CONSOLE_PLATFORMS = ["PS4", "PS5", "XboxOne", "XSX", "Switch"]

ALL_KNOWN_PLATFORMS = sorted(set(PLATFORMS_UE4 + PLATFORMS_UE5 + CONSOLE_PLATFORMS))

#: Safe default when the user does not pick platforms.
DEFAULT_PLATFORMS = ["Win64", "Mac", "Linux"]


@dataclass
class EngineInstall:
    """One discovered or registered Unreal Engine installation."""

    name: str
    root: Path
    major: int
    minor: int
    patch: int
    changelist: int = 0
    branch: str = ""
    licensee: bool = False
    promoted: bool = False
    custom: bool = False  # True when named/added by hand through the registry

    # ------------------------------------------------------------------
    @property
    def version_str(self) -> str:
        return "%d.%d.%d" % (self.major, self.minor, self.patch)

    @property
    def generation(self) -> int:
        """4 for UE4.x, 5 for UE5.x (matches Engine.Association style)."""
        return self.major

    @property
    def is_ue5(self) -> bool:
        return self.major >= 5

    @property
    def version_tuple(self) -> Tuple[int, int, int, int]:
        return (self.major, self.minor, self.patch, self.changelist)

    @property
    def engine_dir(self) -> Path:
        return self.root / "Engine"

    @property
    def build_version_file(self) -> Path:
        return self.root / BUILD_VERSION_REL

    @property
    def uat_script(self) -> Path:
        """Path to ``RunUAT`` for the current host OS."""
        ext = ".bat" if util.host_os() == "windows" else ".sh"
        return self.root / UAT_BATCH_DIR / ("RunUAT" + ext)

    @property
    def supported_platforms(self) -> List[str]:
        return list(PLATFORMS_UE5 if self.is_ue5 else PLATFORMS_UE4)

    @property
    def family_label(self) -> str:
        return "UE%d" % self.generation

    @property
    def display(self) -> str:
        return "%s %s (%s) @ %s" % (
            self.family_label,
            self.version_str,
            self.name,
            self.root,
        )

    def describe(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "family": self.family_label,
            "version": self.version_str,
            "root": str(self.root),
            "uat": str(self.uat_script),
            "uatExists": self.uat_script.is_file(),
            "isSourceBuild": self.branch.startswith("++UE"),
            "branch": self.branch,
            "licenseeVersion": self.licensee,
            "platforms": self.supported_platforms,
            "registered": self.custom,
        }

    # ------------------------------------------------------------------
    @classmethod
    def from_root(cls, root, name: Optional[str] = None) -> "EngineInstall":
        """Build an install descriptor from an engine root directory.

        Raises :class:`EngineError` when the directory is not a UE install.
        """
        root = Path(root).expanduser()
        if not root.is_dir():
            raise EngineError("engine root does not exist: %s" % root)
        root = root.resolve()  # canonical, and immune to the caller's cwd
        version_file = root / BUILD_VERSION_REL
        if not version_file.is_file():
            raise EngineError(
                "not a Unreal Engine root (missing %s): %s"
                % (BUILD_VERSION_REL.as_posix(), root)
            )
        try:
            data = json.loads(version_file.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise EngineError("cannot parse %s: %s" % (version_file, exc)) from exc

        try:
            major = int(data["MajorVersion"])
            minor = int(data.get("MinorVersion", 0))
            patch = int(data.get("PatchVersion", 0))
        except (TypeError, ValueError) as exc:
            raise EngineError(
                "%s has no usable Major/Minor/Patch version fields" % version_file
            ) from exc
        if major < 4 or major > 9:
            raise EngineError(
                "%s reports MajorVersion=%d which is not a UE4/UE5 install"
                % (version_file, major)
            )

        version_str = "%d.%d" % (major, minor)
        return cls(
            name=name or version_str,
            root=root,
            major=major,
            minor=minor,
            patch=patch,
            changelist=int(data.get("Changelist") or 0),
            branch=str(data.get("BranchName") or ""),
            licensee=bool(data.get("IsLicenseeVersion")),
            promoted=bool(data.get("IsPromotedBuild")),
        )


# ---------------------------------------------------------------------------
# Registry (user-registered engines)
# ---------------------------------------------------------------------------

class EngineRegistry:
    """Persistent list of engines the user pointed uebuild at."""

    FORMAT_VERSION = 1

    def __init__(self, path: Optional[Path] = None):
        env_file = os.environ.get("UEBUILD_ENGINES_FILE")
        if path is None and env_file:
            path = Path(env_file)
        self.path = Path(path) if path else util.config_dir() / "engines.json"
        self._entries: List[Dict[str, object]] = []
        self.load()

    # -- persistence -----------------------------------------------------
    def load(self) -> None:
        self._entries = []
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return  # treat a corrupt registry as empty, never crash
        for entry in data.get("engines", []):
            if isinstance(entry, dict) and entry.get("root"):
                self._entries.append(
                    {
                        "name": str(entry.get("name") or ""),
                        "root": str(entry["root"]),
                        "custom": bool(entry.get("custom", True)),
                    }
                )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": self.FORMAT_VERSION,
            "engines": self._entries,
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    # -- operations -------------------------------------------------------
    def entries(self) -> List[EngineInstall]:
        """Registered engines that still parse (stale paths are skipped)."""
        installs: List[EngineInstall] = []
        for entry in self._entries:
            try:
                installs.append(
                    EngineInstall.from_root(entry["root"], name=entry["name"] or None)
                )
            except EngineError:
                continue
        for install in installs:
            install.custom = True
        return installs

    def stale_entries(self) -> List[Dict[str, object]]:
        stale = []
        for entry in self._entries:
            try:
                EngineInstall.from_root(entry["root"])
            except EngineError:
                stale.append(dict(entry))
        return stale

    def _unique_name(self, wanted: str, root: Path) -> str:
        existing = {e["name"] for e in self._entries}
        if wanted not in existing:
            return wanted
        for entry in self._entries:
            if entry["name"] == wanted and _same_path(entry["root"], root):
                return wanted  # re-adding the same root is a no-op
        counter = 2
        while "%s-%d" % (wanted, counter) in existing:
            counter += 1
        return "%s-%d" % (wanted, counter)

    def add(self, root, name: Optional[str] = None) -> EngineInstall:
        install = EngineInstall.from_root(root, name=name)
        install.custom = True
        install.name = self._unique_name(install.name, install.root)
        for entry in self._entries:
            if _same_path(entry["root"], install.root) and not name:
                entry["name"] = install.name
                self.save()
                return install
        self._entries.append(
            {"name": install.name, "root": str(install.root), "custom": True}
        )
        self.save()
        return install

    def remove(self, query) -> bool:
        query_str = str(query)
        before = len(self._entries)
        self._entries = [
            e
            for e in self._entries
            if not (e["name"] == query_str or _same_path(e["root"], Path(query_str)))
        ]
        changed = len(self._entries) != before
        if changed:
            self.save()
        return changed


def _same_path(a, b) -> bool:
    try:
        ra, rb = Path(a).expanduser(), Path(b).expanduser()
        if ra.exists() and rb.exists():
            return os.path.normcase(str(ra.resolve())) == os.path.normcase(
                str(rb.resolve())
            )
        return os.path.normcase(str(ra)) == os.path.normcase(str(rb))
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _windows_registry_roots() -> List[Path]:
    """Epic launcher writes install dirs to the registry on Windows."""
    roots: List[Path] = []
    try:
        import winreg  # type: ignore
    except ImportError:
        return roots
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\EpicGames\Unreal Engine") as key:
                count, _, _ = winreg.QueryInfoKey(key)
                for index in range(count):
                    try:
                        sub_name = winreg.EnumKey(key, index)
                        with winreg.OpenKey(key, sub_name) as sub:
                            value, _ = winreg.QueryValueEx(sub, "InstalledDirectory")
                            roots.append(Path(value))
                    except OSError:
                        continue
        except OSError:
            continue
    return roots


def candidate_roots() -> List[Path]:
    """Directories that *might* be engine roots on this machine."""
    roots: List[Path] = []

    # 1. Explicit environment overrides first.
    for var in ("UE_ROOT", "UE5_ROOT", "UE4_ROOT"):
        value = os.environ.get(var)
        if value:
            roots.append(Path(value).expanduser())

    # 2. Common install locations per OS.
    os_name = util.host_os()
    home = Path.home()
    glob_specs: List[Tuple[Path, str]] = []
    if os_name == "windows":
        for drive in ("C:\\", "D:\\"):
            base = Path(drive) / "Program Files" / "Epic Games"
            glob_specs.append((base, "UE_*"))
            glob_specs.append((base, "UE*"))
        glob_specs.append((home, "UnrealEngine*"))
        roots.extend(_windows_registry_roots())
    elif os_name == "macos":
        glob_specs.append((Path("/Users/Shared/Epic Games"), "UE_*"))
        glob_specs.append((home, "UnrealEngine*"))
    else:
        glob_specs.append((home / "Epic Games", "UE_*"))
        glob_specs.append((home, "UnrealEngine*"))
        glob_specs.append((home, "UE_*"))
        glob_specs.append((Path("/opt"), "UE_*"))
        glob_specs.append((Path("/opt"), "UnrealEngine*"))
        glob_specs.append((Path("/usr/local"), "UE_*"))

    for base, pattern in glob_specs:
        try:
            for match in sorted(base.glob(pattern)):
                if match.is_dir():
                    roots.append(match)
        except OSError:
            continue

    # De-duplicate while keeping order.
    seen = set()
    unique: List[Path] = []
    for root in roots:
        key = os.path.normcase(str(root))
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def discover_engines() -> List[EngineInstall]:
    """Scan the machine for UE4/UE5 installs (launcher or source builds)."""
    installs: List[EngineInstall] = []
    for root in candidate_roots():
        try:
            installs.append(EngineInstall.from_root(root))
        except EngineError:
            continue

    # Dedupe by real path; keep first occurrence.
    unique: List[EngineInstall] = []
    for install in installs:
        if not any(_same_path(i.root, install.root) for i in unique):
            unique.append(install)
    unique.sort(key=lambda i: i.version_tuple, reverse=True)
    return unique


def all_engines(registry: Optional[EngineRegistry] = None) -> List[EngineInstall]:
    """Registered engines first, then anything discovered on the machine."""
    registry = registry or EngineRegistry()
    combined: List[EngineInstall] = []
    for install in registry.entries() + discover_engines():
        if not any(_same_path(i.root, install.root) for i in combined):
            combined.append(install)
    combined.sort(key=lambda i: (i.version_tuple, i.custom), reverse=True)
    return combined


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def _as_install(query: str, engines: Sequence[EngineInstall]) -> Optional[EngineInstall]:
    q = query.strip()
    q_norm = q.lower()
    if q_norm.startswith("ue_"):
        q_norm = q_norm[3:]

    for install in engines:
        if install.name.lower() == q_norm or install.name.lower() == q.lower():
            return install
    for install in engines:
        if install.version_str == q_norm or "%d.%d" % (install.major, install.minor) == q_norm:
            return install
    # Directory-name style: "UE_5.3", folder called "5.3", or a path.
    if os.sep in q or (os.altsep and os.altsep in q) or Path(q).suffix or q_norm.startswith(("~", ".")):
        try:
            return EngineInstall.from_root(Path(q).expanduser())
        except EngineError:
            return None
    for install in engines:
        if install.root.name.lower() == q.lower():
            return install
    # Prefix match: "5" -> newest UE5.x, "5.3" handled above.
    candidates = [i for i in engines if i.version_str.startswith(q_norm)]
    if candidates:
        return candidates[0]
    return None


def resolve_engine(
    query: Optional[str],
    engines: Optional[Sequence[EngineInstall]] = None,
    registry: Optional[EngineRegistry] = None,
) -> EngineInstall:
    """Resolve ``query`` to an :class:`EngineInstall`.

    ``query`` may be ``None``/"latest", "latest-ue4"/"latest-ue5", a version
    ("5.3", "4.27"), a registry name, a directory name ("UE_4.27") or an
    absolute path to an engine root.
    """
    installs = list(engines) if engines is not None else all_engines(registry)
    # Deterministic: newest first, so "latest"/prefix queries behave the same
    # regardless of the order callers pass lists in.
    installs.sort(key=lambda i: i.version_tuple, reverse=True)

    if query is None or query.strip().lower() in ("", "latest"):
        if not installs:
            raise EngineError(
                "no Unreal Engine installs found; register one with "
                "'uebuild engines add <UE_5.x path>' or set UE_ROOT"
            )
        return installs[0]

    q = query.strip().lower()
    if q in ("latest-ue4", "ue4"):
        ue4 = [i for i in installs if not i.is_ue5]
        if not ue4:
            raise EngineError("no UE4 engine found for query '%s'" % query)
        return ue4[0]
    if q in ("latest-ue5", "ue5"):
        ue5 = [i for i in installs if i.is_ue5]
        if not ue5:
            raise EngineError("no UE5 engine found for query '%s'" % query)
        return ue5[0]

    install = _as_install(query, installs)
    if install is not None:
        return install

    # Maybe it is a path that was not part of the known list.
    path = Path(query).expanduser()
    if path.is_dir():
        return EngineInstall.from_root(path)

    raise EngineError(
        "cannot resolve engine '%s'; known installs: %s"
        % (query, ", ".join(i.display for i in installs) or "(none)")
    )


def infer_engine_for_plugin(
    engine_version: Optional[str],
    engines: Sequence[EngineInstall],
) -> Optional[EngineInstall]:
    """Best engine for a plugin's ``EngineVersion`` string (e.g. "5.3.0").

    Prefers an exact major.minor, then same generation, then newest overall.
    Returns ``None`` when nothing is usable or the field is missing.
    """
    if not engine_version or not engines:
        return engines[0] if engines else None
    parts = []
    for chunk in str(engine_version).split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        if digits == "":
            break
        parts.append(int(digits))
    if not parts:
        return engines[0]
    major = parts[0]
    minor = parts[1] if len(parts) > 1 else None
    if minor is not None:
        exact = [i for i in engines if i.major == major and i.minor == minor]
        if exact:
            return exact[0]
    same_gen = [i for i in engines if i.major == major]
    if same_gen:
        return same_gen[0]
    return engines[0]
