// Arena Agent - registry of editor tools the AI agent can call.

#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Result of executing one agent tool. */
struct ARENAAGENT_API FArenaToolResult
{
	bool bSuccess = false;
	FString Message;
	TSharedPtr<FJsonObject> Data;

	/** Serializes the result as the JSON string stored in a tool-result chat message. */
	FString ToMessageString() const;

	static FArenaToolResult Ok(const FString& InMessage, const TSharedPtr<FJsonObject>& InData = nullptr)
	{
		FArenaToolResult Result;
		Result.bSuccess = true;
		Result.Message = InMessage;
		Result.Data = InData;
		return Result;
	}

	static FArenaToolResult Err(const FString& InMessage)
	{
		FArenaToolResult Result;
		Result.bSuccess = false;
		Result.Message = InMessage;
		return Result;
	}
};

/**
 * Holds every tool the agent may call: name, description, JSON schema and executor.
 * Executors run on the game thread.
 */
class ARENAAGENT_API FArenaToolRegistry
{
public:
	using FExecutor = TFunction<FArenaToolResult(const TSharedPtr<FJsonObject>& Args)>;

	static FArenaToolRegistry& Get();

	/** Builds OpenAI-style tool definitions for the request payload. */
	TArray<TSharedPtr<FJsonObject>> BuildOpenAIToolSchemas() const;

	/** Executes a tool by name. Unknown tools yield a failure result. */
	FArenaToolResult Execute(const FString& ToolName, const TSharedPtr<FJsonObject>& Args);

	int32 NumTools() const { return Tools.Num(); }

private:
	struct FToolDefinition
	{
		FString Name;
		FString Description;
		TSharedPtr<FJsonObject> ParametersSchema;
		FExecutor Executor;
	};

	FArenaToolRegistry();
	void RegisterBuiltInTools();

	void RegisterTool(const FString& Name, const FString& Description, const TSharedPtr<FJsonObject>& ParametersSchema, FExecutor Executor);

	TArray<FToolDefinition> Tools;
};
