// uebuild example editor module build rules.
using UnrealBuildTool;

public class DummyEditor : ModuleRules
{
	public DummyEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"DummyRuntime",
			"UnrealEd"
		});
	}
}
