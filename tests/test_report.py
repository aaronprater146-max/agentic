from __future__ import annotations

import json

from uebuild import report
from uebuild.build import BuildResult


def make_result(success=True, label="Foo | UE5 5.3 | Win64+Linux"):
    return BuildResult(
        label=label,
        plugin_name="Foo",
        engine_name="UE5 5.3.2",
        platforms=["Win64", "Linux"],
        success=success,
        returncode=0 if success else 6,
        uat_exit_code=0 if success else 6,
        command="RunUAT.sh BuildPlugin -Plugin=/x.uplugin",
        log_file="/logs/foo.log",
        package_dir="/out",
        duration_s=65.0,
        error_count=0 if success else 2,
        warning_count=1,
        errors=[] if success else ["ERROR: boom"],
        warnings=["WARNING: meh"],
        package_verified=success,
        message="BUILD SUCCESSFUL" if success else "UAT exited with code 6",
    )


def test_json_report_roundtrip(tmp_path):
    results = [make_result(), make_result(success=False, label="Bar | UE4 4.27 | Win64")]
    path = report.write_json(results, tmp_path / "report.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["summary"]["total"] == 2
    assert data["summary"]["passed"] == 1
    assert data["summary"]["failed"] == 1
    assert data["summary"]["errors"] == 2
    assert data["summary"]["warnings"] == 2
    assert len(data["results"]) == 2
    assert data["results"][1]["plugin"] == "Foo"
    assert data["results"][1]["returncode"] == 6
    assert data["summary"]["tool"].startswith("uebuild")


def test_html_report_contents(tmp_path):
    results = [make_result(), make_result(success=False, label="Bar | UE4 4.27 | Win64")]
    path = report.write_html(results, tmp_path / "report.html")
    html_text = path.read_text(encoding="utf-8")
    assert "uebuild plugin build report" in html_text
    assert "Foo" in html_text and "Bar" in html_text
    assert ">PASS<" in html_text and ">FAIL<" in html_text
    assert "UE4 4.27" in html_text
    assert "ERROR: boom" in html_text
    # escaping check: no raw <script> injection
    assert "<script>" not in html_text


def test_html_escapes_malicious_log_lines(tmp_path):
    bad = make_result(success=False)
    bad.errors = ["<img src=x onerror=alert(1)>"]
    path = report.write_html([bad], tmp_path / "r.html")
    text = path.read_text(encoding="utf-8")
    assert "<img src=x" not in text
    assert "&lt;img" in text


def test_empty_matrix_report(tmp_path):
    path = report.write_html([], tmp_path / "empty.html")
    assert "No builds were run" in path.read_text(encoding="utf-8")
