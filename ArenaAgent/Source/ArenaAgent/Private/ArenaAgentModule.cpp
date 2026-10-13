// Arena Agent - module implementation.

#include "ArenaAgentModule.h"

#include "ArenaAgentLog.h"
#include "ArenaAgentRunner.h"
#include "ArenaToolRegistry.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "SArenaChatWidget.h"
#include "ToolMenus.h"
#include "Widgets/Docking/SDockTab.h"

#define LOCTEXT_NAMESPACE "ArenaAgent"

DEFINE_LOG_CATEGORY(LogArenaAgent);

IMPLEMENT_MODULE(FArenaAgentModule, ArenaAgent)

FArenaAgentModule* FArenaAgentModule::Get()
{
	return FModuleManager::GetModulePtr<FArenaAgentModule>(TEXT("ArenaAgent"));
}

void FArenaAgentModule::StartupModule()
{
	// Warm up the tool registry early so schema errors surface at startup.
	UE_LOG(LogArenaAgent, Log, TEXT("Arena Agent starting: %d tools available."), FArenaToolRegistry::Get().NumTools());

	// The runner owns all conversation state so the chat survives tab close/reopen.
	Runner = MakeShared<FArenaAgentRunner>();
	Runner->Initialize();

	// Dockable chat tab.
	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(ChatTabId, FOnSpawnTab::CreateRaw(this, &FArenaAgentModule::SpawnChatTab))
		.SetDisplayName(LOCTEXT("ArenaAgentTabTitle", "Arena Agent"))
		.SetTooltipText(LOCTEXT("ArenaAgentTabTooltip", "Chat with the Arena.ai agent to create Blueprints and gameplay systems"))
		.SetMenuType(ETabSpawnerMenuType::Hidden);

	RegisterMenus();

	// The panel is opened on demand via Window -> Arena Agent Chat or the toolbar button.
	UE_LOG(LogArenaAgent, Log, TEXT("Arena Agent ready. Open the chat via Window > Arena Agent Chat."));
}

void FArenaAgentModule::ShutdownModule()
{
	Runner.Reset();

	if (FSlateApplication::IsInitialized())
	{
		FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(ChatTabId);
	}
	UToolMenus::Get()->UnregisterOwner("ArenaAgent");
}

void FArenaAgentModule::RegisterMenus()
{
	// Main menu: Window -> Arena Agent Chat
	UToolMenu* WindowMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
	if (WindowMenu)
	{
		FToolMenuSection& Section = WindowMenu->FindOrAddSection("ArenaAgent");
		Section.AddMenuEntry(
			"OpenArenaAgentChat",
			LOCTEXT("OpenArenaAgentChat", "Arena Agent Chat"),
			LOCTEXT("OpenArenaAgentChatTooltip", "Open the Arena.ai agent chat panel"),
			FSlateIcon(),
			FUIAction(FExecuteAction::CreateRaw(this, &FArenaAgentModule::OpenChatTab)));
	}

	// Toolbar button next to the Play controls.
	UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
	if (ToolbarMenu)
	{
		FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("ArenaAgent");
		Section.AddMenuEntry(
			"OpenArenaAgentChatToolbar",
			LOCTEXT("OpenArenaAgentChatToolbar", "Arena Agent"),
			LOCTEXT("OpenArenaAgentChatToolbarTooltip", "Open the Arena.ai agent chat panel"),
			FSlateIcon(),
			FUIAction(FExecuteAction::CreateRaw(this, &FArenaAgentModule::OpenChatTab)));
	}
}

TSharedRef<SDockTab> FArenaAgentModule::SpawnChatTab(const FSpawnTabArgs& Args)
{
	TSharedRef<SDockTab> Tab = SNew(SDockTab)
		.TabRole(ETabRole::NomadTab);

	Tab->SetContent(
		SNew(SArenaChatWidget)
		.Runner(Runner));

	return Tab;
}

void FArenaAgentModule::OpenChatTab()
{
	FGlobalTabmanager::Get()->TryInvokeTab(ChatTabId);
}

#undef LOCTEXT_NAMESPACE
