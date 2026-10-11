"""Scan UnrealAutomationTool / UBT output for errors, warnings and exit codes."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

# Error-level patterns. UAT/UBT output mixes MSBuild, clang and C# styles.
_ERROR_RES = [
    re.compile(r"\bERROR:\s"),
    re.compile(r"\berror\s+[A-Z]{1,4}\d+\s*:"),            # error C2660:, error LNK2019:, error CS1002:
    re.compile(r"\berror\s*:", re.IGNORECASE),             # clang: file.cpp:12: error: ...
    re.compile(r"\bfatal error\b", re.IGNORECASE),
    re.compile(r"\bBUILD FAILED\b"),
    re.compile(r"\bAutomationException\b"),
    re.compile(r"\bUnhandled Exception:\b"),
]

_WARNING_RES = [
    re.compile(r"\bWARNING:\s"),
    re.compile(r"\bwarning\s+[A-Z]{1,4}\d+\s*:"),          # warning C4100:
    re.compile(r"\bwarning\s*:", re.IGNORECASE),           # clang / LogCompile: Warning:
]

_MS_ERROR_SUMMARY = re.compile(r"\b(\d+)\s+Error\(s\)")
_MS_WARNING_SUMMARY = re.compile(r"\b(\d+)\s+Warning\(s\)")

# Lines that mention errors but are benign conclusions.
_IGNORE_RES = [
    re.compile(r"ExitCode=0"),
    re.compile(r"BUILD SUCCEEDED"),
]

_EXIT_CODE_RES = [
    re.compile(r"AutomationTool exiting with ExitCode=(\d+)"),
    re.compile(r"RunUAT ERROR.*?ExitCode=(\d+)", re.IGNORECASE),
    re.compile(r"ExitCode=(\d+)\s*\("),
]

MAX_SAMPLES = 50


def classify_line(line: str) -> Optional[str]:
    """Return ``"error"``, ``"warning"`` or ``None`` for one log line."""
    for pattern in _IGNORE_RES:
        if pattern.search(line):
            return None
    m = _MS_ERROR_SUMMARY.search(line)
    if m:
        return "error" if int(m.group(1)) > 0 else None
    m = _MS_WARNING_SUMMARY.search(line)
    if m:
        return "warning" if int(m.group(1)) > 0 else None
    for pattern in _ERROR_RES:
        if pattern.search(line):
            return "error"
    for pattern in _WARNING_RES:
        if pattern.search(line):
            return "warning"
    return None


def extract_exit_code(lines: Iterable[str]) -> Optional[int]:
    code: Optional[int] = None
    for line in lines:
        for pattern in _EXIT_CODE_RES:
            m = pattern.search(line)
            if m:
                code = int(m.group(1))
    return code


@dataclass
class ScanResult:
    error_count: int = 0
    warning_count: int = 0
    error_lines: List[str] = field(default_factory=list)
    warning_lines: List[str] = field(default_factory=list)
    exit_code: Optional[int] = None
    build_failed_line: bool = False

    @property
    def failed(self) -> bool:
        return (
            self.build_failed_line
            or (self.exit_code not in (None, 0))
            or self.error_count > 0
        )


def scan_lines(lines: Iterable[str]) -> ScanResult:
    result = ScanResult()
    for raw in lines:
        line = raw.rstrip("\r\n")
        kind = classify_line(line)
        if kind == "error":
            result.error_count += 1
            if len(result.error_lines) < MAX_SAMPLES:
                result.error_lines.append(line.strip())
            if "BUILD FAILED" in line:
                result.build_failed_line = True
        elif kind == "warning":
            result.warning_count += 1
            if len(result.warning_lines) < MAX_SAMPLES:
                result.warning_lines.append(line.strip())
    return result


def scan_text(text: str) -> ScanResult:
    result = scan_lines(text.splitlines())
    result.exit_code = extract_exit_code(text.splitlines())
    if result.exit_code not in (None, 0):
        result.build_failed_line = result.build_failed_line or result.exit_code != 0
    return result
