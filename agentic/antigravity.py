"""Antigravity IDE integration and workspace configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def get_tasks_config() -> dict:
    return {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "UE5: Create New Plugin (UE 5.8.3)",
                "type": "shell",
                "command": "python3 -m agentic create ${input:pluginName} --template ${input:pluginTemplate}",
                "problemMatcher": [],
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared"
                },
                "group": {
                    "kind": "build",
                    "isDefault": False
                }
            },
            {
                "label": "UE5: Build Plugin (Development - UBT)",
                "type": "shell",
                "command": "python3 -m agentic build ${input:targetPlugin} --mode ubt",
                "group": {
                    "kind": "build",
                    "isDefault": True
                },
                "problemMatcher": ["$msCompile"],
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared"
                }
            },
            {
                "label": "UE5: Package Plugin (RunUAT Distribution)",
                "type": "shell",
                "command": "python3 -m agentic package ${input:targetPlugin}",
                "group": "build",
                "problemMatcher": ["$msCompile"],
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "panel": "shared"
                }
            },
            {
                "label": "UE5: Validate & Lint Plugins",
                "type": "shell",
                "command": "python3 -m agentic validate --all",
                "problemMatcher": [],
                "presentation": {
                    "echo": True,
                    "reveal": "always"
                }
            },
            {
                "label": "UE5: Clean Build Artifacts",
                "type": "shell",
                "command": "rm -rf .build Saved Intermediate Binaries",
                "windows": {
                    "command": "powershell -Command Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .build, Saved, Intermediate, Binaries"
                },
                "problemMatcher": []
            },
            {
                "label": "UE5: Build ArenaAgent Plugin",
                "type": "shell",
                "command": "python3 -m agentic build ArenaAgent",
                "group": "build",
                "problemMatcher": ["$msCompile"]
            },
            {
                "label": "UE5: Build AntigravitySourceCodeAccess Plugin",
                "type": "shell",
                "command": "python3 -m agentic build AntigravitySourceCodeAccess",
                "group": "build",
                "problemMatcher": ["$msCompile"]
            }
        ],
        "inputs": [
            {
                "id": "pluginName",
                "type": "promptString",
                "description": "Enter the name of your new UE 5.8.3 plugin:",
                "default": "MyCustomPlugin"
            },
            {
                "id": "pluginTemplate",
                "type": "pickString",
                "description": "Choose plugin template architecture:",
                "options": [
                    "runtime",
                    "editor",
                    "blueprint-library",
                    "agent",
                    "minimal"
                ],
                "default": "runtime"
            },
            {
                "id": "targetPlugin",
                "type": "promptString",
                "description": "Path or name of the plugin to build/package:",
                "default": "ArenaAgent"
            }
        ]
    }


def get_settings_config() -> dict:
    return {
        "C_Cpp.default.cppStandard": "c++20",
        "C_Cpp.default.intelliSenseMode": "linux-clang-x64",
        "files.associations": {
            "*.uplugin": "json",
            "*.uproject": "json",
            "*.Build.cs": "csharp",
            "*.Target.cs": "csharp"
        },
        "files.exclude": {
            "**/.git": True,
            "**/.svn": True,
            "**/.hg": True,
            "**/CVS": True,
            "**/.DS_Store": True,
            "**/Thumbs.db": True,
            "**/.build/scratch_*": True,
            "**/Intermediate": True,
            "**/Binaries": True,
            "**/DerivedDataCache": True
        },
        "search.exclude": {
            "**/node_modules": True,
            "**/bower_components": True,
            "**/*.code-search": True,
            "**/Intermediate": True,
            "**/Binaries": True,
            "**/DerivedDataCache": True,
            "**/.build": True
        }
    }


def get_launch_config() -> dict:
    return {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Launch Unreal Editor (Attach Plugin)",
                "type": "cppdbg",
                "request": "launch",
                "program": "${env:UNREAL_INSTALL_DIR}/Engine/Binaries/Linux/UnrealEditor",
                "args": [
                    "${workspaceFolder}/.build/scratch_ArenaAgent/ArenaAgentHost.uproject",
                    "-log",
                    "-NoHotReload"
                ],
                "stopAtEntry": False,
                "cwd": "${workspaceFolder}",
                "environment": [],
                "externalConsole": False,
                "MIMode": "gdb",
                "setupCommands": [
                    {
                        "description": "Enable pretty-printing for gdb",
                        "text": "-enable-pretty-printing",
                        "ignoreFailures": True
                    }
                ]
            }
        ]
    }


def init_antigravity_workspace(target_root: Optional[str | Path] = None) -> list[Path]:
    root = Path(target_root) if target_root else Path.cwd()
    vscode_dir = root / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []

    # 1. tasks.json
    tasks_path = vscode_dir / "tasks.json"
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(get_tasks_config(), f, indent=4)
        f.write("\n")
    created.append(tasks_path)

    # 2. settings.json
    settings_path = vscode_dir / "settings.json"
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(get_settings_config(), f, indent=4)
        f.write("\n")
    created.append(settings_path)

    # 3. launch.json
    launch_path = vscode_dir / "launch.json"
    with open(launch_path, "w", encoding="utf-8") as f:
        json.dump(get_launch_config(), f, indent=4)
        f.write("\n")
    created.append(launch_path)

    # 4. agentic.code-workspace
    workspace_data = {
        "folders": [
            {
                "name": "Agentic (UE 5.8.3)",
                "path": "."
            }
        ],
        "settings": get_settings_config()
    }
    workspace_path = root / "agentic.code-workspace"
    with open(workspace_path, "w", encoding="utf-8") as f:
        json.dump(workspace_data, f, indent=4)
        f.write("\n")
    created.append(workspace_path)

    return created
