&AtServer
Procedure OnCreateAtServer(Cancel, StandardProcessing)
	Closing = False;
	QueryText = Parameters["QueryText"];
	OldQueryText = Parameters["OldQueryText"];
	If OldQueryText = "" Then
		OldQueryText = QueryText;
	EndIf;	
EndProcedure

&AtClient
Procedure CancelChanges(Command)
	QueryText = OldQueryText;
	ThisForm.Close();
EndProcedure

&AtClient
Procedure ApplyChanges(Command)
	OldQueryText = QueryText;
	ThisForm.Close();
EndProcedure

&AtClient
Procedure AskWhatToDo(Result, Params) Export
	If Result = DialogReturnCode.Yes Then
		ApplyChanges(Undefined);
	ElsIf Result = DialogReturnCode.No Then
		CancelChanges(Undefined);
	EndIf;
EndProcedure

&AtClient
Procedure BeforeClose(Cancel, Exit, MessageText, StandardProcessing)
	Var Notification;
	Var Type;

	If Closing Then
		Return;
	EndIf;

	If Exit = True Then
		// Если происходи закрытие приложения
		If QueryText <> OldQueryText Then			
			Cancel = True;
			MessageText = NStr("ru='Редактор запроса будет закрыт'; SYS='QueryEditor.QueryEditorWillClose'", "ru");
		EndIf;
		
		Return;
	EndIf;

	If QueryText = OldQueryText Then
		ThisForm.OnCloseNotifyDescription.AdditionalParameters["QueryText"] = QueryText;
		If ThisForm.OnCloseNotifyDescription <> Undefined Then
			ExecuteNotifyProcessing(ThisForm.OnCloseNotifyDescription, ThisForm);
			Cancel = NOT(Closing);
			StandardProcessing = False;
		EndIf;
	Else
		Cancel = NOT(Closing);
		Type = QuestionDialogMode.YesNoCancel;
		Notification = New NotifyDescription("AskWhatToDo", ThisForm);
		ShowQueryBox(Notification, NStr("ru='Применить изменения?'; SYS='QueryEditor.ApplyChanges'", "ru"), Type);
	EndIf;
EndProcedure

&AtClient
Procedure SetTextSelectionBounds(Val StartRow, Val StartCol) Export
	If (StartRow > 0) AND (StartCol > 0) Then
		Items.QueryText.SetTextSelectionBounds(StartRow, StartCol, StartRow, StartCol);
	EndIf;
EndProcedure

&AtClient
Procedure SetOldQueryText(Val Text) Export
	OldQueryText = Text;
EndProcedure
