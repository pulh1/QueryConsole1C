&AtServer
Procedure OnCreateAtServer(Cancel, StandardProcessing)
	Var StartTableName;
	Var Prop;	
	AvailableTablesBase = GetFromTempStorage(Parameters["AvailableTablesAddress"]);
	ValueToFormAttribute(AvailableTablesBase, "AvailableTables");
	                                  
	StartTableName = Parameters["StartTableName"];     
	DisplayChangesTables = Parameters["DisplayChangesTables"];
	QueryWizardAddress = Parameters["QueryWizardAddress"];
	CurrentQuerySchemaSelectQuery = Parameters["CurrentQuerySchemaSelectQuery"];
	NestedQueryPositionAddress = Parameters["NestedQueryPositionAddress"];
				  
	Prop = Undefined;
	Parameters.Property("FormMode", Prop);
	If Prop <> Undefined Then
		Mode = Parameters["FormMode"];
	Else
		Mode = "";
	EndIf;
	
	FindTable(QueryWizardAddress, 
	          CurrentQuerySchemaSelectQuery, 
			  StartTableName, 
              Parameters["SourcesImagesCacheAddress"], 
			  Parameters["ExpressionsImagesCacheAddress"]);
	
	If (Mode = "CharacteristicTypeMode") Then
		Items.AvailableTables.SelectionMode = TableSelectionMode.MultiRow;
	Else
		Items.AvailableTables.SelectionMode = TableSelectionMode.SingleRow;
	EndIf;
EndProcedure

&AtClient
Procedure AvailableTablesBeforeExpand(Item, Row, Cancel)
	Var CurrentItems;
	Var DataProcessor;
	
	Try
		DataProcessor = GetForm("ExternalDataProcessor.QueryWizard.Form.QueryWizard");
	Except
		Message(ErrorDescription());
		Return;
	EndTry;
	
	CurrentItems = AvailableTables.FindByID(Row);
	If DataProcessor.IsFakeItem(CurrentItems) Then
		EditedRow = Row;
		AttachIdleHandler("AvailableTablesBeforeExpandHandler", 0.01, True);
	EndIf;
EndProcedure

&AtClient
Procedure AvailableTablesBeforeExpandHandler()
	AvailableTablesBeforeExpandAtServer(QueryWizardAddress, Number(CurrentQuerySchemaSelectQuery), NestedQueryPositionAddress, EditedRow);
EndProcedure

&AtServer
Procedure RemoveUnwantedItems()
	Var TypesList;
	Var RootItem;
	Var Deleted;
	
	If (Mode = "CharacteristicTypeMode") Then
		TypesList = New Array();
		TypesList.Add("Справочники");
		TypesList.Add("Документы");
		TypesList.Add("Перечисления");
		TypesList.Add("ПланыВидовХарактеристик");
		TypesList.Add("ПланыСчетов");
		TypesList.Add("ПланыВидовРасчета");
		TypesList.Add("БизнесПроцессы");
		TypesList.Add("ТочкиМаршрута");
		TypesList.Add("Задачи");
		TypesList.Add("ПланыОбмена");
		TypesList.Add("Catalog'");
		TypesList.Add("Documents");
		TypesList.Add("Enums");
		TypesList.Add("ChartsOfCharacteristicTypes");
		TypesList.Add("ChartsOfAccounts");
		TypesList.Add("ChartsOfCalculationTypes");
		TypesList.Add("BusinessProcesses");
		TypesList.Add("RoutePoints");
		TypesList.Add("Tasks");
		TypesList.Add("ExchangePlans");
		
		While(True) Do
			Deleted = False;
			For Each RootItem In AvailableTables.GetItems() Do
				If (TypesList.Find(RootItem["Name"]) = Undefined) Then
					AvailableTables.GetItems().Delete(AvailableTables.GetItems().IndexOf(RootItem));
					Deleted = True;
					Break;
				EndIf;
			EndDo;			
			
			If (NOT Deleted) Then
				Break;
			EndIf;
		EndDo;
	EndIf;
EndProcedure

&AtServer
Procedure FindTable(Val QueryWizardAddress, 
					Val CurrentQuerySchemaSelectQuery, 
					Val StartTableName, 
					Val SourcesImagesCacheAddress, 
                    Val ExpressionsImagesCacheAddress)
	Var MainObject;
	Var RootItem;
	Var QueryT;
	Var Item;

	RemoveUnwantedItems();
	MainObject = FormAttributeToValue("Object");
	QueryT = MainObject.GetSchemaQuery(GetFromTempStorage(QueryWizardAddress), CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress);	
	For Each RootItem In AvailableTables.GetItems() Do
		
		
		If (RootItem.GetItems().Count() = 1) AND (RootItem.GetItems().Get(0)["Name"] = "FakeFieldeItem") Then
			AvailableTablesBeforeExpandAtServer(QueryWizardAddress, CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress, RootItem.GetID(), 
			SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, MainObject, 
			QueryT);
		EndIf;
		If StartTableName <> "" Then
			For Each Item In RootItem.GetItems() Do
				If Item["Name"] = StartTableName Then
					Items.AvailableTables.CurrentRow = Item.GetID();
					
				EndIf;
			EndDo;
		EndIf;
	EndDo;
EndProcedure

&AtServer
Procedure AvailableTablesBeforeExpandAtServer(Val QueryWizardAddress, 
											  Val CurrentQuerySchemaSelectQuery, 
											  Val NestedQueryPositionAddress, 
											  Val Row, 
                                              Val SourcesImagesCacheAddress = Undefined, 
											  Val ExpressionsImagesCacheAddress = Undefined, 
											  Val MainObject = Undefined, 
											  Val Query = Undefined)
	Var MainObjectT;

	If MainObject = Undefined Then
		MainObjectT = FormAttributeToValue("Object");

		MainObjectT.AvailableTablesBeforeExpandAtServer(QueryWizardAddress, CurrentQuerySchemaSelectQuery, 
                                                        NestedQueryPositionAddress, Row, AvailableTables);
	Else
		MainObject.AvailableTablesBeforeExpandAtServer(QueryWizardAddress, CurrentQuerySchemaSelectQuery, 
                                                       NestedQueryPositionAddress, Row, AvailableTables, ,DisplayChangesTables, SourcesImagesCacheAddress, 
                                                       ExpressionsImagesCacheAddress, Query);
	EndIf;
EndProcedure

&AtClient
Function  GetItemIndexes(Item)
	Var ItemIndexes;
	Var Parent;

	ItemIndexes = New Array;
	ItemIndexes.Insert(0, Item["Index"]);
	Parent = Item.GetParent();
	While (Parent <> Undefined) AND (Parent["Type"] > 0) Do
		ItemIndexes.Insert(0, Parent["Index"]);
		Parent = Parent.GetParent();
	EndDo;
	Return ItemIndexes;
EndFunction

&AtClient
Procedure AvailableTablesSelection(Item, SelectedRow, Field, StandardProcessing)
	OK(Undefined);
EndProcedure

&AtClient
Procedure OK(Command)
	Var CurrentRow;
	Var CurrentItems;
	Var SelectedRow;
	Var CurrentItem;
	Var ItemIndexes;
	Var Tmp;
	
	If (Mode = "ReplaceTabmeMode") Then
		CurrentRow = Items.AvailableTables.CurrentRow;
		If CurrentRow = Undefined Then
			Return;
		EndIf;
		CurrentItems = AvailableTables.FindByID(CurrentRow);

		If CurrentItems.GetParent() = Undefined Then
			Return;
		EndIf;

		While (CurrentItems["Type"] <> 1)
			AND (CurrentItems["Type"] <> 3)
			AND (CurrentItems <> Undefined) Do
			CurrentItems = CurrentItems.GetParent();
		EndDo;
		If (CurrentItems = Undefined)
			OR ((CurrentItems["Type"] <> 1) AND (CurrentItems["Type"] <> 3)) Then
			Return;
		EndIf;
		
		ThisForm.OnCloseNotifyDescription.AdditionalParameters["ItemIndexes"] = GetItemIndexes(CurrentItems);
		ThisForm.Close(DialogReturnCode.OK);
	ElsIf (Mode = "CharacteristicTypeMode") Then
		CurrentItems = New Structure;
		For Each SelectedRow In Items.AvailableTables.SelectedRows Do
			CurrentItem = AvailableTables.FindByID(SelectedRow);
			
			While (CurrentItem["Type"] <> 1)
				AND (CurrentItem["Type"] <> 3)
				AND (CurrentItem <> Undefined) Do
				CurrentItem = CurrentItem.GetParent();
			EndDo;
			If (CurrentItem = Undefined)
				OR ((CurrentItem["Type"] <> 1) AND (CurrentItem["Type"] <> 3)) Then
				
				Tmp = Undefined;
				CurrentItems.Property(CurrentItem.Name, Tmp);
				If (Tmp <> Undefined) Then
					Continue;
				EndIf;
			EndIf;
			
			If (CurrentItem.GetParent() <> Undefined) Then
				CurrentItems.Insert(CurrentItem.Presentation, CurrentItem.Name);
			Else
				For Each Tmp In CurrentItem.GetItems() Do
					CurrentItems.Insert(Tmp.Presentation, Tmp.Name);
				EndDo;
			EndIf;
		EndDo;
		
		ThisForm.OnCloseNotifyDescription.AdditionalParameters["ItemIndexes"] = CurrentItems;
		ThisForm.Close(DialogReturnCode.OK);
	ElsIf (Mode = "CharacteristicSourceMode") Then
		CurrentItems = New Structure;
		CurrentRow = Items.AvailableTables.CurrentRow;
		If CurrentRow = Undefined Then
			Return;
		EndIf;
		CurrentItem = AvailableTables.FindByID(CurrentRow);

		If CurrentItem.GetParent() = Undefined Then
			Return;
		EndIf;

		While (CurrentItem["Type"] <> 1)
			AND (CurrentItem["Type"] <> 3)
			AND (CurrentItem <> Undefined) Do
			CurrentItem = CurrentItem.GetParent();
		EndDo;
		If (CurrentItem = Undefined)
			OR ((CurrentItem["Type"] <> 1) AND (CurrentItem["Type"] <> 3)) Then
			Return;
		EndIf;
		If (CurrentItem.GetParent() <> Undefined) Then
			CurrentItems.Insert("Table", CurrentItem.Name);
		EndIf;
		
		ThisForm.OnCloseNotifyDescription.AdditionalParameters["ItemIndexes"] = CurrentItems;
		ThisForm.Close(DialogReturnCode.OK);
	EndIf;
	
EndProcedure

&AtClient
Procedure Cancel(Command)
	ThisForm.Close(DialogReturnCode.Cancel);
EndProcedure
