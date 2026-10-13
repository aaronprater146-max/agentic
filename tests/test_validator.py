"""Unit tests for plugin validator and linter."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentic.creator import PluginScaffolder
from agentic.validator import PluginValidator


class TestPluginValidator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.scaffolder = PluginScaffolder(engine_version="5.8.3")
        self.validator = PluginValidator(target_engine_version="5.8.3")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_scaffolded_plugins(self):
        for tmpl in ["runtime", "editor", "blueprint-library", "agent", "minimal"]:
            p_path = self.scaffolder.create(f"Valid_{tmpl.replace('-', '_')}", template=tmpl, output_dir=self.temp_dir)
            report = self.validator.validate_plugin(p_path)
            self.assertTrue(report.is_valid, f"Failed on template {tmpl}: {[str(e) for e in report.errors]}")
            self.assertEqual(len(report.errors), 0)

    def test_missing_uplugin_detected(self):
        empty_dir = Path(self.temp_dir) / "EmptyPlugin"
        empty_dir.mkdir()
        report = self.validator.validate_plugin(empty_dir)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("No .uplugin manifest found" in e.message for e in report.errors))

    def test_corrupted_json_detected(self):
        corrupt_dir = Path(self.temp_dir) / "CorruptPlugin"
        corrupt_dir.mkdir()
        (corrupt_dir / "CorruptPlugin.uplugin").write_text("{ unclosed json: ", encoding="utf-8")
        report = self.validator.validate_plugin(corrupt_dir)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("Invalid JSON syntax" in e.message for e in report.errors))

    def test_missing_generated_header_detected(self):
        p_path = self.scaffolder.create("MissingGenHeader", template="runtime", output_dir=self.temp_dir)
        comp_h = p_path / "Source" / "MissingGenHeader" / "Public" / "MissingGenHeaderComponent.h"
        # Overwrite component header with GENERATED_BODY() but remove generated.h include
        comp_h.write_text("#pragma once\nUCLASS()\nclass UMissing : public UObject { GENERATED_BODY() };\n")
        report = self.validator.validate_plugin(p_path)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("Uses GENERATED_BODY() but missing '#include \"*.generated.h\"'" in e.message for e in report.errors))


if __name__ == "__main__":
    unittest.main()
