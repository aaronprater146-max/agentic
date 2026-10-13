---
name: ue5-plugin-builder
description: >-
  Workflows, procedures, and runbooks for scaffolding, compiling, validating, and
  packaging Unreal Engine 5.8.3 plugins with Antigravity IDE and Antigravity AI agents.
---

# UE 5.8.3 Plugin Builder Skill for Antigravity

This skill enables Antigravity AI agents to scaffold, develop, build, and package production-grade Unreal Engine 5.8.3 plugins.

---

## 1. Plugin Creation Runbook

To generate a new Unreal Engine 5.8.3 plugin with clean module structure:

```bash
python3 -m agentic create <PluginName> --template <TemplateType>
```

### Supported Templates
- `runtime`: Gameplay modules with ActorComponent, UObject, and modern `TObjectPtr` conventions.
- `editor`: Editor extensions with Nomad dockable Slate tabs, toolbars, and ToolMenus.
- `blueprint-library`: Blueprint Function Library with static BlueprintCallable nodes.
- `agent`: In-editor AI agent assistant pattern with tool registry and JSON-based tool loops.
- `minimal`: Minimal module skeleton implementing `IModuleInterface`.

---

## 2. Compilation & Packaging Runbook

### Developer Incremental Build (UBT Scratch Host)
UBT compiles plugins within a target project context. The build runner automatically maintains a lightweight scratch project and executes UBT:

```bash
python3 -m agentic build <PluginName>
```

Under the hood on Linux:
```bash
"$UNREAL_INSTALL_DIR/Engine/Build/BatchFiles/RunUBT.sh" <PluginName>HostEditor Linux Development -Project="$PWD/.build/scratch_<PluginName>/<PluginName>Host.uproject"
```
Under the hood on Windows:
```cmd
"%UNREAL_INSTALL_DIR%\Engine\Build\BatchFiles\RunUBT.bat" <PluginName>HostEditor Win64 Development -Project="%CD%\.build\scratch_<PluginName>\<PluginName>Host.uproject" -WaitMutex
```

### Marketplace & Distribution Packaging (RunUAT)
To build precompiled binaries packaged for redistribution:

```bash
python3 -m agentic package <PluginName>
```

Under the hood:
```bash
RunUAT.sh BuildPlugin -Plugin="$PWD/<PluginName>/<PluginName>.uplugin" -Package="$PWD/.build/packaged/<PluginName>" -Rocket
```

---

## 3. Pre-Flight Verification & Linting Runbook

To check plugin health before compilation:

```bash
python3 -m agentic validate <PluginName>
# Or validate all plugins in workspace:
python3 -m agentic validate --all
```

Checks performed:
1. `.uplugin` manifest validity, `FileVersion: 3`, and `EngineVersion: "5.8.3"`.
2. Module registration and presence of `Build.cs`.
3. `CppStandardVersion.Cpp20` compliance in `Build.cs`.
4. `#pragma once` include guards.
5. `IMPLEMENT_MODULE` declaration.
6. Generated header `#include "<Header>.generated.h"` ordering when `GENERATED_BODY()` is used.

---

## 4. Antigravity Source Code Editor Integration

When developing plugins, enable the bundled `AntigravitySourceCodeAccess` plugin inside Unreal Editor:
1. Copy `AntigravitySourceCodeAccess` into your project's `Plugins/` directory.
2. In Unreal Editor: **Edit > Editor Preferences > General > Source Code**.
3. Set **Source Code Editor** to **Antigravity**.
4. Double-clicking any C++ class, Blueprint node, or compilation error inside Unreal Editor will now directly jump to the exact file and line in Antigravity IDE.
