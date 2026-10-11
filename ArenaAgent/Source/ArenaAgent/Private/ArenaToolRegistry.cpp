// Arena Agent - built-in editor tools implementation.

#include "ArenaToolRegistry.h"

#include "ArenaAgentLog.h"
#include "ArenaAgentSettings.h"
#include "ArenaBlueprintUtils.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "Components/ActorComponent.h"
#include "Dom/JsonValue.h"
#include "Editor.h"
#include "EditorSelectUtils.h"
#include "Engine/DataTable.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/FileManager.h"
#include "IPythonScriptPlugin.h"
#include "Misc/Paths.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/UObjectIterator.h"

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

FString FArenaToolResult::ToMessageString() const
{
	TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetBoolField(TEXT("success"), bSuccess);
	Root->SetStringField(TEXT("message"), Message);
	if (Data.IsValid())
	{
		Root->SetObjectField(TEXT("data"), Data);
	}

	FString Output;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
		TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Output);
	FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
	return Output;
}

static FString GetStringArg(const TSharedPtr<FJsonObject>& Args, const FString& Key, const FString& Default = TEXT(""))
{
	FString Value;
	if (Args.IsValid() && Args->TryGetStringField(Key, Value))
	{
		return Value.TrimStartAndEnd();
	}
	return Default;
}

static bool GetBoolArg(const TSharedPtr<FJsonObject>& Args, const FString& Key, bool Default = false)
{
	bool Value = Default;
	if (Args.IsValid())
	{
		Args->TryGetBoolField(Key, Value);
	}
	return Value;
}

static double GetNumberArg(const TSharedPtr<FJsonObject>& Args, const FString& Key, double Default = 0.0)
{
	double Value = Default;
	if (Args.IsValid())
	{
		Args->TryGetNumberField(Key, Value);
	}
	return Value;
}

static FVector GetVectorArg(const TSharedPtr<FJsonObject>& Args, const FString& Key, const FVector& Default = FVector::ZeroVector)
{
	FVector Value = Default;
	const TSharedPtr<FJsonObject>* Object = nullptr;
	if (Args.IsValid() && Args->TryGetObjectField(Key, Object) && Object->IsValid())
	{
		double X = Default.X;
		double Y = Default.Y;
		double Z = Default.Z;
		(*Object)->TryGetNumberField(TEXT("x"), X);
		(*Object)->TryGetNumberField(TEXT("y"), Y);
		(*Object)->TryGetNumberField(TEXT("z"), Z);
		Value = FVector(X, Y, Z);
	}
	return Value;
}

static TMap<FString, FString> GetStringMapArg(const TSharedPtr<FJsonObject>& Args, const FString& Key)
{
	TMap<FString, FString> Result;
	const TSharedPtr<FJsonObject>* Object = nullptr;
	if (Args.IsValid() && Args->TryGetObjectField(Key, Object) && Object->IsValid())
	{
		for (const TPair<FString, TSharedPtr<FJsonValue>>& Pair : (*Object)->Values)
		{
			FString Value;
			if (Pair.Value.IsValid() && Pair.Value->TryGetString(Value))
			{
				Result.Add(Pair.Key, Value);
			}
		}
	}
	return Result;
}

/** Parses an array of {name, type} objects, e.g. function parameters. */
static TArray<TPair<FString, FString>> GetNamedTypeArrayArg(const TSharedPtr<FJsonObject>& Args, const FString& Key)
{
	TArray<TPair<FString, FString>> Result;
	const TArray<TSharedPtr<FJsonValue>>* ArrayValue = nullptr;
	if (!Args.IsValid() || !Args->TryGetArrayField(Key, ArrayValue))
	{
		return Result;
	}
	for (const TSharedPtr<FJsonValue>& Value : *ArrayValue)
	{
		const TSharedPtr<FJsonObject>* Object = nullptr;
		if (Value.IsValid() && Value->TryGetObject(Object) && Object->IsValid())
		{
			FString Name;
			FString Type;
			(*Object)->TryGetStringField(TEXT("name"), Name);
			(*Object)->TryGetStringField(TEXT("type"), Type);
			if (!Name.IsEmpty())
			{
				Result.Add(TPair<FString, FString>(Name, Type.IsEmpty() ? TEXT("float") : Type));
			}
		}
	}
	return Result;
}

static void MaybeAutoSave(UObject* Asset)
{
	if (GetDefault<UArenaAgentSettings>()->bAutoSaveAssets)
	{
		FArenaBlueprintUtils::SaveAsset(Asset);
	}
}

/** Small JSON-schema builder. */
class FArenaSchemaBuilder
{
public:
	FArenaSchemaBuilder()
	{
		Root = MakeShared<FJsonObject>();
		Root->SetStringField(TEXT("type"), TEXT("object"));
		Properties = MakeShared<FJsonObject>();
	}

	FArenaSchemaBuilder& Add(const FString& Name, const FString& Type, const FString& Description)
	{
		TSharedPtr<FJsonObject> Property = MakeShared<FJsonObject>();
		Property->SetStringField(TEXT("type"), Type);
		Property->SetStringField(TEXT("description"), Description);
		Properties->SetObjectField(Name, Property);
		return *this;
	}

	FArenaSchemaBuilder& Require(const FString& Name)
	{
		Required.Add(MakeShared<FJsonValueString>(Name));
		return *this;
	}

	TSharedPtr<FJsonObject> Build()
	{
		Root->SetObjectField(TEXT("properties"), Properties);
		if (Required.Num() > 0)
		{
			Root->SetArrayField(TEXT("required"), Required);
		}
		return Root;
	}

private:
	TSharedPtr<FJsonObject> Root;
	TSharedPtr<FJsonObject> Properties;
	TArray<TSharedPtr<FJsonValue>> Required;
};

// ----------------------------------------------------------------------------
// Registry
// ----------------------------------------------------------------------------

FArenaToolRegistry& FArenaToolRegistry::Get()
{
	static FArenaToolRegistry Instance;
	return Instance;
}

FArenaToolRegistry::FArenaToolRegistry()
{
	RegisterBuiltInTools();
}

void FArenaToolRegistry::RegisterTool(const FString& Name, const FString& Description,
	const TSharedPtr<FJsonObject>& ParametersSchema, FExecutor Executor)
{
	FToolDefinition Definition;
	Definition.Name = Name;
	Definition.Description = Description;
	Definition.ParametersSchema = ParametersSchema.IsValid() ? ParametersSchema : MakeShared<FJsonObject>();
	Definition.Executor = MoveTemp(Executor);
	Tools.Add(MoveTemp(Definition));
}

TArray<TSharedPtr<FJsonObject>> FArenaToolRegistry::BuildOpenAIToolSchemas() const
{
	TArray<TSharedPtr<FJsonObject>> Schemas;
	Schemas.Reserve(Tools.Num());
	for (const FToolDefinition& Tool : Tools)
	{
		TSharedPtr<FJsonObject> ToolSchema = MakeShared<FJsonObject>();
		ToolSchema->SetStringField(TEXT("type"), TEXT("function"));

		TSharedPtr<FJsonObject> Function = MakeShared<FJsonObject>();
		Function->SetStringField(TEXT("name"), Tool.Name);
		Function->SetStringField(TEXT("description"), Tool.Description);
		Function->SetObjectField(TEXT("parameters"), Tool.ParametersSchema);

		ToolSchema->SetObjectField(TEXT("function"), Function);
		Schemas.Add(ToolSchema);
	}
	return Schemas;
}

FArenaToolResult FArenaToolRegistry::Execute(const FString& ToolName, const TSharedPtr<FJsonObject>& Args)
{
	for (const FToolDefinition& Tool : Tools)
	{
		if (Tool.Name == ToolName && Tool.Executor)
		{
			UE_LOG(LogArenaAgent, Log, TEXT("Executing tool: %s"), *ToolName);
			return Tool.Executor(Args);
		}
	}
	return FArenaToolResult::Err(FString::Printf(TEXT("Unknown tool '%s'."), *ToolName));
}

// ----------------------------------------------------------------------------
// Tool implementations
// ----------------------------------------------------------------------------

void FArenaToolRegistry::RegisterBuiltInTools()
{
	// ------------------------------------------------------------------ info
	RegisterTool(TEXT("get_editor_context"),
		TEXT("Returns information about the current editor state: the open level, selected actors and the configured default asset folder. Call this first when unsure about the environment."),
		FArenaSchemaBuilder().Build(),
		[](const TSharedPtr<FJsonObject>&) -> FArenaToolResult
		{
			TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();

			UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
			if (World)
			{
				Data->SetStringField(TEXT("level"), World->GetMapName());
			}

			TArray<TSharedPtr<FJsonValue>> Selection;
			if (GEditor)
			{
				for (FSelectionIterator It(GEditor->GetSelectedActorIterator()); It; ++It)
				{
					AActor* Actor = Cast<AActor>(*It);
					if (!Actor)
					{
						continue;
					}
					TSharedPtr<FJsonObject> ActorObject = MakeShared<FJsonObject>();
					ActorObject->SetStringField(TEXT("name"), Actor->GetName());
					ActorObject->SetStringField(TEXT("label"), Actor->GetActorLabel());
					if (Actor->GetClass())
					{
						ActorObject->SetStringField(TEXT("class"), Actor->GetClass()->GetPathName());
					}
					Selection.Add(MakeShared<FJsonValueObject>(ActorObject));
				}
			}
			Data->SetArrayField(TEXT("selected_actors"), Selection);
			Data->SetStringField(TEXT("default_asset_folder"), GetDefault<UArenaAgentSettings>()->DefaultAssetFolder);

			return FArenaToolResult::Ok(TEXT("Editor context."), Data);
		});

	// --------------------------------------------------------------- create
	RegisterTool(TEXT("create_blueprint"),
		TEXT("Creates a new Blueprint asset. parent_class is an Unreal class path such as /Script/Engine.Actor, /Script/Engine.Character, /Script/Engine.Pawn, /Script/Engine.GameModeBase, /Script/Engine.PlayerController, /Script/Engine.HUD. UserWidget-derived parents create Widget Blueprints. asset_path is a full /Game/ object path without extension, e.g. /Game/ArenaAI/BP_Hero."),
		FArenaSchemaBuilder()
			.Add(TEXT("asset_path"), TEXT("string"), TEXT("Target object path, e.g. /Game/ArenaAI/BP_Hero"))
			.Add(TEXT("parent_class"), TEXT("string"), TEXT("Parent class path. Defaults to /Script/Engine.Actor"))
			.Require(TEXT("asset_path"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString AssetPath = GetStringArg(Args, TEXT("asset_path"));
			const FString ParentClassPath = GetStringArg(Args, TEXT("parent_class"), TEXT("/Script/Engine.Actor"));

			if (AssetPath.IsEmpty())
			{
				return FArenaToolResult::Err(TEXT("asset_path is required."));
			}

			UClass* ParentClass = FArenaBlueprintUtils::ResolveClass(ParentClassPath);
			if (!ParentClass)
			{
				return FArenaToolResult::Err(FString::Printf(
					TEXT("Parent class '%s' could not be resolved. Use search_classes to find a valid class path."), *ParentClassPath));
			}

			FString Error;
			UBlueprint* Blueprint = FArenaBlueprintUtils::CreateBlueprintAsset(ParentClass, AssetPath, Error);
			if (!Blueprint)
			{
				return FArenaToolResult::Err(Error);
			}

			FArenaBlueprintUtils::CompileBlueprint(Blueprint, Error);
			MaybeAutoSave(Blueprint);

			return FArenaToolResult::Ok(
				FString::Printf(TEXT("Created Blueprint %s with parent %s."), *Blueprint->GetPathName(), *ParentClass->GetPathName()),
				FArenaBlueprintUtils::DescribeBlueprint(Blueprint));
		});

	// ------------------------------------------------------------ component
	RegisterTool(TEXT("add_component"),
		TEXT("Adds a component to an Actor Blueprint's component list. component_class is e.g. /Script/Engine.StaticMeshComponent, /Script/Engine.BoxComponent, /Script/Engine.SceneComponent, /Script/Engine.SkeletalMeshComponent, /Script/Engine.CameraComponent, /Script/Engine.AudioComponent."),
		FArenaSchemaBuilder()
			.Add(TEXT("blueprint"), TEXT("string"), TEXT("Blueprint object path"))
			.Add(TEXT("component_class"), TEXT("string"), TEXT("Component class path"))
			.Add(TEXT("name"), TEXT("string"), TEXT("Component name (variable name)"))
			.Add(TEXT("attach_to"), TEXT("string"), TEXT("Optional: name of an existing component to attach to"))
			.Add(TEXT("location"), TEXT("object"), TEXT("Optional relative location {x,y,z}"))
			.Add(TEXT("rotation"), TEXT("object"), TEXT("Optional relative rotation {pitch,yaw,roll}"))
			.Add(TEXT("scale"), TEXT("object"), TEXT("Optional relative scale {x,y,z}, defaults to 1"))
			.Require(TEXT("blueprint")).Require(TEXT("component_class")).Require(TEXT("name"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString BlueprintPath = GetStringArg(Args, TEXT("blueprint"));
			UBlueprint* Blueprint = FArenaBlueprintUtils::LoadBlueprint(BlueprintPath);
			if (!Blueprint)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Blueprint '%s' could not be loaded."), *BlueprintPath));
			}

			const FString ComponentClassPath = GetStringArg(Args, TEXT("component_class"));
			UClass* ComponentClass = FArenaBlueprintUtils::ResolveClass(ComponentClassPath);
			if (!ComponentClass)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Component class '%s' could not be resolved."), *ComponentClassPath));
			}

			const FName ComponentName(*GetStringArg(Args, TEXT("name")));
			if (ComponentName == NAME_None)
			{
				return FArenaToolResult::Err(TEXT("name is required."));
			}

			const FVector Location = GetVectorArg(Args, TEXT("location"));
			const FVector ScaleValue = GetVectorArg(Args, TEXT("scale"), FVector::OneVector);
			const FVector RotationValue = GetVectorArg(Args, TEXT("rotation"));
			const FRotator Rotation(RotationValue.X, RotationValue.Y, RotationValue.Z);

			FString Error;
			USCS_Node* Node = FArenaBlueprintUtils::AddComponent(Blueprint, ComponentClass, ComponentName,
				FName(*GetStringArg(Args, TEXT("attach_to"))), Location, Rotation, ScaleValue, Error);
			if (!Node)
			{
				return FArenaToolResult::Err(Error);
			}

			FArenaBlueprintUtils::CompileBlueprint(Blueprint, Error);
			MaybeAutoSave(Blueprint);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Added component '%s' (%s) to %s."),
				*ComponentName.ToString(), *ComponentClassPath, *BlueprintPath));
		});

	// ------------------------------------------------------------- variable
	RegisterTool(TEXT("add_variable"),
		TEXT("Adds a variable to a Blueprint. Supported types: float, int, int64, bool, string, name, text, vector, vector2d, rotator, transform, color, linearcolor, object (with object_class), enum (with enum_path). Set is_array true for arrays."),
		FArenaSchemaBuilder()
			.Add(TEXT("blueprint"), TEXT("string"), TEXT("Blueprint object path"))
			.Add(TEXT("name"), TEXT("string"), TEXT("Variable name"))
			.Add(TEXT("type"), TEXT("string"), TEXT("Type token, e.g. float, int, bool, string, vector, object. Defaults to float"))
			.Add(TEXT("is_array"), TEXT("boolean"), TEXT("Optional: make it an array"))
			.Add(TEXT("object_class"), TEXT("string"), TEXT("For type=object: class path the object reference accepts"))
			.Add(TEXT("enum_path"), TEXT("string"), TEXT("For type=enum: enum object path"))
			.Add(TEXT("default_value"), TEXT("string"), TEXT("Optional default value as string"))
			.Add(TEXT("category"), TEXT("string"), TEXT("Optional editor category"))
			.Add(TEXT("tooltip"), TEXT("string"), TEXT("Optional tooltip"))
			.Require(TEXT("blueprint")).Require(TEXT("name"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString BlueprintPath = GetStringArg(Args, TEXT("blueprint"));
			UBlueprint* Blueprint = FArenaBlueprintUtils::LoadBlueprint(BlueprintPath);
			if (!Blueprint)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Blueprint '%s' could not be loaded."), *BlueprintPath));
			}

			FString Error;
			if (!FArenaBlueprintUtils::AddVariable(Blueprint,
				GetStringArg(Args, TEXT("name")),
				GetStringArg(Args, TEXT("type"), TEXT("float")),
				GetBoolArg(Args, TEXT("is_array")),
				GetStringArg(Args, TEXT("object_class")),
				GetStringArg(Args, TEXT("enum_path")),
				GetStringArg(Args, TEXT("default_value")),
				GetStringArg(Args, TEXT("category"), TEXT("Default")),
				GetStringArg(Args, TEXT("tooltip")),
				Error))
			{
				return FArenaToolResult::Err(Error);
			}

			FArenaBlueprintUtils::CompileBlueprint(Blueprint, Error);
			MaybeAutoSave(Blueprint);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Added variable '%s' to %s."), *GetStringArg(Args, TEXT("name")), *BlueprintPath));
		});

	// ------------------------------------------------------------- function
	RegisterTool(TEXT("add_function"),
		TEXT("Adds a new function to a Blueprint with typed input and output parameters plus a wired entry->result execution chain."),
		FArenaSchemaBuilder()
			.Add(TEXT("blueprint"), TEXT("string"), TEXT("Blueprint object path"))
			.Add(TEXT("name"), TEXT("string"), TEXT("Function name"))
			.Add(TEXT("inputs"), TEXT("array"), TEXT("Optional inputs: [{\"name\": \"Damage\", \"type\": \"float\"}, ...]"))
			.Add(TEXT("outputs"), TEXT("array"), TEXT("Optional outputs: [{\"name\": \"Result\", \"type\": \"bool\"}, ...]"))
			.Require(TEXT("blueprint")).Require(TEXT("name"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString BlueprintPath = GetStringArg(Args, TEXT("blueprint"));
			UBlueprint* Blueprint = FArenaBlueprintUtils::LoadBlueprint(BlueprintPath);
			if (!Blueprint)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Blueprint '%s' could not be loaded."), *BlueprintPath));
			}

			const FString FunctionName = GetStringArg(Args, TEXT("name"));
			if (FunctionName.IsEmpty())
			{
				return FArenaToolResult::Err(TEXT("name is required."));
			}

			auto BuildPins = [&](const TArray<TPair<FString, FString>>& Raw, TArray<TPair<FString, FEdGraphPinType>>& Out, FString& OutError) -> bool
			{
				for (const TPair<FString, FString>& Entry : Raw)
				{
					FEdGraphPinType PinType;
					if (!FArenaBlueprintUtils::PinTypeFromToken(Entry.Value, false, TEXT(), TEXT(), PinType, OutError))
					{
						return false;
					}
					Out.Add(TPair<FString, FEdGraphPinType>(Entry.Key, PinType));
				}
				return true;
			};

			FString Error;
			TArray<TPair<FString, FEdGraphPinType>> Inputs;
			TArray<TPair<FString, FEdGraphPinType>> Outputs;
			if (!BuildPins(GetNamedTypeArrayArg(Args, TEXT("inputs")), Inputs, Error) ||
				!BuildPins(GetNamedTypeArrayArg(Args, TEXT("outputs")), Outputs, Error))
			{
				return FArenaToolResult::Err(Error);
			}

			if (!FArenaBlueprintUtils::AddFunction(Blueprint, FunctionName, Inputs, Outputs, Error))
			{
				return FArenaToolResult::Err(Error);
			}

			FArenaBlueprintUtils::CompileBlueprint(Blueprint, Error);
			MaybeAutoSave(Blueprint);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Added function '%s' to %s."), *FunctionName, *BlueprintPath));
		});

	// ---------------------------------------------------------------- event
	RegisterTool(TEXT("add_event"),
		TEXT("Adds an event node to the Blueprint's EventGraph, creating the graph if needed. event can be a friendly name (BeginPlay, Tick, EndPlay, ActorBeginOverlap, ActorHit, Destroyed, Construction, Possessed, AnyDamage) or a raw event function name such as ReceiveBeginPlay."),
		FArenaSchemaBuilder()
			.Add(TEXT("blueprint"), TEXT("string"), TEXT("Blueprint object path"))
			.Add(TEXT("event"), TEXT("string"), TEXT("Friendly or raw event name, e.g. BeginPlay or ReceiveTick"))
			.Require(TEXT("blueprint")).Require(TEXT("event"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString BlueprintPath = GetStringArg(Args, TEXT("blueprint"));
			UBlueprint* Blueprint = FArenaBlueprintUtils::LoadBlueprint(BlueprintPath);
			if (!Blueprint)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Blueprint '%s' could not be loaded."), *BlueprintPath));
			}

			FString Error;
			if (!FArenaBlueprintUtils::AddEvent(Blueprint, GetStringArg(Args, TEXT("event")), Error))
			{
				return FArenaToolResult::Err(Error);
			}

			FArenaBlueprintUtils::CompileBlueprint(Blueprint, Error);
			MaybeAutoSave(Blueprint);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Added event '%s' to %s."), *GetStringArg(Args, TEXT("event")), *BlueprintPath));
		});

	// ------------------------------------------------------------ call node
	RegisterTool(TEXT("add_call_node"),
		TEXT("Appends a Call Function node to the end of an execution chain. Targets an event node (anchor_event) inside an event graph, or a function entry (anchor_function). params sets literal pin default values, e.g. {\"InString\": \"Hello\"}. Example: call PrintString after BeginPlay with owner /Script/Engine.KismetSystemLibrary."),
		FArenaSchemaBuilder()
			.Add(TEXT("blueprint"), TEXT("string"), TEXT("Blueprint object path"))
			.Add(TEXT("function"), TEXT("string"), TEXT("Function to call, e.g. PrintString, ApplyDamage, K2_SetActorLocation"))
			.Add(TEXT("owner"), TEXT("string"), TEXT("Optional class owning the function. Defaults to the Blueprint parent class. Use /Script/Engine.KismetSystemLibrary for PrintString etc."))
			.Add(TEXT("anchor_event"), TEXT("string"), TEXT("Attach after this event node, e.g. ReceiveBeginPlay"))
			.Add(TEXT("anchor_function"), TEXT("string"), TEXT("Attach inside this function graph"))
			.Add(TEXT("graph"), TEXT("string"), TEXT("Optional explicit graph name (defaults to EventGraph)"))
			.Add(TEXT("params"), TEXT("object"), TEXT("Optional pin default values as {pin_name: value}"))
			.Require(TEXT("blueprint")).Require(TEXT("function"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString BlueprintPath = GetStringArg(Args, TEXT("blueprint"));
			UBlueprint* Blueprint = FArenaBlueprintUtils::LoadBlueprint(BlueprintPath);
			if (!Blueprint)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Blueprint '%s' could not be loaded."), *BlueprintPath));
			}

			FString Error;
			if (!FArenaBlueprintUtils::AddCallNode(Blueprint,
				GetStringArg(Args, TEXT("graph")),
				GetStringArg(Args, TEXT("anchor_event")),
				GetStringArg(Args, TEXT("anchor_function")),
				GetStringArg(Args, TEXT("function")),
				GetStringArg(Args, TEXT("owner")),
				GetStringMapArg(Args, TEXT("params")),
				Error))
			{
				return FArenaToolResult::Err(Error);
			}

			FArenaBlueprintUtils::CompileBlueprint(Blueprint, Error);
			MaybeAutoSave(Blueprint);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Added call to '%s' in %s."), *GetStringArg(Args, TEXT("function")), *BlueprintPath));
		});

	// -------------------------------------------------------------- compile
	RegisterTool(TEXT("compile_blueprint"),
		TEXT("Recompiles a Blueprint. Use after edits if you need to force compilation."),
		FArenaSchemaBuilder()
			.Add(TEXT("blueprint"), TEXT("string"), TEXT("Blueprint object path"))
			.Require(TEXT("blueprint"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString BlueprintPath = GetStringArg(Args, TEXT("blueprint"));
			UBlueprint* Blueprint = FArenaBlueprintUtils::LoadBlueprint(BlueprintPath);
			if (!Blueprint)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Blueprint '%s' could not be loaded."), *BlueprintPath));
			}

			FString Error;
			if (!FArenaBlueprintUtils::CompileBlueprint(Blueprint, Error))
			{
				return FArenaToolResult::Err(Error);
			}
			return FArenaToolResult::Ok(FString::Printf(TEXT("Compiled %s."), *BlueprintPath));
		});

	// ------------------------------------------------------------- describe
	RegisterTool(TEXT("get_blueprint_info"),
		TEXT("Returns the structure of a Blueprint: parent class, components, variables, functions and events. Use it to verify your changes."),
		FArenaSchemaBuilder()
			.Add(TEXT("blueprint"), TEXT("string"), TEXT("Blueprint object path"))
			.Require(TEXT("blueprint"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString BlueprintPath = GetStringArg(Args, TEXT("blueprint"));
			UBlueprint* Blueprint = FArenaBlueprintUtils::LoadBlueprint(BlueprintPath);
			if (!Blueprint)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Blueprint '%s' could not be loaded."), *BlueprintPath));
			}
			return FArenaToolResult::Ok(FString::Printf(TEXT("Described %s."), *BlueprintPath),
				FArenaBlueprintUtils::DescribeBlueprint(Blueprint));
		});

	// ---------------------------------------------------------------- spawn
	RegisterTool(TEXT("spawn_actor"),
		TEXT("Spawns an instance of a Blueprint (or native class) into the current editor level."),
		FArenaSchemaBuilder()
			.Add(TEXT("class"), TEXT("string"), TEXT("Blueprint object path or native class path"))
			.Add(TEXT("location"), TEXT("object"), TEXT("Optional spawn location {x,y,z}"))
			.Add(TEXT("yaw"), TEXT("number"), TEXT("Optional yaw rotation in degrees"))
			.Require(TEXT("class"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString ClassPath = GetStringArg(Args, TEXT("class"));
			UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
			if (!World)
			{
				return FArenaToolResult::Err(TEXT("No editor world available."));
			}

			UClass* SpawnClass = nullptr;
			if (UBlueprint* Blueprint = FArenaBlueprintUtils::LoadBlueprint(ClassPath))
			{
				SpawnClass = Blueprint->GeneratedClass;
			}
			else
			{
				SpawnClass = FArenaBlueprintUtils::ResolveClass(ClassPath);
			}
			if (!SpawnClass)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("'%s' could not be resolved to a spawnable class."), *ClassPath));
			}
			if (!SpawnClass->IsChildOf<AActor>())
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("'%s' is not an Actor class."), *ClassPath));
			}

			const FVector Location = GetVectorArg(Args, TEXT("location"));
			const FRotator Rotation(0.0, GetNumberArg(Args, TEXT("yaw")), 0.0);

			FActorSpawnParameters SpawnParams;
			SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			AActor* SpawnedActor = World->SpawnActor<AActor>(SpawnClass, &Location, &Rotation, SpawnParams);
			if (!SpawnedActor)
			{
				return FArenaToolResult::Err(TEXT("SpawnActor failed."));
			}

			TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
			Data->SetStringField(TEXT("actor_name"), SpawnedActor->GetName());
			Data->SetStringField(TEXT("label"), SpawnedActor->GetActorLabel());

			return FArenaToolResult::Ok(
				FString::Printf(TEXT("Spawned '%s' at (%.0f, %.0f, %.0f)."), *SpawnedActor->GetActorLabel(), Location.X, Location.Y, Location.Z),
				Data);
		});

	// ----------------------------------------------------------------- list
	RegisterTool(TEXT("list_assets"),
		TEXT("Lists assets under a content path, optionally filtered by class name (e.g. Blueprint, DataTable)."),
		FArenaSchemaBuilder()
			.Add(TEXT("path"), TEXT("string"), TEXT("Content path, defaults to /Game"))
			.Add(TEXT("filter"), TEXT("string"), TEXT("Optional class name substring filter"))
			.Add(TEXT("recursive"), TEXT("boolean"), TEXT("Search subfolders, defaults to true"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString Path = GetStringArg(Args, TEXT("path"), TEXT("/Game"));
			const FString Filter = GetStringArg(Args, TEXT("filter"));
			const bool bRecursive = GetBoolArg(Args, TEXT("recursive"), true);

			FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
			TArray<FAssetData> Assets;
			AssetRegistryModule.Get().GetAssetsByPath(FName(*Path), Assets, bRecursive);

			TArray<TSharedPtr<FJsonValue>> Items;
			int32 Count = 0;
			for (const FAssetData& Asset : Assets)
			{
				const FString ClassName = Asset.AssetClassPath.GetAssetName().ToString();
				if (!Filter.IsEmpty() && !ClassName.Contains(Filter, ESearchCase::IgnoreCase))
				{
					continue;
				}
				TSharedPtr<FJsonObject> Item = MakeShared<FJsonObject>();
				Item->SetStringField(TEXT("path"), Asset.GetObjectPathString());
				Item->SetStringField(TEXT("class"), ClassName);
				Items.Add(MakeShared<FJsonValueObject>(Item));
				if (++Count >= 100)
				{
					break;
				}
			}

			TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
			Data->SetArrayField(TEXT("assets"), Items);
			Data->SetNumberField(TEXT("count"), Count);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Found %d asset(s) under %s."), Count, *Path), Data);
		});

	// -------------------------------------------------------- search classes
	RegisterTool(TEXT("search_classes"),
		TEXT("Searches Unreal classes by name substring to discover valid parent or component class paths. Optionally restrict to subclasses of base_class."),
		FArenaSchemaBuilder()
			.Add(TEXT("query"), TEXT("string"), TEXT("Name substring to search for, e.g. Character or Health"))
			.Add(TEXT("base_class"), TEXT("string"), TEXT("Optional: only return subclasses of this class path"))
			.Require(TEXT("query"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString Query = GetStringArg(Args, TEXT("query"));
			const FString BaseClassPath = GetStringArg(Args, TEXT("base_class"));

			UClass* BaseClass = nullptr;
			if (!BaseClassPath.IsEmpty())
			{
				BaseClass = FArenaBlueprintUtils::ResolveClass(BaseClassPath);
				if (!BaseClass)
				{
					return FArenaToolResult::Err(FString::Printf(TEXT("base_class '%s' could not be resolved."), *BaseClassPath));
				}
			}

			TArray<UClass*> Candidates;
			if (BaseClass)
			{
				GetDerivedClasses(BaseClass, Candidates, true);
				Candidates.Insert(BaseClass, 0);
			}
			else
			{
				for (TObjectIterator<UClass> It; It; ++It)
				{
					Candidates.Add(*It);
				}
			}

			TArray<TSharedPtr<FJsonValue>> Items;
			int32 Count = 0;
			TSet<FString> Seen;
			for (const UClass* Candidate : Candidates)
			{
				if (!Candidate)
				{
					continue;
				}
				if (!Candidate->GetName().Contains(Query, ESearchCase::IgnoreCase))
				{
					continue;
				}
				const FString ClassPath = Candidate->GetPathName();
				if (Seen.Contains(ClassPath))
				{
					continue;
				}
				Seen.Add(ClassPath);
				Items.Add(MakeShared<FJsonValueString>(ClassPath));
				if (++Count >= 30)
				{
					break;
				}
			}

			TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
			Data->SetArrayField(TEXT("classes"), Items);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Found %d class(es) matching '%s'."), Count, *Query), Data);
		});

	// ---------------------------------------------------------------- folder
	RegisterTool(TEXT("create_folder"),
		TEXT("Creates a folder in the project's Content directory. Path must start with /Game/."),
		FArenaSchemaBuilder()
			.Add(TEXT("path"), TEXT("string"), TEXT("Folder path, e.g. /Game/ArenaAI/RPG"))
			.Require(TEXT("path"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString Path = GetStringArg(Args, TEXT("path"));
			if (!Path.StartsWith(TEXT("/Game/")))
			{
				return FArenaToolResult::Err(TEXT("Path must start with /Game/."));
			}

			const FString RelativePath = Path.Mid(6);
			const FString AbsolutePath = FPaths::Combine(FPaths::ProjectContentDir(), RelativePath);
			if (IFileManager::Get().MakeDirectory(*AbsolutePath, true))
			{
				return FArenaToolResult::Ok(FString::Printf(TEXT("Created folder %s."), *Path));
			}
			return FArenaToolResult::Err(FString::Printf(TEXT("Could not create folder %s."), *Path));
		});

	// ----------------------------------------------------------- data table
	RegisterTool(TEXT("create_data_table"),
		TEXT("Creates an empty DataTable asset with the given row structure, e.g. row_struct /Script/Engine.DataTable or a custom UserDefinedStruct path."),
		FArenaSchemaBuilder()
			.Add(TEXT("asset_path"), TEXT("string"), TEXT("Target object path, e.g. /Game/ArenaAI/DT_Items"))
			.Add(TEXT("row_struct"), TEXT("string"), TEXT("Row structure path"))
			.Require(TEXT("asset_path")).Require(TEXT("row_struct"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString AssetPath = GetStringArg(Args, TEXT("asset_path"));
			const FString RowStructPath = GetStringArg(Args, TEXT("row_struct"));

			FString PackagePath;
			FString AssetName;
			if (!FArenaBlueprintUtils::SplitAssetPath(AssetPath, PackagePath, AssetName))
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("'%s' is not a valid /Game/ asset path."), *AssetPath));
			}

			UStruct* RowStruct = LoadObject<UStruct>(nullptr, *RowStructPath);
			if (!RowStruct)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Row structure '%s' could not be resolved."), *RowStructPath));
			}

			if (LoadObject<UObject>(nullptr, *AssetPath))
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("An asset already exists at %s."), *AssetPath));
			}

			UPackage* Package = CreatePackage(*PackagePath);
			UDataTable* Table = NewObject<UDataTable>(Package, FName(*AssetName), RF_Public | RF_Standalone);
			Table->RowStruct = RowStruct;
			Package->MarkPackageDirty();
			FAssetRegistryModule::AssetCreated(Table);
			MaybeAutoSave(Table);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Created DataTable %s."), *AssetPath));
		});

	// ---------------------------------------------------------------- rename
	RegisterTool(TEXT("rename_asset"),
		TEXT("Renames or moves an asset to a new /Game/ path."),
		FArenaSchemaBuilder()
			.Add(TEXT("asset_path"), TEXT("string"), TEXT("Current object path"))
			.Add(TEXT("new_path"), TEXT("string"), TEXT("New object path"))
			.Require(TEXT("asset_path")).Require(TEXT("new_path"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString OldPath = GetStringArg(Args, TEXT("asset_path"));
			const FString NewPath = GetStringArg(Args, TEXT("new_path"));

			FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
			if (AssetToolsModule.Get().RenameAsset(FName(*OldPath), FName(*NewPath)))
			{
				return FArenaToolResult::Ok(FString::Printf(TEXT("Renamed %s to %s."), *OldPath, *NewPath));
			}
			return FArenaToolResult::Err(FString::Printf(TEXT("Rename from %s to %s failed."), *OldPath, *NewPath));
		});

	// ------------------------------------------------------------- duplicate
	RegisterTool(TEXT("duplicate_asset"),
		TEXT("Duplicates an asset inside its folder with a new name."),
		FArenaSchemaBuilder()
			.Add(TEXT("asset_path"), TEXT("string"), TEXT("Source object path"))
			.Add(TEXT("new_name"), TEXT("string"), TEXT("Name for the copy"))
			.Require(TEXT("asset_path")).Require(TEXT("new_name"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString AssetPath = GetStringArg(Args, TEXT("asset_path"));
			const FString NewName = GetStringArg(Args, TEXT("new_name"));

			FString PackagePath;
			FString AssetName;
			if (!FArenaBlueprintUtils::SplitAssetPath(AssetPath, PackagePath, AssetName))
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("'%s' is not a valid /Game/ asset path."), *AssetPath));
			}

			FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
			UObject* Duplicate = AssetToolsModule.Get().DuplicateAsset(NewName, PackagePath);
			if (!Duplicate)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Duplicating %s failed."), *AssetPath));
			}
			MaybeAutoSave(Duplicate);

			return FArenaToolResult::Ok(FString::Printf(TEXT("Duplicated %s as %s."), *AssetPath, *Duplicate->GetPathName()));
		});

	// ---------------------------------------------------------------- delete
	RegisterTool(TEXT("delete_asset"),
		TEXT("Deletes an asset from the project. The editor may ask for confirmation."),
		FArenaSchemaBuilder()
			.Add(TEXT("asset_path"), TEXT("string"), TEXT("Object path to delete"))
			.Require(TEXT("asset_path"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString AssetPath = GetStringArg(Args, TEXT("asset_path"));
			UObject* Asset = LoadObject<UObject>(nullptr, *AssetPath);
			if (!Asset)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Asset '%s' could not be loaded."), *AssetPath));
			}

			TArray<UObject*> ObjectsToDelete;
			ObjectsToDelete.Add(Asset);
			FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
			AssetToolsModule.Get().DeleteAssets(ObjectsToDelete, FText::GetEmpty());

			if (LoadObject<UObject>(nullptr, *AssetPath))
			{
				return FArenaToolResult::Err(TEXT("Deletion was cancelled or failed."));
			}
			return FArenaToolResult::Ok(FString::Printf(TEXT("Deleted %s."), *AssetPath));
		});

	// ------------------------------------------------------------------ open
	RegisterTool(TEXT("open_asset"),
		TEXT("Opens an asset in its editor."),
		FArenaSchemaBuilder()
			.Add(TEXT("asset_path"), TEXT("string"), TEXT("Object path to open"))
			.Require(TEXT("asset_path"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			const FString AssetPath = GetStringArg(Args, TEXT("asset_path"));
			UObject* Asset = LoadObject<UObject>(nullptr, *AssetPath);
			if (!Asset)
			{
				return FArenaToolResult::Err(FString::Printf(TEXT("Asset '%s' could not be loaded."), *AssetPath));
			}

			UAssetEditorSubsystem* AssetEditorSubsystem = GEditor ? GEditor->GetEditorSubsystem<UAssetEditorSubsystem>() : nullptr;
			if (AssetEditorSubsystem && AssetEditorSubsystem->OpenEditorForAsset(Asset))
			{
				return FArenaToolResult::Ok(FString::Printf(TEXT("Opened %s."), *AssetPath));
			}
			return FArenaToolResult::Err(FString::Printf(TEXT("Could not open %s."), *AssetPath));
		});

	// ---------------------------------------------------------------- python
	RegisterTool(TEXT("run_python"),
		TEXT("Executes Unreal Editor Python code. Use only for tasks the dedicated tools cannot do, and only when the user enabled Python in the Arena Agent settings. The code runs with full editor access (unreal module available)."),
		FArenaSchemaBuilder()
			.Add(TEXT("code"), TEXT("string"), TEXT("Python source code to execute"))
			.Require(TEXT("code"))
			.Build(),
		[](const TSharedPtr<FJsonObject>& Args) -> FArenaToolResult
		{
			if (!GetDefault<UArenaAgentSettings>()->bAllowPython)
			{
				return FArenaToolResult::Err(TEXT("Python execution is disabled. Enable 'Allow Python Execution' in Project Settings > Plugins > Arena Agent."));
			}

			const FString Code = GetStringArg(Args, TEXT("code"));
			if (Code.IsEmpty())
			{
				return FArenaToolResult::Err(TEXT("code is required."));
			}

			IPythonScriptPlugin* PythonPlugin = IPythonScriptPlugin::Get();
			if (!PythonPlugin)
			{
				return FArenaToolResult::Err(TEXT("The Python plugin is not loaded."));
			}

			FString Output;
			const bool bOk = PythonPlugin->ExecPythonCommandReturningResult(Output, *Code);
			TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
			Data->SetStringField(TEXT("output"), Output);

			if (bOk)
			{
				return FArenaToolResult::Ok(TEXT("Python executed."), Data);
			}
			return FArenaToolResult::Err(FString::Printf(TEXT("Python execution failed: %s"), *Output.Left(500)));
		});

	UE_LOG(LogArenaAgent, Log, TEXT("Registered %d agent tools."), Tools.Num());
}
