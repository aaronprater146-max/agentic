"""Plugin scaffolding generator for Unreal Engine 5.8.3 plugins."""

from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path
from typing import Optional


def _generate_png_icon(width: int = 128, height: int = 128, r: int = 41, g: int = 128, b: int = 185) -> bytes:
    """Generates a valid 128x128 PNG icon in pure Python using zlib."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        for x in range(width):
            # Draw rounded border
            is_border = (x < 3 or x >= width - 3 or y < 3 or y >= height - 3)
            # Subtle gradient
            factor = 0.8 + 0.4 * (y / height)
            cr = min(255, int(r * factor))
            cg = min(255, int(g * factor))
            cb = min(255, int(b * factor))
            if is_border:
                raw.extend((255, 255, 255))
            else:
                raw.extend((cr, cg, cb))

    compressed = zlib.compress(bytes(raw), level=9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", compressed)
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


class PluginScaffolder:
    VALID_TEMPLATES = {
        "runtime": "Runtime gameplay component and module for UE 5.8",
        "editor": "Editor extension with dockable Slate tab and toolbar actions",
        "blueprint-library": "Blueprint Function Library with static BlueprintCallable nodes",
        "agent": "AI agent in-editor assistant pattern with tool execution",
        "minimal": "Minimal clean skeleton module",
    }

    def __init__(self, engine_version: str = "5.8.3"):
        self.engine_version = engine_version

    @staticmethod
    def sanitize_name(name: str) -> str:
        clean = name.strip()
        if clean.endswith(".uplugin"):
            clean = clean[:-8]
        clean = re.sub(r"[^a-zA-Z0-9_]", "", clean)
        if not clean or clean[0].isdigit():
            clean = "UE5_" + clean
        return clean

    def create(
        self,
        name: str,
        template: str = "runtime",
        output_dir: Optional[str | Path] = None,
        author: str = "Agentic Developer",
        description: Optional[str] = None,
        category: Optional[str] = None,
        with_antigravity: bool = True,
    ) -> Path:
        plugin_name = self.sanitize_name(name)
        tmpl = template.lower().strip()
        if tmpl not in self.VALID_TEMPLATES:
            raise ValueError(f"Unknown template '{template}'. Valid choices: {list(self.VALID_TEMPLATES.keys())}")

        target_root = Path(output_dir) if output_dir else Path.cwd() / "Plugins"
        plugin_dir = target_root / plugin_name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        is_editor = tmpl in ("editor", "agent")
        default_cat = "Editor" if is_editor else "Gameplay"
        desc = description or f"{plugin_name} plugin for Unreal Engine {self.engine_version}."
        cat = category or default_cat

        # 1. Create .uplugin manifest
        self._write_uplugin(plugin_dir, plugin_name, tmpl, author, desc, cat)

        # 2. Create Icon
        res_dir = plugin_dir / "Resources"
        res_dir.mkdir(exist_ok=True)
        (res_dir / "Icon128.png").write_bytes(_generate_png_icon())

        # 3. Create Source directory structure
        source_dir = plugin_dir / "Source" / plugin_name
        public_dir = source_dir / "Public"
        private_dir = source_dir / "Private"
        public_dir.mkdir(parents=True, exist_ok=True)
        private_dir.mkdir(parents=True, exist_ok=True)

        # 4. Build.cs
        self._write_build_cs(source_dir, plugin_name, tmpl)

        # 5. Core Module Header and Source
        self._write_module_files(public_dir, private_dir, plugin_name, tmpl)

        # 6. Template specific files
        if tmpl == "runtime":
            self._write_runtime_template(public_dir, private_dir, plugin_name)
        elif tmpl == "editor":
            self._write_editor_template(public_dir, private_dir, plugin_name)
        elif tmpl == "blueprint-library":
            self._write_bp_library_template(public_dir, private_dir, plugin_name)
        elif tmpl == "agent":
            self._write_agent_template(public_dir, private_dir, plugin_name)

        # 7. Helper build scripts
        self._write_helper_scripts(plugin_dir, plugin_name)

        # 8. README.md & AGENTS.md
        self._write_docs(plugin_dir, plugin_name, tmpl, desc)

        return plugin_dir

    def _write_uplugin(
        self,
        plugin_dir: Path,
        plugin_name: str,
        template: str,
        author: str,
        description: str,
        category: str,
    ) -> None:
        module_type = "Editor" if template in ("editor", "agent") else "Runtime"
        loading_phase = "PostEngineInit" if module_type == "Editor" else "Default"
        if template == "blueprint-library":
            loading_phase = "PreDefault"

        uplugin_data = {
            "FileVersion": 3,
            "Version": 1,
            "VersionName": "1.0.0",
            "FriendlyName": plugin_name,
            "Description": description,
            "Category": category,
            "CreatedBy": author,
            "CreatedByURL": "",
            "DocsURL": "",
            "MarketplaceURL": "",
            "SupportURL": "",
            "EngineVersion": self.engine_version,
            "CanContainContent": False,
            "IsBetaVersion": False,
            "IsExperimentalVersion": False,
            "Installed": False,
            "Modules": [
                {
                    "Name": plugin_name,
                    "Type": module_type,
                    "LoadingPhase": loading_phase,
                }
            ],
        }

        if template == "agent":
            uplugin_data["Plugins"] = [
                {
                    "Name": "PythonScriptPlugin",
                    "Enabled": True,
                }
            ]

        with open(plugin_dir / f"{plugin_name}.uplugin", "w", encoding="utf-8") as f:
            json.dump(uplugin_data, f, indent=4)
            f.write("\n")

    def _write_build_cs(self, source_dir: Path, plugin_name: str, template: str) -> None:
        public_deps = ["Core", "CoreUObject", "Engine"]
        private_deps = []

        if template in ("editor", "agent"):
            public_deps.extend(["Slate", "SlateCore", "InputCore", "ToolMenus", "UnrealEd"])
            private_deps.extend(["WorkspaceMenuStructure", "Projects"])

        if template == "agent":
            private_deps.extend(["HTTP", "Json", "JsonUtilities"])

        pub_str = ",\n                ".join(f'"{d}"' for d in public_deps)
        priv_str = ",\n                ".join(f'"{d}"' for d in private_deps) if private_deps else ""

        code = f"""// Copyright (c) 2026. All Rights Reserved.

using UnrealBuildTool;

public class {plugin_name} : ModuleRules
{{
    public {plugin_name}(ReadOnlyTargetRules Target) : base(Target)
    {{
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
        CppStandard = CppStandardVersion.Cpp20;

        PublicIncludePaths.AddRange(
            new string[] {{
            }}
        );

        PrivateIncludePaths.AddRange(
            new string[] {{
            }}
        );

        PublicDependencyModuleNames.AddRange(
            new string[]
            {{
                {pub_str}
            }}
        );

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {{
                {priv_str}
            }}
        );
    }}
}}
"""
        (source_dir / f"{plugin_name}.Build.cs").write_text(code, encoding="utf-8")

    def _write_module_files(self, public_dir: Path, private_dir: Path, plugin_name: str, template: str) -> None:
        # Header
        h_code = f"""#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class F{plugin_name}Module : public IModuleInterface
{{
public:
    /** IModuleInterface implementation */
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;

    /** Singleton accessor */
    static inline F{plugin_name}Module& Get()
    {{
        return FModuleManager::LoadModuleChecked<F{plugin_name}Module>("{plugin_name}");
    }}

    /** Quick check for module availability */
    static inline bool IsAvailable()
    {{
        return FModuleManager::Get().IsModuleLoaded("{plugin_name}");
    }}
}};
"""
        (public_dir / f"{plugin_name}Module.h").write_text(h_code, encoding="utf-8")

        # Source
        extra_startup = ""
        extra_shutdown = ""
        extra_includes = ""

        if template == "editor":
            extra_includes = f'#include "{plugin_name}Commands.h"\n#include "ToolMenus.h"'
            extra_startup = f"""    F{plugin_name}Commands::Register();
    UE_LOG(Log{plugin_name}, Log, TEXT("Registered {plugin_name} editor commands."));"""
            extra_shutdown = f"""    F{plugin_name}Commands::Unregister();"""

        cpp_code = f"""#include "{plugin_name}Module.h"
{extra_includes}

DEFINE_LOG_CATEGORY_STATIC(Log{plugin_name}, Log, All);

#define LOCTEXT_NAMESPACE "F{plugin_name}Module"

void F{plugin_name}Module::StartupModule()
{{
    UE_LOG(Log{plugin_name}, Log, TEXT("{plugin_name} module initialized (Unreal Engine 5.8.3)"));
{extra_startup}
}}

void F{plugin_name}Module::ShutdownModule()
{{
    UE_LOG(Log{plugin_name}, Log, TEXT("{plugin_name} module shutting down"));
{extra_shutdown}
}}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(F{plugin_name}Module, {plugin_name})
"""
        (private_dir / f"{plugin_name}Module.cpp").write_text(cpp_code, encoding="utf-8")

    def _write_runtime_template(self, public_dir: Path, private_dir: Path, plugin_name: str) -> None:
        comp_h = f"""#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "{plugin_name}Component.generated.h"

/**
 * Modern Unreal Engine 5.8 Gameplay Component example.
 */
UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class U{plugin_name}Component : public UActorComponent
{{
    GENERATED_BODY()

public:
    U{plugin_name}Component();

    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

    /** Sample health property using modern UE 5.8 patterns */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "{plugin_name}|Stats")
    float CurrentHealth = 100.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "{plugin_name}|Stats")
    float MaxHealth = 100.0f;

    /** Blueprint callable sample function */
    UFUNCTION(BlueprintCallable, Category = "{plugin_name}|Actions")
    void ApplyDamage(float Amount);

    /** Returns normalized health (0.0 to 1.0) */
    UFUNCTION(BlueprintPure, Category = "{plugin_name}|Stats")
    float GetHealthPercent() const;
}};
"""
        (public_dir / f"{plugin_name}Component.h").write_text(comp_h, encoding="utf-8")

        comp_cpp = f"""#include "{plugin_name}Component.h"

U{plugin_name}Component::U{plugin_name}Component()
{{
    PrimaryComponentTick.bCanEverTick = false;
}}

void U{plugin_name}Component::BeginPlay()
{{
    Super::BeginPlay();
}}

void U{plugin_name}Component::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
}}

void U{plugin_name}Component::ApplyDamage(float Amount)
{{
    CurrentHealth = FMath::Clamp(CurrentHealth - Amount, 0.0f, MaxHealth);
}}

float U{plugin_name}Component::GetHealthPercent() const
{{
    return (MaxHealth > 0.0f) ? (CurrentHealth / MaxHealth) : 0.0f;
}}
"""
        (private_dir / f"{plugin_name}Component.cpp").write_text(comp_cpp, encoding="utf-8")

    def _write_editor_template(self, public_dir: Path, private_dir: Path, plugin_name: str) -> None:
        cmd_h = f"""#pragma once

#include "CoreMinimal.h"
#include "Framework/Commands/Commands.h"
#include "Styling/AppStyle.h"

class F{plugin_name}Commands : public TCommands<F{plugin_name}Commands>
{{
public:
    F{plugin_name}Commands()
        : TCommands<F{plugin_name}Commands>(
            TEXT("{plugin_name}"),
            NSLOCTEXT("Contexts", "{plugin_name}", "{plugin_name} Plugin"),
            NAME_None,
            FAppStyle::GetAppStyleSetName()
        )
    {{
    }}

    virtual void RegisterCommands() override;

public:
    TSharedPtr<FUICommandInfo> OpenPluginWindow;
}};
"""
        (public_dir / f"{plugin_name}Commands.h").write_text(cmd_h, encoding="utf-8")

        cmd_cpp = f"""#include "{plugin_name}Commands.h"

#define LOCTEXT_NAMESPACE "F{plugin_name}Commands"

void F{plugin_name}Commands::RegisterCommands()
{{
    UI_COMMAND(OpenPluginWindow, "{plugin_name}", "Bring up {plugin_name} window", EUserInterfaceActionType::Button, FInputChord());
}}

#undef LOCTEXT_NAMESPACE
"""
        (private_dir / f"{plugin_name}Commands.cpp").write_text(cmd_cpp, encoding="utf-8")

        widget_h = f"""#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/DeclarativeSyntaxSupport.h"

class S{plugin_name}Widget : public SCompoundWidget
{{
public:
    SLATE_BEGIN_ARGS(S{plugin_name}Widget) {{}}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);
}};
"""
        (public_dir / f"S{plugin_name}Widget.h").write_text(widget_h, encoding="utf-8")

        widget_cpp = f"""#include "S{plugin_name}Widget.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Layout/SBox.h"

void S{plugin_name}Widget::Construct(const FArguments& InArgs)
{{
    ChildSlot
    [
        SNew(SBox)
        .HAlign(HAlign_Center)
        .VAlign(VAlign_Center)
        [
            SNew(STextBlock)
            .Text(FText::FromString(TEXT("{plugin_name} — Unreal Engine 5.8 Editor Tool")))
        ]
    ];
}}
"""
        (private_dir / f"S{plugin_name}Widget.cpp").write_text(widget_cpp, encoding="utf-8")

    def _write_bp_library_template(self, public_dir: Path, private_dir: Path, plugin_name: str) -> None:
        lib_h = f"""#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "{plugin_name}BPLibrary.generated.h"

/**
 * Blueprint Function Library for {plugin_name} (UE 5.8.3)
 */
UCLASS()
class U{plugin_name}BPLibrary : public UBlueprintFunctionLibrary
{{
    GENERATED_BODY()

public:
    /** Returns {plugin_name} friendly version information */
    UFUNCTION(BlueprintPure, Category = "{plugin_name}|Utility")
    static FString Get{plugin_name}Version();

    /** Computes a sample mathematical calculation */
    UFUNCTION(BlueprintCallable, Category = "{plugin_name}|Math")
    static float ComputeSmoothFactor(float Current, float Target, float DeltaTime, float InterpSpeed);
}};
"""
        (public_dir / f"{plugin_name}BPLibrary.h").write_text(lib_h, encoding="utf-8")

        lib_cpp = f"""#include "{plugin_name}BPLibrary.h"

FString U{plugin_name}BPLibrary::Get{plugin_name}Version()
{{
    return TEXT("{plugin_name} v1.0.0 (UE 5.8.3)");
}}

float U{plugin_name}BPLibrary::ComputeSmoothFactor(float Current, float Target, float DeltaTime, float InterpSpeed)
{{
    return FMath::FInterpTo(Current, Target, DeltaTime, InterpSpeed);
}}
"""
        (private_dir / f"{plugin_name}BPLibrary.cpp").write_text(lib_cpp, encoding="utf-8")

    def _write_agent_template(self, public_dir: Path, private_dir: Path, plugin_name: str) -> None:
        reg_h = f"""#pragma once

#include "CoreMinimal.h"

/**
 * In-editor AI Agent tool definition for {plugin_name}.
 */
struct F{plugin_name}AgentTool
{{
    FString Name;
    FString Description;
    TFunction<FString(const FString& ParamsJson)> Handler;
}};

class F{plugin_name}ToolRegistry
{{
public:
    static F{plugin_name}ToolRegistry& Get();
    void RegisterTool(const FString& Name, const FString& Description, TFunction<FString(const FString&)> Handler);
    FString ExecuteTool(const FString& Name, const FString& ParamsJson);

private:
    TMap<FString, F{plugin_name}AgentTool> Tools;
}};
"""
        (public_dir / f"{plugin_name}ToolRegistry.h").write_text(reg_h, encoding="utf-8")

        reg_cpp = f"""#include "{plugin_name}ToolRegistry.h"

F{plugin_name}ToolRegistry& F{plugin_name}ToolRegistry::Get()
{{
    static F{plugin_name}ToolRegistry Instance;
    return Instance;
}}

void F{plugin_name}ToolRegistry::RegisterTool(const FString& Name, const FString& Description, TFunction<FString(const FString&)> Handler)
{{
    F{plugin_name}AgentTool Tool;
    Tool.Name = Name;
    Tool.Description = Description;
    Tool.Handler = Handler;
    Tools.Add(Name, Tool);
}}

FString F{plugin_name}ToolRegistry::ExecuteTool(const FString& Name, const FString& ParamsJson)
{{
    if (const F{plugin_name}AgentTool* Tool = Tools.Find(Name))
    {{
        return Tool->Handler(ParamsJson);
    }}
    return FString::Printf(TEXT("Error: Tool '%s' not found."), *Name);
}}
"""
        (private_dir / f"{plugin_name}ToolRegistry.cpp").write_text(reg_cpp, encoding="utf-8")

    def _write_helper_scripts(self, plugin_dir: Path, plugin_name: str) -> None:
        scripts_dir = plugin_dir / "Scripts"
        scripts_dir.mkdir(exist_ok=True)

        sh_code = f"""#!/usr/bin/env bash
# Quick build runner for {plugin_name}
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Run agentic build
if command -v agentic >/dev/null 2>&1; then
    exec agentic build "$PLUGIN_ROOT" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 -m agentic build "$PLUGIN_ROOT" "$@"
else
    echo "Error: agentic or python3 required." >&2
    exit 1
fi
"""
        (scripts_dir / "build.sh").write_text(sh_code, encoding="utf-8")

        bat_code = f"""@echo off
rem Quick build runner for {plugin_name} on Windows
set SCRIPT_DIR=%~dp0
set PLUGIN_ROOT=%SCRIPT_DIR%..
python -m agentic build "%PLUGIN_ROOT%" %*
exit /b %ERRORLEVEL%
"""
        (scripts_dir / "Build.bat").write_text(bat_code, encoding="utf-8")

    def _write_docs(self, plugin_dir: Path, plugin_name: str, template: str, description: str) -> None:
        readme = f"""# {plugin_name}

{description}

Target Engine: **Unreal Engine {self.engine_version}**  
Template: **{template}**

---

## Building with Antigravity

Inside the Antigravity IDE:
1. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).
2. Run **Tasks: Run Task** -> **UE5: Build Plugin (Development)**.
3. Or build via terminal:
   ```bash
   agentic build .
   ```

To package for distribution:
```bash
agentic package .
```

---

## Structure
- `{plugin_name}.uplugin` — Plugin manifest (EngineVersion: {self.engine_version})
- `Source/{plugin_name}/` — C++20 module source code
- `Resources/` — Plugin icon (128x128)
- `Scripts/` — Platform build scripts
"""
        (plugin_dir / "README.md").write_text(readme, encoding="utf-8")

        agents_md = f"""# AGENTS.md — AI Context for {plugin_name}

This plugin targets **Unreal Engine {self.engine_version}** and follows modern Epic Games standards:

- **C++ Standard**: C++20 (`CppStandard = CppStandardVersion.Cpp20;`)
- **Pointers**: Prefer `TObjectPtr<T>` for UPROPERTY object pointers over raw `T*`.
- **Includes**: Follow IWYU (Include-What-You-Use). Include `"CoreMinimal.h"` in headers and full definitions in `.cpp`.
- **Memory**: Manage object lifecycles with `UPROPERTY()` or `TWeakObjectPtr` to avoid dangling pointers.
- **Macros**: Every UObject/UActorComponent header must include `"{plugin_name}Component.generated.h"` as the last include and specify `GENERATED_BODY()`.

### Building inside Antigravity:
Run the task `UE5: Build Plugin (Development)` or execute `agentic build {plugin_name}` from the terminal.
"""
        (plugin_dir / "AGENTS.md").write_text(agents_md, encoding="utf-8")
