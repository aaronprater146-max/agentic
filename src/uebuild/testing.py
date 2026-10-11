"""Scaffolding for *fake* engine installs.

uebuild's build pipeline is exercised end-to-end in tests/CI without a real
100 GB Unreal Engine checkout: ``create_fake_engine`` fabricates the minimal
layout uebuild cares about (``Engine/Build/Build.version`` + a RunUAT stub)
and the stub emulates a UAT ``BuildPlugin`` run — writing plausible output,
creating the package directory and honouring ``UEBUILD_FAKE_UAT_FAIL`` to
simulate failures.

This module is NOT used by, and never ships into, real builds.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Optional

BRANCHES = {4: "++UE4+Release-4.27", 5: "++UE5+Release-5.3"}

_FAKE_UAT_PY = '''\
"""Fake UnrealAutomationTool used by uebuild tests. Not a real UAT."""
import json
import os
import pathlib
import shutil
import sys


def arg_value(argv, prefix):
    for arg in argv:
        if arg.startswith(prefix):
            return arg[len(prefix):]
    return None


def main(argv):
    print("Running AutomationTool...")
    print("FakeUAT: BuildPlugin command detected" if "BuildPlugin" in argv
          else "FakeUAT: unexpected command")
    plugin = arg_value(argv, "-Plugin=")
    package = arg_value(argv, "-Package=")
    platforms = arg_value(argv, "-TargetPlatforms=") or "Win64"
    print("Plugin: %s" % plugin)
    print("Package: %s" % package)
    print("TargetPlatforms: %s" % platforms)

    fail_mode = os.environ.get("UEBUILD_FAKE_UAT_FAIL")

    if fail_mode == "warning":
        print("WARNING: Foo.cpp:12: something is deprecated")
        print("warning C4996: \'deprecatedFunc\': was declared deprecated")

    if package:
        name = pathlib.Path(plugin).stem if plugin else "UnknownPlugin"
        dest = pathlib.Path(package) / name
        (dest / "Binaries").mkdir(parents=True, exist_ok=True)
        for platform in platforms.split("+"):
            (dest / "Binaries" / ("%s.dll" % platform)).write_text("fake binary")
        if plugin and pathlib.Path(plugin).is_file():
            shutil.copyfile(plugin, dest / pathlib.Path(plugin).name)
        else:
            (dest / (name + ".uplugin")).write_text(json.dumps({"FileVersion": 3}))
        filter_ini = pathlib.Path(package) / "FilterPlugin.ini"
        filter_ini.write_text("[FilterPlugin]\\n")
        print("Packaged plugin at %s" % dest)

    if fail_mode == "error":
        print("ERROR: FakeCompiler exploded while compiling Foo.cpp")
        print("error C2660: \'Bar\': function does not take 0 arguments")
        print("BUILD FAILED")
        print("AutomationTool exiting with ExitCode=6 (Error_Unknown)")
        return 6

    if fail_mode == "crash":
        print("Log output damaged, exiting without summary")
        return 137

    print("BUILD SUCCESSFUL")
    print("AutomationTool exiting with ExitCode=0 (Success)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

_RUN_SH = """#!/bin/sh
# Fake RunUAT that proxies to the python stub next to it.
exec "$(command -v python3 || command -v python)" "$(dirname "$0")/_fake_uat.py" "$@"
"""

_RUN_BAT = """@echo off
rem Fake RunUAT that proxies to the python stub next to it.
python "%~dp0_fake_uat.py" %*
"""


def create_fake_engine(
    root,
    version: str = "5.3.2",
    changelist: int = 0,
    licensee: bool = False,
) -> Path:
    """Create a fake UE install tree at ``root`` and return the root path.

    Both ``RunUAT.sh`` and ``RunUAT.bat`` stubs are written regardless of the
    host OS so the tree is correct on every platform.
    """
    root = Path(root)
    parts = [p for p in version.split(".")]
    while len(parts) < 3:
        parts.append("0")
    major, minor, patch = (int(parts[0]), int(parts[1]), int(parts[2]))

    build_dir = root / "Engine" / "Build"
    build_dir.mkdir(parents=True, exist_ok=True)
    branch = BRANCHES.get(major, "++UE%d+Release-%d.%d" % (major, major, minor))
    (build_dir / "Build.version").write_text(
        json.dumps(
            {
                "MajorVersion": major,
                "MinorVersion": minor,
                "PatchVersion": patch,
                "Changelist": changelist,
                "CompatibleChangelist": 0,
                "IsLicenseeVersion": 1 if licensee else 0,
                "IsPromotedBuild": 0 if licensee else 1,
                "BranchName": ("++Fortnite+Release" if licensee else branch),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    batch = build_dir / "BatchFiles"
    batch.mkdir(parents=True, exist_ok=True)
    stub = batch / "_fake_uat.py"
    stub.write_text(_FAKE_UAT_PY, encoding="utf-8")
    sh = batch / "RunUAT.sh"
    sh.write_text(_RUN_SH, encoding="utf-8")
    sh.chmod(sh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    (batch / "RunUAT.bat").write_text(_RUN_BAT, encoding="utf-8")

    # A minimal UBT-looking layout for humans poking around.
    (root / "Engine" / "Binaries" / "DotNET").mkdir(parents=True, exist_ok=True)
    return root
