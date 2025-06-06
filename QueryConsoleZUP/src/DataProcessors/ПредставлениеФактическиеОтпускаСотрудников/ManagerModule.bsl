
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления(); 
	
	Описание.ПоддерживаютсяИндексы = Ложь;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина; 
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ИмяВТДляСКД = "Представления_ФактическиеОтпускаСотрудников";  
	
	Описание.ОписаниеВТФильтр =  ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр();
	Описание.ОписаниеВТФильтр.Обязательный = Ложь; 
	
	Описание.ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр = Истина;   
	Описание.ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы = Истина;
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Сотрудник";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Сотрудники");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВидЕжегодногоОтпуска";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ВидыОтпусков");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДатаНачала";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДатаОкончания";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "КоличествоДней";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ЭтоКомпенсация";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Регистратор";
	Поле.ТипЗначения = Метаданные.РегистрыНакопления.ФактическиеОтпуска.СтандартныеРеквизиты.Регистратор.Тип;
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВРабочихДнях";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РабочийПериодС";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РабочийПериодПо";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Основание";
	Поле.ТипЗначения = Новый ОписаниеТипов("Строка");
	Описание.Поля.Добавить(Поле);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "Сотрудник";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "НачалоПериода";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "ОкончаниеПериода";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	Возврат Описание;	
КонецФункции

Функция Справка() Экспорт
	Справка = ЭлементыМоделиОписанияПредставлений.НовыйСправка();	
	Справка.Имя = ИмяПредставления();
	Справка.Описание = "Обеспечивает доступ к методу ""ОстаткиОтпусков.СоздатьВТФактическиеОтпускаСотрудников"".
	|Позволяет получить информацию о фактических отпусках сотрудников.";
	
	Возврат Справка;
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.ФактическиеОтпускаСотрудников";
КонецФункции

Функция Исполнить(ПараметрыВыполнения, Запрос) Экспорт
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	
	ИмяПоляСотрудник = ОписаниеФильтра.ПсевдонимыПолей.Получить("Сотрудник");
	ИмяПоляНачалоПериода = ОписаниеФильтра.ПсевдонимыПолей.Получить("НачалоПериода");
	ИмяПоляОкончаниеПериода = ОписаниеФильтра.ПсевдонимыПолей.Получить("ОкончаниеПериода");
	
	ИменаПолейФильтра = ИмяПоляСотрудник + "," + ИмяПоляНачалоПериода + "," +  ИмяПоляОкончаниеПериода;
	
	ОписательВТ = ОстаткиОтпусков.ОписательВременныхТаблицДляСоздатьВТФактическиеОтпускаСотрудников(
		Запрос.МенеджерВременныхТаблиц, 
		ОписаниеФильтра.ИмяВТ,
		ИменаПолейФильтра,
		ПараметрыВыполнения.ИмяВТРезультат);
	
	ОстаткиОтпусков.СоздатьВТФактическиеОтпускаСотрудников(ОписательВТ, ПараметрыВыполнения.ТолькоРазрешенные);
		
	Возврат Неопределено;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТабуляции) Экспорт
	Утилиты = ГенерацияИсполняемогоКодаПредставленийУтилиты;
	
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	
	ИмяПоляСотрудник = ОписаниеФильтра.ПсевдонимыПолей.Получить("Сотрудник");
	ИмяПоляНачалоПериода = ОписаниеФильтра.ПсевдонимыПолей.Получить("НачалоПериода");
	ИмяПоляОкончаниеПериода = ОписаниеФильтра.ПсевдонимыПолей.Получить("ОкончаниеПериода");
	
	Строка = "ИменаПолейФильтра = """ + ИмяПоляСотрудник + "," + ИмяПоляНачалоПериода + "," +  ИмяПоляОкончаниеПериода + """;
	|
	|ОписательВТ = ОстаткиОтпусков.ОписательВременныхТаблицДляСоздатьВТФактическиеОтпускаСотрудников(
	|	Запрос.МенеджерВременныхТаблиц, 
	|	""" + ОписаниеФильтра.ИмяВТ + """,
	|	ИменаПолейФильтра,
	|	""" + ПараметрыВыполнения.ИмяВТРезультат + """);
	|
	|ОстаткиОтпусков.СоздатьВТФактическиеОтпускаСотрудников(ОписательВТ, " 
		+ Утилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ТолькоРазрешенные) + ");";
		
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);	
	Возврат ТекстовыйДокумент.ПолучитьТекст();
КонецФункции

Функция ТекстЗапросаДляСКД(ПараметрыВыполнения) Экспорт
	Описание = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ПараметрыВыполнения.ИмяИсполняемогоПредставления);
	
	Модель = ГенерацияИсполняемогоКодаПредставленийУтилиты.МодельЗапросаДляСКД(ПараметрыВыполнения, Описание);
	Построитель = МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель);
	
	Запрос = Построитель.ПолучитьМодель().Элементы[0];
	ТекстЗапроса = ГенерацияТекстовЗапросов.ТекстЗапросаВыбора(Запрос);
	Возврат ТекстЗапроса;
КонецФункции

#КонецОбласти

#КонецЕсли
