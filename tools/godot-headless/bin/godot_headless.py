#!/usr/bin/env python3
"""Ephemeral, headless Godot workflow for Arena agents.

This tool deliberately has no third-party Python dependencies. It scaffolds a
portable Pong proof project, validates its Android/Windows export settings,
runs its in-engine confirmation script, optionally invokes Godot exports, and
bundles a small source product. The engine binary and build cache are runtime
inputs: never add them to this repository.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable


TOOL_ID = "godot-headless"
TOOL_VERSION = "0.1.0"
GODOT_TAG_DEFAULT = "4.7.2-stable"
SCONS_VERSION = "4.10.1"
PASS_MARKER = "PONG_CONFIRMATION_PASS"
SENTINEL_NAME = ".arena-toolbox-ephemeral.json"
TOOL_ROOT = Path(__file__).resolve().parents[1]
PONG_TEMPLATE = TOOL_ROOT / "templates" / "pong"


class ToolError(RuntimeError):
    """An actionable tool failure."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json_dump(value), encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_as_text(command: Iterable[object]) -> list[str]:
    return [str(piece) for piece in command]


def path_from(value: str) -> Path:
    return Path(value).expanduser().resolve()


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise ToolError(f"{description} does not exist or is not a file: {path}")


def require_executable(path: Path, description: str) -> None:
    require_file(path, description)
    if not os.access(path, os.X_OK):
        raise ToolError(f"{description} is not executable: {path}")


def remove_or_fail(path: Path, force: bool, description: str) -> None:
    if not path.exists():
        return
    if not force:
        raise ToolError(f"{description} already exists: {path}. Use --force to replace it.")
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def copy_template(source: Path, destination: Path) -> None:
    ignored_names = {".godot", "build", "__pycache__"}

    def ignore(directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in ignored_names or name.endswith(".pyc")}

    shutil.copytree(source, destination, ignore=ignore)


def project_validation(project: Path) -> dict[str, Any]:
    """Return a deterministic, engine-independent compatibility assessment."""
    project = project.resolve()
    required = {
        "project.godot": project / "project.godot",
        "export_presets.cfg": project / "export_presets.cfg",
        "Pong simulation": project / "scripts" / "pong_simulation.gd",
        "Pong scene": project / "scripts" / "main.gd",
        "Headless confirmation": project / "tests" / "headless_confirmation.gd",
        "Product instructions": project / "README.md",
    }
    missing = [label for label, path in required.items() if not path.is_file()]
    checks: list[dict[str, Any]] = []
    for label, path in required.items():
        checks.append({"name": label, "path": str(path), "passed": path.is_file()})

    project_text = (project / "project.godot").read_text(encoding="utf-8") if not missing else ""
    export_text = (project / "export_presets.cfg").read_text(encoding="utf-8") if not missing else ""

    expectations = {
        "project main scene": 'run/main_scene="res://scripts/main.gd"',
        "Compatibility renderer": 'renderer/rendering_method="gl_compatibility"',
        "landscape viewport": "viewport_width=960",
        "Windows export preset": 'name="Windows 10/11 x86_64"',
        "Windows x86_64": 'binary_format/architecture="x86_64"',
        "Android export preset": 'name="Android 9+ (API 28)"',
        "Android minimum SDK 28": 'gradle_build/min_sdk="28"',
        "Android Gradle export": "gradle_build/use_gradle_build=true",
        "Android arm64": "architectures/arm64-v8a=true",
        "Android armv7": "architectures/armeabi-v7a=true",
    }
    for name, needle in expectations.items():
        haystack = project_text if name in {"project main scene", "Compatibility renderer", "landscape viewport"} else export_text
        checks.append({"name": name, "passed": needle in haystack, "expected": needle})

    failures = [check["name"] for check in checks if not check["passed"]]
    return {
        "project": str(project),
        "passed": not failures,
        "failures": failures,
        "checks": checks,
        "targets": {
            "windows_10_11": {
                "preset": "Windows 10/11 x86_64",
                "architecture": "x86_64",
                "status": "configured",
            },
            "android_9_plus": {
                "preset": "Android 9+ (API 28)",
                "min_sdk": 28,
                "abis": ["arm64-v8a", "armeabi-v7a"],
                "status": "configured",
            },
        },
    }


def run_process(command: list[str], *, cwd: Path, timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise ToolError(f"Could not start executable {command[0]!r}: {error}") from error
    except subprocess.TimeoutExpired as error:
        raise ToolError(f"Command timed out after {timeout} seconds: {' '.join(command)}") from error
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def command_scaffold(args: argparse.Namespace) -> int:
    output = path_from(args.output)
    if output == PONG_TEMPLATE or PONG_TEMPLATE in output.parents:
        raise ToolError("The Pong template cannot be used as the scaffold destination.")
    if not PONG_TEMPLATE.is_dir():
        raise ToolError(f"The packaged Pong template is missing: {PONG_TEMPLATE}")
    remove_or_fail(output, args.force, "Scaffold destination")
    output.parent.mkdir(parents=True, exist_ok=True)
    copy_template(PONG_TEMPLATE, output)
    result = project_validation(output)
    if not result["passed"]:
        raise ToolError("The generated Pong scaffold failed its static validation: " + ", ".join(result["failures"]))
    print(json_dump({"action": "scaffold-pong", "tool": TOOL_ID, "version": TOOL_VERSION, **result}), end="")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    result = project_validation(path_from(args.project))
    payload = {
        "action": "validate-project",
        "tool": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "checked_at": utc_now(),
        **result,
    }
    if args.report:
        write_json(path_from(args.report), payload)
    print(json_dump(payload), end="")
    return 0 if result["passed"] else 1


def command_confirm(args: argparse.Namespace) -> int:
    project = path_from(args.project)
    report_path = path_from(args.report)
    engine = path_from(args.godot)
    validation = project_validation(project)
    payload: dict[str, Any] = {
        "action": "confirm-pong",
        "tool": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "checked_at": utc_now(),
        "project_validation": validation,
        "engine": str(engine),
        "status": "failed",
    }

    try:
        require_executable(engine, "Godot executable")
        if not validation["passed"]:
            raise ToolError("Project validation failed: " + ", ".join(validation["failures"]))
        version_result = run_process([str(engine), "--version"], cwd=project, timeout=args.timeout)
        payload["engine_version"] = version_result
        if version_result["returncode"] != 0:
            raise ToolError("Godot --version failed. See the confirmation report for command output.")
        test_result = run_process(
            [
                str(engine),
                "--headless",
                "--path",
                str(project),
                "--script",
                "res://tests/headless_confirmation.gd",
            ],
            cwd=project,
            timeout=args.timeout,
        )
        payload["headless_confirmation"] = test_result
        marker_seen = PASS_MARKER in test_result["stdout"]
        payload["pass_marker_seen"] = marker_seen
        if test_result["returncode"] != 0:
            raise ToolError("Godot headless confirmation exited non-zero. See the confirmation report for output.")
        if not marker_seen:
            raise ToolError(f"Godot exited successfully but did not emit {PASS_MARKER!r}.")
        payload["status"] = "passed"
    except ToolError as error:
        payload["error"] = str(error)
        write_json(report_path, payload)
        print(json_dump(payload), end="")
        return 1

    write_json(report_path, payload)
    print(json_dump(payload), end="")
    return 0


def command_export(args: argparse.Namespace) -> int:
    project = path_from(args.project)
    engine = path_from(args.godot)
    output = path_from(args.output)
    report_path = path_from(args.report) if args.report else output.with_suffix(output.suffix + ".export-report.json")
    validation = project_validation(project)
    target_map = {
        "windows": "Windows 10/11 x86_64",
        "android": "Android 9+ (API 28)",
    }
    payload: dict[str, Any] = {
        "action": "export",
        "tool": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "checked_at": utc_now(),
        "target": args.target,
        "preset": target_map[args.target],
        "mode": args.mode,
        "project_validation": validation,
        "output": str(output),
        "status": "failed",
    }

    try:
        require_executable(engine, "Godot executable")
        if not validation["passed"]:
            raise ToolError("Project validation failed: " + ", ".join(validation["failures"]))
        if args.target == "android":
            android_sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
            java = shutil.which("java")
            payload["android_prerequisites"] = {"android_sdk": android_sdk, "java": java}
            if not android_sdk:
                raise ToolError("Android export requires ANDROID_SDK_ROOT (or ANDROID_HOME) to point to an installed Android SDK.")
            if not java:
                raise ToolError("Android export requires a Java runtime on PATH (Godot 4.7 uses a compatible JDK).")
        remove_or_fail(output, args.force, "Export output")
        output.parent.mkdir(parents=True, exist_ok=True)
        export_flag = "--export-release" if args.mode == "release" else "--export-debug"
        command = [str(engine), "--headless", "--path", str(project), export_flag, target_map[args.target], str(output)]
        result = run_process(command, cwd=project, timeout=args.timeout)
        payload["export_command"] = result
        if result["returncode"] != 0:
            raise ToolError(
                "Godot export failed. Confirm that matching Godot export templates are installed; "
                "Android additionally needs the SDK/JDK configured in Godot."
            )
        if not output.is_file():
            raise ToolError(f"Godot reported success but did not create the expected output: {output}")
        payload["artifact_size_bytes"] = output.stat().st_size
        payload["artifact_sha256"] = sha256(output)
        payload["status"] = "passed"
    except ToolError as error:
        payload["error"] = str(error)
        write_json(report_path, payload)
        print(json_dump(payload), end="")
        return 1

    write_json(report_path, payload)
    print(json_dump(payload), end="")
    return 0


def iter_product_files(project: Path) -> Iterable[Path]:
    ignored_parts = {".godot", "build", "__pycache__", ".git"}
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if any(part in ignored_parts for part in relative.parts):
            continue
        if path.is_file() and not path.name.endswith((".pyc", ".tmp")):
            yield path


def command_bundle(args: argparse.Namespace) -> int:
    project = path_from(args.project)
    output = path_from(args.output)
    confirmation_report = path_from(args.confirmation_report) if args.confirmation_report else None
    validation = project_validation(project)
    if not validation["passed"]:
        raise ToolError("Cannot bundle an invalid project: " + ", ".join(validation["failures"]))
    if confirmation_report:
        require_file(confirmation_report, "Confirmation report")
    remove_or_fail(output, args.force, "Bundle output")
    output.parent.mkdir(parents=True, exist_ok=True)
    root_name = "arena-pong"
    manifest = {
        "product": "Arena Pong",
        "product_type": "Godot source bundle",
        "tool": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "generated_at": utc_now(),
        "targets": validation["targets"],
        "entry_scene": "res://scripts/main.gd",
        "headless_confirmation": "verification/headless-confirmation.json" if confirmation_report else None,
        "notes": [
            "This bundle intentionally excludes Godot engine binaries, SDKs, export templates, and .godot import caches.",
            "Use the toolbox tool's export command with matching Godot 4.7.2 export templates to produce platform binaries.",
        ],
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in iter_product_files(project):
            archive.write(path, f"{root_name}/{path.relative_to(project).as_posix()}")
        archive.writestr(f"{root_name}/PRODUCT_MANIFEST.json", json_dump(manifest))
        if confirmation_report:
            archive.write(confirmation_report, f"{root_name}/verification/headless-confirmation.json")
    payload = {
        "action": "bundle-product",
        "tool": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "bundle": str(output),
        "size_bytes": output.stat().st_size,
        "sha256": sha256(output),
        "included_confirmation_report": bool(confirmation_report),
        "status": "passed",
    }
    print(json_dump(payload), end="")
    return 0


def safe_extract_tar(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:*") as tar:
        destination_real = destination.resolve()
        for member in tar.getmembers():
            member_path = (destination / member.name).resolve()
            if member_path != destination_real and destination_real not in member_path.parents:
                raise ToolError(f"Refusing unsafe path in source archive: {member.name}")
        tar.extractall(destination)


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": f"{TOOL_ID}/{TOOL_VERSION}"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    except OSError as error:
        raise ToolError(f"Unable to download {url}: {error}") from error


def command_bootstrap(args: argparse.Namespace) -> int:
    """Build a temporary Linux headless confirmation runtime from pinned source.

    Release assets redirect through a host intentionally unavailable in some Arena
    environments. The source fallback only uses codeload.github.com and pypi.org,
    which makes the proof workflow repeatable here as well as in a standard Arena
    sandbox. It builds Godot's smaller 2D template-debug runtime; use a matching
    full editor plus export templates for Windows or Android packaging.
    """
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise ToolError("The source bootstrap currently supports Linux x86_64 Arena workers only. Supply a compatible Godot editor with --godot on other hosts.")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.godot_tag):
        raise ToolError("Godot tag may contain only letters, numbers, periods, underscores, and hyphens.")

    destination = path_from(args.destination)
    remove_or_fail(destination, args.force, "Godot destination")
    workdir = path_from(args.workdir) if args.workdir else destination.parent / ".godot-source-bootstrap"
    if destination.is_relative_to(workdir):
        raise ToolError("Godot destination must not be inside the bootstrap work directory unless --keep-workdir is used.")
    remove_or_fail(workdir, args.force, "Bootstrap work directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)
    archive = workdir / "godot-source.tar.gz"
    source_root = workdir / "source"
    python_deps = workdir / "python-deps"
    shim_dir = workdir / "bin"
    build_log = workdir / "build.log"
    source_url = f"https://codeload.github.com/godotengine/godot/tar.gz/refs/tags/{args.godot_tag}"
    payload: dict[str, Any] = {
        "action": "bootstrap-headless-godot",
        "tool": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "checked_at": utc_now(),
        "source_url": source_url,
        "godot_tag": args.godot_tag,
        "scons_version": SCONS_VERSION,
        "destination": str(destination),
        "workdir": str(workdir),
        "status": "failed",
    }

    try:
        print(f"Downloading Godot source tag {args.godot_tag} from codeload.github.com…", flush=True)
        download_file(source_url, archive)
        payload["source_archive_sha256"] = sha256(archive)
        source_root.mkdir()
        safe_extract_tar(archive, source_root)
        source_dirs = [candidate for candidate in source_root.iterdir() if candidate.is_dir() and (candidate / "SConstruct").is_file()]
        if len(source_dirs) != 1:
            raise ToolError("Could not identify the extracted Godot source directory.")
        source_dir = source_dirs[0]
        payload["source_directory"] = str(source_dir)

        pip_command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--target",
            str(python_deps),
            f"scons=={SCONS_VERSION}",
        ]
        pip_result = run_process(pip_command, cwd=workdir, timeout=args.timeout)
        payload["scons_install"] = pip_result
        if pip_result["returncode"] != 0:
            raise ToolError("Could not install the pinned SCons build dependency. See the bootstrap report.")

        shim_dir.mkdir()
        pkg_config = shim_dir / "pkg-config"
        pkg_config.write_text("#!/bin/sh\n# Headless build disables all system pkg-config integrations.\nexit 0\n", encoding="utf-8")
        pkg_config.chmod(pkg_config.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        environment = os.environ.copy()
        environment["PATH"] = str(shim_dir) + os.pathsep + environment.get("PATH", "")
        environment["PYTHONPATH"] = str(python_deps) + os.pathsep + environment.get("PYTHONPATH", "")
        build_command = [
            sys.executable,
            "-m",
            "SCons",
            "platform=linuxbsd",
            "target=template_debug",
            "headless=yes",
            "disable_3d=yes",
            "vulkan=no",
            "opengl3=no",
            "x11=no",
            "wayland=no",
            "alsa=no",
            "pulseaudio=no",
            "dbus=no",
            "speechd=no",
            "fontconfig=no",
            "udev=no",
            "touch=no",
            "use_sowrap=no",
            "lto=none",
            "debug_symbols=no",
            f"-j{args.jobs}",
        ]
        print("Building a temporary 2D headless Godot runtime from source; this can take several minutes…", flush=True)
        with build_log.open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                build_command,
                cwd=str(source_dir),
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=args.timeout,
                check=False,
                env=environment,
            )
        payload["build_command"] = command_as_text(build_command)
        payload["build_returncode"] = completed.returncode
        if completed.returncode != 0:
            payload["build_log_tail"] = build_log.read_text(encoding="utf-8", errors="replace")[-12000:]
            raise ToolError(f"Godot source build failed with exit code {completed.returncode}. See {build_log}.")

        candidates = sorted((source_dir / "bin").glob("godot.linuxbsd.template_debug*.x86_64"), key=lambda candidate: candidate.stat().st_size, reverse=True)
        if not candidates:
            raise ToolError("Godot built successfully but no Linux x86_64 headless runtime binary was found.")
        built_engine = candidates[0]
        shutil.copy2(built_engine, destination)
        destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        payload["engine_sha256"] = sha256(destination)
        payload["engine_size_bytes"] = destination.stat().st_size
        payload["status"] = "passed"
    except (ToolError, subprocess.TimeoutExpired) as error:
        payload["error"] = str(error)
        if build_log.exists() and "build_log_tail" not in payload:
            payload["build_log_tail"] = build_log.read_text(encoding="utf-8", errors="replace")[-12000:]
        if args.report:
            write_json(path_from(args.report), payload)
        print(json_dump(payload), end="")
        return 1
    finally:
        if not args.keep_workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    if args.report:
        write_json(path_from(args.report), payload)
    print(json_dump(payload), end="")
    return 0


def command_workspace_init(args: argparse.Namespace) -> int:
    workspace = path_from(args.path)
    workspace.mkdir(parents=True, exist_ok=True)
    sentinel = workspace / SENTINEL_NAME
    if sentinel.exists() and not args.force:
        raise ToolError(f"Ephemeral workspace marker already exists: {sentinel}. Use --force to refresh it.")
    write_json(
        sentinel,
        {
            "tool": TOOL_ID,
            "tool_version": TOOL_VERSION,
            "created_at": utc_now(),
            "purpose": "safe deletion after an Arena toolbox run",
        },
    )
    print(json_dump({"action": "workspace-init", "workspace": str(workspace), "marker": str(sentinel), "status": "passed"}), end="")
    return 0


def command_cleanup_workspace(args: argparse.Namespace) -> int:
    workspace = path_from(args.path)
    sentinel = workspace / SENTINEL_NAME
    require_file(sentinel, "Ephemeral workspace marker")
    repository_root = Path.cwd().resolve()
    protected = {Path("/").resolve(), Path.home().resolve(), repository_root}
    if workspace in protected:
        raise ToolError(f"Refusing to delete protected path: {workspace}")
    try:
        marker = json.loads(sentinel.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ToolError(f"Ephemeral workspace marker is malformed: {sentinel}") from error
    if marker.get("tool") != TOOL_ID:
        raise ToolError(f"Ephemeral workspace marker does not belong to {TOOL_ID}: {sentinel}")
    shutil.rmtree(workspace)
    print(json_dump({"action": "cleanup-workspace", "workspace": str(workspace), "status": "passed"}), end="")
    return 0


def command_tool_info(_: argparse.Namespace) -> int:
    payload = {
        "id": TOOL_ID,
        "version": TOOL_VERSION,
        "entry_point": "bin/godot_headless.py",
        "runtime": "Python 3 standard library",
        "headless_confirmation": PASS_MARKER,
        "engine_bootstrap": {
            "method": "temporary Linux source build",
            "godot_tag": GODOT_TAG_DEFAULT,
            "source_host": "codeload.github.com",
            "build_dependency": f"scons=={SCONS_VERSION} from pypi.org",
        },
        "configured_targets": {
            "android": "Android 9+ / API 28, arm64-v8a and armeabi-v7a",
            "windows": "Windows 10/11 x86_64",
        },
        "lifecycle": "scaffold -> confirm -> bundle/upload -> delete marked Arena workspace",
    }
    print(json_dump(payload), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ephemeral headless Godot tool for Arena agents.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    scaffold = subcommands.add_parser("scaffold-pong", help="Copy the Pong proof project to an output directory.")
    scaffold.add_argument("--output", required=True, help="Destination project directory.")
    scaffold.add_argument("--force", action="store_true", help="Replace an existing destination directory.")
    scaffold.set_defaults(handler=command_scaffold)

    validate = subcommands.add_parser("validate", help="Validate a generated Pong project's target settings.")
    validate.add_argument("--project", required=True, help="Pong project directory.")
    validate.add_argument("--report", help="Optional JSON report path.")
    validate.set_defaults(handler=command_validate)

    confirm = subcommands.add_parser("confirm", help="Run the in-engine Pong confirmation script headlessly.")
    confirm.add_argument("--godot", required=True, help="Path to a headless-capable Godot 4.7 editor binary.")
    confirm.add_argument("--project", required=True, help="Pong project directory.")
    confirm.add_argument("--report", required=True, help="JSON confirmation report path.")
    confirm.add_argument("--timeout", type=int, default=120, help="Timeout in seconds for each Godot command (default: 120).")
    confirm.set_defaults(handler=command_confirm)

    export = subcommands.add_parser("export", help="Headlessly export the Pong project after prerequisites are installed.")
    export.add_argument("--godot", required=True, help="Path to a Godot 4.7 editor binary with matching export templates.")
    export.add_argument("--project", required=True, help="Pong project directory.")
    export.add_argument("--target", required=True, choices=("windows", "android"), help="Target export platform.")
    export.add_argument("--output", required=True, help="Output .exe or .apk path.")
    export.add_argument("--mode", choices=("debug", "release"), default="debug", help="Godot export mode.")
    export.add_argument("--report", help="JSON export report path (defaults beside output).")
    export.add_argument("--timeout", type=int, default=600, help="Export timeout in seconds (default: 600).")
    export.add_argument("--force", action="store_true", help="Replace an existing export output.")
    export.set_defaults(handler=command_export)

    bundle = subcommands.add_parser("bundle", help="Create a compact, portable source product ZIP.")
    bundle.add_argument("--project", required=True, help="Pong project directory.")
    bundle.add_argument("--output", required=True, help="Destination ZIP path.")
    bundle.add_argument("--confirmation-report", help="Optional confirmation JSON to include in the product ZIP.")
    bundle.add_argument("--force", action="store_true", help="Replace an existing ZIP.")
    bundle.set_defaults(handler=command_bundle)

    bootstrap = subcommands.add_parser("bootstrap", help="Build a temporary headless Godot confirmation runtime from pinned upstream source.")
    bootstrap.add_argument("--destination", required=True, help="Path for the temporary resulting Godot binary.")
    bootstrap.add_argument("--godot-tag", default=GODOT_TAG_DEFAULT, help=f"Godot source tag (default: {GODOT_TAG_DEFAULT}).")
    bootstrap.add_argument("--workdir", help="Temporary build directory (deleted unless --keep-workdir).")
    bootstrap.add_argument("--keep-workdir", action="store_true", help="Retain source, build cache, and logs after bootstrap.")
    bootstrap.add_argument("--report", help="Optional JSON bootstrap report path.")
    bootstrap.add_argument("--jobs", type=int, default=2, help="Parallel compile jobs (default: 2).")
    bootstrap.add_argument("--timeout", type=int, default=1800, help="Timeout in seconds for dependency installation and build (default: 1800).")
    bootstrap.add_argument("--force", action="store_true", help="Replace an existing destination or work directory.")
    bootstrap.set_defaults(handler=command_bootstrap)

    init = subcommands.add_parser("workspace-init", help="Mark a disposable Arena workspace for safe cleanup.")
    init.add_argument("--path", required=True, help="Workspace to mark as ephemeral.")
    init.add_argument("--force", action="store_true", help="Refresh an existing marker.")
    init.set_defaults(handler=command_workspace_init)

    cleanup = subcommands.add_parser("cleanup-workspace", help="Delete a workspace that has this tool's marker.")
    cleanup.add_argument("--path", required=True, help="Marked workspace to delete.")
    cleanup.set_defaults(handler=command_cleanup_workspace)

    info = subcommands.add_parser("tool-info", help="Print machine-readable tool metadata.")
    info.set_defaults(handler=command_tool_info)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except ToolError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
