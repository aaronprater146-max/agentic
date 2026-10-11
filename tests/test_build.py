from __future__ import annotations

import json
import os

import pytest

from uebuild import util
from uebuild.build import (
    GLOBAL_UAT_ARGS,
    BuildRequest,
    find_packaged_uplugin,
    run_build,
)


def make_request(engine, plugin, output, **kwargs):
    defaults = dict(
        plugin=plugin,
        engine=engine,
        output=output,
        platforms=["Win64", "Linux"],
    )
    defaults.update(kwargs)
    return BuildRequest(**defaults)


# ---------------------------------------------------------------------------
# command construction
# ---------------------------------------------------------------------------

def test_command_shape(engine_factory, dummy_plugin, tmp_path):
    req = make_request(engine_factory("5.3.2"), dummy_plugin, tmp_path / "out")
    cmd = req.command()
    assert cmd[0].endswith(("RunUAT.sh", "RunUAT.bat"))
    assert cmd[1] == "BuildPlugin"
    assert any(a == "-Plugin=%s" % dummy_plugin for a in cmd)
    assert any(a.startswith("-Package=") for a in cmd)
    assert "-TargetPlatforms=Win64+Linux" in cmd
    for global_arg in GLOBAL_UAT_ARGS:
        assert global_arg in cmd
    assert "-Rocket" not in cmd


def test_command_flags_and_extras(engine_factory, dummy_plugin, tmp_path):
    req = make_request(
        engine_factory("4.27.2"),
        dummy_plugin,
        tmp_path / "out",
        platforms=["Win64"],
        rocket=True,
        create_subfolder=True,
        no_debug_info=True,
        strict_includes=True,
        no_host_platform=True,
        extra_uat_args={"Unversioned": True, "VS2022": True, "SubTarget": "Extra"},
    )
    cmd = req.command()
    for flag in ("-Rocket", "-CreateSubFolder", "-NoDebugInfo",
                 "-StrictIncludes", "-NoHostPlatform", "-Unversioned"):
        assert flag in cmd
    assert "-SubTarget=Extra" in cmd
    # global args come last
    assert cmd[-len(GLOBAL_UAT_ARGS):] == GLOBAL_UAT_ARGS


def test_command_string_quoting(engine_factory, dummy_plugin, tmp_path):
    weird = tmp_path / "dir with spaces"
    weird.mkdir()
    req = make_request(engine_factory("5.3.2"), dummy_plugin, weird)
    assert "'" in req.command_string() or '"' in req.command_string()


def test_popen_args_windows_uses_shell(engine_factory, dummy_plugin, tmp_path):
    req = make_request(engine_factory("5.3.2"), dummy_plugin, tmp_path / "out")
    args, shell = req.popen_args(host="windows")
    assert shell is True
    assert isinstance(args, str)
    assert "BuildPlugin" in args
    args, shell = req.popen_args(host="linux")
    assert shell is False
    assert isinstance(args, list)


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

def test_validate_ok(engine_factory, dummy_plugin, tmp_path):
    req = make_request(engine_factory("5.3.2"), dummy_plugin, tmp_path / "out")
    fatal, warnings = req.validate()
    assert fatal == []


def test_validate_missing_plugin(engine_factory, tmp_path):
    req = make_request(engine_factory("5.3.2"), tmp_path / "ghost.uplugin",
                       tmp_path / "out")
    fatal, _ = req.validate()
    assert any("plugin not found" in f for f in fatal)


def test_validate_missing_uat(engine_factory, dummy_plugin, tmp_path):
    engine = engine_factory("5.3.2")
    os.remove(engine.uat_script)
    req = make_request(engine, dummy_plugin, tmp_path / "out")
    fatal, _ = req.validate()
    assert any("RunUAT" in f for f in fatal)


def test_validate_unknown_platform(engine_factory, dummy_plugin, tmp_path):
    req = make_request(engine_factory("5.3.2"), dummy_plugin, tmp_path / "out",
                       platforms=["Amiga"])
    fatal, _ = req.validate()
    assert any("Amiga" in f for f in fatal)


def test_validate_console_platform_warns(engine_factory, dummy_plugin, tmp_path):
    req = make_request(engine_factory("5.3.2"), dummy_plugin, tmp_path / "out",
                       platforms=["PS5"])
    fatal, warnings = req.validate()
    assert fatal == []
    assert any("PS5" in w for w in warnings)


def test_validate_generation_mismatch_warns(engine_factory, ue4_plugin, tmp_path):
    ue5 = engine_factory("5.3.2")
    req = make_request(ue5, ue4_plugin, tmp_path / "out", platforms=["Win64"])
    fatal, warnings = req.validate()
    assert any("UE4" in w and "UE5" in w for w in warnings)


# ---------------------------------------------------------------------------
# executing builds against the fake RunUAT
# ---------------------------------------------------------------------------

def test_run_build_success(engine_factory, dummy_plugin, tmp_path):
    req = make_request(engine_factory("5.3.2"), dummy_plugin, tmp_path / "out")
    result = run_build(req, echo=False)
    assert result.success, result.message
    assert result.returncode == 0
    assert result.uat_exit_code == 0
    assert result.package_verified
    assert result.packaged_uplugin and result.packaged_uplugin.endswith(".uplugin")
    assert os.path.isfile(result.log_file)
    assert "BUILD SUCCESSFUL" in open(result.log_file, encoding="utf-8").read()
    assert result.duration_s >= 0


def test_run_build_failure(engine_factory, dummy_plugin, tmp_path):
    req = make_request(
        engine_factory("5.3.2"),
        dummy_plugin,
        tmp_path / "out",
        env={"UEBUILD_FAKE_UAT_FAIL": "error"},
    )
    result = run_build(req, echo=False)
    assert not result.success
    assert result.returncode == 6
    assert result.uat_exit_code == 6
    assert result.error_count >= 1
    assert any("C2660" in line for line in result.errors)


def test_run_build_crash_without_uat_summary(engine_factory, dummy_plugin, tmp_path):
    req = make_request(
        engine_factory("5.3.2"),
        dummy_plugin,
        tmp_path / "out",
        env={"UEBUILD_FAKE_UAT_FAIL": "crash"},
    )
    result = run_build(req, echo=False)
    assert not result.success
    assert result.returncode == 137
    assert result.uat_exit_code is None
    assert "137" in result.message


def test_run_build_warning_still_success(engine_factory, dummy_plugin, tmp_path):
    req = make_request(
        engine_factory("5.3.2"),
        dummy_plugin,
        tmp_path / "out",
        env={"UEBUILD_FAKE_UAT_FAIL": "warning"},
    )
    result = run_build(req, echo=False)
    assert result.success
    assert result.warning_count >= 1


def test_run_build_validation_failure_short_circuits(engine_factory, tmp_path):
    req = make_request(engine_factory("5.3.2"), tmp_path / "ghost.uplugin",
                       tmp_path / "out")
    result = run_build(req, echo=False)
    assert not result.success
    assert result.returncode is None
    assert "validation failed" in result.message


def test_run_build_echoes_output(engine_factory, dummy_plugin, tmp_path, capsys):
    req = make_request(engine_factory("5.3.2"), dummy_plugin, tmp_path / "out")
    run_build(req, echo=True)
    captured = capsys.readouterr()
    assert "Running AutomationTool" in captured.err
    assert "TargetPlatforms: Win64+Linux" in captured.err


def test_find_packaged_uplugin(tmp_path):
    assert find_packaged_uplugin(tmp_path / "none") is None
    nested = tmp_path / "pkg" / "MyPlugin" / "Binaries"
    nested.mkdir(parents=True)
    (nested.parent / "MyPlugin.uplugin").write_text("{}")
    found = find_packaged_uplugin(tmp_path / "pkg")
    assert found and found.name == "MyPlugin.uplugin"
