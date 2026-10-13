"""Unit tests for plugin builder and runner."""

import shutil
import tempfile
import unittest
from pathlib import Path

from agentic.builder import PluginBuilder
from agentic.creator import PluginScaffolder


class TestPluginBuilder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.scaffolder = PluginScaffolder(engine_version="5.8.3")
        self.plugin_path = self.scaffolder.create("BuildTarget", template="runtime", output_dir=self.temp_dir)
        self.builder = PluginBuilder(scratch_root=Path(self.temp_dir) / ".build")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_ubt_dry_run(self):
        res = self.builder.build_ubt(self.plugin_path, dry_run=True)
        self.assertTrue(res.success)
        self.assertTrue(res.dry_run)
        self.assertEqual(res.mode, "ubt")
        self.assertTrue(any("BuildTargetHost.uproject" in arg for arg in res.commands_executed[0]))

        # Verify scratch project files were created
        scratch_dir = Path(self.temp_dir) / ".build" / "scratch_BuildTarget"
        self.assertTrue((scratch_dir / "BuildTargetHost.uproject").exists())
        self.assertTrue((scratch_dir / "Source" / "BuildTargetHost.Target.cs").exists())
        self.assertTrue((scratch_dir / "Source" / "BuildTargetHostEditor.Target.cs").exists())

    def test_package_uat_dry_run(self):
        res = self.builder.package_uat(self.plugin_path, dry_run=True)
        self.assertTrue(res.success)
        self.assertTrue(res.dry_run)
        self.assertEqual(res.mode, "uat")
        self.assertTrue(any("BuildPlugin" in arg for arg in res.commands_executed[0]))
        self.assertTrue(any("BuildTarget.uplugin" in arg for arg in res.commands_executed[0]))

    def test_build_nonexistent_plugin(self):
        res = self.builder.build_ubt(Path(self.temp_dir) / "DoesNotExist")
        self.assertFalse(res.success)
        self.assertEqual(res.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
