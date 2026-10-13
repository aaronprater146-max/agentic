// Arena Agent - editor module: owns the agent runner, the chat tab and menu entries.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleInterface.h"

class FArenaAgentRunner;
class SDockTab;
struct FSpawnTabArgs;

class FArenaAgentModule : public IModuleInterface
{
public:
	//~ Begin IModuleInterface
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
	//~ End IModuleInterface

	static FArenaAgentModule* Get();

	TSharedPtr<FArenaAgentRunner> GetRunner() const { return Runner; }

private:
	void RegisterMenus();
	TSharedRef<SDockTab> SpawnChatTab(const FSpawnTabArgs& Args);
	void OpenChatTab();

	TSharedPtr<FArenaAgentRunner> Runner;
	FName ChatTabId = FName(TEXT("ArenaAgentChat"));
};
