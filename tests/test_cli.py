"""Unit tests for agentic CLI commands."""

import shutil
import tempfile
import unittest
from pathlib import Path

from agentic.cli import main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_info(self):
        code = main(["info"])
        self.assertEqual(code, 0)

    def test_cli_list(self):
        code = main(["list"])
        self.assertEqual(code, 0)

    def test_cli_create_and_validate(self):
        code = main(["create", "CliTestPlugin", "-t", "blueprint-library", "-o", self.temp_dir])
        self.assertEqual(code, 0)

        created = Path(self.temp_dir) / "CliTestPlugin"
        self.assertTrue((created / "CliTestPlugin.uplugin").exists())

        val_code = main(["validate", str(created)])
        self.assertEqual(val_code, 0)

    def test_cli_build_dry_run(self):
        main(["create", "DryRunPlugin", "-t", "runtime", "-o", self.temp_dir])
        created = Path(self.temp_dir) / "DryRunPlugin"
        code = main(["build", str(created), "--dry-run"])
        self.assertEqual(code, 0)

    def test_cli_package_dry_run(self):
        main(["create", "DryRunPkg", "-t", "runtime", "-o", self.temp_dir])
        created = Path(self.temp_dir) / "DryRunPkg"
        code = main(["package", str(created), "--dry-run"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
