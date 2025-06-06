
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления();
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;
	Описание.ИмяВТДляСКД = "Представления_СотрудникиОрганизации";
	
	Описание.Поля = ПредставленияКадровогоУчетаУтилиты.ОписаниеПолейКадровыхДанныхСотрудников();
	Для Индекс = 0 По Описание.Поля.ВГраница() Цикл
		Если Описание.Поля[Индекс].Имя = "Период" Тогда
			Описание.Поля.Удалить(Индекс);
			Прервать;
		КонецЕсли;
	КонецЦикла;
	
	Описание.ОписаниеВТФильтр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр();   
	Описание.ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы = Истина;
	Описание.ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр = Истина;   	
	Описание.ОписаниеВТФильтр.Обязательный = Ложь; 
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "ФизическоеЛицо";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Истина;
	Параметр.Имя = "Организация"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("СправочникСсылка.Организации");
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Истина;
	Параметр.Имя = "НачалоПериода"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Дата");
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "ОкончаниеПериода"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Дата");
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "Подразделение"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("СправочникСсылка.ПодразделенияОрганизаций");
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "ВключаяУволенныхНаНачалоПериода"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Ложь;
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "РаботникиПоТрудовымДоговорам"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Истина;
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "ПодработкиРаботниковПоТрудовымДоговорам"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Ложь;
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "РаботникиПоДоговорамГПХ"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Ложь;
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "ФормироватьСПериодичностьДень"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Истина;
	
	Возврат Описание;	
КонецФункции

Функция Справка() Экспорт
	Справка = ЭлементыМоделиОписанияПредставлений.НовыйСправка();	
	Справка.Имя = ИмяПредставления();
	Справка.Описание = "ИсполняемоеПредставление.СотрудникиОрганизации
	|Обеспечивает доступ к методу КадровыйУчет.СоздатьВТСотрудникиОрганизации.
	|Позволяет получить сотрудников организации (или подразделения), работающих на заданную дату или в заданном периоде.
	|Также позволяет получить данные о работающих сотрудниках в определенный момент времени.";
	
	Возврат Справка;
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.СотрудникиОрганизации";
КонецФункции

// Исполнить.
// 
// Параметры:
//  ПараметрыВыполнения - см. ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления
//  Запрос - Запрос
// 
// Возвращаемое значение:
// 	Произвольный 
Функция Исполнить(ПараметрыВыполнения, Запрос) Экспорт
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	
	ПараметрыПолученияДанных = КадровыйУчет.ПараметрыПолученияСотрудниковОрганизацийПоВременнойТаблице();
	
	Если ПараметрыВыполнения.ОписаниеВТФильтр = Неопределено Тогда
		ПараметрыПолученияДанных.ИмяВТФизическиеЛица = Неопределено;
	Иначе
		ИмяПоляФизическоеЛицо = ОписаниеФильтра.ПсевдонимыПолей.Получить("ФизическоеЛицо");
		ПараметрыПолученияДанных.ИмяВТФизическиеЛица = ПараметрыВыполнения.ОписаниеВТФильтр.ИмяВТ;
		ПараметрыПолученияДанных.ИмяПоляФизическоеЛицо = ИмяПоляФизическоеЛицо;
	КонецЕсли;
	
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметра(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		"Организация");	
		
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметра(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		"НачалоПериода");	
		
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметра(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		"ОкончаниеПериода");	
		
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметра(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		"Подразделение");	
		
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметра(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		"ВключаяУволенныхНаНачалоПериода");	
		
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметра(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		"РаботникиПоТрудовымДоговорам");	
		
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметра(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		"ПодработкиРаботниковПоТрудовымДоговорам");	
		
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметра(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		"РаботникиПоДоговорамГПХ");	
	
	ПараметрыПолученияДанных.КадровыеДанные = Новый Массив();	
	Для Каждого Поле Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		ПараметрыПолученияДанных.КадровыеДанные.Добавить(Поле.Ключ);
	КонецЦикла;
	
	КадровыйУчет.СоздатьВТСотрудникиОрганизации(
		Запрос.МенеджерВременныхТаблиц, 
		ПараметрыВыполнения.ТолькоРазрешенные, 
		ПараметрыПолученияДанных,
		ПараметрыВыполнения.ИмяВТРезультат);
		
	Возврат Неопределено;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТабуляции) Экспорт
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	
	Строка = "ПараметрыПолученияДанных = КадровыйУчет.ПараметрыПолученияСотрудниковОрганизацийПоВременнойТаблице();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Если ПараметрыВыполнения.ОписаниеВТФильтр = Неопределено Тогда
		Строка = "ПараметрыПолученияДанных.ИмяВТФизическиеЛица = Неопределено;";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	Иначе
		ИмяПоляФизическоеЛицо = ОписаниеФильтра.ПсевдонимыПолей.Получить("ФизическоеЛицо");
		Строка = "ПараметрыПолученияДанных.ИмяВТФизическиеЛица = " 
			+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ОписаниеВТФильтр.ИмяВТ) + ";";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		Строка = "ПараметрыПолученияДанных.ИмяПоляФизическоеЛицо = " 
			+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ИмяПоляФизическоеЛицо) + ";";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	КонецЕсли;
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ПараметрыПолученияДанных.Организация",
		"Организация", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ПараметрыПолученияДанных.НачалоПериода",
		"НачалоПериода", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ПараметрыПолученияДанных.ОкончаниеПериода",
		"ОкончаниеПериода", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ПараметрыПолученияДанных.Подразделение",
		"Подразделение", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ПараметрыПолученияДанных.ВключаяУволенныхНаНачалоПериода",
		"ВключаяУволенныхНаНачалоПериода", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ПараметрыПолученияДанных.РаботникиПоТрудовымДоговорам",
		"РаботникиПоТрудовымДоговорам", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ПараметрыПолученияДанных.ПодработкиРаботниковПоТрудовымДоговорам",
		"ПодработкиРаботниковПоТрудовымДоговорам", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ПараметрыПолученияДанных.РаботникиПоДоговорамГПХ",
		"РаботникиПоДоговорамГПХ", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = "ПараметрыПолученияДанных.КадровыеДанные = Новый Массив();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);	
	Для Каждого Поле Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		Строка = "ПараметрыПолученияДанных.КадровыеДанные.Добавить(" 
			+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(Поле.Ключ) + ");";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);	
	КонецЦикла;
	
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка  = "КадровыйУчет.СоздатьВТСотрудникиОрганизации(";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	Строка = "Запрос.МенеджерВременныхТаблиц,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ТолькоРазрешенные) + ",";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	Строка = "ПараметрыПолученияДанных,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ИмяВТРезультат) + ");";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	
	Возврат ТекстовыйДокумент.ПолучитьТекст();
КонецФункции

// Текст запроса для СКД.
// 
// Параметры:
//  ПараметрыВыполнения - см. ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления
// 
// Возвращаемое значение:
//  - Строка
Функция ТекстЗапросаДляСКД(ПараметрыВыполнения) Экспорт
	Описание = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ПараметрыВыполнения.ИмяИсполняемогоПредставления);
	
	Модель = ГенерацияИсполняемогоКодаПредставленийУтилиты.МодельЗапросаДляСКД(ПараметрыВыполнения, Описание);
	Построитель = МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель);
	
	УстанавливаемыеПараметры = Новый Структура();
	УстанавливаемыеПараметры.Вставить("Организация", "Организация");
	УстанавливаемыеПараметры.Вставить("НачалоПериода", "НачалоПериода");
	УстанавливаемыеПараметры.Вставить("ОкончаниеПериода", "ОкончаниеПериода");
	УстанавливаемыеПараметры.Вставить("Подразделение", "Подразделение");
	УстанавливаемыеПараметры.Вставить("ВключаяУволенныхНаНачалоПериода", "ВключаяУволенныхНаНачалоПериода");
	УстанавливаемыеПараметры.Вставить("РаботникиПоТрудовымДоговорам", "РаботникиПоТрудовымДоговорам");
	УстанавливаемыеПараметры.Вставить("ПодработкиРаботниковПоТрудовымДоговорам", "ПодработкиРаботниковПоТрудовымДоговорам");
	УстанавливаемыеПараметры.Вставить("РаботникиПоДоговорамГПХ", "РаботникиПоДоговорамГПХ");
	
	ГенерацияИсполняемогоКодаПредставленийУтилиты.УстановитьПараметраПредставленияВМодельЗапросаДляСКД(
		Построитель, 
		ПараметрыВыполнения, 
		Описание, 
		УстанавливаемыеПараметры);
	
	Запрос = Построитель.ПолучитьМодель().Элементы[0];
	ТекстЗапроса = ГенерацияТекстовЗапросов.ТекстЗапросаВыбора(Запрос);
	Возврат ТекстЗапроса;
КонецФункции

#КонецОбласти

#КонецЕсли
