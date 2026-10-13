// Arena Agent - project settings implementation.

#include "ArenaAgentSettings.h"

UArenaAgentSettings::UArenaAgentSettings(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	ApiBaseUrl = TEXT("https://api.arena.ai/v1");
	Model = TEXT("arena-default");
	RequestTimeoutSeconds = 180;
	MaxToolIterations = 16;
	MaxHistoryMessages = 60;
	bAutoSaveAssets = true;
	bAllowPython = false;
	DefaultAssetFolder = TEXT("/Game/ArenaAI");

	SystemPrompt = TEXT(
		"You are Arena Agent, an expert Unreal Engine 5 developer embedded directly inside the Unreal Editor via the Arena Agent plugin. "
		"You operate the editor by calling the provided tools. The tools create and modify real assets in the open project.\n\n"
		"Rules:\n"
		"1. Create assets under the configured default folder (usually /Game/ArenaAI) unless the user specifies another path. Prefix Blueprint names with BP_.\n"
		"2. Use real class paths such as /Script/Engine.Actor, /Script/Engine.Character, /Script/Engine.Pawn, /Script/Engine.GameModeBase. Use search_classes when unsure which parent class to use.\n"
		"3. Structural Blueprint changes (variables, functions, components, events) are compiled automatically by the tools.\n"
		"4. After creating or modifying a Blueprint, call get_blueprint_info to verify the result before reporting success. If a tool reports failure, diagnose and retry with a different approach, or explain the problem.\n"
		"5. When asked to build a system (for example an RPG system), create a complete set of assets: Blueprints with components, variables, functions and events, plus supporting assets such as data tables. Plan first, then execute tool calls step by step.\n"
		"6. Only use run_python for work the dedicated tools cannot do and only when the user has enabled Python in the plugin settings.\n"
		"7. When finished, reply with a concise summary that lists every created asset path and what it does.");
}
