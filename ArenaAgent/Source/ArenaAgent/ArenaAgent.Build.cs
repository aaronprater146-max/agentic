// Arena Agent - Arena.ai's in-editor agent plugin.
// Editor module that hosts the chat UI, the agent runner and the editor tools.

using UnrealBuildTool;

public class ArenaAgent : ModuleRules
{
	public ArenaAgent(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
		CppStandard = CppStandardVersion.Cpp20;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"CoreUObject",
			"Engine",
			"InputCore",
			"Slate",
			"SlateCore",
			"UnrealEd",
			"Kismet",
			"KismetCompiler",
			"BlueprintGraph",
			"UMG",
			"DeveloperSettings",
			"Settings",
			"HTTP",
			"Json",
			"AssetRegistry",
			"AssetTools",
			"ToolMenus",
			"PythonScriptPlugin"
		});
	}
}
