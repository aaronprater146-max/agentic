from __future__ import annotations

import json
from pathlib import Path

import pytest

from uebuild import testing
from uebuild.engine import EngineInstall, EngineRegistry

DUMMY_UPLUGIN = {
    "FileVersion": 3,
    "Version": 1,
    "VersionName": "1.0.0",
    "FriendlyName": "Dummy Plugin",
    "Description": "A plugin used to exercise uebuild.",
    "Category": "Testing",
    "CreatedBy": "uebuild",
    "CanContainContent": True,
    "IsBetaVersion": False,
    "IsExperimentalVersion": False,
    "Installed": False,
    "EngineVersion": "5.3.0",
    "Modules": [
        {"Name": "DummyRuntime", "Type": "Runtime", "LoadingPhase": "Default"},
        {"Name": "DummyEditor", "Type": "Editor", "LoadingPhase": "Default"},
    ],
}


@pytest.fixture()
def engine_factory(tmp_path):
    """Create fake engine installs under tmp_path."""
    created = []

    def make(version="5.3.2", name=None):
        root = tmp_path / ("UE_%s" % ".".join(version.split(".")[:2]))
        if name:
            root = tmp_path / name
        testing.create_fake_engine(root, version=version)
        install = EngineInstall.from_root(root)
        created.append(install)
        return install

    return make


@pytest.fixture()
def dummy_plugin(tmp_path) -> Path:
    plugin_dir = tmp_path / "plugins" / "DummyPlugin"
    (plugin_dir / "Source" / "DummyRuntime").mkdir(parents=True)
    path = plugin_dir / "DummyPlugin.uplugin"
    path.write_text(json.dumps(DUMMY_UPLUGIN, indent=2), encoding="utf-8")
    (plugin_dir / "Content").mkdir()
    return path


@pytest.fixture()
def ue4_plugin(tmp_path) -> Path:
    plugin_dir = tmp_path / "plugins" / "Legacy"
    (plugin_dir / "Source" / "LegacyRuntime").mkdir(parents=True)
    data = dict(DUMMY_UPLUGIN)
    data["EngineVersion"] = "4.27.0"
    data["Modules"] = [
        {"Name": "LegacyRuntime", "Type": "Runtime", "LoadingPhase": "Default"}
    ]
    path = plugin_dir / "Legacy.uplugin"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


@pytest.fixture()
def isolated_config(tmp_path, monkeypatch):
    """Isolate the engine registry + discovered env engines."""
    cfg = tmp_path / "uebuild-config"
    monkeypatch.setenv("UEBUILD_CONFIG_DIR", str(cfg))
    for var in ("UE_ROOT", "UE4_ROOT", "UE5_ROOT", "UEBUILD_ENGINES_FILE",
                "UEBUILD_FAKE_UAT_FAIL", "NO_COLOR"):
        monkeypatch.delenv(var, raising=False)
    return cfg


@pytest.fixture()
def registry(isolated_config) -> EngineRegistry:
    return EngineRegistry()
