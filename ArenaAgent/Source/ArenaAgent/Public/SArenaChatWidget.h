// Arena Agent - the persistent chat panel (conversation list + message list + input).

#pragma once

#include "CoreMinimal.h"
#include "ArenaAgentRunner.h"
#include "ArenaChatTypes.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Views/SListView.h"

class SMultiLineEditableTextBox;

/**
 * Dockable chat panel. All state lives in the FArenaAgentRunner owned by the
 * module, so closing and reopening the tab keeps the conversation intact.
 */
class ARENAAGENT_API SArenaChatWidget : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SArenaChatWidget) {}
		SLATE_ARGUMENT(TSharedPtr<FArenaAgentRunner>, Runner)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	//~ Begin SWidget interface
	virtual void Tick(const FGeometry& AllottedGeometry, double InCurrentTime, float InDeltaTime) override;
	//~ End SWidget interface

private:
	using FMessagePtr = TSharedPtr<FArenaDisplayMessage>;
	using FConversationPtr = TSharedPtr<FArenaConversationMeta>;

	void SyncFromRunner(bool bScrollToBottom);
	FReply OnSendClicked();
	FReply OnInputKeyDown(const FGeometry& Geometry, const FKeyEvent& KeyEvent);
	void OnInputChanged(const FText& NewText);

	TSharedRef<ITableRow> MakeMessageRow(FMessagePtr Item, const TSharedRef<STableViewBase>& OwnerTable);
	TSharedRef<ITableRow> MakeConversationRow(FConversationPtr Item, const TSharedRef<STableViewBase>& OwnerTable);

	void OnConversationSelected(FConversationPtr Item, ESelectInfo::Type SelectInfo);
	void OnNewConversation();
	void OnDeleteConversation();
	void OnClearHistory();
	void OnClearAllConversations();
	void OnRenameConversation();
	void OnOpenSettings();

	FText GetStatusText() const;
	bool IsRunnerBusy() const;
	FText GetConversationTitle() const;
	TSharedPtr<FArenaConversationMeta> FindConversationMeta(const FString& Id) const;

	TSharedPtr<FArenaAgentRunner> Runner;

	TArray<FMessagePtr> Messages;
	TArray<FConversationPtr> Conversations;

	TSharedPtr<SListView<FMessagePtr>> MessageList;
	TSharedPtr<SListView<FConversationPtr>> ConversationList;
	TSharedPtr<SMultiLineEditableTextBox> InputBox;

	FString InputText;
	int32 LastSyncedRevision = INDEX_NONE;
};
