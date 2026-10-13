// Arena Agent - orchestrates the conversation with the model and executes tool calls.

#pragma once

#include "CoreMinimal.h"
#include "ArenaApiClient.h"
#include "ArenaChatTypes.h"

/**
 * Owns the active conversation, sends it to the chat API and executes any
 * requested tools until the model produces a final text answer.
 * All methods must run on the game thread.
 */
class ARENAAGENT_API FArenaAgentRunner : public TSharedFromThis<FArenaAgentRunner>
{
public:
	FArenaAgentRunner();

	/** Loads the most recent conversation, or creates a new one. */
	void Initialize();

	// ------------------------------------------------ conversation management
	const FArenaConversation& GetConversation() const { return Conversation; }
	TArray<FArenaConversationMeta> ListConversations() const;

	void NewConversation();
	bool LoadConversation(const FString& Id);
	void DeleteConversation(const FString& Id);
	void DeleteAllConversations();
	void ClearCurrentHistory();
	void RenameCurrentConversation(const FString& NewName);
	void SaveCurrentConversation();

	// ------------------------------------------------------------- agent loop
	void SendMessage(const FString& Text);
	void Cancel();
	bool IsBusy() const { return bBusy; }
	FString GetStatus() const { return Status; }

	/** Bumped whenever anything visible to the UI changed. */
	int32 GetRevision() const { return Revision; }

private:
	void Iterate();
	void HandleApiResult(FArenaApiResult Result);
	void AppendMessage(const FArenaChatMessage& Message);
	void AppendAssistantText(const FString& Text);
	void EndTurn(const FString& FinalStatus);
	TArray<FArenaChatMessage> BuildContextMessages() const;
	static FString ResolveApiKey();
	static FString SerializeToolCalls(const TArray<FArenaToolCall>& ToolCalls);

	FArenaConversation Conversation;
	FArenaApiClient ApiClient;
	FString Status = TEXT("Idle");
	int32 Revision = 0;
	int32 IterationsLeft = 0;
	bool bBusy = false;
};
