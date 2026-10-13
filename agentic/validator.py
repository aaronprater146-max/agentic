"""Plugin validator and linter for Unreal Engine 5.8.3 plugins."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ValidationIssue:
    severity: str  # "ERROR" or "WARNING"
    file: Path
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.file.name}: {self.message}"


@dataclass
class ValidationReport:
    plugin_name: str
    plugin_path: Path
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "ERROR"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "WARNING"]


class PluginValidator:
    def __init__(self, target_engine_version: str = "5.8.3"):
        self.target_engine_version = target_engine_version

    def validate_plugin(self, plugin_dir: str | Path) -> ValidationReport:
        p_dir = Path(plugin_dir).resolve()
        issues: list[ValidationIssue] = []

        if not p_dir.is_dir():
            issues.append(ValidationIssue("ERROR", p_dir, f"Plugin directory '{p_dir}' does not exist."))
            return ValidationReport(plugin_name=p_dir.name, plugin_path=p_dir, is_valid=False, issues=issues)

        # 1. Find .uplugin file
        uplugins = list(p_dir.glob("*.uplugin"))
        if not uplugins:
            issues.append(ValidationIssue("ERROR", p_dir, "No .uplugin manifest found in directory."))
            return ValidationReport(plugin_name=p_dir.name, plugin_path=p_dir, is_valid=False, issues=issues)

        uplugin_file = uplugins[0]
        plugin_name = uplugin_file.stem

        # 2. Parse .uplugin JSON
        try:
            with open(uplugin_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            issues.append(ValidationIssue("ERROR", uplugin_file, f"Invalid JSON syntax in .uplugin: {e}"))
            return ValidationReport(plugin_name=plugin_name, plugin_path=p_dir, is_valid=False, issues=issues)

        # 3. Check .uplugin fields
        if data.get("FileVersion") != 3:
            issues.append(ValidationIssue("WARNING", uplugin_file, f"FileVersion is {data.get('FileVersion')}, expected 3."))

        eng_ver = data.get("EngineVersion")
        if not eng_ver:
            issues.append(ValidationIssue("WARNING", uplugin_file, "Missing 'EngineVersion' field (recommended '5.8.3')."))
        elif not eng_ver.startswith("5.8"):
            issues.append(ValidationIssue("WARNING", uplugin_file, f"EngineVersion is '{eng_ver}', expected 5.8.x."))

        modules = data.get("Modules", [])
        if not modules:
            issues.append(ValidationIssue("ERROR", uplugin_file, "No modules defined in 'Modules' array."))

        # 4. Verify each module
        for mod in modules:
            mod_name = mod.get("Name")
            if not mod_name:
                issues.append(ValidationIssue("ERROR", uplugin_file, "Module descriptor missing 'Name' field."))
                continue

            mod_dir = p_dir / "Source" / mod_name
            if not mod_dir.is_dir():
                # Some plugins have flat Source/ folder
                flat_build_cs = p_dir / "Source" / f"{mod_name}.Build.cs"
                if flat_build_cs.exists():
                    mod_dir = p_dir / "Source"
                else:
                    issues.append(ValidationIssue("ERROR", uplugin_file, f"Module source directory '{mod_dir}' not found."))
                    continue

            # Check Build.cs
            build_cs = mod_dir / f"{mod_name}.Build.cs"
            if not build_cs.exists():
                issues.append(ValidationIssue("ERROR", mod_dir, f"Missing build file '{mod_name}.Build.cs'."))
            else:
                self._validate_build_cs(build_cs, mod_name, issues)

            # Check module header & cpp
            self._validate_module_code(mod_dir, mod_name, issues)

        # 5. Check icon
        icon_path = p_dir / "Resources" / "Icon128.png"
        if not icon_path.exists():
            issues.append(ValidationIssue("WARNING", p_dir, "Missing 'Resources/Icon128.png'."))

        has_errors = any(i.severity == "ERROR" for i in issues)
        return ValidationReport(
            plugin_name=plugin_name,
            plugin_path=p_dir,
            is_valid=not has_errors,
            issues=issues,
        )

    def _validate_build_cs(self, build_cs: Path, module_name: str, issues: list[ValidationIssue]) -> None:
        content = build_cs.read_text(encoding="utf-8", errors="ignore")
        if f"class {module_name}" not in content and "ModuleRules" not in content:
            issues.append(ValidationIssue("WARNING", build_cs, f"Build.cs may not declare a ModuleRules class for '{module_name}'."))

        if "CppStandardVersion.Cpp20" not in content and "CppStandard" not in content:
            issues.append(ValidationIssue("WARNING", build_cs, "Recommended CppStandardVersion.Cpp20 not explicitly configured for UE 5.8."))

    def _validate_module_code(self, mod_dir: Path, module_name: str, issues: list[ValidationIssue]) -> None:
        cpp_files = list(mod_dir.rglob("*.cpp"))
        h_files = list(mod_dir.rglob("*.h"))

        # Check for IMPLEMENT_MODULE
        has_implement_module = False
        for cpp in cpp_files:
            c = cpp.read_text(encoding="utf-8", errors="ignore")
            if "IMPLEMENT_MODULE(" in c:
                has_implement_module = True
                break

        if not has_implement_module and cpp_files:
            issues.append(ValidationIssue("WARNING", mod_dir, f"No IMPLEMENT_MODULE found for module '{module_name}'."))

        # Check header pragma once
        for h in h_files:
            c = h.read_text(encoding="utf-8", errors="ignore")
            if "#pragma once" not in c and "#ifndef" not in c:
                issues.append(ValidationIssue("WARNING", h, "Missing '#pragma once' guard."))

            # If GENERATED_BODY is used, check for generated.h include
            if "GENERATED_BODY()" in c:
                gen_include_match = re.search(r'#include\s+["<]([a-zA-Z0-9_]+)\.generated\.h[">]', c)
                if not gen_include_match:
                    issues.append(ValidationIssue("ERROR", h, "Uses GENERATED_BODY() but missing '#include \"*.generated.h\"'."))
