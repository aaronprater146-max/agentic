from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "bin" / "godot_headless.py"


class GodotHeadlessToolTests(unittest.TestCase):
    def run_tool(self, *arguments: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [sys.executable, str(TOOL), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != expect:
            self.fail(
                f"tool returned {completed.returncode}, expected {expect}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        return completed

    def make_fake_godot(self, directory: Path) -> Path:
        engine = directory / "fake-godot.py"
        engine.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--version' in sys.argv:\n"
            "    print('4.7.2-test-headless')\n"
            "else:\n"
            "    print('PONG_CONFIRMATION_PASS')\n",
            encoding="utf-8",
        )
        engine.chmod(engine.stat().st_mode | stat.S_IXUSR)
        return engine

    def test_scaffold_validate_confirm_and_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "arena-pong"
            report = root / "confirmation.json"
            bundle = root / "ArenaPong-source.zip"
            self.run_tool("scaffold-pong", "--output", str(project))

            validation = self.run_tool("validate", "--project", str(project))
            validation_payload = json.loads(validation.stdout)
            self.assertTrue(validation_payload["passed"])
            self.assertEqual(validation_payload["targets"]["android_9_plus"]["min_sdk"], 28)
            self.assertEqual(validation_payload["targets"]["windows_10_11"]["architecture"], "x86_64")

            engine = self.make_fake_godot(root)
            self.run_tool(
                "confirm",
                "--godot",
                str(engine),
                "--project",
                str(project),
                "--report",
                str(report),
            )
            report_payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(report_payload["status"], "passed")
            self.assertTrue(report_payload["pass_marker_seen"])

            self.run_tool(
                "bundle",
                "--project",
                str(project),
                "--confirmation-report",
                str(report),
                "--output",
                str(bundle),
            )
            with zipfile.ZipFile(bundle) as archive:
                names = set(archive.namelist())
            self.assertIn("arena-pong/project.godot", names)
            self.assertIn("arena-pong/verification/headless-confirmation.json", names)
            self.assertIn("arena-pong/PRODUCT_MANIFEST.json", names)
            self.assertFalse(any("/.godot/" in name for name in names))

    def test_bundle_uses_project_display_name_for_metadata_and_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "neon-rally"
            bundle = root / "NeonRallyPong-source.zip"
            self.run_tool("scaffold-pong", "--output", str(project))
            project_file = project / "project.godot"
            project_file.write_text(
                project_file.read_text(encoding="utf-8").replace(
                    'config/name="Arena Pong"', 'config/name="Neon Rally Pong"'
                ),
                encoding="utf-8",
            )
            self.run_tool("bundle", "--project", str(project), "--output", str(bundle))
            with zipfile.ZipFile(bundle) as archive:
                manifest = json.loads(archive.read("neon-rally-pong/PRODUCT_MANIFEST.json"))
                self.assertIn("neon-rally-pong/project.godot", archive.namelist())
            self.assertEqual(manifest["product"], "Neon Rally Pong")

    def test_cleanup_requires_our_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "ephemeral"
            self.run_tool("workspace-init", "--path", str(workspace))
            self.assertTrue(workspace.exists())
            self.run_tool("cleanup-workspace", "--path", str(workspace))
            self.assertFalse(workspace.exists())

    def test_known_global_cache_warning_is_recorded_as_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "arena-pong"
            self.run_tool("scaffold-pong", "--output", str(project))
            engine = root / "global-cache-warning.py"
            engine.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "if '--version' in sys.argv:\n"
                "    print('4.7.2-test-headless')\n"
                "else:\n"
                "    print('PONG_CONFIRMATION_PASS')\n"
                "    print('ERROR: Could not load global script cache.', file=sys.stderr)\n",
                encoding="utf-8",
            )
            engine.chmod(engine.stat().st_mode | stat.S_IXUSR)
            report = root / "warning-confirmation.json"
            self.run_tool(
                "confirm",
                "--godot",
                str(engine),
                "--project",
                str(project),
                "--report",
                str(report),
            )
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "passed")
            self.assertTrue(payload["non_fatal_engine_warnings"])
            self.assertIn("global script cache", payload["non_fatal_engine_warnings"][0]["explanation"])

    def test_confirmation_failure_creates_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "arena-pong"
            self.run_tool("scaffold-pong", "--output", str(project))
            engine = root / "no-marker.py"
            engine.write_text("#!/usr/bin/env python3\nimport sys\nprint('engine output')\n", encoding="utf-8")
            engine.chmod(engine.stat().st_mode | stat.S_IXUSR)
            report = root / "failed-confirmation.json"
            self.run_tool(
                "confirm",
                "--godot",
                str(engine),
                "--project",
                str(project),
                "--report",
                str(report),
                expect=1,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failed")
            self.assertIn("did not emit", payload["error"])


if __name__ == "__main__":
    unittest.main()
