# AGENTS.md — Antigravity Agent Guidelines for Unreal Engine 5.8.3

This repository provides tooling, templates, and plugins for **Unreal Engine 5.8.3** plugin development, optimized for **Antigravity IDE** and AI pair programming.

---

## 🛠️ CLI & Build Commands for Antigravity

Antigravity agents should use the `agentic` CLI to scaffold, build, validate, and package UE 5.8.3 plugins:

```bash
# 1. Scaffold a new UE 5.8.3 plugin
python3 -m agentic create <PluginName> --template <runtime|editor|blueprint-library|agent|minimal>

# 2. Build the plugin incrementally via scratch host UBT (default)
python3 -m agentic build <PluginName>

# 3. Package plugin for distribution / Marketplace with RunUAT
python3 -m agentic package <PluginName>

# 4. Validate & lint plugin architecture, C++20 compliance, and header hygiene
python3 -m agentic validate <PluginName>
python3 -m agentic validate --all

# 5. List all discovered plugins in the workspace
python3 -m agentic list
```

---

## 🏗️ Unreal Engine 5.8.3 C++ Standards

When writing or editing C++ code for plugins in this workspace, strictly follow Epic Games' modern UE 5.8 standards:

### 1. C++ Standard & Build.cs
- Use C++20: Ensure `CppStandard = CppStandardVersion.Cpp20;` and `PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;` in `<PluginName>.Build.cs`.
- Module dependencies:
  - Runtime: `"Core"`, `"CoreUObject"`, `"Engine"`
  - Slate UI: `"Slate"`, `"SlateCore"`, `"InputCore"`
  - Editor: `"UnrealEd"`, `"ToolMenus"`, `"WorkspaceMenuStructure"`
  - AI / Agent: `"HTTP"`, `"Json"`, `"JsonUtilities"`, `"PythonScriptPlugin"`

### 2. Pointer Types & Memory Management
- **`TObjectPtr<T>`**: Always use `TObjectPtr<UObject>` for `UPROPERTY()` object references inside UCLASS and USTRUCT. Do not use raw pointers `UObject*` for garbage-collected properties.
- **Weak references**: Use `TWeakObjectPtr<T>` for cross-actor references or caching to avoid preventing garbage collection.
- **Slate & C++ classes**: Use `TSharedPtr<T>`, `TSharedRef<T>`, or `TWeakPtr<T>` for non-UObject classes.

### 3. Naming Conventions & Type Prefixes
- `U` prefix: Classes derived from `UObject` (e.g. `UMyComponent`, `UBlueprintFunctionLibrary`).
- `A` prefix: Classes derived from `AActor` (e.g. `AMyActor`).
- `F` prefix: Structs and non-UObject C++ classes (e.g. `FMyModule`, `FPluginCommands`).
- `I` prefix: Abstract interfaces (e.g. `IModuleInterface`).
- `E` prefix: Enumerations (e.g. `EMyState`).
- `S` prefix: Slate widgets (e.g. `SMyWidget`).
- `T` prefix: Templates.
- `b` prefix: Boolean variables (e.g. `bIsEnabled`).

### 4. Header Hygiene & Include-What-You-Use (IWYU)
- Every header must start with `#pragma once`.
- Include `"CoreMinimal.h"` at the top of headers.
- If a header defines a `UCLASS`, `USTRUCT`, or `UENUM`, the generated header `#include "<HeaderName>.generated.h"` **must** be the very last include.
- Forward declare types in headers (`class UStaticMeshComponent;`) and include full definitions in `.cpp` files.

### 5. Large World Coordinates (LWC)
- `FVector`, `FTransform`, `FMatrix` are 64-bit double precision in UE5. Do not cast down to single-precision float without explicit need.

---

## ⚡ Antigravity IDE Task Integration

Developers can run actions directly through Antigravity's task system (`Ctrl+Shift+B` or Command Palette -> `Tasks: Run Task`):
- `UE5: Create New Plugin (UE 5.8.3)`: Interactive prompt for plugin name and template architecture.
- `UE5: Build Plugin (Development - UBT)`: Compiles the plugin using UBT in a lightweight scratch host.
- `UE5: Package Plugin (RunUAT Distribution)`: Packages standalone redistributable plugin binaries.
- `UE5: Validate & Lint Plugins`: Verifies syntax, module layout, and dependencies.
- `UE5: Build ArenaAgent Plugin`: Builds the in-editor AI agent plugin.
- `UE5: Build AntigravitySourceCodeAccess Plugin`: Builds the Antigravity editor integration plugin.

---

## 🔌 Bundled Plugins

1. **`ArenaAgent`**: An in-editor AI agent plugin for Unreal Engine 5.8.3, featuring a persistent dockable chat window, saved JSON conversations, and 19 editor tools for creating Blueprints, variables, functions, and spawning actors.
2. **`AntigravitySourceCodeAccess`**: Seamlessly integrates the Antigravity Editor as the native source code editor inside Unreal Engine 5.8.3 on Linux, Windows, and macOS.
