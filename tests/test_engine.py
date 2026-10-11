from __future__ import annotations

import json

import pytest

from uebuild import testing
from uebuild.engine import (
    EngineInstall,
    EngineRegistry,
    all_engines,
    discover_engines,
    infer_engine_for_plugin,
    resolve_engine,
)
from uebuild.errors import EngineError


def test_from_root_parses_build_version(tmp_path):
    root = testing.create_fake_engine(tmp_path / "UE_5.3", version="5.3.2")
    install = EngineInstall.from_root(root)
    assert install.family_label == "UE5"
    assert install.generation == 5
    assert install.is_ue5
    assert install.version_str == "5.3.2"
    assert install.version_tuple == (5, 3, 2, 0)
    assert install.uat_script.name.startswith("RunUAT")
    assert install.uat_script.is_file()


def test_from_root_ue4(tmp_path):
    root = testing.create_fake_engine(tmp_path / "UE_4.27", version="4.27.2")
    install = EngineInstall.from_root(root)
    assert not install.is_ue5
    assert install.family_label == "UE4"
    assert "LinuxArm64" not in install.supported_platforms
    assert "HTML5" in install.supported_platforms


def test_from_root_rejects_missing_dir(tmp_path):
    with pytest.raises(EngineError):
        EngineInstall.from_root(tmp_path / "nope")


def test_from_root_rejects_non_engine_dir(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(EngineError):
        EngineInstall.from_root(tmp_path / "empty")


def test_from_root_rejects_corrupt_version_file(tmp_path):
    root = tmp_path / "UE_bad"
    (root / "Engine" / "Build").mkdir(parents=True)
    (root / "Engine" / "Build" / "Build.version").write_text("{nope", encoding="utf-8")
    with pytest.raises(EngineError):
        EngineInstall.from_root(root)


def test_from_root_rejects_wrong_generation(tmp_path):
    root = tmp_path / "UE_3"
    (root / "Engine" / "Build").mkdir(parents=True)
    (root / "Engine" / "Build" / "Build.version").write_text(
        json.dumps({"MajorVersion": 3, "MinorVersion": 0, "PatchVersion": 0}),
        encoding="utf-8",
    )
    with pytest.raises(EngineError):
        EngineInstall.from_root(root)


def test_registry_roundtrip(isolated_config, tmp_path):
    root = testing.create_fake_engine(tmp_path / "UE_5.4", version="5.4.4")
    registry = EngineRegistry()
    added = registry.add(root)
    assert added.name == "5.4"
    assert added.custom

    fresh = EngineRegistry()
    entries = fresh.entries()
    assert len(entries) == 1
    assert entries[0].root == root
    assert entries[0].version_str == "5.4.4"

    assert fresh.remove("5.4")
    assert EngineRegistry().entries() == []


def test_registry_unique_names(isolated_config, tmp_path):
    first = testing.create_fake_engine(tmp_path / "a", version="5.3.2")
    second = testing.create_fake_engine(tmp_path / "b", version="5.3.2")
    registry = EngineRegistry()
    one = registry.add(first)
    two = registry.add(second)
    assert one.name != two.name


def test_registry_skips_stale_entries(isolated_config, tmp_path):
    root = testing.create_fake_engine(tmp_path / "UE_5.3", version="5.3.2")
    registry = EngineRegistry()
    registry.add(root)
    # wipe the engine, making the registry entry stale
    import shutil

    shutil.rmtree(root)
    assert EngineRegistry().entries() == []
    assert len(EngineRegistry().stale_entries()) == 1


def test_discover_via_env_var(isolated_config, tmp_path, monkeypatch):
    root = testing.create_fake_engine(tmp_path / "UE_5.2", version="5.2.1")
    monkeypatch.setenv("UE_ROOT", str(root))
    found = discover_engines()
    assert any(i.root == root for i in found)


def test_resolve_engine_by_version(isolated_config, engine_factory):
    engines = [engine_factory("4.27.2"), engine_factory("5.3.2"), engine_factory("5.4.4")]
    assert resolve_engine("5.3", engines=engines).version_str == "5.3.2"
    assert resolve_engine("UE_4.27", engines=engines).version_str == "4.27.2"
    assert resolve_engine("latest", engines=engines).version_str == "5.4.4"
    assert resolve_engine("latest-ue4", engines=engines).version_str == "4.27.2"
    assert resolve_engine("latest-ue5", engines=engines).version_str == "5.4.4"
    assert resolve_engine("5", engines=engines).version_str == "5.4.4"


def test_resolve_engine_by_path(isolated_config, engine_factory):
    install = engine_factory("5.5.0")
    resolved = resolve_engine(str(install.root), engines=[])
    assert resolved.version_str == "5.5.0"


def test_resolve_engine_unknown_raises(isolated_config, engine_factory):
    engines = [engine_factory("5.3.2")]
    with pytest.raises(EngineError):
        resolve_engine("7.7", engines=engines)


def test_resolve_engine_none_uses_latest(isolated_config, engine_factory):
    engine_factory("4.26.2")
    newest = engine_factory("5.3.2")
    assert resolve_engine(None, engines=[newest]).root == newest.root


def test_all_engines_merges_registry_and_discovery(
    isolated_config, tmp_path, monkeypatch
):
    reg_root = testing.create_fake_engine(tmp_path / "UE_5.3", version="5.3.2")
    env_root = testing.create_fake_engine(tmp_path / "UE_4.27", version="4.27.2")
    EngineRegistry().add(reg_root)
    monkeypatch.setenv("UE_ROOT", str(env_root))
    combined = all_engines(EngineRegistry())
    roots = {i.root for i in combined}
    assert reg_root in roots and env_root in roots


def test_infer_engine_for_plugin(engine_factory):
    e27 = engine_factory("4.27.2")
    e53 = engine_factory("5.3.2")
    e54 = engine_factory("5.4.4")
    engines = sorted([e27, e53, e54], key=lambda i: i.version_tuple, reverse=True)
    assert infer_engine_for_plugin("5.3.0", engines).root == e53.root
    assert infer_engine_for_plugin("4.27.0", engines).root == e27.root
    # same generation fallback
    assert infer_engine_for_plugin("5.1.0", engines).root == e54.root
    # unknown family -> newest overall
    assert infer_engine_for_plugin("9.0.0", engines).root == e54.root
    # garbage string -> newest overall
    assert infer_engine_for_plugin("custom-branch", engines).root == e54.root
