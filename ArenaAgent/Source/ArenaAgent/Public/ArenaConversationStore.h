// Arena Agent - persists conversations as JSON files under <Project>/Saved/ArenaAgent/Conversations.

#pragma once

#include "CoreMinimal.h"
#include "ArenaChatTypes.h"

/**
 * Reads/writes conversation JSON files.
 * One file per conversation: <Saved>/ArenaAgent/Conversations/<id>.json
 */
class ARENAAGENT_API FArenaConversationStore
{
public:
	static FArenaConversationStore& Get();

	/** Directory conversations are stored in (created on demand). */
	FString GetStorageDirectory() const;

	/** Lists all conversations, most recently updated first. */
	TArray<FArenaConversationMeta> ListConversations() const;

	/** Loads a conversation by id. Returns false if missing/corrupt. */
	bool LoadConversation(const FString& Id, FArenaConversation& OutConversation) const;

	/** Saves (or creates) a conversation. */
	bool SaveConversation(const FArenaConversation& Conversation);

	/** Deletes one conversation file. */
	bool DeleteConversation(const FString& Id);

	/** Deletes every stored conversation. */
	void DeleteAllConversations();

	/** Generates a new unique conversation id. */
	static FString NewConversationId();

private:
	FString ConversationFilePath(const FString& Id) const;

	static bool SerializeConversation(const FArenaConversation& Conversation, FString& OutJson);
	static bool DeserializeConversation(const FString& Json, FArenaConversation& OutConversation);
};
