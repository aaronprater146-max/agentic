// Arena Agent - chat panel implementation.

#include "SArenaChatWidget.h"

#include "ArenaAgentSettings.h"
#include "Brushes/SlateColorBrush.h"
#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"
#include "ISettingsModule.h"
#include "Modules/ModuleManager.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SSplitter.h"
#include "Widgets/Views/STableRow.h"

#define LOCTEXT_NAMESPACE "ArenaAgent"

namespace
{
	const FSlateColorBrush GUserBubbleBrush(FLinearColor(0.16f, 0.27f, 0.44f));
	const FSlateColorBrush GAssistantBubbleBrush(FLinearColor(0.16f, 0.16f, 0.18f));
	const FSlateColorBrush GToolBubbleBrush(FLinearColor(0.13f, 0.17f, 0.14f));
	const FSlateColorBrush GErrorBubbleBrush(FLinearColor(0.4f, 0.15f, 0.15f));
	const FSlateColorBrush GPanelBrush(FLinearColor(0.08f, 0.08f, 0.09f));

	const FLinearColor GMutedTextColor(0.55f, 0.55f, 0.6f);
}

void SArenaChatWidget::Construct(const FArguments& InArgs)
{
	Runner = InArgs._Runner;

	ChildSlot
	[
		SNew(SHorizontalBox)

		// ------------------------------------------------ conversation sidebar
		+ SHorizontalBox::Slot()
		.AutoWidth()
		[
			SNew(SBox)
			.WidthOverride(230)
			[
				SNew(SBorder)
				.BorderImage(&GPanelBrush)
				.Padding(6)
				[
					SNew(SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot()
						.FillWidth(1.0f)
						.VAlign(VAlign_Center)
						[
							SNew(STextBlock)
							.Text(LOCTEXT("ConversationsHeader", "Conversations"))
							.ColorAndOpacity(FSlateColor(GMutedTextColor))
						]
						+ SHorizontalBox::Slot()
						.AutoWidth()
						[
							SNew(SButton)
							.Text(LOCTEXT("NewConversation", "+ New"))
							.ToolTipText(LOCTEXT("NewConversationTooltip", "Start a new conversation"))
							.OnClicked_Lambda([this]() { OnNewConversation(); return FReply::Handled(); })
						]
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0, 4)
					[
						SNew(SSeparator)
					]

					+ SVerticalBox::Slot()
					.FillHeight(1.0f)
					[
						SAssignNew(ConversationList, SListView<FConversationPtr>)
						.ListItemsSource(&Conversations)
						.OnGenerateRow(this, &SArenaChatWidget::MakeConversationRow)
						.OnSelectionChanged(this, &SArenaChatWidget::OnConversationSelected)
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0, 4)
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot()
						.FillWidth(1.0f)
						.Padding(0, 0, 2, 0)
						[
							SNew(SButton)
							.HAlign(HAlign_Center)
							.Text(LOCTEXT("RenameConversation", "Rename"))
							.OnClicked_Lambda([this]() { OnRenameConversation(); return FReply::Handled(); })
						]
						+ SHorizontalBox::Slot()
						.FillWidth(1.0f)
						[
							SNew(SButton)
							.HAlign(HAlign_Center)
							.Text(LOCTEXT("DeleteConversation", "Delete"))
							.ToolTipText(LOCTEXT("DeleteConversationTooltip", "Delete the selected conversation"))
							.OnClicked_Lambda([this]() { OnDeleteConversation(); return FReply::Handled(); })
						]
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(SButton)
						.HAlign(HAlign_Center)
						.Text(LOCTEXT("ClearAll", "Clear All Conversations"))
						.ToolTipText(LOCTEXT("ClearAllTooltip", "Delete every saved conversation"))
						.OnClicked_Lambda([this]() { OnClearAllConversations(); return FReply::Handled(); })
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0, 4, 0, 0)
					[
						SNew(SButton)
						.HAlign(HAlign_Center)
						.Text(LOCTEXT("OpenSettings", "Settings"))
						.ToolTipText(LOCTEXT("OpenSettingsTooltip", "Open the Arena Agent project settings"))
						.OnClicked_Lambda([this]() { OnOpenSettings(); return FReply::Handled(); })
					]
				]
			]
		]

		// --------------------------------------------------------- chat column
		+ SHorizontalBox::Slot()
		.FillWidth(1.0f)
		.Padding(6, 0, 0, 0)
		[
			SNew(SBorder)
			.BorderImage(&GPanelBrush)
			.Padding(8)
			[
				SNew(SVerticalBox)

				// Header: title + status + cancel
				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(this, &SArenaChatWidget::GetConversationTitle)
					]
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(this, &SArenaChatWidget::GetStatusText)
						.ColorAndOpacity(FSlateColor(GMutedTextColor))
					]
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(6, 0, 0, 0)
					[
						SNew(SButton)
						.Text(LOCTEXT("Cancel", "Cancel"))
						.IsEnabled(this, &SArenaChatWidget::IsRunnerBusy)
						.ToolTipText(LOCTEXT("CancelTooltip", "Stop the current request"))
						.OnClicked_Lambda([this]()
						{
							if (Runner.IsValid())
							{
								Runner->Cancel();
							}
							return FReply::Handled();
						})
					]
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0, 4)
				[
					SNew(SSeparator)
				]

				// Message list
				+ SVerticalBox::Slot()
				.FillHeight(1.0f)
				[
					SAssignNew(MessageList, SListView<FMessagePtr>)
					.ListItemsSource(&Messages)
					.OnGenerateRow(this, &SArenaChatWidget::MakeMessageRow)
				]

				// Input
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0, 6, 0, 0)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					[
						SNew(SBox)
						.HeightOverride(72)
						[
							SAssignNew(InputBox, SMultiLineEditableTextBox)
							.HintText(LOCTEXT("InputHint", "Ask Arena to build something… (Enter to send, Shift+Enter for a new line)"))
							.OnTextChanged(this, &SArenaChatWidget::OnInputChanged)
							.OnKeyDownHandler(this, &SArenaChatWidget::OnInputKeyDown)
						]
					]
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(6, 0, 0, 0)
					[
						SNew(SBox)
						.HeightOverride(72)
						[
							SNew(SButton)
							.Text(LOCTEXT("Send", "Send"))
							.OnClicked(this, &SArenaChatWidget::OnSendClicked)
						]
					]
				]

				// Footer: clear history
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0, 4, 0, 0)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(LOCTEXT("FooterHint", "Conversations are saved automatically under Saved/ArenaAgent."))
						.ColorAndOpacity(FSlateColor(GMutedTextColor))
					]
					+ SHorizontalBox::Slot()
					.AutoWidth()
					[
						SNew(SButton)
						.Text(LOCTEXT("ClearHistory", "Clear History"))
						.ToolTipText(LOCTEXT("ClearHistoryTooltip", "Clear the messages of the current conversation"))
						.OnClicked_Lambda([this]() { OnClearHistory(); return FReply::Handled(); })
					]
				]
			]
		]
	];

	SyncFromRunner(false);
}

void SArenaChatWidget::Tick(const FGeometry& AllottedGeometry, double InCurrentTime, float InDeltaTime)
{
	SCompoundWidget::Tick(AllottedGeometry, InCurrentTime, InDeltaTime);

	if (Runner.IsValid() && Runner->GetRevision() != LastSyncedRevision)
	{
		const bool bFirstSync = LastSyncedRevision == INDEX_NONE;
		SyncFromRunner(bFirstSync || Runner->IsBusy());
	}
}

void SArenaChatWidget::SyncFromRunner(bool bScrollToBottom)
{
	if (!Runner.IsValid())
	{
		return;
	}
	LastSyncedRevision = Runner->GetRevision();

	// Messages
	Messages.Empty();
	const TArray<FArenaDisplayMessage> DisplayMessages = ArenaChatHelpers::BuildDisplayMessages(Runner->GetConversation());
	Messages.Reserve(DisplayMessages.Num());
	for (const FArenaDisplayMessage& DisplayMessage : DisplayMessages)
	{
		Messages.Add(MakeShared<FArenaDisplayMessage>(DisplayMessage));
	}
	if (MessageList.IsValid())
	{
		MessageList->RequestListRefresh();
		if (bScrollToBottom && Messages.Num() > 0)
		{
			MessageList->RequestScrollToBottom();
		}
	}

	// Conversations
	const FString SelectedId = Runner->GetConversation().Id;
	Conversations.Empty();
	const TArray<FArenaConversationMeta> Metas = Runner->ListConversations();
	Conversations.Reserve(Metas.Num());
	for (const FArenaConversationMeta& Meta : Metas)
	{
		Conversations.Add(MakeShared<FArenaConversationMeta>(Meta));
	}
	if (ConversationList.IsValid())
	{
		ConversationList->RequestListRefresh();
		if (TSharedPtr<FArenaConversationMeta> Selected = FindConversationMeta(SelectedId))
		{
			ConversationList->SetItemSelection(Selected, true);
		}
	}
}

TSharedPtr<FArenaConversationMeta> SArenaChatWidget::FindConversationMeta(const FString& Id) const
{
	for (const FConversationPtr& Meta : Conversations)
	{
		if (Meta.IsValid() && Meta->Id == Id)
		{
			return Meta;
		}
	}
	return nullptr;
}

TSharedRef<ITableRow> SArenaChatWidget::MakeConversationRow(FConversationPtr Item, const TSharedRef<STableViewBase>& OwnerTable)
{
	const FText Name = Item.IsValid() ? FText::FromString(Item->Name) : FText::GetEmpty();
	const FText When = Item.IsValid() ? FText::FromString(ArenaChatHelpers::FormatTimestamp(Item->Updated)) : FText::GetEmpty();

	return SNew(STableRow<FConversationPtr>, OwnerTable)
	[
		SNew(SBox)
		.Padding(FMargin(4, 6))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(STextBlock)
				.Text(Name)
				.AutoWrapText(true)
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(STextBlock)
				.Text(When)
				.ColorAndOpacity(FSlateColor(GMutedTextColor))
			]
		]
	];
}

void SArenaChatWidget::OnConversationSelected(FConversationPtr Item, ESelectInfo::Type SelectInfo)
{
	if (!Runner.IsValid() || !Item.IsValid())
	{
		return;
	}
	if (Runner->IsBusy())
	{
		return;
	}
	if (Runner->GetConversation().Id != Item->Id)
	{
		Runner->LoadConversation(Item->Id);
	}
}

TSharedRef<ITableRow> SArenaChatWidget::MakeMessageRow(FMessagePtr Item, const TSharedRef<STableViewBase>& OwnerTable)
{
	const FSlateColorBrush* BubbleBrush = &GAssistantBubbleBrush;
	FString RoleLabel = TEXT("Arena");

	if (Item.IsValid())
	{
		if (Item->Role == TEXT("user"))
		{
			BubbleBrush = &GUserBubbleBrush;
			RoleLabel = TEXT("You");
		}
		else if (Item->Role == TEXT("tool"))
		{
			BubbleBrush = &GToolBubbleBrush;
			RoleLabel = TEXT("Tool");
		}
		else if (Item->Role == TEXT("error"))
		{
			BubbleBrush = &GErrorBubbleBrush;
			RoleLabel = TEXT("Error");
		}
	}

	return SNew(STableRow<FMessagePtr>, OwnerTable)
	.Padding(FMargin(0, 2))
	[
		SNew(SBorder)
		.BorderImage(BubbleBrush)
		.Padding(8)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SNew(STextBlock)
					.Text(FText::FromString(RoleLabel))
					.ColorAndOpacity(FSlateColor(GMutedTextColor))
				]
				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(STextBlock)
					.Text(Item.IsValid() ? FText::FromString(Item->TimeString) : FText::GetEmpty())
					.ColorAndOpacity(FSlateColor(GMutedTextColor))
				]
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0, 2, 0, 0)
			[
				SNew(STextBlock)
				.Text(Item.IsValid() ? FText::FromString(Item->Text) : FText::GetEmpty())
				.AutoWrapText(true)
			]
		]
	];
}

FText SArenaChatWidget::GetStatusText() const
{
	return Runner.IsValid() ? FText::FromString(Runner->GetStatus()) : FText::GetEmpty();
}

bool SArenaChatWidget::IsRunnerBusy() const
{
	return Runner.IsValid() && Runner->IsBusy();
}

FText SArenaChatWidget::GetConversationTitle() const
{
	if (!Runner.IsValid())
	{
		return FText::GetEmpty();
	}
	return FText::FromString(FString::Printf(TEXT("Arena Agent — %s"), *Runner->GetConversation().Name));
}

void SArenaChatWidget::OnInputChanged(const FText& NewText)
{
	InputText = NewText.ToString();
}

FReply SArenaChatWidget::OnInputKeyDown(const FGeometry& Geometry, const FKeyEvent& KeyEvent)
{
	if (KeyEvent.GetKey() == EKeys::Enter && !KeyEvent.IsShiftDown())
	{
		OnSendClicked();
		return FReply::Handled();
	}
	return FReply::Unhandled();
}

FReply SArenaChatWidget::OnSendClicked()
{
	if (Runner.IsValid() && !Runner->IsBusy())
	{
		const FString Text = InputText;
		InputText.Reset();
		if (InputBox.IsValid())
		{
			InputBox->SetText(FText::GetEmpty());
		}
		Runner->SendMessage(Text);
	}
	return FReply::Handled();
}

void SArenaChatWidget::OnNewConversation()
{
	if (Runner.IsValid())
	{
		Runner->NewConversation();
	}
}

void SArenaChatWidget::OnDeleteConversation()
{
	if (!Runner.IsValid() || !ConversationList.IsValid())
	{
		return;
	}
	if (TSharedPtr<FArenaConversationMeta> Selected = ConversationList->GetSelectedItem())
	{
		Runner->DeleteConversation(Selected->Id);
	}
}

void SArenaChatWidget::OnClearHistory()
{
	if (Runner.IsValid())
	{
		Runner->ClearCurrentHistory();
	}
}

void SArenaChatWidget::OnClearAllConversations()
{
	if (Runner.IsValid())
	{
		Runner->DeleteAllConversations();
	}
}

void SArenaChatWidget::OnRenameConversation()
{
	if (!Runner.IsValid())
	{
		return;
	}

	TSharedPtr<SEditableTextBox> RenameBox;
	TSharedRef<SWindow> Window = SNew(SWindow)
		.Title(LOCTEXT("RenameTitle", "Rename Conversation"))
		.ClientSize(FVector2D(380, 110))
		.SupportsMinimize(false)
		.SupportsMaximize(false)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(8)
			[
				SAssignNew(RenameBox, SEditableTextBox)
				.Text(FText::FromString(Runner->GetConversation().Name))
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			.HAlign(HAlign_Right)
			.Padding(8)
			[
				SNew(SButton)
				.Text(LOCTEXT("RenameOk", "OK"))
				.OnClicked_Lambda([this, RenameBox, Window]()
				{
					if (Runner.IsValid() && RenameBox.IsValid())
					{
						Runner->RenameCurrentConversation(RenameBox->GetText().ToString());
					}
					if (Window.IsValid())
					{
						Window->RequestDestroyWindow();
					}
					return FReply::Handled();
				})
			]
		];

	FSlateApplication::Get().AddWindow(Window);
}

void SArenaChatWidget::OnOpenSettings()
{
	ISettingsModule* SettingsModule = FModuleManager::GetModulePtr<ISettingsModule>(TEXT("Settings"));
	if (SettingsModule)
	{
		SettingsModule->ShowViewer(TEXT("Project"), TEXT("Plugins"), TEXT("ArenaAgent"));
	}
}

#undef LOCTEXT_NAMESPACE
