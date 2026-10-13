# Unreal Engine 5.8 Plugin Architecture Reference

## Directory Layout

A standard Unreal Engine 5.8 plugin layout:

```text
<PluginName>/
├── <PluginName>.uplugin
├── Resources/
│   └── Icon128.png
├── Source/
│   └── <PluginName>/
│       ├── <PluginName>.Build.cs
│       ├── Public/
│       │   ├── <PluginName>Module.h
│       │   └── ... (Public API headers)
│       └── Private/
│           ├── <PluginName>Module.cpp
│           └── ... (Private implementation)
├── README.md
├── AGENTS.md
└── Scripts/
    ├── build.sh
    └── Build.bat
```

## `.uplugin` Key Fields for UE 5.8.3

```json
{
    "FileVersion": 3,
    "Version": 1,
    "VersionName": "1.0.0",
    "FriendlyName": "MyPlugin",
    "Description": "Plugin description",
    "Category": "Gameplay",
    "CreatedBy": "Author",
    "EngineVersion": "5.8.3",
    "CanContainContent": false,
    "IsBetaVersion": false,
    "IsExperimentalVersion": false,
    "Installed": false,
    "Modules": [
        {
            "Name": "MyPlugin",
            "Type": "Runtime",
            "LoadingPhase": "Default",
            "PlatformAllowList": ["Win64", "Linux", "Mac"]
        }
    ]
}
```

## Module Loading Phases
- `PreDefault`: Loads before most engine modules; ideal for blueprint libraries, early subsystems.
- `Default`: Standard loading phase for gameplay modules and general systems.
- `PostEngineInit`: Used for editor tools that register tabs, toolbars, and menus after the editor UI is fully initialized.
