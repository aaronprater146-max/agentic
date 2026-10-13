// Arena Agent - programmatic Blueprint creation and editing helpers.

#pragma once

#include "CoreMinimal.h"
#include "Templates/SubclassOf.h"

class UBlueprint;
class UClass;
class USCS_Node;
class UEdGraph;
class UEdGraphPin;
struct FEdGraphPinType;

/**
 * Static helpers used by the agent tools to create and mutate Blueprints
 * from C++ (the same operations a developer does in the editor UI).
 */
class ARENAAGENT_API FArenaBlueprintUtils
{
public:
	/** Resolves a class from an object path such as "/Script/Engine.Character". */
	static UClass* ResolveClass(const FString& ClassPath);

	/** Loads a Blueprint asset from an object path such as "/Game/ArenaAI/BP_Hero". */
	static UBlueprint* LoadBlueprint(const FString& AssetPath);

	/** Returns the package path and asset name for a full object path "/Game/Folder/Name". */
	static bool SplitAssetPath(const FString& AssetPath, FString& OutPackagePath, FString& OutAssetName);

	/**
	 * Creates a new Blueprint of the requested parent class.
	 * Supports Actor-derived classes and UUserWidget-derived classes.
	 */
	static UBlueprint* CreateBlueprintAsset(UClass* ParentClass, const FString& AssetPath, FString& OutError);

	/** Saves the package of an asset (used when bAutoSaveAssets is enabled). */
	static bool SaveAsset(UObject* Asset);

	/** Recompiles a Blueprint synchronously. */
	static bool CompileBlueprint(UBlueprint* Blueprint, FString& OutError);

	/** Adds a component to the Blueprint's SimpleConstructionScript. */
	static USCS_Node* AddComponent(UBlueprint* Blueprint, UClass* ComponentClass, const FName ComponentName,
		const FName AttachToName, const FVector& RelativeLocation, const FRotator& RelativeRotation,
		const FVector& RelativeScale, FString& OutError);

	/** Adds a variable to the Blueprint. Type is given as a friendly token ("float", "vector", "object", ...). */
	static bool AddVariable(UBlueprint* Blueprint, const FString& VariableName, const FString& TypeToken,
		bool bIsArray, const FString& ObjectClassPath, const FString& EnumPath, const FString& DefaultValue,
		const FString& Category, const FString& Tooltip, FString& OutError);

	/** Converts a friendly type token into a pin type. */
	static bool PinTypeFromToken(const FString& TypeToken, bool bIsArray, const FString& ObjectClassPath,
		const FString& EnumPath, FEdGraphPinType& OutPinType, FString& OutError);

	/** Adds a new function graph with entry/result nodes and optional typed parameters. */
	static bool AddFunction(UBlueprint* Blueprint, const FString& FunctionName,
		const TArray<TPair<FString, FEdGraphPinType>>& Inputs,
		const TArray<TPair<FString, FEdGraphPinType>>& Outputs, FString& OutError);

	/**
	 * Adds an event node (e.g. ReceiveBeginPlay) to the EventGraph, creating the graph when needed.
	 * EventKey is a friendly name ("BeginPlay", "Tick", ...) or the raw function name.
	 */
	static bool AddEvent(UBlueprint* Blueprint, const FString& EventKey, FString& OutError);

	/**
	 * Appends a "Call Function" node to the end of an execution chain inside a graph.
	 * Anchor by event name (event graphs) or function name (function graphs).
	 */
	static bool AddCallNode(UBlueprint* Blueprint, const FString& GraphName, const FString& AnchorEvent,
		const FString& AnchorFunction, const FString& FunctionName, const FString& OwnerClassPath,
		const TMap<FString, FString>& PinDefaults, FString& OutError);

	/** Walks an exec chain from a "then" pin to the last unconnected then pin. */
	static UEdGraphPin* FindLastThenPin(UEdGraphPin* StartThenPin);

	/** Finds (or creates) the primary EventGraph of a Blueprint. */
	static UEdGraph* FindOrCreateEventGraph(UBlueprint* Blueprint);

	/** Builds a JSON description of a Blueprint: parent, components, variables, functions, events. */
	static TSharedPtr<class FJsonObject> DescribeBlueprint(UBlueprint* Blueprint);
};
