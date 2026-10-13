// Arena Agent - programmatic Blueprint creation and editing implementation.

#include "ArenaBlueprintUtils.h"

#include "ArenaAgentLog.h"
#include "Blueprint/WidgetBlueprint.h"
#include "Blueprint/WidgetBlueprintGeneratedClass.h"
#include "Blueprint/UserWidget.h"
#include "BlueprintCompilationManager.h"
#include "Components/ActorComponent.h"
#include "Components/SceneComponent.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphSchema_K2.h"
#include "Engine/Blueprint.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "GameFramework/Actor.h"
#include "K2Node.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Event.h"
#include "K2Node_FunctionEntry.h"
#include "K2Node_FunctionResult.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "KismetEditorUtilities.h"
#include "Misc/PackageName.h"
#include "UObject/Class.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"

UClass* FArenaBlueprintUtils::ResolveClass(const FString& ClassPath)
{
	if (ClassPath.IsEmpty())
	{
		return nullptr;
	}
	UObject* Loaded = LoadObject<UObject>(nullptr, *ClassPath);
	return Cast<UClass>(Loaded);
}

UBlueprint* FArenaBlueprintUtils::LoadBlueprint(const FString& AssetPath)
{
	FString Clean = AssetPath;
	if (Clean.EndsWith(TEXT(".uasset")))
	{
		Clean.LeftChopInline(7, EAllowShrinking::No);
	}
	return LoadObject<UBlueprint>(nullptr, *Clean);
}

bool FArenaBlueprintUtils::SplitAssetPath(const FString& AssetPath, FString& OutPackagePath, FString& OutAssetName)
{
	FString Clean = AssetPath.TrimStartAndEnd();
	if (Clean.EndsWith(TEXT(".uasset")))
	{
		Clean.LeftChopInline(7, EAllowShrinking::No);
	}

	if (!Clean.StartsWith(TEXT("/Game/")))
	{
		return false;
	}

	int32 LastSlashIndex = INDEX_NONE;
	if (!Clean.FindLastChar(TEXT('/'), LastSlashIndex) || LastSlashIndex <= 0 || LastSlashIndex == Clean.Len() - 1)
	{
		return false;
	}

	OutPackagePath = Clean.Left(LastSlashIndex);
	OutAssetName = Clean.Mid(LastSlashIndex + 1);

	// Object names may not start with a digit.
	if (!OutAssetName.IsEmpty() && FChar::IsDigit(OutAssetName[0]))
	{
		OutAssetName = TEXT("_") + OutAssetName;
	}

	return !OutPackagePath.IsEmpty() && !OutAssetName.IsEmpty();
}

UBlueprint* FArenaBlueprintUtils::CreateBlueprintAsset(UClass* ParentClass, const FString& AssetPath, FString& OutError)
{
	if (!ParentClass)
	{
		OutError = TEXT("Parent class could not be resolved.");
		return nullptr;
	}

	FString PackagePath;
	FString AssetName;
	if (!SplitAssetPath(AssetPath, PackagePath, AssetName))
	{
		OutError = FString::Printf(TEXT("'%s' is not a valid asset path. Use a /Game/ path such as /Game/ArenaAI/BP_Hero."), *AssetPath);
		return nullptr;
	}

	if (LoadObject<UObject>(nullptr, *AssetPath))
	{
		OutError = FString::Printf(TEXT("An asset already exists at %s."), *AssetPath);
		return nullptr;
	}

	UClass* BlueprintClass = nullptr;
	UClass* BlueprintGeneratedClass = nullptr;

	if (ParentClass->IsChildOf<UUserWidget>())
	{
		BlueprintClass = UWidgetBlueprint::StaticClass();
		BlueprintGeneratedClass = UWidgetBlueprintGeneratedClass::StaticClass();
	}
	else if (ParentClass->IsChildOf<AActor>())
	{
		BlueprintClass = UBlueprint::StaticClass();
		BlueprintGeneratedClass = UBlueprintGeneratedClass::StaticClass();
	}
	else
	{
		OutError = FString::Printf(
			TEXT("Parent class '%s' is not supported. Use an Actor-derived class (Actor, Pawn, Character, GameModeBase, ...) or a UserWidget-derived class."),
			*ParentClass->GetPathName());
		return nullptr;
	}

	UBlueprint* NewBlueprint = FKismetEditorUtilities::CreateBlueprint(
		ParentClass, PackagePath, FName(*AssetName), BPTYPE_Normal, BlueprintClass, BlueprintGeneratedClass);

	if (!NewBlueprint)
	{
		OutError = FString::Printf(TEXT("CreateBlueprint failed for parent class '%s'."), *ParentClass->GetPathName());
		return nullptr;
	}

	UE_LOG(LogArenaAgent, Log, TEXT("Created Blueprint %s"), *NewBlueprint->GetPathName());
	return NewBlueprint;
}

bool FArenaBlueprintUtils::SaveAsset(UObject* Asset)
{
	if (!Asset)
	{
		return false;
	}

	UPackage* Package = Asset->GetOutermost();
	if (!Package)
	{
		return false;
	}

	const FString Filename = FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension());
	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	return UPackage::SavePackage(Package, Asset, *Filename, SaveArgs);
}

bool FArenaBlueprintUtils::CompileBlueprint(UBlueprint* Blueprint, FString& OutError)
{
	if (!Blueprint)
	{
		OutError = TEXT("No Blueprint to compile.");
		return false;
	}

	FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);

	FBPCompilationOptions Options;
	Options.Blueprint = Blueprint;
	FBlueprintCompilationManager::CompileSynchronously(Options);
	return true;
}

USCS_Node* FArenaBlueprintUtils::AddComponent(UBlueprint* Blueprint, UClass* ComponentClass, const FName ComponentName,
	const FName AttachToName, const FVector& RelativeLocation, const FRotator& RelativeRotation,
	const FVector& RelativeScale, FString& OutError)
{
	if (!Blueprint || !ComponentClass)
	{
		OutError = TEXT("Invalid Blueprint or component class.");
		return nullptr;
	}
	if (!ComponentClass->IsChildOf<UActorComponent>())
	{
		OutError = FString::Printf(TEXT("'%s' is not an actor component class."), *ComponentClass->GetPathName());
		return nullptr;
	}

	USimpleConstructionScript* SCS = Blueprint->SimpleConstructionScript;
	if (!SCS)
	{
		OutError = TEXT("This Blueprint has no SimpleConstructionScript; components can only be added to Actor Blueprints.");
		return nullptr;
	}

	for (const USCS_Node* Existing : SCS->GetAllNodes())
	{
		if (Existing && Existing->GetVariableName() == ComponentName)
		{
			OutError = FString::Printf(TEXT("A component named '%s' already exists."), *ComponentName.ToString());
			return nullptr;
		}
	}

	USCS_Node* NewNode = SCS->CreateNode(ComponentClass, ComponentName);
	if (!NewNode)
	{
		OutError = TEXT("SimpleConstructionScript::CreateNode failed.");
		return nullptr;
	}

	if (AttachToName != NAME_None)
	{
		USCS_Node* ParentNode = nullptr;
		for (USCS_Node* Existing : SCS->GetAllNodes())
		{
			if (Existing && Existing->GetVariableName() == AttachToName)
			{
				ParentNode = Existing;
				break;
			}
		}
		if (!ParentNode)
		{
			OutError = FString::Printf(TEXT("Attach target component '%s' was not found."), *AttachToName.ToString());
			return nullptr;
		}
		ParentNode->AddChild(NewNode);
	}
	else
	{
		SCS->AddNode(NewNode);
	}

	if (USceneComponent* SceneComponent = Cast<USceneComponent>(NewNode->ComponentTemplate))
	{
		SceneComponent->SetRelativeLocationAndRotation(RelativeLocation, RelativeRotation);
		SceneComponent->SetRelativeScale3D(RelativeScale);
	}

	return NewNode;
}

bool FArenaBlueprintUtils::PinTypeFromToken(const FString& TypeToken, bool bIsArray, const FString& ObjectClassPath,
	const FString& EnumPath, FEdGraphPinType& OutPinType, FString& OutError)
{
	OutPinType = FEdGraphPinType();
	const FString Token = TypeToken.ToLower().TrimStartAndEnd();
	bool bHandled = true;

	if (Token == TEXT("float"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Float;
	}
	else if (Token == TEXT("int") || Token == TEXT("integer"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Int;
	}
	else if (Token == TEXT("int64"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Int64;
	}
	else if (Token == TEXT("bool") || Token == TEXT("boolean"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
	}
	else if (Token == TEXT("string"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_String;
	}
	else if (Token == TEXT("name"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Name;
	}
	else if (Token == TEXT("text"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Text;
	}
	else if (Token == TEXT("vector"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
		OutPinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
	}
	else if (Token == TEXT("vector2d"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
		OutPinType.PinSubCategoryObject = TBaseStructure<FVector2D>::Get();
	}
	else if (Token == TEXT("rotator"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
		OutPinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
	}
	else if (Token == TEXT("transform"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
		OutPinType.PinSubCategoryObject = TBaseStructure<FTransform>::Get();
	}
	else if (Token == TEXT("color"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
		OutPinType.PinSubCategoryObject = TBaseStructure<FColor>::Get();
	}
	else if (Token == TEXT("linearcolor"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
		OutPinType.PinSubCategoryObject = TBaseStructure<FLinearColor>::Get();
	}
	else if (Token == TEXT("object"))
	{
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Object;
		if (!ObjectClassPath.IsEmpty())
		{
			UObject* ObjectClass = LoadObject<UObject>(nullptr, *ObjectClassPath);
			if (!ObjectClass)
			{
				OutError = FString::Printf(TEXT("Object class '%s' could not be resolved."), *ObjectClassPath);
				return false;
			}
			OutPinType.PinSubCategoryObject = ObjectClass;
		}
		else
		{
			OutPinType.PinSubCategoryObject = UObject::StaticClass();
		}
	}
	else if (Token == TEXT("enum"))
	{
		if (EnumPath.IsEmpty())
		{
			OutError = TEXT("Type 'enum' requires the enum_path parameter.");
			return false;
		}
		UEnum* Enum = LoadObject<UEnum>(nullptr, *EnumPath);
		if (!Enum)
		{
			OutError = FString::Printf(TEXT("Enum '%s' could not be resolved."), *EnumPath);
			return false;
		}
		OutPinType.PinCategory = UEdGraphSchema_K2::PC_Byte;
		OutPinType.PinSubCategoryObject = Enum;
	}
	else
	{
		bHandled = false;
	}

	if (!bHandled)
	{
		OutError = FString::Printf(
			TEXT("Unsupported variable type '%s'. Supported: float, int, int64, bool, string, name, text, vector, vector2d, rotator, transform, color, linearcolor, object, enum."),
			*TypeToken);
		return false;
	}

	if (bIsArray)
	{
		OutPinType.ContainerType = EPinContainerType::Array;
	}
	return true;
}

bool FArenaBlueprintUtils::AddVariable(UBlueprint* Blueprint, const FString& VariableName, const FString& TypeToken,
	bool bIsArray, const FString& ObjectClassPath, const FString& EnumPath, const FString& DefaultValue,
	const FString& Category, const FString& Tooltip, FString& OutError)
{
	if (!Blueprint)
	{
		OutError = TEXT("Invalid Blueprint.");
		return false;
	}

	const FName VariableFName(*VariableName);
	for (const FBPVariableDescription& Existing : Blueprint->NewVariables)
	{
		if (Existing.VarName == VariableFName)
		{
			OutError = FString::Printf(TEXT("A variable named '%s' already exists."), *VariableName);
			return false;
		}
	}

	FEdGraphPinType PinType;
	if (!PinTypeFromToken(TypeToken, bIsArray, ObjectClassPath, EnumPath, PinType, OutError))
	{
		return false;
	}

	FBPVariableDescription Description;
	Description.VarName = VariableFName;
	Description.VarType = PinType;
	if (!Category.IsEmpty())
	{
		Description.Category = FName(*Category);
	}
	if (!DefaultValue.IsEmpty())
	{
		Description.DefaultValue = DefaultValue;
	}

	Blueprint->NewVariables.Add(Description);
	return true;
}

static FString GetFunctionGraphFunctionName(const UEdGraph* Graph);

bool FArenaBlueprintUtils::AddFunction(UBlueprint* Blueprint, const FString& FunctionName,
	const TArray<TPair<FString, FEdGraphPinType>>& Inputs,
	const TArray<TPair<FString, FEdGraphPinType>>& Outputs, FString& OutError)
{
	if (!Blueprint)
	{
		OutError = TEXT("Invalid Blueprint.");
		return false;
	}

	// Reject duplicate function names (scan explicitly; UBlueprint has no guaranteed lookup helper).
	for (const UEdGraph* ExistingGraph : Blueprint->FunctionGraphs)
	{
		if (GetFunctionGraphFunctionName(ExistingGraph) == FunctionName)
		{
			OutError = FString::Printf(TEXT("A function named '%s' already exists."), *FunctionName);
			return false;
		}
	}

	UEdGraph* NewGraph = FBlueprintEditorUtils::CreateNewGraph(Blueprint, FName(*FunctionName), UEdGraph::StaticClass(), UEdGraphSchema_K2::StaticClass());
	if (!NewGraph)
	{
		OutError = TEXT("CreateNewGraph failed.");
		return false;
	}
	FBlueprintEditorUtils::AddFunctionGraph<UEdGraph>(Blueprint, NewGraph, false, nullptr);

	UK2Node_FunctionEntry* EntryNode = NewObject<UK2Node_FunctionEntry>(NewGraph);
	EntryNode->CustomFunctionName = FName(*FunctionName);
	EntryNode->CreateNewGuid();
	EntryNode->PostPlacedNewNode();
	NewGraph->AddNode(EntryNode);
	EntryNode->AllocateDefaultPins();
	EntryNode->NodePosX = 0;
	EntryNode->NodePosY = 0;

	bool bAllPinsCreated = true;
	for (const TPair<FString, FEdGraphPinType>& Input : Inputs)
	{
		UEdGraphPin* Pin = EntryNode->CreateUserDefinedPin(FName(*Input.Key), Input.Value, EGPD_Out);
		if (!Pin)
		{
			bAllPinsCreated = false;
		}
	}

	UK2Node_FunctionResult* ResultNode = NewObject<UK2Node_FunctionResult>(NewGraph);
	ResultNode->CreateNewGuid();
	ResultNode->PostPlacedNewNode();
	NewGraph->AddNode(ResultNode);
	ResultNode->AllocateDefaultPins();
	ResultNode->NodePosX = 400;
	ResultNode->NodePosY = 0;

	for (const TPair<FString, FEdGraphPinType>& Output : Outputs)
	{
		UEdGraphPin* Pin = ResultNode->CreateUserDefinedPin(FName(*Output.Key), Output.Value, EGPD_In);
		if (!Pin)
		{
			bAllPinsCreated = false;
		}
	}

	if (UEdGraphPin* ThenPin = EntryNode->FindPin(UEdGraphSchema_K2::PN_Then, EGPD_Out))
	{
		if (UEdGraphPin* ExecPin = ResultNode->FindPin(UEdGraphSchema_K2::PN_Execute, EGPD_In))
		{
			ThenPin->MakeLinkTo(ExecPin);
		}
	}

	if (!bAllPinsCreated)
	{
		UE_LOG(LogArenaAgent, Warning, TEXT("Some function pins could not be created for '%s'."), *FunctionName);
	}
	return true;
}

UEdGraph* FArenaBlueprintUtils::FindOrCreateEventGraph(UBlueprint* Blueprint)
{
	if (!Blueprint)
	{
		return nullptr;
	}

	UEdGraph* FirstEventGraph = nullptr;
	for (UEdGraph* Graph : Blueprint->EventGraphs)
	{
		if (!Graph)
		{
			continue;
		}
		if (Graph->GetFName() == TEXT("EventGraph"))
		{
			return Graph;
		}
		if (!FirstEventGraph)
		{
			FirstEventGraph = Graph;
		}
	}
	if (FirstEventGraph)
	{
		return FirstEventGraph;
	}

	UEdGraph* NewGraph = FBlueprintEditorUtils::CreateNewGraph(Blueprint, TEXT("EventGraph"), UEdGraph::StaticClass(), UEdGraphSchema_K2::StaticClass());
	if (NewGraph)
	{
		Blueprint->EventGraphs.Add(NewGraph);
	}
	return NewGraph;
}

bool FArenaBlueprintUtils::AddEvent(UBlueprint* Blueprint, const FString& EventKey, FString& OutError)
{
	if (!Blueprint)
	{
		OutError = TEXT("Invalid Blueprint.");
		return false;
	}

	UEdGraph* EventGraph = FindOrCreateEventGraph(Blueprint);
	if (!EventGraph)
	{
		OutError = TEXT("Could not find or create the EventGraph.");
		return false;
	}

	static const TMap<FString, FString> FriendlyNames = {
		{ TEXT("beginplay"), TEXT("ReceiveBeginPlay") },
		{ TEXT("tick"), TEXT("ReceiveTick") },
		{ TEXT("endplay"), TEXT("ReceiveEndPlay") },
		{ TEXT("actorbeginoverlap"), TEXT("ReceiveActorBeginOverlap") },
		{ TEXT("actorbeginoverlapend"), TEXT("ReceiveActorEndOverlap") },
		{ TEXT("actorhit"), TEXT("ReceiveHit") },
		{ TEXT("destroyed"), TEXT("ReceiveDestroyed") },
		{ TEXT("construction"), TEXT("UserConstructionScript") },
		{ TEXT("possessed"), TEXT("ReceivePossessed") },
		{ TEXT("unpossessed"), TEXT("ReceiveUnpossessed") },
		{ TEXT("anydamage"), TEXT("ReceiveAnyDamage") },
		{ TEXT("pointdamage"), TEXT("ReceivePointDamage") },
		{ TEXT("radialdamage"), TEXT("ReceiveRadialDamage") },
	};

	FString FunctionName = EventKey.TrimStartAndEnd();
	const FString NormalizedKey = FunctionName.ToLower().Replace(TEXT("_"), TEXT("")).Replace(TEXT(" "), TEXT(""));
	if (const FString* Mapped = FriendlyNames.Find(NormalizedKey))
	{
		FunctionName = *Mapped;
	}

	int32 NodePositionX = 0;
	int32 NodePositionY = 0;
	UObject* FunctionOwner = Blueprint->ParentClass ? Blueprint->ParentClass : static_cast<UObject*>(AActor::StaticClass());
	FKismetEditorUtilities::AddDefaultEventNode(Blueprint, EventGraph, FName(*FunctionName), FunctionOwner, NodePositionX, NodePositionY);
	return true;
}

UEdGraphPin* FArenaBlueprintUtils::FindLastThenPin(UEdGraphPin* StartThenPin)
{
	UEdGraphPin* Current = StartThenPin;
	TSet<const UEdGraphPin*> Visited;

	while (Current && Current->LinkedTo.Num() > 0 && !Visited.Contains(Current))
	{
		Visited.Add(Current);
		UEdGraphPin* Next = Current->LinkedTo[0];
		if (!Next)
		{
			break;
		}
		UK2Node* Node = Cast<UK2Node>(Next->GetOwningNode());
		if (!Node)
		{
			break;
		}
		UEdGraphPin* NextThen = Node->FindPin(UEdGraphSchema_K2::PN_Then, EGPD_Out);
		if (!NextThen)
		{
			break;
		}
		Current = NextThen;
	}

	return Current;
}

static FString GetFunctionGraphFunctionName(const UEdGraph* Graph)
{
	if (!Graph)
	{
		return FString();
	}
	for (const UEdGraphNode* Node : Graph->Nodes)
	{
		if (const UK2Node_FunctionEntry* Entry = Cast<UK2Node_FunctionEntry>(Node))
		{
			if (Entry->CustomFunctionName != NAME_None)
			{
				return Entry->CustomFunctionName.ToString();
			}
		}
	}
	return Graph->GetName();
}

bool FArenaBlueprintUtils::AddCallNode(UBlueprint* Blueprint, const FString& GraphName, const FString& AnchorEvent,
	const FString& AnchorFunction, const FString& FunctionName, const FString& OwnerClassPath,
	const TMap<FString, FString>& PinDefaults, FString& OutError)
{
	if (!Blueprint)
	{
		OutError = TEXT("Invalid Blueprint.");
		return false;
	}
	if (FunctionName.IsEmpty())
	{
		OutError = TEXT("The function parameter is required.");
		return false;
	}

	// ---- Locate the target graph -------------------------------------------
	UEdGraph* Graph = nullptr;

	if (!GraphName.IsEmpty())
	{
		for (UEdGraph* Candidate : Blueprint->EventGraphs)
		{
			if (Candidate && Candidate->GetFName().ToString() == GraphName)
			{
				Graph = Candidate;
				break;
			}
		}
		if (!Graph)
		{
			for (UEdGraph* Candidate : Blueprint->FunctionGraphs)
			{
				if (Candidate && Candidate->GetFName().ToString() == GraphName)
				{
					Graph = Candidate;
					break;
				}
			}
		}
	}
	else if (!AnchorFunction.IsEmpty())
	{
		for (UEdGraph* Candidate : Blueprint->FunctionGraphs)
		{
			if (GetFunctionGraphFunctionName(Candidate) == AnchorFunction)
			{
				Graph = Candidate;
				break;
			}
		}
	}
	else
	{
		Graph = FindOrCreateEventGraph(Blueprint);
	}

	if (!Graph)
	{
		OutError = TEXT("Target graph not found. Use add_event or add_function first, or pass a valid graph name.");
		return false;
	}

	// ---- Locate the anchor node --------------------------------------------
	UK2Node* AnchorNode = nullptr;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (!AnchorEvent.IsEmpty())
		{
			if (const UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node))
			{
				if (EventNode->EventReference.GetMemberName().ToString() == AnchorEvent ||
					EventNode->CustomFunctionName.ToString() == AnchorEvent)
				{
					AnchorNode = const_cast<UK2Node_Event*>(EventNode);
					break;
				}
			}
		}
		else if (!AnchorFunction.IsEmpty())
		{
			if (UK2Node_FunctionEntry* Entry = Cast<UK2Node_FunctionEntry>(Node))
			{
				AnchorNode = Entry;
				break;
			}
		}
	}
	if (!AnchorNode)
	{
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node))
			{
				AnchorNode = EventNode;
				break;
			}
		}
	}
	if (!AnchorNode)
	{
		OutError = TEXT("No event or function entry node found to attach the call to. Use add_event or add_function first.");
		return false;
	}

	UEdGraphPin* ThenPin = AnchorNode->FindPin(UEdGraphSchema_K2::PN_Then, EGPD_Out);
	if (!ThenPin)
	{
		OutError = TEXT("The anchor node has no execution output pin.");
		return false;
	}
	ThenPin = FindLastThenPin(ThenPin);

	// ---- Resolve the owning class and function ------------------------------
	UClass* OwnerClass = nullptr;
	if (!OwnerClassPath.IsEmpty())
	{
		OwnerClass = ResolveClass(OwnerClassPath);
		if (!OwnerClass)
		{
			OutError = FString::Printf(TEXT("Owner class '%s' could not be resolved."), *OwnerClassPath);
			return false;
		}
	}
	else
	{
		OwnerClass = Blueprint->ParentClass;
	}
	if (!OwnerClass)
	{
		OutError = TEXT("No owner class available; pass the owner parameter.");
		return false;
	}

	UClass* FunctionOwner = nullptr;
	for (UClass* Candidate = OwnerClass; Candidate; Candidate = Candidate->GetSuperClass())
	{
		if (Candidate->FindFunctionByName(FName(*FunctionName), EIncludeSuperFlag::ExcludeSuper))
		{
			FunctionOwner = Candidate;
			break;
		}
	}
	if (!FunctionOwner)
	{
		OutError = FString::Printf(
			TEXT("Function '%s' was not found on '%s' or its parents. Check the owner class (e.g. /Script/Engine.KismetSystemLibrary for PrintString)."),
			*FunctionName, *OwnerClass->GetPathName());
		return false;
	}

	// ---- Create the call node -------------------------------------------------
	UK2Node_CallFunction* CallNode = NewObject<UK2Node_CallFunction>(Graph);
	CallNode->SetFromFunction(FName(*FunctionName), FunctionOwner);
	CallNode->CreateNewGuid();
	CallNode->PostPlacedNewNode();
	Graph->AddNode(CallNode);
	CallNode->AllocateDefaultPins();
	CallNode->NodePosX = AnchorNode->NodePosX + 400;
	CallNode->NodePosY = AnchorNode->NodePosY + (AnchorNode->NodePosY % 32 == 0 ? 32 : 0);

	for (const TPair<FString, FString>& Pair : PinDefaults)
	{
		if (UEdGraphPin* Pin = CallNode->FindPin(FName(*Pair.Key), EGPD_In))
		{
			Pin->DefaultValue = Pair.Value;
		}
	}

	if (UEdGraphPin* ExecIn = CallNode->FindPin(UEdGraphSchema_K2::PN_Execute, EGPD_In))
	{
		ThenPin->MakeLinkTo(ExecIn);
	}

	return true;
}

TSharedPtr<FJsonObject> FArenaBlueprintUtils::DescribeBlueprint(UBlueprint* Blueprint)
{
	TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
	if (!Blueprint)
	{
		return Root;
	}

	Root->SetStringField(TEXT("path"), Blueprint->GetPathName());
	if (Blueprint->ParentClass)
	{
		Root->SetStringField(TEXT("parent_class"), Blueprint->ParentClass->GetPathName());
	}

	// Components
	TArray<TSharedPtr<FJsonValue>> Components;
	if (const USimpleConstructionScript* SCS = Blueprint->SimpleConstructionScript)
	{
		for (const USCS_Node* Node : SCS->GetAllNodes())
		{
			if (!Node)
			{
				continue;
			}
			TSharedPtr<FJsonObject> Component = MakeShared<FJsonObject>();
			Component->SetStringField(TEXT("name"), Node->GetVariableName().ToString());
			if (Node->ComponentClass)
			{
				Component->SetStringField(TEXT("class"), Node->ComponentClass->GetPathName());
			}
			if (Node->ParentNode)
			{
				Component->SetStringField(TEXT("attached_to"), Node->ParentNode->GetVariableName().ToString());
			}
			Components.Add(MakeShared<FJsonValueObject>(Component));
		}
	}
	Root->SetArrayField(TEXT("components"), Components);

	// Variables
	TArray<TSharedPtr<FJsonValue>> Variables;
	for (const FBPVariableDescription& Variable : Blueprint->NewVariables)
	{
		TSharedPtr<FJsonObject> VariableObject = MakeShared<FJsonObject>();
		VariableObject->SetStringField(TEXT("name"), Variable.VarName.ToString());
		FString TypeString = Variable.VarType.PinCategory.ToString();
		if (Variable.VarType.PinSubCategoryObject.IsValid())
		{
			TypeString += FString::Printf(TEXT("<%s>"), *Variable.VarType.PinSubCategoryObject->GetName());
		}
		if (Variable.VarType.ContainerType == EPinContainerType::Array)
		{
			TypeString += TEXT("[]");
		}
		VariableObject->SetStringField(TEXT("type"), TypeString);
		if (!Variable.DefaultValue.IsEmpty())
		{
			VariableObject->SetStringField(TEXT("default"), Variable.DefaultValue);
		}
		Variables.Add(MakeShared<FJsonValueObject>(VariableObject));
	}
	Root->SetArrayField(TEXT("variables"), Variables);

	// Functions
	TArray<TSharedPtr<FJsonValue>> Functions;
	for (const UEdGraph* Graph : Blueprint->FunctionGraphs)
	{
		if (!Graph)
		{
			continue;
		}
		TSharedPtr<FJsonObject> FunctionObject = MakeShared<FJsonObject>();
		FunctionObject->SetStringField(TEXT("name"), GetFunctionGraphFunctionName(Graph));

		TArray<TSharedPtr<FJsonValue>> Parameters;
		for (const UEdGraphNode* Node : Graph->Nodes)
		{
			if (const UK2Node_FunctionEntry* Entry = Cast<UK2Node_FunctionEntry>(Node))
			{
				for (const UEdGraphPin* Pin : Entry->Pins)
				{
					if (!Pin || Pin->Direction != EGPD_Out || Pin->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
					{
						continue;
					}
					TSharedPtr<FJsonValue> ParameterValue = MakeShared<FJsonValueString>(
						FString::Printf(TEXT("%s: %s"), *Pin->GetName(), *Pin->PinType.PinCategory.ToString()));
					Parameters.Add(ParameterValue);
				}
			}
		}
		FunctionObject->SetArrayField(TEXT("inputs"), Parameters);
		Functions.Add(MakeShared<FJsonValueObject>(FunctionObject));
	}
	Root->SetArrayField(TEXT("functions"), Functions);

	// Events (and the call nodes attached inside each event graph)
	TArray<TSharedPtr<FJsonValue>> Events;
	for (const UEdGraph* Graph : Blueprint->EventGraphs)
	{
		if (!Graph)
		{
			continue;
		}
		for (const UEdGraphNode* Node : Graph->Nodes)
		{
			if (const UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node))
			{
				TSharedPtr<FJsonObject> EventObject = MakeShared<FJsonObject>();
				FString EventName = EventNode->EventReference.GetMemberName().ToString();
				if (EventName.IsEmpty())
				{
					EventName = EventNode->CustomFunctionName.ToString();
				}
				EventObject->SetStringField(TEXT("name"), EventName);
				EventObject->SetStringField(TEXT("graph"), Graph->GetName());

				TArray<TSharedPtr<FJsonValue>> Calls;
				for (const UEdGraphNode* OtherNode : Graph->Nodes)
				{
					if (const UK2Node_CallFunction* CallNode = Cast<UK2Node_CallFunction>(OtherNode))
					{
						Calls.Add(MakeShared<FJsonValueString>(CallNode->FunctionReference.GetMemberName().ToString()));
					}
				}
				EventObject->SetArrayField(TEXT("calls_in_graph"), Calls);
				Events.Add(MakeShared<FJsonValueObject>(EventObject));
			}
		}
	}
	Root->SetArrayField(TEXT("events"), Events);

	return Root;
}
