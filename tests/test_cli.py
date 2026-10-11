from __future__ import annotations

import json

import pytest

from uebuild import cli


def run(argv, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return cli.main(argv)


def add_engine(install, monkeypatch, tmp_path):
    assert run(["engines", "add", str(install.root)], monkeypatch, tmp_path) == 0


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "uebuild" in capsys.readouterr().out


def test_engines_add_list_remove(
    isolated_config, engine_factory, tmp_path, monkeypatch, capsys
):
    e = engine_factory("5.3.2")
    assert run(["engines", "add", str(e.root)], monkeypatch, tmp_path) == 0
    out = capsys.readouterr().out
    assert "registered" in out

    assert run(["engines", "list"], monkeypatch, tmp_path) == 0
    out = capsys.readouterr().out
    assert "5.3.2" in out and "UE5" in out

    assert run(["engines", "list", "--json"], monkeypatch, tmp_path) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["version"] == "5.3.2"

    assert run(["engines", "show", "5.3"], monkeypatch, tmp_path) == 0
    assert "RunUAT" in capsys.readouterr().out

    assert run(["engines", "remove", "5.3"], monkeypatch, tmp_path) == 0

    assert run(["engines", "list"], monkeypatch, tmp_path) == 0
    assert "5.3.2" not in capsys.readouterr().out


def test_engines_add_discover(
    isolated_config, engine_factory, tmp_path, monkeypatch
):
    e = engine_factory("4.27.2")
    monkeypatch.setenv("UE_ROOT", str(e.root))
    assert run(["engines", "add", "--discover"], monkeypatch, tmp_path) == 0
    assert run(["engines", "list", "--no-discover"], monkeypatch, tmp_path) == 0


def test_plugin_info(isolated_config, dummy_plugin, tmp_path, monkeypatch, capsys):
    assert run(["plugin", "info", str(dummy_plugin)], monkeypatch, tmp_path) == 0
    out = capsys.readouterr().out
    assert "DummyPlugin" in out
    assert "DummyRuntime" in out


def test_plugin_info_json(isolated_config, dummy_plugin, tmp_path, monkeypatch, capsys):
    assert run(["plugin", "info", str(dummy_plugin), "--json"], monkeypatch, tmp_path) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["name"] == "DummyPlugin"
    assert data["engineVersion"] == "5.3.0"


def test_plugin_info_missing(isolated_config, tmp_path, monkeypatch, capsys):
    code = run(["plugin", "info", "nope.uplugin"], monkeypatch, tmp_path)
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_build_dry_run(isolated_config, engine_factory, dummy_plugin, tmp_path,
                       monkeypatch, capsys):
    add_engine(engine_factory("5.3.2"), monkeypatch, tmp_path)
    code = run(
        [
            "build",
            "--plugin", str(dummy_plugin),
            "--engine", "5.3",
            "--platforms", "Win64+Linux",
            "--rocket",
            "--dry-run",
        ],
        monkeypatch, tmp_path,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "BuildPlugin" in out
    assert "-Rocket" in out
    assert "-TargetPlatforms=Win64+Linux" in out


def test_build_infers_engine_from_descriptor(
    isolated_config, engine_factory, dummy_plugin, tmp_path, monkeypatch, capsys
):
    add_engine(engine_factory("5.3.2"), monkeypatch, tmp_path)
    code = run(["build", "--plugin", str(dummy_plugin), "--dry-run"],
               monkeypatch, tmp_path)
    assert code == 0
    err = capsys.readouterr().out
    assert "picked" in err


def test_build_end_to_end(isolated_config, engine_factory, dummy_plugin, tmp_path,
                          monkeypatch, capsys):
    add_engine(engine_factory("5.3.2"), monkeypatch, tmp_path)
    report_html = tmp_path / "report.html"
    report_json = tmp_path / "report.json"
    code = run(
        [
            "build",
            "--plugin", str(dummy_plugin),
            "--engine", "5.3",
            "--platforms", "Win64",
            "--quiet",
            "--report-html", str(report_html),
            "--report-json", str(report_json),
        ],
        monkeypatch, tmp_path,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert report_html.is_file()
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert data["summary"]["passed"] == 1
    assert data["summary"]["failed"] == 0


def test_build_failure_exit_code(isolated_config, engine_factory, dummy_plugin,
                                 tmp_path, monkeypatch, capsys):
    add_engine(engine_factory("5.3.2"), monkeypatch, tmp_path)
    monkeypatch.setenv("UEBUILD_FAKE_UAT_FAIL", "error")
    code = run(
        ["build", "--plugin", str(dummy_plugin), "--engine", "5.3",
         "--platforms", "Win64", "--quiet"],
        monkeypatch, tmp_path,
    )
    assert code == 2
    assert "FAIL" in capsys.readouterr().out


def test_matrix_dry_run(isolated_config, engine_factory, dummy_plugin, tmp_path,
                        monkeypatch, capsys):
    add_engine(engine_factory("4.27.2"), monkeypatch, tmp_path)
    add_engine(engine_factory("5.3.2"), monkeypatch, tmp_path)
    cfg = tmp_path / "matrix.json"
    cfg.write_text(json.dumps({
        "defaults": {"platforms": ["Win64"]},
        "jobs": [{"plugin": str(dummy_plugin), "engines": ["4.27", "5.3"]}],
    }), encoding="utf-8")
    code = run(["matrix", "--config", str(cfg), "--dry-run"], monkeypatch, tmp_path)
    assert code == 0
    out = capsys.readouterr().out
    assert out.count("BuildPlugin") == 2
    assert "4.27" in out and "5.3" in out


def test_matrix_end_to_end(isolated_config, engine_factory, dummy_plugin, tmp_path,
                           monkeypatch, capsys):
    add_engine(engine_factory("4.27.2"), monkeypatch, tmp_path)
    add_engine(engine_factory("5.3.2"), monkeypatch, tmp_path)
    cfg = tmp_path / "matrix.json"
    html_path = tmp_path / "matrix-report.html"
    cfg.write_text(json.dumps({
        "defaults": {"platforms": ["Win64"], "outputRoot": str(tmp_path / "dist")},
        "jobs": [{"plugin": str(dummy_plugin), "engines": ["4.27", "5.3"]}],
    }), encoding="utf-8")
    code = run(
        ["matrix", "--config", str(cfg), "--quiet",
         "--report-html", str(html_path)],
        monkeypatch, tmp_path,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "2/2 passed" in out
    text = html_path.read_text(encoding="utf-8")
    assert "UE4 4.27.2" in text and "UE5 5.3.2" in text


def test_matrix_bad_config_exit_code(isolated_config, tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "matrix.json"
    cfg.write_text("{broken", encoding="utf-8")
    code = run(["matrix", "--config", str(cfg)], monkeypatch, tmp_path)
    assert code == 1
