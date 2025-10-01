Procedure AvailableTablesBeforeExpandAtServer(Val QueryWizardAddress, 
											  Val CurrentQuerySchemaSelectQuery, 
											  Val NestedQueryPositionAddress, 
											  Val Row, 
                                              Val AvailableTablesTree, 
											  Val Lavel = 1, 
											  Val DisplayChangesTables = True, 
                                              Val SourcesImagesCacheAddress = Undefined, 
											  Val ExpressionsImagesCacheAddress = Undefined, 
											  Query = Undefined) Export
	Var QuerySchema;
	Var ItemIndexes;
	Var CurrentItems;
	Var Parent;
	Var Item;
										  
	If (Query = Undefined) Then
		QuerySchema = GetFromTempStorage(QueryWizardAddress);
		If QuerySchema = Undefined Then
			Return;
		EndIf;
		Query = GetSchemaQuery(QuerySchema, CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress);
	EndIf;

	If TypeOf(Query) = Type("QuerySchemaTableDropQuery") Then
		Return;
	EndIf;

	CurrentItems = AvailableTablesTree.FindByID(Row);
	ItemIndexes = New Array;
	ItemIndexes.Insert(0, CurrentItems["Index"]);
	Parent = CurrentItems.GetParent();
	While (Parent <> Undefined) AND (Parent["Type"] > 0) Do
		ItemIndexes.Insert(0, Parent["Index"]);
		Parent = Parent.GetParent();
	EndDo;

	FillSourcesByIndex(CurrentItems.GetItems(), Query.AvailableTables, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
					   ItemIndexes, , ,DisplayChangesTables);
	If Lavel > 1 Then
		For Each Item In CurrentItems.GetItems() Do
			If (Item.GetItems().Count() = 1)
				AND (Item.GetItems().Get(0)["Name"] = "FakeFieldeItem") Then
				AvailableTablesBeforeExpandAtServer(QueryWizardAddress, CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress,
                                                    Item.GetID(), AvailableTablesTree, Lavel - 1, DisplayChangesTables, 
                                                    SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, Query);
			EndIf;
		EndDo;
	EndIf;
EndProcedure

Procedure SourcesBeforeExpandAtServer(Val QueryWizardAddress, 
									  Val CurrentQuerySchemaSelectQuery, 
                                      Val CurrentQuerySchemaOperator, 
									  Val NestedQueryPositionAddress,
									  Val Row, 
									  Val SourcesTree, 
									  Val Lavel = 1, 
									  Val SourcesImagesCacheAddress = Undefined, 
									  Val ExpressionsImagesCacheAddress = Undefined, 
									  Query = Undefined) Export
	Var QuerySchema;
	Var Operators;
	Var ItemIndexes;
	Var CurrentItems;
	Var Parent;
	Var Operator;
	Var Item;
	
	If (Query = Undefined) Then
		QuerySchema = GetFromTempStorage(QueryWizardAddress);
		If QuerySchema = Undefined Then
			Return;
		EndIf;
		Query = GetSchemaQuery(QuerySchema, CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress);
	EndIf;

	If TypeOf(Query) = Type("QuerySchemaTableDropQuery") Then
		Return;
	EndIf;

	Operators  = Query.Operators;
	Operator = Operators.Get(CurrentQuerySchemaOperator);
	CurrentItems = SourcesTree.FindByID(Row);
	ItemIndexes = New Array;
	ItemIndexes.Insert(0, CurrentItems["Index"]);
	Parent = CurrentItems.GetParent();
	While (Parent <> Undefined) AND (Parent["Type"] > 0) Do
		ItemIndexes.Insert(0, Parent["Index"]);
		Parent = Parent.GetParent();
	EndDo;

	FillSourcesByIndex(CurrentItems.GetItems(), Operator.Sources, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
					   ItemIndexes, Query.AvailableTables);
	If Lavel > 1 Then
		For Each Item In CurrentItems.GetItems() Do
			If (Item.GetItems().Count() = 1)
				AND (Item.GetItems().Get(0)["Name"] = "FakeFieldeItem") Then
				SourcesBeforeExpandAtServer(QueryWizardAddress, CurrentQuerySchemaSelectQuery, CurrentQuerySchemaOperator, 
                                            NestedQueryPositionAddress, Item.GetID(), SourcesTree, Lavel - 1, 
                                            SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, Query);
			EndIf;
		EndDo;
	EndIf;
EndProcedure

Procedure FillPropertyFields(Val QueryWizardAddress, 
							 Val CurrentQuerySchemaSelectQuery, 
                             Val CurrentQuerySchemaOperator, 
							 Val NestedQueryPositionAddress,
							 Val PropertyName, 
							 Val FieldsTree, 
							 Val TableIndex, 
							 Val SourcesImagesCacheAddress = Undefined, 
							 Val ExpressionsImagesCacheAddress = Undefined) Export
							 
	Var QuerySchema;
	Var Query;
	Var Source;
	Var TableParameters;
	Var Count;
	Var Pos;
	Var ParameterFields;
						 
	QuerySchema = GetFromTempStorage(QueryWizardAddress);
	If QuerySchema = Undefined Then
		Return;
	EndIf;


	Batch = QuerySchema.QueryBatch;
	Query = GetSchemaQuery(QuerySchema, CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress);
	Source = Query.Operators.Get(CurrentQuerySchemaOperator).Sources.Get(TableIndex).Source;

	If TypeOf(Source) <> Type("QuerySchemaTable") Then
		Return;
	EndIf;

	TableName = Source.TableName;
	Alias = Source.Alias;

	TableParameters = Query.AvailableTables.Find(Source.TableName).Parameters;
	Count = TableParameters.Count();
	For Pos = 0 To Count - 1 Do
		If PropertyName = TableParameters.Get(Pos).Name Then
			ParameterFields = TableParameters.Get(Pos).AvailableFields;

			FillSourcesByIndex(FieldsTree.GetItems(), ParameterFields, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress);
			Break;
		EndIf;
	EndDo;
EndProcedure

Procedure FillPropertyFieldsExpand(Val QueryWizardAddress, 
								   Val CurrentQuerySchemaSelectQuery, 
                                   Val CurrentQuerySchemaOperator, 
								   Val NestedQueryPositionAddress,
								   Val Row, 
								   Val SourcesTree, 
								   Val PropertyName, 
								   Val TableIndex, 
                                   Val SourcesImagesCacheAddress = Undefined, 
								   Val ExpressionsImagesCacheAddress = Undefined) Export
	Var QuerySchema;
	Var Query;
	Var Source;
	Var ItemIndexes;
	Var CurrentItems;
	Var Parent;
	Var TableParameters;
	Var Count;
	Var Pos;
	Var ParameterFields;
	Var Pos1;
	
	QuerySchema = GetFromTempStorage(QueryWizardAddress);
	If QuerySchema = Undefined Then
		Return;
	EndIf;


	Batch = QuerySchema.QueryBatch;
	Query = GetSchemaQuery(QuerySchema, CurrentQuerySchemaSelectQuery, NestedQueryPositionAddress);
	Source = Query.Operators.Get(CurrentQuerySchemaOperator).Sources.Get(TableIndex).Source;


	If TypeOf(Source) <> Type("QuerySchemaTable") Then
		Return;
	EndIf;
	
	TableName = Source.TableName;
	Alias = Source.Alias;

	TableParameters = Query.AvailableTables.Find(Source.TableName).Parameters;
	CurrentItems = SourcesTree.FindByID(Row);
	ItemIndexes = New Array;
	ItemIndexes.Insert(0, CurrentItems["Index"]);
	Parent = CurrentItems.GetParent();
	While (Parent <> Undefined) AND (Parent["Type"] > 0) Do
		ItemIndexes.Insert(0, Parent["Index"]);
		Parent = Parent.GetParent();
	EndDo;

	Count = TableParameters.Count();
	For Pos = 0 To Count - 1 Do
		If PropertyName = TableParameters.Get(Pos).Name Then
			ParameterFields = TableParameters.Get(Pos).AvailableFields;

			FillSourcesByIndex(CurrentItems.GetItems(), ParameterFields, 
							   SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, ItemIndexes);

			For Pos1 = 0 To CurrentItems.GetItems().Count() - 1 Do
				Item = CurrentItems.GetItems().Get(Pos1);
			EndDo;
			Break;
		EndIf;
	EndDo;
EndProcedure

Function GetSchemaQuery(Val QuerySchema, 
						Val CurrentQuerySchemaSelectQuery,
						Val NestedQueryPositionAddress = Undefined) Export
	Var Batch;
	Var Query;
	Var Operator;
	Var Positions;
	
	Batch = QuerySchema.QueryBatch;
	Query = Batch.Get(CurrentQuerySchemaSelectQuery);
	
	If NestedQueryPositionAddress <> Undefined Then
		 // Если вложенный запрос
		Positions = GetFromTempStorage(NestedQueryPositionAddress);	    			
		For Pos = 0 To Positions.Count() - 1 Do
			Operator = Query.Operators.Get(Positions[Pos]); 			
			Pos = Pos + 1;
			Query = Operator.Sources.Get(Positions[Pos]).Source.Query; 					
		EndDo; 
		PutToTempStorage(Positions, NestedQueryPositionAddress);	
	EndIf; 
	Return Query;
EndFunction

/////////////////
Procedure FillSourcesByIndex(Val ItemsTree, 
							 Val DataSource, 							  
							 Val SourcesImagesCacheAddress, 
							 Val ExpressionsImagesCacheAddress,
							 Val Indexes = Undefined, 
							 Val AvailableTables = Undefined, 
							 Val EnableSort = False,
                             Val ShowTablesForChange = True) Export						 
							 
	// TODO заполняем списко таблиц						 
	Var Source;
	
	If Indexes = Undefined Then
		Source = DataSource;
	Else
		Source = GetSource(DataSource, Indexes);
	EndIf;
	If Source <> Undefined Then
		FillSourcesItems(ItemsTree, Source, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort, ShowTablesForChange);
	EndIf;
EndProcedure

Procedure FillSourcesItems(Val ItemsTree, 
						   Val Source, 
						   Val SourcesImagesCacheAddress, 
						   Val ExpressionsImagesCacheAddress, 
						   Val AvailableTables, 
						   Val EnableSort, 
						   Val ShowTablesForChange = True,
						   Val FakeField = False)
	Var Items;
	Var Count;
	Var Pos;
	Var NewItem;
					   
	If TypeOf(Source) = Type("QuerySchemaAvailableTables") Then
		Items = Source;
	ElsIf TypeOf(Source) = Type("QuerySchemaAvailableTablesGroup") Then
		Items = Source.Content;
	ElsIf TypeOf(Source) = Type("QuerySchemaAvailableTable") Then
		Items = Source.Fields;
	ElsIf TypeOf(Source) = Type("QuerySchemaAvailableNestedTable") Then
		Items = Source.Fields;
	ElsIf TypeOf(Source) = Type("QuerySchemaAvailableField") Then
		Items = Source.Fields;
	ElsIf TypeOf(Source) = Type("QuerySchemaAvailableFields") Then
		Items = Source;
	ElsIf TypeOf(Source) = Type("QuerySchemaSources") Then
		Items = Source;
	ElsIf TypeOf(Source) = Type("QuerySchemaSource") Then

		FillSourcesItems(ItemsTree, Source.Source, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort, ShowTablesForChange, FakeField);
		Return;
	ElsIf TypeOf(Source) = Type("QuerySchemaTable") Then
		Items = Source.AvailableFields;
	ElsIf TypeOf(Source) = Type("QuerySchemaNestedQuery") Then
		Items = Source.AvailableFields;
	ElsIf TypeOf(Source) = Type("QuerySchemaTempTableDescription") Then
		Items = Source.AvailableFields;
	Else
		Return;
	EndIf;

	ItemsTree.Clear();
	Count = Items.Count();
	If NOT(FakeField) Then
		For Pos = 0 To Count - 1 Do
			AddSourceItem(ItemsTree, Items.Get(Pos), Pos, AvailableTables, EnableSort, 
                          SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, ShowTablesForChange);
		EndDo;
	Else
		If Count > 0 Then
			NewItem = ItemsTree.Add();
			NewItem["Name"] = "FakeFieldeItem";
		EndIf;
	EndIf;

	If EnableSort Then
		qSort(ItemsTree, "Presentation");
	EndIf;
EndProcedure

Procedure AddSourceItem(Val ItemsTree, 
						Val Source, 
						Val Pos, 
						Val AvailableTables, 
						Val EnableSort, 
                        Val SourcesImagesCacheAddress, 
						Val ExpressionsImagesCacheAddress,
						Val ShowTablesForChange = True)
	Var NewElement;
	Var Prop;
	Var ParentItemPicture;
	Var Parent;
	Var Name;
	Var AvailableTable;
	
	If TypeOf(Source) = Type("QuerySchemaAvailableTablesGroup") Then
		NewElement = ItemsTree.Add();
		NewElement["Type"] = 1;
		NewElement["Presentation"] = Source.Presentation;
		NewElement["Name"] = Source.Presentation;
		NewElement["Index"] = Pos;
		Prop = 0;
		NewElement.Property("Picture", Prop);
		If (Prop <> Undefined) Then
			NewElement["Picture"] = GetPictureForSource(NewElement["Name"], SourcesImagesCacheAddress, , , True);
		EndIf;

		FillSourcesItems(NewElement.GetItems(), Source.Content, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort, ShowTablesForChange, True);
	ElsIf TypeOf(Source) = Type("QuerySchemaAvailableTable") Then
		If NOT(ShowTablesForChange)
			AND ((Find(Source.Name, ".Changes") = StrLen(Source.Name) - StrLen(".Changes") + 1)
			OR   (Find(Source.Name, ".Изменения") = StrLen(Source.Name) - StrLen(".Изменения") + 1))Then
			If (Find(Source.Name, ".Changes") > 0) OR (Find(Source.Name, ".Изменения") > 0) Then
				Return;
			EndIf;
		EndIf;

		NewElement = ItemsTree.Add();
		NewElement["Type"] = 1;
		NewElement["Name"] = Source.Name;

		If (Find(Source.Name, "ExternalDataSource.") = 1) OR (Find(Source.Name, "ВнешнийИсточникДанных.") = 1) Then
			NewElement["Presentation"] = Mid(Source.Name, Find(Source.Name, ".") + 1, StrLen(Source.Name));
			NewElement["Presentation"] = Mid(NewElement["Presentation"], Find(NewElement["Presentation"], ".") + 1, 
	            StrLen(NewElement["Presentation"]));
			NewElement["Presentation"] = Mid(NewElement["Presentation"], Find(NewElement["Presentation"], ".") + 1, 
	            StrLen(NewElement["Presentation"]));
		Else
			NewElement["Presentation"] = Mid(Source.Name, Find(Source.Name, ".") + 1, StrLen(Source.Name));
		EndIf;

		NewElement["Index"] = Pos;
		Prop = 0;
		NewElement.Property("Picture", Prop);
		If (Prop <> Undefined) Then
			ParentItemPicture = Undefined;
			NewElement["Picture"] = GetPictureForSource(NewElement["Name"], SourcesImagesCacheAddress,, ParentItemPicture);
			Parent = NewElement.GetParent();
			If (Parent <> Undefined) AND (ParentItemPicture <> Undefined) Then
				Parent["Picture"] = ParentItemPicture;
			EndIf;
		EndIf;

		FillSourcesItems(NewElement.GetItems(), Source.Fields, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort, ShowTablesForChange, True);
	ElsIf TypeOf(Source) = Type("QuerySchemaAvailableNestedTable") Then
		NewElement = ItemsTree.Add();
		NewElement["Type"] = 3;
		NewElement["Presentation"] = Source.Name;
		NewElement["Name"] = GetName(2, NewElement);
		NewElement["Index"] = Pos;
		Prop = 0;
		NewElement.Property("Picture", Prop);
		If (Prop <> Undefined) Then
			NewElement["Picture"] = GetPictureForSource("NestedTable", SourcesImagesCacheAddress);
		EndIf;
		FillSourcesItems(NewElement.GetItems(), Source.Fields, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort,, True);
	ElsIf TypeOf(Source) = Type("QuerySchemaAvailableField") Then
		NewElement = ItemsTree.Add();
		NewElement["Type"] = 2;
		NewElement["Presentation"] = Source.Name;
		NewElement["Name"] = GetName(NewElement["Type"], NewElement);
		NewElement["ValueType"] = Source.ValueType;
		NewElement["Index"] = Pos;
		NewElement.Property("Picture", Prop);
		If (Prop <> Undefined) Then
			NewElement["Picture"] = GetPictureForAvailableField(Source, ExpressionsImagesCacheAddress);
		EndIf;

		FillSourcesItems(NewElement.GetItems(), Source.Fields, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort,, True);
	ElsIf TypeOf(Source) = Type("QuerySchemaSource") Then

		AddSourceItem(ItemsTree, Source.Source, Pos, AvailableTables, EnableSort, 
					  SourcesImagesCacheAddress, ExpressionsImagesCacheAddress);
	ElsIf TypeOf(Source) = Type("QuerySchemaTable") Then
		NewElement = ItemsTree.Add();
		NewElement["Type"] = 1;
		NewElement["Index"] = Pos;
		NewElement["Presentation"] = Source.Alias;
	    Name = StrReplace(Source.Alias, ".", "");
		NewElement["ValueType"] = "QuerySchemaTable";
		NewElement["Name"] =  Name;
		NewElement["TableName"] = Source.TableName;
		Prop = 0;
		NewElement.Property("ParametersCount", Prop);
		If (Prop <> Undefined)
			AND (AvailableTables <> Undefined)
			AND (AvailableTables.Find(Source.TableName) <> Undefined) Then

			AvailableTable = AvailableTables.Find(Source.TableName);
			If TypeOf(AvailableTable) = Type("QuerySchemaAvailableTable") Then
				NewElement["ParametersCount"] = AvailableTable.Parameters.Count();
			Else
				NewElement["ParametersCount"] = 0;
			EndIf;
		EndIf;
		Prop = 0;
		NewElement.Property("Picture", Prop);
		If (Prop <> Undefined) Then
			NewElement["Picture"] = GetPictureForSource(NewElement["TableName"], SourcesImagesCacheAddress);
		EndIf;

		FillSourcesItems(NewElement.GetItems(), Source.AvailableFields, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort,, True);
	ElsIf TypeOf(Source) = Type("QuerySchemaNestedQuery") Then
		NewElement = ItemsTree.Add();
		NewElement["Type"] = 1;
		NewElement["Index"] = Pos;
		NewElement["Presentation"] = Source.Alias;
		NewElement["ValueType"] = "QuerySchemaNestedQuery";
		NewElement["Name"] = GetName(NewElement["Type"], NewElement);
		NewElement["TableName"] = Source.Alias;
		Prop = 0;
		NewElement.Property("Picture", Prop);
		If (Prop <> Undefined) Then
			NewElement["Picture"] = GetPictureForSource("NestedQuery", SourcesImagesCacheAddress);
		EndIf;

		FillSourcesItems(NewElement.GetItems(), Source.AvailableFields, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort,, True);
	ElsIf TypeOf(Source) = Type("QuerySchemaTempTableDescription") Then
		NewElement = ItemsTree.Add();
		NewElement["Type"] = 1;
		NewElement["Index"] = Pos;
		NewElement["Presentation"] = Source.Alias;
		Name = StrReplace(Source.Alias, ".", "");
		NewElement["ValueType"] = "QuerySchemaTempTableDescription";
		NewElement["Name"] =  Name;
		NewElement["TableName"] = Source.Alias;
		Prop = 0;
		NewElement.Property("Picture", Prop);
		If (Prop <> Undefined) Then
			NewElement["Picture"] = GetPictureForSource("TempTable", SourcesImagesCacheAddress);
		EndIf;

		FillSourcesItems(NewElement.GetItems(), Source.AvailableFields, SourcesImagesCacheAddress, ExpressionsImagesCacheAddress, 
						 AvailableTables, EnableSort,, True);
	EndIf;
EndProcedure

Function GetSource(Val DataSource, 
				   Val Indexes)
	Var Source;
	Var Pos;

	Source = DataSource;
	For Pos = 0 To Indexes.Count() - 1 Do
		If TypeOf(Source) = Type("QuerySchemaAvailableTables") Then
			Source = Source.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaSources") Then
			Source = Source.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaSource") Then
			Source = Source.Source.AvailableFields.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaAvailableTablesGroup") Then
			Source = Source.Content.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaAvailableTable") Then
			Source = Source.Fields.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaAvailableNestedTable") Then
			Source = Source.Fields.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaAvailableField") Then
			Source = Source.Fields.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaAvailableFields") Then
			Source = Source.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaTable") Then
			Source = Source.AvailableFields.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaNestedQuery") Then
			Source = Source.AvailableFields.Get(Indexes[Pos]);
		ElsIf TypeOf(Source) = Type("QuerySchemaTempTableDescription") Then
			Source = Source.AvailableFields.Get(Indexes[Pos]);
		Else
			Return Undefined;
		EndIf;
	EndDo;
	Return Source;
EndFunction

/////////////////
Function GetPictureForSource(Val TableName, 
							 Val SourcesImagesCacheAddress,
							 Val IsNestedTableRet = Undefined, 
							 Val ParentItemPicture = Undefined,                          
							 Val TablesGroup = False)  Export
	Var SourcesImagesCache;
	Var SourceTableImage;
	Var TmpTableName;
	Var Pos;
	Var N;
	Var SourceTypes;
	Var Image;
	Var Pos2;
	Var Pos1;
	Var SourceType;
	Var F;
	Var IsSourcesImagesCacheChanged;
	
	IsSourcesImagesCacheChanged = False;
	SourceTypes = Undefined;
	If SourcesImagesCacheAddress <> Undefined Then
		SourcesImagesCache = GetFromTempStorage(SourcesImagesCacheAddress);
	EndIf;

	If SourcesImagesCache <> Undefined Then
		SourceTypes = SourcesImagesCache.Get("SourceTypes_");

		SourceTableImage = SourcesImagesCache.Get(TableName);
		If SourceTableImage <> Undefined Then
			IsNestedTableRet = SourceTableImage["IsNestedTableRet"];
			ParentItemPicture = SourceTableImage["ParentItemPicture"];
			Return SourceTableImage["Image"];
		EndIf;
	EndIf;

	If IsNestedTableRet <> Undefined Then
		IsNestedTableRet = False;
	EndIf;

	Image = -1;
	Pos = Find(TableName, ".Cube.") + Find(TableName, ".Куб.");
	If Pos > 0 Then
		ParentItemPicture = 14;
		Image = 36;
	EndIf;

	If TypeOf(SourceTypes) <> Type("Array") Then
		SourceTypes = New Array;

		AddSourceType(SourceTypes, "Catalog.", 1,, "Catalogs");
		AddSourceType(SourceTypes, "Справочник.", 1,, "Справочники");

		AddSourceType(SourceTypes, "Document.", 2,, "Documents");
		AddSourceType(SourceTypes, "Документ.", 2,, "Документы");

		AddSourceType(SourceTypes, "FilterCriterion.", 37,, "FilterCriteria");
		AddSourceType(SourceTypes, "КритерийОтбора.", 37,, "КритерииОтбора");

		AddSourceType(SourceTypes, ".Recalculation", 34, True, "Recalculations", 0);
		AddSourceType(SourceTypes, ".РегистрРасчета", 34, True, "Перерасчеты", 0);

		AddSourceType(SourceTypes, "CalculationRegister.", 8, True, "CalculationRegisters");
		AddSourceType(SourceTypes, "РегистрРасчета.", 8, True, "РегистрыРасчета");

		AddSourceType(SourceTypes, "InformationRegister.", 3, True, "InformationRegisters");
		AddSourceType(SourceTypes, "РегистрСведений.", 3, True, "РегистрыСведений");

		AddSourceType(SourceTypes, "AccumulationRegister.", 6, True, "AccumulationRegisters");
		AddSourceType(SourceTypes, "РегистрНакопления.", 6, True, "РегистрыНакопления");

		AddSourceType(SourceTypes, "Report.", 15,, "Reports");
		AddSourceType(SourceTypes, "Отчет.", 15,, "Отчеты");

		AddSourceType(SourceTypes, "DataProcessor.", 11, , "DataProcessors");
		AddSourceType(SourceTypes, "Обработка.", 11, , "Обработки");

		AddSourceType(SourceTypes, "Enum.", 13,, "Enums");
		AddSourceType(SourceTypes, "Перечисление.", 13,, "Перечисления");

		AddSourceType(SourceTypes, "Constant.", 10,, "Constants");
		AddSourceType(SourceTypes, "Константа.", 10,, "Константы");
		AddSourceType(SourceTypes, "Константы (Изменения)", 10,, "Constants (Changes)");

		AddSourceType(SourceTypes, "DocumentJournal.", 12,, "DocumentJournals");
		AddSourceType(SourceTypes, "ЖурналДокументов.", 12,, "ЖурналыДокументов");

		AddSourceType(SourceTypes, "ChartOfCharacteristicTypes.", 4,, "ChartsOfCharacteristicTypes");
		AddSourceType(SourceTypes, "ПланВидовХарактеристик.", 4,, "ПланыВидовХарактеристик");

		AddSourceType(SourceTypes, "ExternalDataSource.", 35, True, "ExternalDataSources",, 14);
		AddSourceType(SourceTypes, "ВнешнийИсточникДанных.", 35, True, "ВнешнийИсточникДанных",, 14);

		AddSourceType(SourceTypes, "AccountingRegister.", 5, True, "AccountingRegisters");
		AddSourceType(SourceTypes, "РегистрБухгалтерии.", 5, True, "РегистрыБухгалтерии");

		AddSourceType(SourceTypes, "Task.", 16, True, "Tasks");
		AddSourceType(SourceTypes, "Задача.", 16, True, "Задачи");

		AddSourceType(SourceTypes, "ChartOfAccounts.", 32, True, "ChartsOfAccounts");
		AddSourceType(SourceTypes, "ПланСчетов.", 32, True, "ПланыСчетов");

		AddSourceType(SourceTypes, "ChartOfCalculationTypes.", 9,, "ChartsOfCalculationTypes");
		AddSourceType(SourceTypes, "ПланВидовРасчета.", 9,, "ПланыВидовРасчета");

		AddSourceType(SourceTypes, "ExchangePlan.", 31, True, "ExchangePlans");
		AddSourceType(SourceTypes, "ПланОбмена.", 31, True, "ПланыОбмена");

		AddSourceType(SourceTypes, "BusinessProcess.", 7, True, "BusinessProcesses");
		AddSourceType(SourceTypes, "БизнесПроцесс.", 7, True, "БизнесПроцессы");

		AddSourceType(SourceTypes, "Sequence.", 28, True, "Sequences");
		AddSourceType(SourceTypes, "Последовательность.", 28, True, "Последовательности");

		AddSourceType(SourceTypes, " ", 20, True, NStr("ru='Временные таблицы'; SYS='QueryEditor.TemporaryTables'", "ru")); // добавить NSTr

		AddSourceType(SourceTypes, "NestedTable", 29);
		AddSourceType(SourceTypes, "NestedQuery", 21);
		AddSourceType(SourceTypes, "TempTable", 18);

		If SourcesImagesCache <> Undefined Then
			SourcesImagesCache.Insert("SourceTypes_", SourceTypes);
			IsSourcesImagesCacheChanged = True;
		EndIf;
	EndIf;

	If Image < 0 Then
		Pos1 = Find(TableName, ".Changes");
		Pos2 = Find(TableName, ".Изменения");
		If (Pos1 > 0) OR (Pos2 > 0) Then
			If (Pos1 = StrLen(TableName) - StrLen(".Changes") + 1)
				OR (Pos2 = StrLen(TableName) - StrLen(".Изменения") + 1) Then
				Image = 33;
			EndIf;
		EndIf;
	EndIf;
	
	TmpTableName = TableName;
	Pos = Find(TmpTableName, ".");
	N = 0;
	While Find(TmpTableName, ".") Do
		TmpTableName = Mid(TmpTableName, Pos + 1, StrLen(TmpTableName));
		Pos = Find(TmpTableName, ".");
		N = N + 1;
	EndDo;

	If Image < 0 Then
		For Each SourceType In SourceTypes Do
			If (SourceType["Equival"] <> "")
				AND (TableName = SourceType["Equival"]) Then

				ParentItemPicture = SourceType["ParentItemPicture"];
				Image = SourceType["Image"];
				Break;
			EndIf;

			F = Find(TableName, SourceType["Name"]);
			If ((F > 0) AND (F = SourceType["StartPos"]))
				OR ((F > 0) AND (SourceType["StartPos"] = 0)) Then

				If (N >= 2)
					AND (SourceType["HaveNested"] = False) Then

					If IsNestedTableRet <> Undefined Then
						IsNestedTableRet = True;
					EndIf;
					Image = 29; // для вложенной таблицы
					Break;
				Else
					ParentItemPicture = SourceType["ParentItemPicture"];
					Image = SourceType["Image"];
					Break;
				EndIf;

			EndIf;
		EndDo;
	EndIf;

	If Image < 0 Then
		Pos = Find(TableName, ".");
		If (Pos = 0) AND (StrLen(TmpTableName) > 0) Then // для временной таблицы
			If NOT(TablesGroup) Then
				Image = 17;  // это для временной таблицы
			Else
				Image = 14; // а это для группы внешнего источника
			EndIf;
		EndIf;
	EndIf;

	If SourcesImagesCache <> Undefined Then
		SourceTableImage = New Structure;
		SourceTableImage.Insert("Image", Image);
		SourceTableImage.Insert("IsNestedTableRet", IsNestedTableRet);
		SourceTableImage.Insert("ParentItemPicture", ParentItemPicture);

		SourcesImagesCache.Insert(TableName, SourceTableImage);
		IsSourcesImagesCacheChanged = True;
	EndIf;
	
	If IsSourcesImagesCacheChanged Then
		PutToTempStorage(SourcesImagesCache, SourcesImagesCacheAddress);	    			
	EndIf; 
	
	Return Image;
EndFunction

Procedure AddSourceType(Val SourceTypes, 
						Val Name, 
						Val Image, 
						Val HaveNested = False, 
						Val Equival = "", 
						Val StartPos = 1, 
						Val ParentItemPicture = Undefined)
	Var Item;
                
	Item = New Structure;
	Item.Insert("Name", Name);
	Item.Insert("Image", Image);
	Item.Insert("HaveNested", HaveNested);
	Item.Insert("Equival", Equival);
	Item.Insert("StartPos", StartPos);
	Item.Insert("ParentItemPicture", ParentItemPicture);

	SourceTypes.Add(Item);
EndProcedure

Function GetPictureForAvailableField(Val Field, 
									 Val ExpressionsImagesCacheAddress,
									 Val Query = Undefined, 
									 Val Operator = Undefined) Export
	Var ExpressionsImagesCache;
	Var Presentation;
	Var ExpressionImage;
	Var F;
	Var Count;
	Var Pos;
	Var Alias;
	Var Source;
	Var ExpressionString;
	Var ExpressionItem;
	Var Image;
	Var Fields;
	Var Fld;
	
	If TypeOf(Field) = Type("QuerySchemaExpression")  Then
		Presentation = String(Field);

		// пробуем найти в кэше
		If ExpressionsImagesCacheAddress <> Undefined Then
			ExpressionsImagesCache = GetFromTempStorage(ExpressionsImagesCacheAddress);
			ExpressionImage = ExpressionsImagesCache.Get(Presentation);
			If ExpressionImage <> Undefined Then
				Return ExpressionImage;
			EndIf;
		EndIf;

		// поиск выражения в доступных полях
		If Find(Presentation, " ")
			OR Find(Presentation, "(")
			OR Find(Presentation, "+")
			OR Find(Presentation, "-") Then
		    	Return 30;
		EndIf;

		F = Find(Presentation, ".");
		Alias = Mid(Presentation, 0, F - 1);
		ExpressionString = Mid(Presentation, F + 1, StrLen(Presentation));
		Count = Operator.Sources.Count();
		For Pos = 0 To Count - 1 Do
			Source = Operator.Sources.Get(Pos).Source;
			If Source.Alias = Alias Then
				ExpressionItem = FindExpression(ExpressionString, Source.AvailableFields);
				If ExpressionItem <> Undefined Then
					Image = GetPictureForAvailableField(ExpressionItem, ExpressionsImagesCacheAddress);
					If ExpressionsImagesCache <> Undefined Then
			        	ExpressionsImagesCache.Insert(Presentation, Image);
						PutToTempStorage(ExpressionsImagesCache, ExpressionsImagesCacheAddress);
					EndIf;
					Return Image;
				Else
					Break;
				EndIf;
			EndIf;
		EndDo;
	ElsIf TypeOf(Field) = Type("QuerySchemaColumn")  Then
		// для псевдонима
		Fields = Field.Fields;
		Count = Fields.Count();
		For Pos = 0 To Count - 1 Do
			Fld = Fields.Get(Pos);
			If (TypeOf(Fld) = Type("QuerySchemaExpression"))
				OR (TypeOf(Fld) = Type("QuerySchemaNestedTable")) Then
				Return GetPictureForAvailableField(Fld, ExpressionsImagesCacheAddress, Query, Query.Operators.Get(Pos));
			EndIf;
		EndDo;
	ElsIf TypeOf(Field) = Type("QuerySchemaAvailableField") Then
		If Field.Role.Dimension Then
			Return 27;
		ElsIf Field.Role.Resource Then
			Return 23;
		EndIf;
	ElsIf TypeOf(Field) = Type("QuerySchemaNestedTableColumn")
		OR TypeOf(Field) = Type("QuerySchemaAvailableNestedTable")
		OR TypeOf(Field) = Type("QuerySchemaNestedTable") Then

		Return 29;
	EndIf;

	Return 22;
EndFunction

Function FindExpression(Val ExpressionString, 
						Val AvailableFields)
	Var F;
	Var Count;
	Var Pos;
	Var Field;
	Var Alias;
	Var Expression;

	F = Find(ExpressionString, ".");
	Alias = Mid(ExpressionString, 0, F - 1);
	If F > 0 Then
		Expression = Mid(ExpressionString, F + 1, StrLen(ExpressionString));
	Else
		Expression = "";
	EndIf;

	Count = AvailableFields.Count();
	For Pos = 0 To Count - 1 Do
		Field = AvailableFields.Get(Pos);
		If Field.Name = Alias Then
			If Expression = "" Then
				Return Field;
			Else
				Return FindExpression(Expression, Field.Fields);
			EndIf;
		EndIf;
	EndDo;
EndFunction

// быстрая сортировка
Procedure qSort(Collection, Field, low = Undefined, high = Undefined) Export
	Var j;
	Var i;
	Var m;
	
	If (low = Undefined) OR (high = Undefined) Then
		low = 0;
		high = Collection.Count() - 1;
	EndIf;

	If (Collection.Count() = 0) OR (Collection.Count() = 1) Then
		Return;
	EndIf;

    i = low;
	j = high;
	m = Collection[(i + j) / 2];

	While i <= j Do
		While Collection[i][Field] < m[Field] Do i = i + 1 EndDo;
		While Collection[j][Field] > m[Field] Do j = j - 1 EndDo;
		If i <= j Then
			If i <> j Then
				Collection.Move(j, i - j);
				Collection.Move(i + 1, j - i - 1);
			EndIf;
			i = i + 1;
			j = j - 1;
		EndIf;
	EndDo;

	If low < j Then
		qSort(Collection, Field, low, j);
	EndIf;

	If i < high Then
		qSort(Collection, Field, i, high);
	EndIf;
EndProcedure

/////////////////
Function GetName(Val Type, 
				 Val Item)
	Var ParentItem;
	Var ParentPresentation;
	Var ItemPresentation;
	Var Name;

	Name = "";
	If Type = 1 Then // Если таблица
		ParentItem = Item.GetParent();
		ItemPresentation = StrReplace(Item["Presentation"], ".", "");
		If ParentItem <> Undefined Then
			ParentPresentation = StrReplace(ParentItem["Presentation"], ".", "");
			If ParentItem["Type"] >= 0 Then
				Name = ParentPresentation + "." + ItemPresentation;
			Else
				Name = ItemPresentation;
			EndIf;
		Else
			Name = ItemPresentation;
		EndIf;
	ElsIf Type = 2  Then // Если поле
		Name = GetFieldName(Item, 3);
		If Name = "" Then
			Name = Item["Presentation"];
		EndIf;
	EndIf;
	Return Name;
EndFunction

Function GetFieldName(Val Item, 
					  Val Type = 1)
	Var ParentItem;
	Var ParentItemPresentation;
	Var Name;

	ParentItem = Item.GetParent();
	If ParentItem = Undefined Then
		Return "";
	EndIf;

	If Item["Type"] <> 2 Then
		Name = StrReplace(Item["Presentation"], ".", "");
	Else
		Name = Item["Presentation"];
	EndIf;

	If ParentItem["Type"] <> 2 Then
		If Find(ParentItem["Name"], ".") = 0 Then
			ParentItemPresentation = "";
		Else
			ParentItemPresentation = StrReplace(ParentItem["Presentation"], ".", "");
		EndIf;
	Else
		ParentItemPresentation = ParentItem["Presentation"];
	EndIf;

	If ParentItem["Type"] <> 1 Then
		ParentItemPresentation = GetFieldName(ParentItem, Type);
		If ParentItemPresentation = "" Then
			ParentItemPresentation = ParentItem["Name"];
		EndIf;

		Name = ParentItemPresentation + "." + Name;
	Else
		If Type = 3 Then
			Name = ParentItem["Name"] + "." + Name;
		Else
			If ParentItemPresentation <> "" Then
				Name = ParentItemPresentation + "." + Name;
			EndIf;
		EndIf;
	EndIf;
	Return Name;
EndFunction