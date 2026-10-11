// uebuild example build rules — real plugins list their dependencies here.
using UnrealBuildTool;

public class DummyRuntime : ModuleRules
{
	public DummyRuntime(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine"
		});
	}
}
