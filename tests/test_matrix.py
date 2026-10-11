from __future__ import annotations

import json

import pytest

from uebuild import matrix
from uebuild.build import run_build
from uebuild.errors import ConfigError
from uebuild.testing import create_fake_engine


def write_matrix(tmp_path, data) -> str:
    path = tmp_path / "matrix.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def two_engines(tmp_path):
    create_fake_engine(tmp_path / "UE_4.27", version="4.27.2")
    create_fake_engine(tmp_path / "UE_5.3", version="5.3.2")


def test_load_matrix_missing(tmp_path):
    with pytest.raises(ConfigError):
        matrix.load_matrix(tmp_path / "nope.json")


def test_load_matrix_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{bad", encoding="utf-8")
    with pytest.raises(ConfigError):
        matrix.load_matrix(path)


def test_load_matrix_requires_jobs(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"jobs": []}), encoding="utf-8")
    with pytest.raises(ConfigError):
        matrix.load_matrix(path)


def test_comments_tolerated(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(
        "// plugin build matrix\n" + json.dumps({"jobs": [{"engines": []}]}),
        encoding="utf-8",
    )
    data = matrix.load_matrix(path)
    assert "jobs" in data


def test_expand_matrix_multi_engine(tmp_path, dummy_plugin, engine_factory):
    e27 = engine_factory("4.27.2")
    e53 = engine_factory("5.3.2")
    cfg = {
        "_base_dir": tmp_path,
        "defaults": {"platforms": ["Win64"], "outputRoot": "dist", "rocket": True},
        "jobs": [
            {"plugin": str(dummy_plugin), "engines": ["4.27", "5.3"]},
        ],
    }
    requests = matrix.expand_matrix(cfg, engines=[e27, e53])
    assert len(requests) == 2
    engines_used = {r.engine.version_str for r in requests}
    assert engines_used == {"4.27.2", "5.3.2"}
    for req in requests:
        assert req.platforms == ["Win64"]
        assert req.rocket
        assert str(req.output).endswith(dummy_plugin.stem + "/" + req.engine.version_str)


def test_expand_matrix_per_engine_options(tmp_path, dummy_plugin, engine_factory):
    e27 = engine_factory("4.27.2")
    e53 = engine_factory("5.3.2")
    cfg = {
        "_base_dir": tmp_path,
        "defaults": {},
        "jobs": [
            {
                "plugin": str(dummy_plugin),
                "engines": [
                    {"name": "4.27", "platforms": ["Win64"]},
                    {"name": "5.3", "platforms": "Win64+Linux"},
                ],
            }
        ],
    }
    requests = matrix.expand_matrix(cfg, engines=[e53, e27])
    by_engine = {r.engine.version_str: r for r in requests}
    assert by_engine["4.27.2"].platforms == ["Win64"]
    assert by_engine["5.3.2"].platforms == ["Win64", "Linux"]


def test_expand_matrix_defaults_platforms(tmp_path, dummy_plugin, engine_factory):
    e53 = engine_factory("5.3.2")
    cfg = {
        "_base_dir": tmp_path,
        "jobs": [{"plugin": str(dummy_plugin), "engines": ["5.3"]}],
    }
    requests = matrix.expand_matrix(cfg, engines=[e53])
    assert requests[0].platforms == ["Win64", "Mac", "Linux"]


def test_expand_matrix_output_template(tmp_path, dummy_plugin, engine_factory):
    e53 = engine_factory("5.3.2")
    cfg = {
        "_base_dir": tmp_path,
        "jobs": [
            {
                "plugin": str(dummy_plugin),
                "engines": ["5.3"],
                "output": "packages/{plugin}/{engine}/{platforms}",
            }
        ],
        "defaults": {"platforms": ["Win64", "LinuxArm64"]},
    }
    requests = matrix.expand_matrix(cfg, engines=[e53])
    out = str(requests[0].output)
    assert "DummyPlugin/5.3.2/Win64+LinuxArm64" in out.replace("\\", "/"), out


def test_expand_matrix_unknown_engine_is_error(tmp_path, dummy_plugin, engine_factory):
    e53 = engine_factory("5.3.2")
    cfg = {
        "_base_dir": tmp_path,
        "jobs": [{"plugin": str(dummy_plugin), "engines": ["9.9"]}],
    }
    from uebuild.errors import EngineError

    with pytest.raises(EngineError):
        matrix.expand_matrix(cfg, engines=[e53])


def test_expand_matrix_job_missing_plugin_key(tmp_path, engine_factory):
    e53 = engine_factory("5.3.2")
    with pytest.raises(ConfigError):
        matrix.expand_matrix(
            {"_base_dir": tmp_path, "jobs": [{"engines": ["5.3"]}]}, engines=[e53]
        )


def test_matrix_end_to_end_with_fake_uat(tmp_path, dummy_plugin, engine_factory):
    e27 = engine_factory("4.27.2")
    e53 = engine_factory("5.3.2")
    cfg = matrix.load_matrix(
        write_matrix(
            tmp_path,
            {
                "defaults": {"platforms": ["Win64"], "outputRoot": "dist"},
                "jobs": [{"plugin": str(dummy_plugin), "engines": ["4.27", "5.3"]}],
            },
        )
    )
    requests = matrix.expand_matrix(cfg, engines=[e27, e53])
    results = [run_build(r, echo=False) for r in requests]
    assert all(r.success for r in results), [r.message for r in results]
    outputs = {str(r.package_dir) for r in results}
    assert len(outputs) == 2
