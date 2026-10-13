// Arena Agent - project settings (Project Settings -> Plugins -> Arena Agent).

#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "ArenaAgentSettings.generated.h"

/**
 * Configuration for the Arena Agent plugin.
 * Exposed under Project Settings -> Plugins -> Arena Agent.
 */
UCLASS(config = Editor, defaultconfig, meta = (DisplayName = "Arena Agent"))
class ARENAAGENT_API UArenaAgentSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	UArenaAgentSettings(const FObjectInitializer& ObjectInitializer);

	//~ Begin UDeveloperSettings interface
	virtual FName GetCategoryName() const override { return TEXT("Plugins"); }
	//~ End UDeveloperSettings interface

	static const UArenaAgentSettings* Get() { return GetDefault<UArenaAgentSettings>(); }

	/** Base URL of the OpenAI-compatible chat completions API. "/chat/completions" is appended. */
	UPROPERTY(config, EditAnywhere, Category = "Arena API", meta = (DisplayName = "API Base URL"))
	FString ApiBaseUrl;

	/** API key sent as "Authorization: Bearer <key>". May also be provided via the ARENA_API_KEY environment variable. */
	UPROPERTY(config, EditAnywhere, Category = "Arena API", meta = (DisplayName = "API Key"))
	FString ApiKey;

	/** Model name passed in the request payload. */
	UPROPERTY(config, EditAnywhere, Category = "Arena API", meta = (DisplayName = "Model"))
	FString Model;

	/** Extra time in seconds to wait for the model before failing a request. */
	UPROPERTY(config, EditAnywhere, Category = "Arena API", meta = (DisplayName = "Request Timeout (s)", ClampMin = "10", ClampMax = "600"))
	int32 RequestTimeoutSeconds;

	/** System prompt injected at the start of every request. */
	UPROPERTY(config, EditAnywhere, Category = "Agent", meta = (MultiLine = "true", DisplayName = "System Prompt"))
	FString SystemPrompt;

	/** Maximum number of model<->tool round trips per user message. */
	UPROPERTY(config, EditAnywhere, Category = "Agent", meta = (ClampMin = "1", ClampMax = "64", DisplayName = "Max Tool Iterations"))
	int32 MaxToolIterations;

	/** How many of the most recent messages are sent as context. */
	UPROPERTY(config, EditAnywhere, Category = "Agent", meta = (ClampMin = "4", ClampMax = "500", DisplayName = "Context Message Limit"))
	int32 MaxHistoryMessages;

	/** Automatically save packages after the agent creates or edits assets. */
	UPROPERTY(config, EditAnywhere, Category = "Agent", meta = (DisplayName = "Auto Save Assets"))
	bool bAutoSaveAssets;

	/** Allow the agent to run arbitrary Unreal Python via the run_python tool. Off by default. */
	UPROPERTY(config, EditAnywhere, Category = "Agent", meta = (DisplayName = "Allow Python Execution"))
	bool bAllowPython;

	/** Folder (relative to /Game) where the agent creates assets unless told otherwise. */
	UPROPERTY(config, EditAnywhere, Category = "Agent", meta = (DisplayName = "Default Asset Folder"))
	FString DefaultAssetFolder;
};
