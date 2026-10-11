// Arena Agent - agent loop implementation.

#include "ArenaAgentRunner.h"

#include "ArenaAgentLog.h"
#include "ArenaAgentSettings.h"
#include "ArenaConversationStore.h"
#include "ArenaToolRegistry.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "HAL/PlatformMisc.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

FArenaAgentRunner::FArenaAgentRunner()
{
	Conversation.Id = FArenaConversationStore::NewConversationId();
	Conversation.Name = TEXT("New Conversation");
	Conversation.Created = ArenaChatHelpers::NowUnix();
	Conversation.Updated = Conversation.Created;
}

void FArenaAgentRunner::Initialize()
{
	const TArray<FArenaConversationMeta> Conversations = FArenaConversationStore::Get().ListConversations();
	if (Conversations.Num() > 0 && LoadConversation(Conversations[0].Id))
	{
		UE_LOG(LogArenaAgent, Log, TEXT("Restored conversation '%s'."), *Conversation.Name);
	}
	else
	{
		SaveCurrentConversation();
	}
	++Revision;
}

TArray<FArenaConversationMeta> FArenaAgentRunner::ListConversations() const
{
	return FArenaConversationStore::Get().ListConversations();
}

void FArenaAgentRunner::NewConversation()
{
	if (bBusy)
	{
		return;
	}
	Conversation = FArenaConversation();
	Conversation.Id = FArenaConversationStore::NewConversationId();
	Conversation.Name = TEXT("New Conversation");
	Conversation.Created = ArenaChatHelpers::NowUnix();
	Conversation.Updated = Conversation.Created;
	SaveCurrentConversation();
	Status = TEXT("Idle");
	++Revision;
}

bool FArenaAgentRunner::LoadConversation(const FString& Id)
{
	if (bBusy)
	{
		return false;
	}
	FArenaConversation Loaded;
	if (!FArenaConversationStore::Get().LoadConversation(Id, Loaded))
	{
		return false;
	}
	Conversation = MoveTemp(Loaded);
	Status = TEXT("Idle");
	++Revision;
	return true;
}

void FArenaAgentRunner::DeleteConversation(const FString& Id)
{
	if (bBusy)
	{
		return;
	}
	const bool bWasCurrent = Conversation.Id == Id;
	FArenaConversationStore::Get().DeleteConversation(Id);
	if (bWasCurrent)
	{
		NewConversation();
	}
	++Revision;
}

void FArenaAgentRunner::DeleteAllConversations()
{
	if (bBusy)
	{
		return;
	}
	FArenaConversationStore::Get().DeleteAllConversations();
	NewConversation();
	++Revision;
}

void FArenaAgentRunner::ClearCurrentHistory()
{
	if (bBusy)
	{
		return;
	}
	Conversation.Messages.Empty();
	Conversation.Updated = ArenaChatHelpers::NowUnix();
	SaveCurrentConversation();
	++Revision;
}

void FArenaAgentRunner::RenameCurrentConversation(const FString& NewName)
{
	const FString Trimmed = NewName.TrimStartAndEnd();
	if (Trimmed.IsEmpty())
	{
		return;
	}
	Conversation.Name = Trimmed.Left(80);
	Conversation.Updated = ArenaChatHelpers::NowUnix();
	SaveCurrentConversation();
	++Revision;
}

void FArenaAgentRunner::SaveCurrentConversation()
{
	FArenaConversationStore::Get().SaveConversation(Conversation);
}

FString FArenaAgentRunner::ResolveApiKey()
{
	const UArenaAgentSettings* Settings = GetDefault<UArenaAgentSettings>();
	if (!Settings->ApiKey.IsEmpty())
	{
		return Settings->ApiKey;
	}
	FString EnvironmentKey;
	FPlatformMisc::GetEnvironmentVariable(TEXT("ARENA_API_KEY"), EnvironmentKey);
	return EnvironmentKey;
}

void FArenaAgentRunner::AppendMessage(const FArenaChatMessage& Message)
{
	Conversation.Messages.Add(Message);
	Conversation.Updated = ArenaChatHelpers::NowUnix();
	SaveCurrentConversation();
	++Revision;
}

void FArenaAgentRunner::AppendAssistantText(const FString& Text)
{
	FArenaChatMessage Message;
	Message.Role = TEXT("assistant");
	Message.Content = Text;
	Message.Timestamp = ArenaChatHelpers::NowUnix();
	AppendMessage(Message);
}

void FArenaAgentRunner::EndTurn(const FString& FinalStatus)
{
	bBusy = false;
	Status = FinalStatus;
	SaveCurrentConversation();
	++Revision;
}

TArray<FArenaChatMessage> FArenaAgentRunner::BuildContextMessages() const
{
	const int32 Limit = FMath::Max(4, GetDefault<UArenaAgentSettings>()->MaxHistoryMessages);
	const TArray<FArenaChatMessage>& All = Conversation.Messages;

	int32 StartIndex = FMath::Max(0, All.Num() - Limit);
	// Keep tool-call/result pairs together by starting on a user message when possible.
	while (StartIndex > 0 && All[StartIndex].Role != TEXT("user"))
	{
		++StartIndex;
	}

	TArray<FArenaChatMessage> Context;
	for (int32 Index = StartIndex; Index < All.Num(); ++Index)
	{
		Context.Add(All[Index]);
	}
	return Context;
}

FString FArenaAgentRunner::SerializeToolCalls(const TArray<FArenaToolCall>& ToolCalls)
{
	TArray<TSharedPtr<FJsonValue>> CallsArray;
	for (const FArenaToolCall& Call : ToolCalls)
	{
		TSharedPtr<FJsonObject> FunctionObject = MakeShared<FJsonObject>();
		FunctionObject->SetStringField(TEXT("name"), Call.Name);
		FunctionObject->SetStringField(TEXT("arguments"), Call.ArgumentsJson);

		TSharedPtr<FJsonObject> CallObject = MakeShared<FJsonObject>();
		CallObject->SetStringField(TEXT("id"), Call.Id);
		CallObject->SetStringField(TEXT("type"), TEXT("function"));
		CallObject->SetObjectField(TEXT("function"), FunctionObject);

		CallsArray.Add(MakeShared<FJsonValueObject>(CallObject));
	}

	FString Output;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
		TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Output);
	TSharedPtr<FJsonValueArray> RootValue = MakeShared<FJsonValueArray>(CallsArray);
	FJsonSerializer::Serialize(RootValue.ToSharedRef(), Writer);
	return Output;
}

void FArenaAgentRunner::SendMessage(const FString& Text)
{
	const FString Trimmed = Text.TrimStartAndEnd();
	if (bBusy || Trimmed.IsEmpty())
	{
		return;
	}

	FArenaChatMessage UserMessage;
	UserMessage.Role = TEXT("user");
	UserMessage.Content = Trimmed;
	UserMessage.Timestamp = ArenaChatHelpers::NowUnix();
	Conversation.Messages.Add(UserMessage);

	// Auto-name the conversation after its first user message.
	if (Conversation.Name.IsEmpty() || Conversation.Name == TEXT("New Conversation"))
	{
		Conversation.Name = Trimmed.Left(48);
	}

	Conversation.Updated = UserMessage.Timestamp;
	SaveCurrentConversation();

	bBusy = true;
	IterationsLeft = FMath::Max(1, GetDefault<UArenaAgentSettings>()->MaxToolIterations);
	Status = TEXT("Thinking…");
	++Revision;

	Iterate();
}

void FArenaAgentRunner::Iterate()
{
	const UArenaAgentSettings* Settings = GetDefault<UArenaAgentSettings>();

	const FString ApiKey = ResolveApiKey();
	if (ApiKey.IsEmpty())
	{
		AppendAssistantText(TEXT("⚠️ No API key configured. Set it under Project Settings → Plugins → Arena Agent (or the ARENA_API_KEY environment variable)."));
		EndTurn(TEXT("Missing API key"));
		return;
	}

	FArenaChatRequest Request;
	Request.BaseUrl = Settings->ApiBaseUrl;
	Request.ApiKey = ApiKey;
	Request.Model = Settings->Model;
	Request.SystemPrompt = Settings->SystemPrompt;
	Request.Messages = BuildContextMessages();
	Request.ToolDefinitions = FArenaToolRegistry::Get().BuildOpenAIToolSchemas();
	Request.TimeoutSeconds = Settings->RequestTimeoutSeconds;

	TWeakPtr<FArenaAgentRunner> WeakThis = SharedThis(this);
	ApiClient.SendChatCompletion(Request, [WeakThis](FArenaApiResult Result)
	{
		if (TSharedPtr<FArenaAgentRunner> Self = WeakThis.Pin())
		{
			Self->HandleApiResult(MoveTemp(Result));
		}
	});
}

void FArenaAgentRunner::HandleApiResult(FArenaApiResult Result)
{
	if (!bBusy)
	{
		// Cancelled in the meantime.
		return;
	}

	if (!Result.bSuccess)
	{
		AppendAssistantText(FString::Printf(TEXT("⚠️ Request failed: %s"), *Result.Error));
		EndTurn(TEXT("Request failed"));
		return;
	}

	if (Result.ToolCalls.Num() > 0)
	{
		// Record the assistant message that issued the tool calls.
		FArenaChatMessage AssistantMessage;
		AssistantMessage.Role = TEXT("assistant");
		AssistantMessage.Content = Result.Content;
		AssistantMessage.ToolCallsJson = SerializeToolCalls(Result.ToolCalls);
		AssistantMessage.Timestamp = ArenaChatHelpers::NowUnix();
		AppendMessage(AssistantMessage);

		// Execute every requested tool on the game thread and record results.
		for (const FArenaToolCall& Call : Result.ToolCalls)
		{
			Status = FString::Printf(TEXT("Running %s…"), *Call.Name);
			++Revision;

			const FArenaToolResult ToolResult = FArenaToolRegistry::Get().Execute(Call.Name, Call.Arguments);

			FArenaChatMessage ToolMessage;
			ToolMessage.Role = TEXT("tool");
			ToolMessage.ToolCallId = Call.Id;
			ToolMessage.ToolName = Call.Name;
			ToolMessage.Content = ToolResult.ToMessageString();
			ToolMessage.Timestamp = ArenaChatHelpers::NowUnix();
			AppendMessage(ToolMessage);
		}

		--IterationsLeft;
		if (IterationsLeft <= 0)
		{
			AppendAssistantText(TEXT("Reached the maximum number of tool iterations; stopping. Ask me to continue if more work is needed."));
			EndTurn(TEXT("Iteration limit reached"));
			return;
		}

		Status = TEXT("Thinking…");
		++Revision;
		Iterate();
		return;
	}

	AppendAssistantText(Result.Content.IsEmpty() ? TEXT("(The model returned an empty response.)") : Result.Content);
	EndTurn(TEXT("Idle"));
}

void FArenaAgentRunner::Cancel()
{
	if (!bBusy)
	{
		return;
	}
	ApiClient.Cancel();
	EndTurn(TEXT("Cancelled"));
}
