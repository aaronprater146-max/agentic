"""Unit tests for plugin creator/scaffolding engine."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentic.creator import PluginScaffolder


class TestPluginScaffolder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.scaffolder = PluginScaffolder(engine_version="5.8.3")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitize_name(self):
        self.assertEqual(PluginScaffolder.sanitize_name("MyPlugin"), "MyPlugin")
        self.assertEqual(PluginScaffolder.sanitize_name("MyPlugin.uplugin"), "MyPlugin")
        self.assertEqual(PluginScaffolder.sanitize_name("123Plugin"), "UE5_123Plugin")
        self.assertEqual(PluginScaffolder.sanitize_name("Special-Chars!_Plugin"), "SpecialChars_Plugin")

    def test_create_runtime_template(self):
        plugin_path = self.scaffolder.create("TestRuntime", template="runtime", output_dir=self.temp_dir)
        self.assertTrue(plugin_path.is_dir())

        # Check .uplugin
        uplugin_file = plugin_path / "TestRuntime.uplugin"
        self.assertTrue(uplugin_file.exists())
        with open(uplugin_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["EngineVersion"], "5.8.3")
            self.assertEqual(data["FileVersion"], 3)
            self.assertEqual(len(data["Modules"]), 1)
            self.assertEqual(data["Modules"][0]["Type"], "Runtime")

        # Check Icon
        icon_file = plugin_path / "Resources" / "Icon128.png"
        self.assertTrue(icon_file.exists())
        self.assertGreater(icon_file.stat().st_size, 100)

        # Check Build.cs
        build_cs = plugin_path / "Source" / "TestRuntime" / "TestRuntime.Build.cs"
        self.assertTrue(build_cs.exists())
        self.assertIn("CppStandardVersion.Cpp20", build_cs.read_text())

        # Check Module and Component files
        public_dir = plugin_path / "Source" / "TestRuntime" / "Public"
        private_dir = plugin_path / "Source" / "TestRuntime" / "Private"
        self.assertTrue((public_dir / "TestRuntimeModule.h").exists())
        self.assertTrue((private_dir / "TestRuntimeModule.cpp").exists())
        self.assertTrue((public_dir / "TestRuntimeComponent.h").exists())
        self.assertTrue((private_dir / "TestRuntimeComponent.cpp").exists())

    def test_create_editor_template(self):
        plugin_path = self.scaffolder.create("TestEditor", template="editor", output_dir=self.temp_dir)
        uplugin_file = plugin_path / "TestEditor.uplugin"
        with open(uplugin_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["Modules"][0]["Type"], "Editor")

        public_dir = plugin_path / "Source" / "TestEditor" / "Public"
        self.assertTrue((public_dir / "TestEditorCommands.h").exists())
        self.assertTrue((public_dir / "STestEditorWidget.h").exists())

    def test_create_blueprint_library_template(self):
        plugin_path = self.scaffolder.create("TestBPLib", template="blueprint-library", output_dir=self.temp_dir)
        public_dir = plugin_path / "Source" / "TestBPLib" / "Public"
        bplib_h = public_dir / "TestBPLibBPLibrary.h"
        self.assertTrue(bplib_h.exists())
        self.assertIn("UBlueprintFunctionLibrary", bplib_h.read_text())

    def test_create_agent_template(self):
        plugin_path = self.scaffolder.create("TestAgent", template="agent", output_dir=self.temp_dir)
        uplugin_file = plugin_path / "TestAgent.uplugin"
        with open(uplugin_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["Modules"][0]["Type"], "Editor")
            self.assertTrue(any(p["Name"] == "PythonScriptPlugin" for p in data.get("Plugins", [])))

        public_dir = plugin_path / "Source" / "TestAgent" / "Public"
        self.assertTrue((public_dir / "TestAgentToolRegistry.h").exists())

    def test_invalid_template_raises(self):
        with self.assertRaises(ValueError):
            self.scaffolder.create("BadPlugin", template="non_existent", output_dir=self.temp_dir)


if __name__ == "__main__":
    unittest.main()
