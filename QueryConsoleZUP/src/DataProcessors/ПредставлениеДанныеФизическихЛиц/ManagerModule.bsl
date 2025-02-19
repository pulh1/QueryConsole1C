
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления();
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;
	Описание.ИмяВТДляСКД = "Представления_КадровыеДанныеФизическихЛиц";
	
	Описание.Поля = ПредставленияКадровогоУчетаУтилиты.ОписаниеПолейКадровыхДанныхФизическихЛиц();
	
	Описание.ОписаниеВТФильтр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр();   
	Описание.ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы = Истина;;
	Описание.ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр = Истина;   	 
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "ФизическоеЛицо";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	 
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "Период";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	Возврат Описание;	
КонецФункции

Функция Справка() Экспорт
	Справка = ЭлементыМоделиОписанияПредставлений.НовыйСправка();	
	Справка.Имя = ИмяПредставления();
	Справка.Описание = "Обеспечивает доступ к методу ""КадровыйУчет.СоздатьВТКадровыеДанныеФизическихЛиц"".
	|Позволяет получить данные физических лиц (ФИО, документы, образование и т.п.)";
	
	Возврат Справка;
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.ДанныеФизическихЛиц";
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
	ИмяВТФильтр = ОписаниеФильтра.ИмяВТ;
	ИмяВТРезультат = ПараметрыВыполнения.ИмяВТРезультат;
	
	Поля = Новый Массив();
	Для Каждого Поле Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		Поля.Добавить(Поле.Ключ);
	КонецЦикла;	
	
	ИменаПолейФильтра = ОписаниеФильтра.ПсевдонимыПолей.Получить("ФизическоеЛицо") + "," + 
		ОписаниеФильтра.ПсевдонимыПолей.Получить("Период");
	
	ОписаниеФильтра = КадровыйУчет.ОписательВременныхТаблицДляСоздатьВТКадровыеДанныеФизическихЛиц(
		Запрос.МенеджерВременныхТаблиц, 
		ИмяВТФильтр,
		ИменаПолейФильтра);	
	
	ОписаниеФильтра.ИмяВТКадровыеДанныеФизическихЛиц = ИмяВТРезультат;
	КадровыйУчет.СоздатьВТКадровыеДанныеФизическихЛиц(
		ОписаниеФильтра, 
		ПараметрыВыполнения.ТолькоРазрешенные, 
		Поля);
		
	Возврат Неопределено;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТабуляции) Экспорт
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	
	Строка = "Поля = Новый Массив();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Для Каждого Поле Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		Строка = "Поля.Добавить(""" + Поле.Ключ + """);";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	КонецЦикла;	
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияЗначения("ИмяВТФильтр", ОписаниеФильтра.ИмяВТ);
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ФормироватьСПериодичностьДень",
		"ФормироватьСПериодичностьДень", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	ИменаПолейФильтра = ОписаниеФильтра.ПсевдонимыПолей.Получить("ФизическоеЛицо") + "," + 
		ОписаниеФильтра.ПсевдонимыПолей.Получить("Период");
		
	Строка = "ИменаПолейФильтра = """ + ИменаПолейФильтра + """;"; 
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Строка  = "ОписаниеФильтра = КадровыйУчет.ОписательВременныхТаблицДляСоздатьВТКадровыеДанныеФизическихЛиц(";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	Строка = "Запрос.МенеджерВременныхТаблиц,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	Строка = "ИмяВТФильтр,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	Строка = "ИменаПолейФильтра);";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияЗначения(
		"ОписаниеФильтра.ИмяВТКадровыеДанныеФизическихЛиц", 
		ПараметрыВыполнения.ИмяВТРезультат);
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияЗначения(
		"ТолькоРазрешенные", 
		ПараметрыВыполнения.ТолькоРазрешенные);
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Строка  = "КадровыйУчет.СоздатьВТКадровыеДанныеФизическихЛиц(";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	Строка = "ОписаниеФильтра,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	Строка = "ТолькоРазрешенные,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	Строка = "Поля);";
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
	
	Запрос = Построитель.ПолучитьМодель().Элементы[0];
	ТекстЗапроса = ГенерацияТекстовЗапросов.ТекстЗапросаВыбора(Запрос);
	Возврат ТекстЗапроса;
КонецФункции

#КонецОбласти

#КонецЕсли