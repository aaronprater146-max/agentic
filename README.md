# Agentic — UE 5.8.3 Plugins & Antigravity IDE Automation

A toolkit for scaffolding, developing, and building **Unreal Engine 5.8.3** plugins with **Antigravity IDE** and Antigravity AI agents.

---

## 🚀 Quick Start with Antigravity IDE

1. **Open Workspace**: Open this directory in **Antigravity IDE** (or VS Code).
2. **Build with One Click**:
   - Press `Ctrl+Shift+B` (or `Cmd+Shift+B` on macOS) to run the default build task: `UE5: Build Plugin (Development - UBT)`.
   - Or open Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and type `Tasks: Run Task`.
3. **Available Antigravity Tasks**:
   - `UE5: Create New Plugin (UE 5.8.3)`: Interactively scaffold a new plugin.
   - `UE5: Build Plugin (Development - UBT)`: Fast incremental build via UBT scratch host.
   - `UE5: Package Plugin (RunUAT Distribution)`: Produce precompiled standalone binaries ready for distribution.
   - `UE5: Validate & Lint Plugins`: Verify `.uplugin` schema, C++20 compliance, and header hygiene.
   - `UE5: Build ArenaAgent Plugin`: Compile the bundled in-editor AI agent.
   - `UE5: Build AntigravitySourceCodeAccess Plugin`: Compile the Antigravity editor integration.

---

## 🛠️ CLI Usage (`agentic`)

The workspace includes the `agentic` CLI tool in `./bin/agentic` (or run via `python3 -m agentic`):

### 1. Creating UE 5.8.3 Plugins
```bash
./bin/agentic create <PluginName> --template <template>
```

#### Available Templates
| Template | Description | Key Modules |
| --- | --- | --- |
| `runtime` | Gameplay module with modern ActorComponent, `TObjectPtr`, and Blueprint events | `Core`, `CoreUObject`, `Engine` |
| `editor` | Editor extension with dockable Nomad Slate tab and ToolMenus integration | `Slate`, `SlateCore`, `UnrealEd`, `ToolMenus` |
| `blueprint-library` | Blueprint Function Library with static BlueprintCallable nodes | `Core`, `CoreUObject`, `Engine` |
| `agent` | In-editor AI agent assistant pattern with persistent tool registry | `HTTP`, `Json`, `Slate`, `UnrealEd` |
| `minimal` | Clean, lightweight `IModuleInterface` module | `Core`, `CoreUObject`, `Engine` |

Example:
```bash
# Create an inventory runtime plugin
./bin/agentic create InventorySystem --template runtime

# Create an editor level-design utility
./bin/agentic create LevelTools --template editor
```

Each generated plugin includes:
- `<PluginName>.uplugin` with `"EngineVersion": "5.8.3"` and `"FileVersion": 3`
- `Source/<PluginName>/<PluginName>.Build.cs` targeting C++20 (`CppStandard = CppStandardVersion.Cpp20;`)
- Clean public/private C++ source files implementing `IModuleInterface`
- Valid 128x128 icon in `Resources/Icon128.png`
- Plugin-specific `AGENTS.md` and build scripts

---

### 2. Building Plugins Easily with Antigravity

UnrealBuildTool (UBT) requires plugins to compile in the context of an engine target. `agentic build` automates this cross-platform (Linux, Windows, macOS) by:
1. Detecting your Unreal Engine 5.8 installation (from `UNREAL_INSTALL_DIR`, `UE5_8_DIR`, `ARENA_UE_PATH`, Windows registry, or `/opt`).
2. Maintaining a lightweight host scratch project in `.build/scratch_<PluginName>/`.
3. Executing UBT for lightning-fast incremental compilation:

```bash
# Build any plugin
./bin/agentic build ArenaAgent

# Build a newly created plugin
./bin/agentic build InventorySystem

# Dry-run mode (previews generated scratch project and exact command line)
./bin/agentic build ArenaAgent --dry-run
```

---

### 3. Packaging Plugins for Distribution (RunUAT)

To create precompiled, standalone binaries for sharing with team members or publishing to the Fab / Epic Marketplace:

```bash
./bin/agentic package ArenaAgent
```

This runs Epic's `RunUAT BuildPlugin -Plugin=... -Package=... -Rocket` and outputs clean binaries to `.build/packaged/<PluginName>/`.

---

### 4. Validating & Linting Plugins

Verify plugin health, schema, C++20 compliance, and header hygiene:

```bash
./bin/agentic validate --all
```

Checks performed:
- Valid `.uplugin` JSON, `FileVersion: 3`, and `EngineVersion: "5.8.3"`
- Existence of `Build.cs` and `CppStandardVersion.Cpp20`
- Inclusion of `#pragma once` in headers
- Module registration via `IMPLEMENT_MODULE`
- `#include "<Class>.generated.h"` ordering when `GENERATED_BODY()` is used

---

## 🔌 Bundled Plugins

### 1. `ArenaAgent` (UE 5.8.3 In-Editor AI Agent)
An editor plugin that integrates **Arena.ai** into the Unreal Editor:
- **Persistent Chat Panel**: Dockable tab via *Window → Arena Agent Chat*.
- **Saved Conversations**: Stored as JSON under `Saved/ArenaAgent/Conversations/`.
- **19 In-Editor Tools**: Create Blueprints, add SCS components, typed variables, functions, event nodes, spawn actors, and run Python.
- See [`ArenaAgent/README.md`](ArenaAgent/README.md) for full documentation.

### 2. `AntigravitySourceCodeAccess` (Source Code Editor Integration)
Integrates **Antigravity IDE** as the native source code editor inside Unreal Engine 5.8:
- Double-click any C++ class or compilation error inside Unreal Editor to jump directly to the code in Antigravity.
- Tested and supported across Linux, Windows, and macOS.
- Enable in Unreal Editor under **Edit > Editor Preferences > General > Source Code > Antigravity**.

---

## 🤖 Antigravity AI Pair Programming (`AGENTS.md`)

This repository is equipped with project-level AI rules and skills:
- **`AGENTS.md`**: Provides context, Epic Games C++ coding standards (such as `TObjectPtr`, memory management, and IWYU), and CLI commands for AI agents.
- **`skills/ue5-plugin-builder/`**: Antigravity Skill providing runbooks for plugin scaffolding, building, headless test execution, and troubleshooting.

---

## 🧪 Testing

Run the test suite with Python's built-in `unittest`:

```bash
python3 -m unittest discover tests
```
