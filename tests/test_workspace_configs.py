"""Unit tests for Antigravity workspace files and tasks."""

import json
import unittest
from pathlib import Path


class TestWorkspaceConfigs(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).parent.parent

    def test_tasks_json_validity(self):
        tasks_file = self.repo_root / ".vscode" / "tasks.json"
        self.assertTrue(tasks_file.exists(), ".vscode/tasks.json must exist")

        with open(tasks_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("version"), "2.0.0")
        tasks = data.get("tasks", [])
        self.assertGreater(len(tasks), 0)

        task_labels = [t.get("label") for t in tasks]
        self.assertIn("UE5: Create New Plugin (UE 5.8.3)", task_labels)
        self.assertIn("UE5: Build Plugin (Development - UBT)", task_labels)
        self.assertIn("UE5: Package Plugin (RunUAT Distribution)", task_labels)
        self.assertIn("UE5: Validate & Lint Plugins", task_labels)

    def test_settings_json_validity(self):
        settings_file = self.repo_root / ".vscode" / "settings.json"
        self.assertTrue(settings_file.exists(), ".vscode/settings.json must exist")

        with open(settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("C_Cpp.default.cppStandard"), "c++20")
        self.assertIn("*.uplugin", data.get("files.associations", {}))

    def test_workspace_file_validity(self):
        workspace_file = self.repo_root / "agentic.code-workspace"
        self.assertTrue(workspace_file.exists(), "agentic.code-workspace must exist")

        with open(workspace_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("folders", data)
        self.assertIn("settings", data)

    def test_skill_manifest_validity(self):
        skill_md = self.repo_root / "skills" / "ue5-plugin-builder" / "SKILL.md"
        self.assertTrue(skill_md.exists(), "SKILL.md must exist")
        content = skill_md.read_text(encoding="utf-8")
        self.assertIn("name: ue5-plugin-builder", content)


if __name__ == "__main__":
    unittest.main()
