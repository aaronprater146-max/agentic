"""Construct and run headless ``RunUAT BuildPlugin`` invocations.

``BuildPlugin`` is the officially supported UnrealAutomationTool command for
compiling + packaging a plugin without opening the editor::

    RunUAT.sh BuildPlugin -Plugin=/path/Foo.uplugin \
        -Package=/out/dir -TargetPlatforms=Win64+Linux -Rocket -NoP4 -UTF8Output

The command line is identical for UE4 and UE5; the only difference is which
RunUAT script you point at and which target platforms each engine supports.
"""
from __future__ import annotations

import os
import queue
import shlex
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, TextIO, Tuple, Union

from . import logparse, util
from .engine import ALL_KNOWN_PLATFORMS, CONSOLE_PLATFORMS, DEFAULT_PLATFORMS, EngineInstall
from .errors import BuildValidationError
from .plugin import PluginDescriptor
from .util import colorize

DEFAULT_TIMEOUT_SECONDS = 4 * 3600  # UBT full compiles are slow; be generous.

#: Global flags passed to every UAT run to make it safe for CI machines.
GLOBAL_UAT_ARGS = ["-NoP4", "-UTF8Output"]

#: Extra environment for child processes.
CHILD_ENV = {
    "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    "DOTNET_NOLOGO": "1",
}

ExtraArg = Union[str, bool]


@dataclass
class BuildRequest:
    """Everything needed for one BuildPlugin invocation."""

    plugin: Path
    engine: EngineInstall
    output: Path
    platforms: List[str] = field(default_factory=lambda: list(DEFAULT_PLATFORMS))
    rocket: bool = False
    create_subfolder: bool = False
    no_debug_info: bool = False
    strict_includes: bool = False
    no_host_platform: bool = False
    extra_uat_args: Dict[str, ExtraArg] = field(default_factory=dict)
    timeout: Optional[float] = DEFAULT_TIMEOUT_SECONDS
    logs_dir: Optional[Path] = None
    env: Dict[str, str] = field(default_factory=dict)
    label: str = ""

    # ------------------------------------------------------------------
    def plugin_abs(self) -> Path:
        return Path(self.plugin).expanduser().resolve()

    def output_abs(self) -> Path:
        return Path(self.output).expanduser().resolve()

    def default_label(self) -> str:
        return "%s | %s %s | %s" % (
            self.plugin_abs().stem,
            self.engine.family_label,
            self.engine.version_str,
            "+".join(self.platforms),
        )

    # ------------------------------------------------------------------
    def command(self) -> List[str]:
        """The full argument vector, no shell involvement."""
        cmd = [
            str(self.engine.uat_script),
            "BuildPlugin",
            "-Plugin=%s" % self.plugin_abs(),
            "-Package=%s" % self.output_abs(),
            "-TargetPlatforms=%s" % "+".join(self.platforms),
        ]
        if self.rocket:
            cmd.append("-Rocket")
        if self.create_subfolder:
            cmd.append("-CreateSubFolder")
        if self.no_debug_info:
            cmd.append("-NoDebugInfo")
        if self.strict_includes:
            cmd.append("-StrictIncludes")
        if self.no_host_platform:
            cmd.append("-NoHostPlatform")
        for key in sorted(self.extra_uat_args):
            value = self.extra_uat_args[key]
            if value is True:
                cmd.append("-%s" % key)
            elif value in (False, None, ""):
                continue
            else:
                cmd.append("-%s=%s" % (key, value))
        cmd.extend(GLOBAL_UAT_ARGS)
        return cmd

    def command_string(self) -> str:
        try:
            return shlex.join(self.command())
        except AttributeError:  # Python 3.9 fallback
            return " ".join(shlex.quote(part) for part in self.command())

    def popen_args(self, host: Optional[str] = None):
        """Return ``(args, shell)`` suitable for ``subprocess.Popen``.

        ``.bat`` files cannot be exec()ed directly on Windows; run them via
        ``cmd /c`` with a properly quoted command line string.
        """
        host = host or util.host_os()
        if host == "windows":
            return subprocess.list2cmdline(self.command()), True
        return [str(c) for c in self.command()], False

    # ------------------------------------------------------------------
    def validate(self) -> Tuple[List[str], List[str]]:
        """Return ``(fatal_errors, warnings)``."""
        fatal: List[str] = []
        warnings: List[str] = []
        if not self.plugin_abs().is_file():
            fatal.append("plugin not found: %s" % self.plugin_abs())
        if not self.engine.uat_script.is_file():
            fatal.append(
                "RunUAT script missing: %s (is '%s' a complete engine install?)"
                % (self.engine.uat_script, self.engine.root)
            )
        if not self.platforms:
            fatal.append("no target platforms selected")
        for platform in self.platforms:
            if platform not in ALL_KNOWN_PLATFORMS:
                fatal.append("unknown target platform: %s" % platform)
            elif platform not in self.engine.supported_platforms:
                if platform in CONSOLE_PLATFORMS:
                    warnings.append(
                        "%s requires the platform SDK and Epic approval; "
                        "build will fail on machines without it" % platform
                    )
                else:
                    warnings.append(
                        "%s is not a known UE%d platform; passing it through anyway"
                        % (platform, self.engine.generation)
                    )
            try:
                descriptor = PluginDescriptor.from_file(self.plugin_abs())
                if not descriptor.supports_platform(platform):
                    warnings.append(
                        "plugin SupportedTargetPlatforms does not include %s" % platform
                    )
            except Exception:
                pass
        try:
            descriptor = PluginDescriptor.from_file(self.plugin_abs())
            warnings.extend(descriptor.validate(engine=self.engine))
        except Exception:
            pass
        return fatal, warnings


@dataclass
class BuildResult:
    label: str
    plugin_name: str
    engine_name: str
    platforms: List[str]
    success: bool
    returncode: Optional[int]
    uat_exit_code: Optional[int]
    command: str
    log_file: Optional[str]
    package_dir: str
    duration_s: float
    error_count: int = 0
    warning_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    package_verified: bool = False
    packaged_uplugin: Optional[str] = None
    message: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "label": self.label,
            "plugin": self.plugin_name,
            "engine": self.engine_name,
            "platforms": self.platforms,
            "success": self.success,
            "returncode": self.returncode,
            "uatExitCode": self.uat_exit_code,
            "command": self.command,
            "logFile": self.log_file,
            "packageDir": self.package_dir,
            "durationSeconds": round(self.duration_s, 2),
            "errorCount": self.error_count,
            "warningCount": self.warning_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "packageVerified": self.package_verified,
            "packagedUplugin": self.packaged_uplugin,
            "message": self.message,
        }


def find_packaged_uplugin(package_dir: Path) -> Optional[Path]:
    """Locate the packaged .uplugin produced by BuildPlugin, if any."""
    if not package_dir.is_dir():
        return None
    for candidate in sorted(package_dir.rglob("*.uplugin")):
        return candidate
    return None


class _StreamScanner:
    """Feed output lines through the classifier; keep bounded samples."""

    def __init__(self, tail: int = 400):
        self.scan = logparse.ScanResult()
        self.tail_lines: deque = deque(maxlen=tail)
        self.total_lines = 0

    def feed(self, line: str) -> Optional[str]:
        self.total_lines += 1
        self.tail_lines.append(line)
        kind = logparse.classify_line(line)
        if kind == "error":
            self.scan.error_count += 1
            if len(self.scan.error_lines) < logparse.MAX_SAMPLES:
                self.scan.error_lines.append(line.strip())
            if "BUILD FAILED" in line:
                self.scan.build_failed_line = True
        elif kind == "warning":
            self.scan.warning_count += 1
            if len(self.scan.warning_lines) < logparse.MAX_SAMPLES:
                self.scan.warning_lines.append(line.strip())
        return kind


def _reader_thread(stream, out_queue: "queue.Queue[Optional[str]]") -> None:
    try:
        for line in iter(stream.readline, ""):
            out_queue.put(line)
    except (OSError, ValueError):
        pass
    finally:
        out_queue.put(None)  # sentinel: stream closed


def run_build(
    request: BuildRequest,
    echo: bool = True,
    stream: Optional[TextIO] = None,
    line_callback: Optional[Callable[[str, Optional[str]], None]] = None,
) -> BuildResult:
    """Run one BuildPlugin build headlessly and collect the outcome."""
    stream = stream or sys.stderr
    use_color = util.supports_color(stream)
    label = request.label or request.default_label()
    plugin_name = request.plugin_abs().stem
    engine_name = "%s %s" % (request.engine.family_label, request.engine.version_str)
    package_dir = request.output_abs()

    fatal, _notes = request.validate()
    base_kwargs = dict(
        label=label,
        plugin_name=plugin_name,
        engine_name=engine_name,
        platforms=list(request.platforms),
        command=request.command_string(),
        package_dir=str(package_dir),
    )
    if fatal:
        return BuildResult(
            success=False,
            returncode=None,
            uat_exit_code=None,
            log_file=None,
            duration_s=0.0,
            message="validation failed: " + "; ".join(fatal),
            **base_kwargs,
        )

    logs_dir = Path(request.logs_dir) if request.logs_dir else package_dir.parent / "uebuild-logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_name = "%s_%s_%s.log" % (
        util.sanitize_filename(plugin_name),
        util.sanitize_filename(request.engine.version_str),
        util.utc_stamp(),
    )
    log_path = logs_dir / log_name

    env = dict(os.environ)
    env.update(CHILD_ENV)
    env.update(request.env)

    pop_args, use_shell = request.popen_args()
    started = time.monotonic()
    if echo:
        print(
            colorize("uebuild:", "cyan", "bold", enabled=use_color),
            "%s" % label,
            file=stream,
        )
        print("  $ %s" % request.command_string(), file=stream)
        print("  log: %s" % log_path, file=stream)

    scanner = _StreamScanner()
    returncode: Optional[int] = None
    timed_out = False
    launch_error: Optional[str] = None

    try:
        with open(log_path, "w", encoding="utf-8", errors="replace") as log_fh:
            proc = subprocess.Popen(
                pop_args,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,  # strictly headless: never prompt
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=str(request.engine.root),
            )
            lines: "queue.Queue[Optional[str]]" = queue.Queue()
            reader = threading.Thread(
                target=_reader_thread, args=(proc.stdout, lines), daemon=True
            )
            reader.start()

            eof = False
            while not eof:
                if request.timeout and (time.monotonic() - started) > request.timeout:
                    timed_out = True
                    proc.kill()
                try:
                    line = lines.get(timeout=0.2)
                except queue.Empty:
                    if proc.poll() is not None and reader.is_alive() is False:
                        break
                    continue
                if line is None:
                    eof = True
                    break
                line = line.rstrip("\r\n")
                log_fh.write(line + "\n")
                kind = scanner.feed(line)
                if line_callback:
                    line_callback(line, kind)
                if echo:
                    if kind == "error":
                        print(colorize(line, "red", enabled=use_color), file=stream)
                    elif kind == "warning":
                        print(colorize(line, "yellow", enabled=use_color), file=stream)
                    else:
                        print(line, file=stream)
            reader.join(timeout=5)
            returncode = proc.wait()
    except OSError as exc:
        launch_error = str(exc)

    duration = time.monotonic() - started
    exit_code = logparse.extract_exit_code(scanner.tail_lines)

    packaged = find_packaged_uplugin(package_dir)
    package_verified = packaged is not None

    if launch_error:
        success, message = False, "failed to launch UAT: %s" % launch_error
    elif timed_out:
        success, message = False, "build timed out after %s" % util.human_duration(request.timeout or 0)
    elif returncode != 0:
        tail = ""
        for candidate in reversed(scanner.tail_lines):
            if candidate.strip():
                tail = candidate.strip()
                break
        success = False
        message = "UAT exited with code %s%s" % (
            returncode,
            " — " + tail if tail else "",
        )
    elif exit_code not in (None, 0):
        success, message = False, "AutomationTool reported ExitCode=%d" % exit_code
    elif scanner.scan.build_failed_line:
        success, message = False, "log contains 'BUILD FAILED'"
    elif not package_verified:
        success = True
        message = (
            "UAT succeeded but no packaged .uplugin found under %s "
            "(content-only plugin or unexpected output layout)" % package_dir
        )
    else:
        success, message = True, "BUILD SUCCESSFUL"

    return BuildResult(
        success=success,
        returncode=returncode,
        uat_exit_code=exit_code,
        log_file=str(log_path),
        duration_s=duration,
        error_count=scanner.scan.error_count,
        warning_count=scanner.scan.warning_count,
        errors=scanner.scan.error_lines,
        warnings=scanner.scan.warning_lines,
        package_verified=package_verified,
        packaged_uplugin=str(packaged) if packaged else None,
        message=message,
        **base_kwargs,
    )
