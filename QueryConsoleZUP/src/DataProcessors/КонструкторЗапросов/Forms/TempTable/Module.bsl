
// BSLLS-off

&AtServer
Procedure OnCreateAtServer(Cancel, StandardProcessing)
	Changed = False; 	
	SetIndex(Parameters["Index"],
			 Parameters["QueryWizardAddress"],
			 Parameters["CurrentQuerySchemaSelectQuery"],
			 Parameters["CurrentQuerySchemaOperator"],
			 Parameters["NestedQueryPositionAddress"]);

EndProcedure

&AtServer
Procedure SetIndex(Val NewIndex, Val QueryAddress, Val CurrentQuery, Val CurrentOperator, Val NestedQueryPosition)
	Var QuerySchema;
	Var Query;
	Var Source;

	Index = NewIndex;

	QueryWizardAddress = QueryAddress;
	CurrentQuerySchemaSelectQuery = CurrentQuery;
	CurrentQuerySchemaOperator = CurrentOperator;
	NestedQueryPositionAddress =  NestedQueryPosition;

	If Index < 0 Then
		Return;
	EndIf;

	QuerySchema = GetFromTempStorage(QueryWizardAddress);
	If QuerySchema = Undefined Then
		Return;
	EndIf;

	Batch = QuerySchema.QueryBatch;
	Query = GetSchemaQuery(QuerySchema);

	Source = Query.Operators.Get(CurrentQuerySchemaOperator).Sources.Get(Index).Source;

	If TypeOf(Source) <> Type("QuerySchemaTempTableDescription") Then
		Return;
	EndIf;

	TableName = Source.TableName;
	Name = TableName;
	FillAvailableFields(Fields.GetItems(), Source.AvailableFields);
EndProcedure

&AtServer
Function GetSchemaQuery(Val QuerySchema)
	Var MainObject;

	MainObject = FormAttributeToValue("Object");
	Return MainObject.GetSchemaQuery(QuerySchema, CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress);
EndFunction

&AtClient
Procedure OK(Command)
	If ApplyChangesAtServer() Then
		ThisForm.Close();
	EndIf;
EndProcedure

&AtClient
Procedure Cancel(Command)
	ThisForm.Close();
EndProcedure

&AtServerNoContext
Procedure FillAvailableFields(Val AvailableFieldsTree, Val AvailableFields)
	Var Count;
	Var Pos;
	Var Field;
	Var NewElement;

	// Заполняет список полей
	If AvailableFields = Undefined Then
		Return;
	EndIf;

	Count = AvailableFields.Count();
	For Pos = 0 To  Count-1 Do
		NewElement = AvailableFieldsTree.Add();
		Field = AvailableFields.Get(Pos);
		NewElement["Name"] = Field.Name;
		NewElement["ValueType"] = Field.ValueType;
		NewElement["Changed"] = False;
		NewElement["New"] = False;
		NewElement["Index"] = Pos;
	EndDo;
EndProcedure

&AtServer
Function ApplyChangesAtServer()
	Var QuerySchema;
	Var Query;
	Var Source;
	Var Message;
	Var Count;
	Var Pos;
	Var Item;
	Var AvailableFields;

	QuerySchema = GetFromTempStorage(QueryWizardAddress);
	If QuerySchema = Undefined Then
		Return True;
	EndIf;

	Batch = QuerySchema.QueryBatch;
	Query = GetSchemaQuery(QuerySchema);

	If Index >= 0 Then
		Source = Query.Operators.Get(CurrentQuerySchemaOperator).Sources.Get(Index).Source;
		Try
	    	Source.TableName = TableName;
		Except
			Message = New UserMessage;
			Message.Text = BriefErrorDescription(ErrorInfo());
			Message.Field = "TableName";
			Message.Message();
			Return False;
		EndTry;
	Else
		Try
			Source = Query.Operators.Get(CurrentQuerySchemaOperator).Sources.Add(Type("QuerySchemaTempTableDescription"), 
                                                                                 TableName);
			Source = Source.Source;
		Except
			Message = New UserMessage;
			Message.Text = BriefErrorDescription(ErrorInfo());
			Message.Field = "TableName";
			Message.Message();

			Return False;
		EndTry;
	EndIf;

	If Changed Then
		AvailableFields = Source.AvailableFields;
		// внесем изменения
		Count = Fields.GetItems().Count();
		For Pos = 0 To Count - 1 Do
			Item = Fields.GetItems().Get(Pos);
			If (Item["Changed"]) AND (Item["New"] = False) Then
				AvailableFields.Delete(Item["Index"]);
				If Item["ValueType"].Types().Count() > 0 Then
					AvailableFields.Insert(Item["Index"], Item["Name"], Item["ValueType"].Types()[0]);
				Else
					AvailableFields.Insert(Item["Index"], Item["Name"]);
				EndIf;
			EndIf;
		EndDo;

		// удалим поля
		Pos = 0;
		While Pos < AvailableFields.Count() Do
			Item = AvailableFields.Get(Pos);
			If NOT(FindField(Item.Name, Fields.GetItems())) Then
				AvailableFields.Delete(Pos);
				Pos = Pos - 1;
			EndIf;
			Pos = Pos + 1;
		EndDo;

		// добавим новые поля
		Count = Fields.GetItems().Count();
		For Pos = 0 To Count - 1 Do
			Item = Fields.GetItems().Get(Pos);
			If Item["New"] Then
				If Item["ValueType"].Types().Count() > 0 Then
					AvailableFields.Add(Item.Name, Item["ValueType"].Types()[0]);
				Else
					AvailableFields.Add(Item.Name);
				EndIf;
			EndIf;
		EndDo;
	EndIf;
	
	PutToTempStorage(QuerySchema, QueryWizardAddress);
	Return True;
EndFunction

&AtServerNoContext
Function FindField(Val Name, Val Values)
	Var Count;
	Var Pos;
	Var Item;

	Count = Values.Count();
	For Pos = 0 To Count - 1 Do
	    Item = Values.Get(Pos);
		If Item.Name = Name Then
			Return True
		EndIf;
	EndDo;
	Return False;
EndFunction

&AtClient
Procedure Add(Command)
	Var NewItem;

	NewItem = Fields.GetItems().Add();
	NewItem["New"] = True;
	Changed = True;
EndProcedure

&AtClient
Procedure Delete(Command)
	Var CurrentRow;
	Var CurrentItems;

	CurrentRow = Items.Fields.CurrentRow;
	If (CurrentRow = Undefined) Then
		Return;
	EndIf;
	CurrentItems = Fields.FindByID(CurrentRow);
	Fields.GetItems().Delete(Fields.GetItems().IndexOf(CurrentItems));
	Changed = True;
EndProcedure

&AtClient
Procedure FieldsOnChange(Item)
	Var CurrentRow;
	Var CurrentItems;

	Changed = True;
	CurrentRow = Items.Fields.CurrentRow;
	If (CurrentRow = Undefined) Then
		Return;
	EndIf;
	CurrentItems = Fields.FindByID(CurrentRow);
	CurrentItems["Changed"] = True;
EndProcedure

&AtClient
Procedure AddCopy(Command)
	Var CurrentRow;
	Var CurrentItems;
	Var NewItem;

	CurrentRow = Items.Fields.CurrentRow;
	If (CurrentRow = Undefined) Then
		Return;
	EndIf;
	CurrentItems = Fields.FindByID(CurrentRow);
	NewItem = Fields.GetItems().Add();
	NewItem["Name"] = CurrentItems["Name"];
	NewItem["ValueType"] = CurrentItems["ValueType"];
	NewItem["Index"] = CurrentItems["Index"];
	NewItem["Changed"] = CurrentItems["Changed"];
	NewItem["New"] = True;
	Items.Fields.CurrentRow = NewItem.GetID();
	Changed = True;
EndProcedure

&AtClient
Procedure Edit(Command)
	Items.Fields.ChangeRow();
EndProcedure

&AtClient
Procedure FieldsBeforeAddRow(Item, Cancel, Clone, Parent, Folder, Parameter)
	If NOT(Clone) Then
		Add(Undefined);
	Else
		AddCopy(Undefined);
	EndIf;
	Cancel = True;
EndProcedure

&AtClient
Procedure FieldsBeforeRowChange(Item, Cancel)
EndProcedure

&AtClient
Procedure FieldsBeforeDeleteRow(Item, Cancel)
	Delete(Undefined);
	Cancel = True;
EndProcedure