// Arena Agent - HTTP client for an OpenAI-compatible chat completions API with tool calling.

#pragma once

#include "CoreMinimal.h"
#include "ArenaChatTypes.h"
#include "Interfaces/IHttpRequest.h"

/** A fully described chat request. */
struct ARENAAGENT_API FArenaChatRequest
{
	FString BaseUrl;
	FString ApiKey;
	FString Model;
	FString SystemPrompt;
	TArray<FArenaChatMessage> Messages;
	/** OpenAI-style tool definitions: [{"type":"function","function":{...}}]. */
	TArray<TSharedPtr<class FJsonObject>> ToolDefinitions;
	int32 TimeoutSeconds = 180;
};

/** Parsed API response. */
struct ARENAAGENT_API FArenaApiResult
{
	bool bSuccess = false;
	FString Error;
	/** Final text content (empty when the model issued tool calls). */
	FString Content;
	/** Tool calls requested by the model, if any. */
	TArray<FArenaToolCall> ToolCalls;
};

/**
 * Sends a single chat completion request and reports the parsed result.
 * The completion callback is invoked on the game thread.
 */
class ARENAAGENT_API FArenaApiClient
{
public:
	using FResponseHandler = TFunction<void(FArenaApiResult)>;

	/** Starts an asynchronous request. Any in-flight request of this client is cancelled first. */
	void SendChatCompletion(const FArenaChatRequest& Request, FResponseHandler Handler);

	/** Cancels the in-flight request (its completion is ignored). */
	void Cancel();

	bool HasInFlightRequest() const { return ActiveRequest.IsValid(); }

	/** Builds the JSON payload for a request (exposed for tests/debugging). */
	static FString BuildPayloadJson(const FArenaChatRequest& Request);

private:
	static FArenaApiResult ParseResponse(int32 ResponseCode, const FString& Body);

	TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> ActiveRequest;
	bool bCancelled = false;
};
