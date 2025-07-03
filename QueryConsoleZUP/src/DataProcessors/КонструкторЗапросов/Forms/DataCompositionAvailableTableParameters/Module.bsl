&AtServer
Procedure OnCreateAtServer(Cancel, StandardProcessing)
	GetBSLVariant();
	FillDataCompositionTableParameters(Parameters["Index"],
									   Parameters["QueryWizardAddress"],
									   Parameters["CurrentQuerySchemaSelectQuery"],
									   Parameters["CurrentQuerySchemaOperator"],
									   Parameters["NestedQueryPositionAddress"]);										  
EndProcedure

&AtServer
Procedure GetBSLVariant()
	Var Schema;
	Var QueryText;
	
	Schema = New QuerySchema();
	Schema.SetQueryText("SELECT 1");
	
	QueryText = Schema.GetQueryText();

	RussianBSLVariant = (StrFind(QueryText, "SELECT") = 0);
EndProcedure

&AtServer
Procedure FillDataCompositionTableParameters(Val Index, Val QueryAddress, Val CurrentQuery, Val CurrentOperator, Val NestedQueryPosition)
	Var QuerySchema;
	Var Query;
	Var Source;
	Var TypesAttribute;
	Var TableParameters;
	Var Count;
	Var Pos;
	Var Parameter;
	Var NewAttribute;
	Var Name;
	Var TypesForAttribute;
	Var AdditionalyAttribute;
	Var NewFormElement;
	Var ParameterType;
	Var VariantsCount;
	Var VariantsPos;
	Var Param;
	Var ParamNode;
	Var FirstParamNode;
	Var TempStr;

	QueryWizardAddress = QueryAddress;
	CurrentQuerySchemaSelectQuery = CurrentQuery;
	CurrentQuerySchemaOperator = CurrentOperator;
	TableIndex = Index;
	NestedQueryPositionAddress = NestedQueryPosition;
	
	QuerySchema = GetFromTempStorage(QueryWizardAddress);
	If QuerySchema = Undefined Then
		Return;
	EndIf;

	Batch = QuerySchema.QueryBatch;
	Query = GetSchemaQuery(QuerySchema);

	Source = Query.Operators.Get(CurrentQuerySchemaOperator).Sources.Get(TableIndex).Source;

	If TypeOf(Source) <> Type("QuerySchemaTable") Then
		Return;
	EndIf;

	TableName = Source.TableName;
	Alias = Source.Alias;

	TableParameters = Query.AvailableTables.Find(Source.TableName).Parameters;
	Count = TableParameters.Count();

	If Count = 0 Then
		Return;	
	EndIf; 
	
	TypesAttribute = New Array;
	TypesAttribute.Add(Type("String"));

	AdditionalyAttribute = New Array;	
	For Pos = 0 To Count - 1 Do
		Parameter = TableParameters.Get(Pos);
		TypesForAttribute = New TypeDescription(TypesAttribute);

		Name = Parameter.Name;
		NewAttribute = Attributes.Add();
		NewAttribute["Name"] = Name;

		NewAttribute = New FormAttribute(Name, TypesForAttribute, "", Name, False);
		AdditionalyAttribute.Add(NewAttribute);
	EndDo;
	
	ChangeAttributes(AdditionalyAttribute);	
	
	For Pos = 0 To Count - 1 Do
		Parameter = TableParameters.Get(Pos);
		Name = Parameter.Name;
		
		NewFormElement = Items.Add(Name, Type("FormField"), Items.ParametersGroup);
		NewFormElement.DataPath = Name;
		NewFormElement.Type = FormFieldType.InputField;

		ParameterType = Parameter.ParameterType;
		If ParameterType = QuerySchemaAvailableTableParameterType.Variant Then
			VariantsCount = Parameter.Variants.Count();
			For VariantsPos = 0 To VariantsCount - 1 Do
				//If VariantsPos = 0 Then
				NewFormElement.DropListButton = True;
				NewFormElement.ListChoiceMode = False;
				NewFormElement.ChoiceButton = False;
				//NewFormElement.TextEdit = False;
				//NewFormElement.ClearButton = True;
				Break;
				//EndIf;
				//NewFormElement.ChoiceList.Add(Parameter.Variants.Get(VariantsPos));
			EndDo;
		ElsIf (ParameterType = QuerySchemaAvailableTableParameterType.Value)
			OR (ParameterType = QuerySchemaAvailableTableParameterType.Array) Then

			NewFormElement.DropListButton = True;
			NewFormElement.TextEdit = True;
			NewFormElement.ClearButton = False;
			For Each Parameter In QuerySchema.FindParameters() Do
				NewFormElement.ChoiceList.Add("&" + Parameter.Name);
			EndDo;
		ElsIf (ParameterType = QuerySchemaAvailableTableParameterType.Condition)
			OR (ParameterType = QuerySchemaAvailableTableParameterType.Order)
			OR (ParameterType = QuerySchemaAvailableTableParameterType.FieldList) Then

			NewFormElement.ChoiceButton = True;
			NewFormElement.MultiLine = True;
			NewFormElement.TitleLocation = FormItemTitleLocation.Left;
			NewFormElement.SetAction("StartChoice", "ConditionStartChoice");
		EndIf;

		Param = Source.DataCompositionParameters.Get(Pos);
		
		If Param = Undefined Then
			ThisForm[Name] = "";
			Continue;
		EndIf;
		
		If TypeOf(Param) = Type("QuerySchemaTableParameter") Then
			ThisForm[Name] = Param.Expression;
			IsParameters = True;
		ElsIf TypeOf(Param) = Type("QuerySchemaDataCompositionFilterExpressions") Then
			TempStr = "";
			FirstParamNode = True;
			
			For Each ParamNode In Param Do				
				If FirstParamNode Then
					FirstParamNode = False;
				Else
					TempStr = TempStr + ", ";
				EndIf;				
				TempStr = TempStr + "(" + ParamNode.Expression + ")";
				If ParamNode.UseChildren Then
					TempStr = TempStr + ".*";
				EndIf;
				If ParamNode.Alias <> "" Then
					If(RussianBSLVariant) Then
						TempStr = TempStr + " " + "КАК" + " " + ParamNode.Alias;
					Else
						TempStr = TempStr + " " + "AS" + " " + ParamNode.Alias;
					EndIf;										
				EndIf;
			EndDo;
			ThisForm[Name] = TempStr;
		EndIf;
	EndDo;	
EndProcedure

&AtServer
Function GetSchemaQuery(Val QuerySchema)
	Var MainObject;

	MainObject = FormAttributeToValue("Object");
	Return MainObject.GetSchemaQuery(QuerySchema, CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress);
EndFunction

&AtClient
Procedure OK(Command)
	If OKAtServer() Then
		ThisForm.Close();
	EndIf;
EndProcedure

&AtServer
Function OKAtServer()
	Var Count;
	Var Pos;
	Var Attribute;
	Var QuerySchema;
	Var Query;
	Var Operator;
	Var Source;
	Var QueryText;
	Var Param;
	Var Message;
	Var ParametersArray;
	Var Parameter;

	Count = Attributes.Count();
	Changed = False;
	For Pos = 0 To Count - 1 Do
		Attribute = Attributes.Get(Pos);
		Attribute["Value"] = ThisForm[Attribute["Name"]];
	EndDo;

	QuerySchema = GetFromTempStorage(QueryWizardAddress);
	If QuerySchema = Undefined Then
		Return True;
	EndIf;

	Batch = QuerySchema.QueryBatch;
	Query = GetSchemaQuery(QuerySchema);

	Operator = Query.Operators.Get(CurrentQuerySchemaOperator);
	If Operator = Undefined Then
		Return True;
	EndIf;
	Source = Query.Operators.Get(CurrentQuerySchemaOperator).Sources.Get(TableIndex).Source;

	If  (Source = Undefined)
		OR (TypeOf(Source) <> Type("QuerySchemaTable"))
		OR (TableName <> Source.TableName)
		OR (Alias <> Source.Alias) Then
		Return True;
	EndIf;

	QueryText = QuerySchema.GetQueryText();
	Try
		For Pos = 0 To Count - 1 Do
			Attribute = Attributes.Get(Pos);
			Param = Source.DataCompositionParameters.Get(Pos);
			If Param <> Undefined Then				
				If TypeOf(Param) = Type("QuerySchemaDataCompositionFilterExpressions") Then
					
					Param.Clear();
					
					ParametersArray = StrSplit(Attribute["Value"], ",", False);
					For Each Parameter In ParametersArray Do
						Parameter = TrimAll(Parameter);
						Param.Add(Parameter);
					EndDo;					
				ElsIf TypeOf(Param) = Type("QuerySchemaTableParameter") Then
					
					If Param.Expression <> Attribute["Value"] Then
						Param.Expression = New QuerySchemaExpression(Attribute["Value"]);
					EndIf;
				EndIf;
			EndIf;
		EndDo;
	Except
		Message = New UserMessage;
		Message.Text = BriefErrorDescription(ErrorInfo());
		Message.Field = Attribute["Name"];
		Message.Message();

		QuerySchema.SetQueryText(QueryText);
		Return False;
	EndTry;
	Return True;
EndFunction

&AtClient
Procedure Cancel(Command)
	ThisForm.Close();
EndProcedure

&AtClient
Procedure ConditionStartChoice(Item, ChoiceData, StandardProcessing) Export
	StandardProcessing = False;
	ConditionChangeInDialog(Item.EditText, Item.Name);
EndProcedure

&AtClient
Procedure ConditionChangeInDialog(Val Expression, Val Name)
	Var Params;
	Var Notification;

	Params = New Structure;
	Params.Insert("Expression", Expression);
	Params.Insert("PropertyName", Name);
	Params.Insert("TableIndex", TableIndex);
	Params.Insert("Changed", False);
	
	Params.Insert("QueryWizardAddress", QueryWizardAddress);
	Params.Insert("CurrentQuerySchemaSelectQuery", CurrentQuerySchemaSelectQuery);   
	Params.Insert("CurrentQuerySchemaOperator", CurrentQuerySchemaOperator);
	Params.Insert("NestedQueryPositionAddress", NestedQueryPositionAddress);
		
	Notification = New NotifyDescription("ConditionChanged", ThisForm, Params);
    OpenForm("ExternalDataProcessor.QueryWizard.Form.ArbitraryExpression", Params, ThisForm,,,,Notification, 
             FormWindowOpeningMode.LockOwnerWindow);
EndProcedure

&AtClient
Procedure ConditionChanged(ChildForm, Params) Export
	If ChildForm = Undefined Then
		Return;
	EndIf;

	If Params["Changed"] Then
		ThisForm[Params["PropertyName"]] = Params["Expression"];
	EndIf;
	ChildForm.Closing = True;
	ChildForm.Close();
EndProcedure