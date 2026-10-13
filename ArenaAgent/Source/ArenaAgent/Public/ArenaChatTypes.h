// Arena Agent - shared data types for chat messages, tool calls and conversations.

#pragma once

#include "CoreMinimal.h"

/** A single message in a conversation. Mirrors the OpenAI chat-completions message model. */
struct ARENAAGENT_API FArenaChatMessage
{
	/** "system", "user", "assistant" or "tool". */
	FString Role;

	/** Text content of the message (may be empty for tool-call assistant messages). */
	FString Content;

	/** For role "tool": the id of the tool call this message answers. */
	FString ToolCallId;

	/** For role "tool": the name of the tool that ran. */
	FString ToolName;

	/** For role "assistant": raw JSON array of tool_calls issued with this message, e.g.
	 *  [{"id":"call_1","type":"function","function":{"name":"create_blueprint","arguments":"{...}"}}] */
	FString ToolCallsJson;

	/** Unix timestamp (seconds) when the message was created. */
	int64 Timestamp = 0;
};

/** A tool invocation requested by the model. */
struct ARENAAGENT_API FArenaToolCall
{
	/** Tool call id assigned by the API (echoed back in the tool result message). */
	FString Id;

	/** Tool name, e.g. "create_blueprint". */
	FString Name;

	/** Raw JSON object string with the arguments (always valid JSON; "{}" as fallback). */
	FString ArgumentsJson;

	/** Parsed arguments (never null; empty object if parsing failed). */
	TSharedPtr<class FJsonObject> Arguments;
};

/** A full conversation (one chat session). Persisted to disk as JSON. */
struct ARENAAGENT_API FArenaConversation
{
	FString Id;
	FString Name;
	int64 Created = 0;
	int64 Updated = 0;
	TArray<FArenaChatMessage> Messages;
};

/** Lightweight metadata used to list conversations in the UI. */
struct ARENAAGENT_API FArenaConversationMeta
{
	FString Id;
	FString Name;
	int64 Created = 0;
	int64 Updated = 0;
	int32 MessageCount = 0;
};

/** A flattened message prepared for display in the chat list. */
struct ARENAAGENT_API FArenaDisplayMessage
{
	/** "user", "assistant", "tool" or "error". Controls bubble styling. */
	FString Role;

	/** Display text (may contain several physical lines). */
	FString Text;

	/** Short human readable time, e.g. "10/11 14:32". */
	FString TimeString;
};

namespace ArenaChatHelpers
{
	/** Current unix timestamp in seconds. */
	ARENAAGENT_API int64 NowUnix();

	/** Formats a unix timestamp as "MM/DD HH:MM". */
	ARENAAGENT_API FString FormatTimestamp(int64 UnixSeconds);

	/** Builds display messages from a conversation (flattens tool calls/results for readability). */
	ARENAAGENT_API TArray<FArenaDisplayMessage> BuildDisplayMessages(const FArenaConversation& Conversation);
}
