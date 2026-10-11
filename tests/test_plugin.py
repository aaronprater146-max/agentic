from __future__ import annotations

import json

import pytest

from uebuild.errors import PluginError
from uebuild.plugin import PluginDescriptor


def test_parse_valid_descriptor(dummy_plugin):
    d = PluginDescriptor.from_file(dummy_plugin)
    assert d.name == "DummyPlugin"
    assert d.file_version == 3
    assert d.friendly_name == "Dummy Plugin"
    assert d.semantic_version == "1.0.0"
    assert d.engine_version == "5.3.0"
    assert d.can_contain_content
    assert not d.content_only
    assert [m.name for m in d.modules] == ["DummyRuntime", "DummyEditor"]
    assert d.modules[1].module_type == "Editor"


def test_accept_folder_instead_of_file(dummy_plugin):
    d = PluginDescriptor.from_file(dummy_plugin.parent)
    assert d.path.name == "DummyPlugin.uplugin"


def test_missing_file_raises(tmp_path):
    with pytest.raises(PluginError):
        PluginDescriptor.from_file(tmp_path / "ghost.uplugin")


def test_wrong_suffix_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    with pytest.raises(PluginError):
        PluginDescriptor.from_file(p)


def test_invalid_json_raises(tmp_path):
    p = tmp_path / "Broken.uplugin"
    p.write_text("{broken", encoding="utf-8")
    with pytest.raises(PluginError):
        PluginDescriptor.from_file(p)


def test_non_object_json_raises(tmp_path):
    p = tmp_path / "List.uplugin"
    p.write_text("[1,2,3]", encoding="utf-8")
    with pytest.raises(PluginError):
        PluginDescriptor.from_file(p)


def test_utf8_bom_tolerated(dummy_plugin):
    text = dummy_plugin.read_text(encoding="utf-8")
    dummy_plugin.write_text("﻿" + text, encoding="utf-8")
    PluginDescriptor.from_file(dummy_plugin)


def test_content_only_descriptor(tmp_path):
    p = tmp_path / "Content.uplugin"
    p.write_text(json.dumps({"FileVersion": 3, "CanContainContent": True}))
    d = PluginDescriptor.from_file(p)
    assert d.content_only
    warnings = d.validate()
    assert any("content-only" in w for w in warnings)


def test_missing_source_dir_warns(tmp_path):
    folder = tmp_path / "NoSource"
    folder.mkdir()
    (folder / "NoSource.uplugin").write_text(
        json.dumps(
            {
                "FileVersion": 3,
                "Modules": [{"Name": "M", "Type": "Runtime"}],
            }
        )
    )
    d = PluginDescriptor.from_file(folder / "NoSource.uplugin")
    warnings = d.validate()
    assert any("Source/" in w for w in warnings)


def test_engine_version_mismatch_warns(dummy_plugin, engine_factory):
    d = PluginDescriptor.from_file(dummy_plugin)
    ue4 = engine_factory("4.27.2")
    warnings = d.validate(engine=ue4)
    assert any("targets UE4" in w or "targets UE5" in w for w in warnings)


def test_engine_minor_mismatch_warns(dummy_plugin, engine_factory):
    d = PluginDescriptor.from_file(dummy_plugin)  # declares 5.3.0
    other = engine_factory("5.4.4", name="UE_5.4")
    warnings = d.validate(engine=other)
    assert any("5.3.0" in w for w in warnings)


def test_exact_engine_match_no_mismatch_warning(dummy_plugin, engine_factory):
    d = PluginDescriptor.from_file(dummy_plugin)
    match = engine_factory("5.3.2")
    warnings = [w for w in d.validate(engine=match) if "descriptor targets" in w]
    assert warnings == []


def test_supported_target_platforms(tmp_path):
    p = tmp_path / "Plat.uplugin"
    p.write_text(
        json.dumps(
            {
                "FileVersion": 3,
                "SupportedTargetPlatforms": ["Win64", "Linux"],
                "Modules": [{"Name": "M", "Type": "Runtime"}],
            }
        )
    )
    d = PluginDescriptor.from_file(p)
    assert d.supports_platform("Win64")
    assert d.supports_platform("Linux")
    assert not d.supports_platform("Mac")
    assert not d.supports_platform("Android")


def test_module_platform_lists_parsed(tmp_path):
    p = tmp_path / "Mod.uplugin"
    p.write_text(
        json.dumps(
            {
                "FileVersion": 3,
                "Modules": [
                    {
                        "Name": "OnlyWindows",
                        "Type": "Runtime",
                        "PlatformAllowList": ["Win64"],
                    },
                    {
                        "Name": "NotLinux",
                        "Type": "Runtime",
                        "BlacklistPlatforms": ["Linux"],
                    },
                ],
            }
        )
    )
    d = PluginDescriptor.from_file(p)
    assert d.modules[0].platform_allowlist == ["Win64"]
    assert d.modules[1].platform_denylist == ["Linux"]  # legacy key honoured
