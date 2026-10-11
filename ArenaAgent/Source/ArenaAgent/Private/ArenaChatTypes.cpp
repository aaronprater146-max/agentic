// Arena Agent - shared data type helpers.

#include "ArenaChatTypes.h"

#include "Dom/JsonObject.h"
#include "Misc/DateTime.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace ArenaChatHelpers
{

int64 NowUnix()
{
	return FDateTime::UtcNow().ToUnixTimestamp();
}

FString FormatTimestamp(int64 UnixSeconds)
{
	const FDateTime Time = FDateTime::FromUnixTimestamp(UnixSeconds);
	return Time.ToString(TEXT("%m/%d %H:%M"));
}

static FString MakeTimeString(int64 UnixSeconds)
{
	return UnixSeconds > 0 ? FormatTimestamp(UnixSeconds) : FString();
}

static FString TruncateMiddle(const FString& In, int32 MaxChars)
{
	if (In.Len() <= MaxChars)
	{
		return In;
	}
	const int32 Half = FMath::Max(8, MaxChars / 2);
	return In.Left(Half) + TEXT(" … ") + In.Right(Half);
}

TArray<FArenaDisplayMessage> BuildDisplayMessages(const FArenaConversation& Conversation)
{
	TArray<FArenaDisplayMessage> Result;

	for (const FArenaChatMessage& Message : Conversation.Messages)
	{
		if (Message.Role == TEXT("system"))
		{
			continue;
		}

		if (Message.Role == TEXT("user"))
		{
			FArenaDisplayMessage Display;
			Display.Role = TEXT("user");
			Display.Text = Message.Content;
			Display.TimeString = MakeTimeString(Message.Timestamp);
			Result.Add(Display);
			continue;
		}

		if (Message.Role == TEXT("assistant"))
		{
			// If the assistant message carried tool calls, show one compact line per call.
			if (!Message.ToolCallsJson.IsEmpty())
			{
				TArray<TSharedPtr<FJsonValue>> ParsedCalls;
				TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message.ToolCallsJson);
				if (FJsonSerializer::Deserialize(Reader, ParsedCalls))
				{
					for (const TSharedPtr<FJsonValue>& CallValue : ParsedCalls)
					{
						const TSharedPtr<FJsonObject>* CallObject = nullptr;
						if (!CallValue.IsValid() || !CallValue->TryGetObject(CallObject) || !CallObject->IsValid())
						{
							continue;
						}

						FString CallName;
						(*CallObject)->TryGetStringField(TEXT("name"), CallName);
						const TSharedPtr<FJsonObject>* FunctionObject = nullptr;
						if ((*CallObject)->TryGetObjectField(TEXT("function"), FunctionObject) && FunctionObject->IsValid())
						{
							FString FunctionName;
							if ((*FunctionObject)->TryGetStringField(TEXT("name"), FunctionName))
							{
								CallName = FunctionName;
							}
						}

						FArenaDisplayMessage Display;
						Display.Role = TEXT("tool");
						Display.Text = FString::Printf(TEXT("⚙ %s"), *CallName);
						Display.TimeString = MakeTimeString(Message.Timestamp);
						Result.Add(Display);
					}
				}
			}

			if (!Message.Content.TrimStartAndEnd().IsEmpty())
			{
				FArenaDisplayMessage Display;
				Display.Role = TEXT("assistant");
				Display.Text = Message.Content;
				Display.TimeString = MakeTimeString(Message.Timestamp);
				Result.Add(Display);
			}
			continue;
		}

		if (Message.Role == TEXT("tool"))
		{
			// Show a short summary of the tool result.
			FString Summary = Message.Content;
			TSharedPtr<FJsonObject> ResultObject;
			TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message.Content);
			if (FJsonSerializer::Deserialize(Reader, ResultObject) && ResultObject.IsValid())
			{
				bool bSuccess = false;
				ResultObject->TryGetBoolField(TEXT("success"), bSuccess);
				FString ResultMessage;
				ResultObject->TryGetStringField(TEXT("message"), ResultMessage);
				Summary = FString::Printf(TEXT("%s %s"), bSuccess ? TEXT("✓") : TEXT("✗"), *ResultMessage);
			}

			FArenaDisplayMessage Display;
			Display.Role = TEXT("tool");
			Display.Text = TruncateMiddle(Summary, 400);
			Display.TimeString = MakeTimeString(Message.Timestamp);
			Result.Add(Display);
			continue;
		}
	}

	return Result;
}

} // namespace ArenaChatHelpers
