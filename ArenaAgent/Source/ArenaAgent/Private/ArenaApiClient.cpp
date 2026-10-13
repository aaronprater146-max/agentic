// Arena Agent - HTTP client implementation.

#include "ArenaApiClient.h"

#include "ArenaAgentLog.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

static FString RtrimSlash(FString Url)
{
	while (Url.EndsWith(TEXT("/")))
	{
		Url.LeftChopInline(1, EAllowShrinking::No);
	}
	return Url;
}

FString FArenaApiClient::BuildPayloadJson(const FArenaChatRequest& Request)
{
	TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetStringField(TEXT("model"), Request.Model);
	Root->SetBoolField(TEXT("stream"), false);

	TArray<TSharedPtr<FJsonValue>> MessagesArray;

	// System prompt first.
	if (!Request.SystemPrompt.IsEmpty())
	{
		TSharedPtr<FJsonObject> SystemMessage = MakeShared<FJsonObject>();
		SystemMessage->SetStringField(TEXT("role"), TEXT("system"));
		SystemMessage->SetStringField(TEXT("content"), Request.SystemPrompt);
		MessagesArray.Add(MakeShared<FJsonValueObject>(SystemMessage));
	}

	for (const FArenaChatMessage& Message : Request.Messages)
	{
		TSharedPtr<FJsonObject> MessageObject = MakeShared<FJsonObject>();
		MessageObject->SetStringField(TEXT("role"), Message.Role);
		MessageObject->SetStringField(TEXT("content"), Message.Content);

		if (Message.Role == TEXT("assistant") && !Message.ToolCallsJson.IsEmpty())
		{
			TArray<TSharedPtr<FJsonValue>> ParsedCalls;
			TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message.ToolCallsJson);
			if (FJsonSerializer::Deserialize(Reader, ParsedCalls))
			{
				MessageObject->SetField(TEXT("tool_calls"), MakeShared<FJsonValueArray>(ParsedCalls));
			}
		}

		if (Message.Role == TEXT("tool"))
		{
			MessageObject->SetStringField(TEXT("tool_call_id"), Message.ToolCallId);
			if (!Message.ToolName.IsEmpty())
			{
				MessageObject->SetStringField(TEXT("name"), Message.ToolName);
			}
		}

		MessagesArray.Add(MakeShared<FJsonValueObject>(MessageObject));
	}
	Root->SetArrayField(TEXT("messages"), MessagesArray);

	if (Request.ToolDefinitions.Num() > 0)
	{
		TArray<TSharedPtr<FJsonValue>> ToolsArray;
		ToolsArray.Reserve(Request.ToolDefinitions.Num());
		for (const TSharedPtr<FJsonObject>& Tool : Request.ToolDefinitions)
		{
			if (Tool.IsValid())
			{
				ToolsArray.Add(MakeShared<FJsonValueObject>(Tool));
			}
		}
		Root->SetArrayField(TEXT("tools"), ToolsArray);
		Root->SetStringField(TEXT("tool_choice"), TEXT("auto"));
	}

	FString Output;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
		TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Output);
	FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
	return Output;
}

FArenaApiResult FArenaApiClient::ParseResponse(int32 ResponseCode, const FString& Body)
{
	FArenaApiResult Result;

	TSharedPtr<FJsonObject> Root;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Body);
	const bool bParsed = FJsonSerializer::Deserialize(Reader, Root) && Root.IsValid();

	if (ResponseCode < 200 || ResponseCode >= 300)
	{
		FString ErrorText = FString::Printf(TEXT("HTTP %d"), ResponseCode);
		if (bParsed)
		{
			const TSharedPtr<FJsonObject>* ErrorObject = nullptr;
			if (Root->TryGetObjectField(TEXT("error"), ErrorObject) && ErrorObject->IsValid())
			{
				FString ApiMessage;
				if ((*ErrorObject)->TryGetStringField(TEXT("message"), ApiMessage))
				{
					ErrorText += TEXT(": ") + ApiMessage;
				}
			}
		}
		else if (!Body.IsEmpty())
		{
			ErrorText += TEXT(": ") + Body.Left(300);
		}

		if (ResponseCode == 401 || ResponseCode == 403)
		{
			ErrorText += TEXT(" - Check the API key in Project Settings > Plugins > Arena Agent.");
		}

		Result.bSuccess = false;
		Result.Error = ErrorText;
		return Result;
	}

	if (!bParsed)
	{
		Result.bSuccess = false;
		Result.Error = TEXT("Could not parse the API response as JSON.");
		return Result;
	}

	const TArray<TSharedPtr<FJsonValue>>* Choices = nullptr;
	if (!Root->TryGetArrayField(TEXT("choices"), Choices) || Choices->Num() == 0)
	{
		Result.bSuccess = false;
		Result.Error = TEXT("API response contains no choices.");
		return Result;
	}

	const TSharedPtr<FJsonObject>* FirstChoice = nullptr;
	if (!(*Choices)[0].IsValid() || !(*Choices)[0]->TryGetObject(FirstChoice) || !FirstChoice->IsValid())
	{
		Result.bSuccess = false;
		Result.Error = TEXT("API response choice is malformed.");
		return Result;
	}

	const TSharedPtr<FJsonObject>* MessageObject = nullptr;
	if (!(*FirstChoice)->TryGetObjectField(TEXT("message"), MessageObject) || !MessageObject->IsValid())
	{
		Result.bSuccess = false;
		Result.Error = TEXT("API response choice has no message.");
		return Result;
	}

	(*MessageObject)->TryGetStringField(TEXT("content"), Result.Content);

	const TArray<TSharedPtr<FJsonValue>>* ToolCallsArray = nullptr;
	if ((*MessageObject)->TryGetArrayField(TEXT("tool_calls"), ToolCallsArray))
	{
		for (const TSharedPtr<FJsonValue>& CallValue : *ToolCallsArray)
		{
			const TSharedPtr<FJsonObject>* CallObject = nullptr;
			if (!CallValue.IsValid() || !CallValue->TryGetObject(CallObject) || !CallObject->IsValid())
			{
				continue;
			}

			FArenaToolCall Call;
			(*CallObject)->TryGetStringField(TEXT("id"), Call.Id);

			const TSharedPtr<FJsonObject>* FunctionObject = nullptr;
			if ((*CallObject)->TryGetObjectField(TEXT("function"), FunctionObject) && FunctionObject->IsValid())
			{
				(*FunctionObject)->TryGetStringField(TEXT("name"), Call.Name);
				(*FunctionObject)->TryGetStringField(TEXT("arguments"), Call.ArgumentsJson);
			}

			if (Call.Id.IsEmpty())
			{
				Call.Id = FString::Printf(TEXT("call_%d"), Result.ToolCalls.Num());
			}

			// Validate / normalize the arguments JSON.
			if (Call.ArgumentsJson.IsEmpty())
			{
				Call.ArgumentsJson = TEXT("{}");
			}
			TSharedPtr<FJsonObject> ParsedArgs;
			TSharedRef<TJsonReader<>> ArgsReader = TJsonReaderFactory<>::Create(Call.ArgumentsJson);
			if (FJsonSerializer::Deserialize(ArgsReader, ParsedArgs) && ParsedArgs.IsValid())
			{
				Call.Arguments = ParsedArgs;
			}
			else
			{
				UE_LOG(LogArenaAgent, Warning, TEXT("Tool call %s had unparseable arguments: %s"), *Call.Name, *Call.ArgumentsJson);
				Call.ArgumentsJson = TEXT("{}");
				Call.Arguments = MakeShared<FJsonObject>();
			}

			Result.ToolCalls.Add(MoveTemp(Call));
		}
	}

	Result.bSuccess = true;
	return Result;
}

void FArenaApiClient::SendChatCompletion(const FArenaChatRequest& Request, FResponseHandler Handler)
{
	Cancel();
	bCancelled = false;

	const FString Url = RtrimSlash(Request.BaseUrl) + TEXT("/chat/completions");
	const FString Payload = BuildPayloadJson(Request);

	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> HttpRequest = FHttpModule::Get().CreateRequest();
	HttpRequest->SetURL(Url);
	HttpRequest->SetVerb(TEXT("POST"));
	HttpRequest->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	if (!Request.ApiKey.IsEmpty())
	{
		HttpRequest->SetHeader(TEXT("Authorization"), FString::Printf(TEXT("Bearer %s"), *Request.ApiKey));
	}
	HttpRequest->SetTimeout(FMath::Max(10, Request.TimeoutSeconds));
	HttpRequest->SetContentAsString(Payload);

	HttpRequest->OnProcessRequestComplete().BindLambda(
		[this, Handler](FHttpRequestPtr InRequest, FHttpResponsePtr Response, bool bConnected)
		{
			if (bCancelled)
			{
				return;
			}
			ActiveRequest.Reset();

			if (!Handler)
			{
				return;
			}

			if (!bConnected || !Response.IsValid())
			{
				FArenaApiResult Result;
				Result.bSuccess = false;
				Result.Error = TEXT("Network error - could not reach the API endpoint. Check the API Base URL and your connection.");
				Handler(MoveTemp(Result));
				return;
			}

			Handler(ParseResponse(Response->GetResponseCode(), Response->GetContentAsString()));
		});

	ActiveRequest = HttpRequest;

	if (!HttpRequest->ProcessRequest())
	{
		ActiveRequest.Reset();
		if (Handler)
		{
			FArenaApiResult Result;
			Result.bSuccess = false;
			Result.Error = TEXT("Failed to start the HTTP request.");
			Handler(MoveTemp(Result));
		}
	}
}

void FArenaApiClient::Cancel()
{
	if (ActiveRequest.IsValid())
	{
		bCancelled = true;
		ActiveRequest->CancelRequest();
		ActiveRequest.Reset();
	}
}
