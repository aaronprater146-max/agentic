// Arena Agent - conversation persistence implementation.

#include "ArenaConversationStore.h"

#include "ArenaAgentLog.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformFileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Guid.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

FArenaConversationStore& FArenaConversationStore::Get()
{
	static FArenaConversationStore Instance;
	return Instance;
}

FString FArenaConversationStore::GetStorageDirectory() const
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("ArenaAgent"), TEXT("Conversations"));
}

FString FArenaConversationStore::ConversationFilePath(const FString& Id) const
{
	return FPaths::Combine(GetStorageDirectory(), Id + TEXT(".json"));
}

FString FArenaConversationStore::NewConversationId()
{
	return FGuid::NewGuid().ToString(EGuidFormats::Digits);
}

TArray<FArenaConversationMeta> FArenaConversationStore::ListConversations() const
{
	TArray<FArenaConversationMeta> Result;

	const FString Directory = GetStorageDirectory();
	TArray<FString> Files;
	IFileManager::Get().FindFiles(Files, *(Directory / TEXT("*.json")), true, false);

	for (const FString& File : Files)
	{
		FString Json;
		if (!FFileHelper::LoadFileToString(Json, *(Directory / File)))
		{
			continue;
		}

		FArenaConversation Conversation;
		if (!DeserializeConversation(Json, Conversation))
		{
			UE_LOG(LogArenaAgent, Warning, TEXT("Skipping unreadable conversation file: %s"), *File);
			continue;
		}

		FArenaConversationMeta Meta;
		Meta.Id = Conversation.Id;
		Meta.Name = Conversation.Name;
		Meta.Created = Conversation.Created;
		Meta.Updated = Conversation.Updated;
		Meta.MessageCount = Conversation.Messages.Num();
		Result.Add(Meta);
	}

	Result.Sort([](const FArenaConversationMeta& A, const FArenaConversationMeta& B)
	{
		return A.Updated > B.Updated;
	});

	return Result;
}

bool FArenaConversationStore::LoadConversation(const FString& Id, FArenaConversation& OutConversation) const
{
	FString Json;
	if (!FFileHelper::LoadFileToString(Json, *ConversationFilePath(Id)))
	{
		return false;
	}
	return DeserializeConversation(Json, OutConversation);
}

bool FArenaConversationStore::SaveConversation(const FArenaConversation& Conversation)
{
	const FString Directory = GetStorageDirectory();
	IFileManager::Get().MakeDirectory(*Directory, true);

	FString Json;
	if (!SerializeConversation(Conversation, Json))
	{
		return false;
	}
	return FFileHelper::SaveStringToFile(Json, *ConversationFilePath(Conversation.Id), FFileHelper::EEncodingOptions::ForceUTF8);
}

bool FArenaConversationStore::DeleteConversation(const FString& Id)
{
	const FString Path = ConversationFilePath(Id);
	if (IFileManager::Get().FileExists(*Path))
	{
		return IFileManager::Get().Delete(*Path, false, true) == 0;
	}
	return false;
}

void FArenaConversationStore::DeleteAllConversations()
{
	const FString Directory = GetStorageDirectory();
	TArray<FString> Files;
	IFileManager::Get().FindFiles(Files, *(Directory / TEXT("*.json")), true, false);
	for (const FString& File : Files)
	{
		IFileManager::Get().Delete(*(Directory / File), false, true);
	}
}

static TSharedPtr<FJsonObject> MessageToJson(const FArenaChatMessage& Message)
{
	TSharedPtr<FJsonObject> Object = MakeShared<FJsonObject>();
	Object->SetStringField(TEXT("role"), Message.Role);
	Object->SetStringField(TEXT("content"), Message.Content);
	if (!Message.ToolCallId.IsEmpty())
	{
		Object->SetStringField(TEXT("tool_call_id"), Message.ToolCallId);
	}
	if (!Message.ToolName.IsEmpty())
	{
		Object->SetStringField(TEXT("tool_name"), Message.ToolName);
	}
	if (!Message.ToolCallsJson.IsEmpty())
	{
		Object->SetStringField(TEXT("tool_calls_json"), Message.ToolCallsJson);
	}
	Object->SetNumberField(TEXT("ts"), static_cast<double>(Message.Timestamp));
	return Object;
}

static bool MessageFromJson(const TSharedPtr<FJsonObject>& Object, FArenaChatMessage& OutMessage)
{
	if (!Object.IsValid())
	{
		return false;
	}
	Object->TryGetStringField(TEXT("role"), OutMessage.Role);
	Object->TryGetStringField(TEXT("content"), OutMessage.Content);
	Object->TryGetStringField(TEXT("tool_call_id"), OutMessage.ToolCallId);
	Object->TryGetStringField(TEXT("tool_name"), OutMessage.ToolName);
	Object->TryGetStringField(TEXT("tool_calls_json"), OutMessage.ToolCallsJson);

	double Timestamp = 0.0;
	if (Object->TryGetNumberField(TEXT("ts"), Timestamp))
	{
		OutMessage.Timestamp = static_cast<int64>(Timestamp);
	}
	return !OutMessage.Role.IsEmpty();
}

bool FArenaConversationStore::SerializeConversation(const FArenaConversation& Conversation, FString& OutJson)
{
	TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetStringField(TEXT("id"), Conversation.Id);
	Root->SetStringField(TEXT("name"), Conversation.Name);
	Root->SetNumberField(TEXT("created"), static_cast<double>(Conversation.Created));
	Root->SetNumberField(TEXT("updated"), static_cast<double>(Conversation.Updated));

	TArray<TSharedPtr<FJsonValue>> Messages;
	Messages.Reserve(Conversation.Messages.Num());
	for (const FArenaChatMessage& Message : Conversation.Messages)
	{
		Messages.Add(MakeShared<FJsonValueObject>(MessageToJson(Message)));
	}
	Root->SetArrayField(TEXT("messages"), Messages);

	TSharedRef<TJsonWriter<TCHAR, TPrettyJsonPrintPolicy<TCHAR>>> Writer =
		TJsonWriterFactory<TCHAR, TPrettyJsonPrintPolicy<TCHAR>>::Create(&OutJson);
	return FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
}

bool FArenaConversationStore::DeserializeConversation(const FString& Json, FArenaConversation& OutConversation)
{
	TSharedPtr<FJsonObject> Root;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return false;
	}

	OutConversation = FArenaConversation();
	Root->TryGetStringField(TEXT("id"), OutConversation.Id);
	Root->TryGetStringField(TEXT("name"), OutConversation.Name);

	double Created = 0.0;
	if (Root->TryGetNumberField(TEXT("created"), Created))
	{
		OutConversation.Created = static_cast<int64>(Created);
	}
	double Updated = 0.0;
	if (Root->TryGetNumberField(TEXT("updated"), Updated))
	{
		OutConversation.Updated = static_cast<int64>(Updated);
	}

	const TArray<TSharedPtr<FJsonValue>>* MessagesArray = nullptr;
	if (Root->TryGetArrayField(TEXT("messages"), MessagesArray))
	{
		for (const TSharedPtr<FJsonValue>& Value : *MessagesArray)
		{
			const TSharedPtr<FJsonObject>* MessageObject = nullptr;
			if (Value.IsValid() && Value->TryGetObject(MessageObject) && MessageObject->IsValid())
			{
				FArenaChatMessage Message;
				if (MessageFromJson(*MessageObject, Message))
				{
					OutConversation.Messages.Add(Message);
				}
			}
		}
	}

	return !OutConversation.Id.IsEmpty();
}
