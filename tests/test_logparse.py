from __future__ import annotations

from uebuild import logparse


def test_classify_uat_error():
    assert logparse.classify_line("ERROR: Unable to instantiate module") == "error"


def test_classify_msbuild_error():
    line = r"C:\p\Foo.cpp(12): error C2660: 'Bar': function does not take 1 arg"
    assert logparse.classify_line(line) == "error"


def test_classify_clang_error():
    assert logparse.classify_line("Foo.cpp:12:5: error: use of undeclared identifier 'x'") == "error"


def test_classify_cs_error():
    assert logparse.classify_line("Program.cs(1,1): error CS1002: ; expected") == "error"


def test_classify_fatal_and_build_failed():
    assert logparse.classify_line("c1xx: fatal error C1083: Cannot open file") == "error"
    assert logparse.classify_line("BUILD FAILED") == "error"


def test_classify_warnings():
    assert logparse.classify_line("WARNING: missing precompiled manifest") == "warning"
    assert logparse.classify_line("Foo.cpp(9): warning C4100: 'a': unreferenced") == "warning"
    assert logparse.classify_line("LogCompile: Warning: bad thing") == "warning"


def test_benign_lines_are_neutral():
    assert logparse.classify_line("Took 12.34s to run UnrealBuildTool.exe, ExitCode=0") is None
    assert logparse.classify_line("AutomationTool exiting with ExitCode=0 (Success)") is None
    assert logparse.classify_line("BUILD SUCCEEDED") is None
    assert logparse.classify_line("     0 Warning(s)") is None
    assert logparse.classify_line("     0 Error(s)") is None


def test_msbuild_summary_counts():
    assert logparse.classify_line("     3 Error(s)") == "error"
    assert logparse.classify_line("     2 Warning(s)") == "warning"


def test_scan_text_counts_and_samples():
    text = "\n".join(
        [
            "UAT: starting",
            "WARNING: deprecated thing",
            "WARNING: another deprecated thing",
            "ERROR: boom",
            "BUILD FAILED",
            "AutomationTool exiting with ExitCode=6 (Error_Unknown)",
        ]
    )
    result = logparse.scan_text(text)
    assert result.error_count == 2
    assert result.warning_count == 2
    assert result.exit_code == 6
    assert result.failed
    assert any("boom" in line for line in result.error_lines)


def test_scan_success_not_failed():
    text = "\n".join(["BUILD SUCCESSFUL", "AutomationTool exiting with ExitCode=0 (Success)"])
    result = logparse.scan_text(text)
    assert not result.failed
    assert result.exit_code == 0


def test_error_samples_capped():
    text = "\n".join("ERROR: e%d" % i for i in range(200))
    result = logparse.scan_text(text)
    assert result.error_count == 200
    assert len(result.error_lines) == logparse.MAX_SAMPLES
