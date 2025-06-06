
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления();
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;
	Описание.ПоддерживаетсяПсевдонимыПолей = Истина;
	Описание.ИмяВТДляСКД = "Представления_Периоды";
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Описание.Поля.Добавить(Поле);
	Поле.Имя = "Период";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Имя = "НачалоИнтервала";
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Дата");
	Параметр.Обязательный = Истина;
	Параметр.ДопустимПараметрЗапроса = Истина;
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Имя = "ОкончаниеИнтервала";
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Дата");
	Параметр.Обязательный = Истина;
	Параметр.ДопустимПараметрЗапроса = Истина;
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Имя = "Периодичность";
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Строка");
	Параметр.Обязательный = Ложь;
	Параметр.ДопустимПараметрЗапроса = Ложь;
	Параметр.ЗначениеПоУмолчанию = "МЕСЯЦ";
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Имя = "ИспользоватьКонецПериода";
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.Обязательный = Ложь;
	Параметр.ДопустимПараметрЗапроса = Ложь;
	Параметр.ЗначениеПоУмолчанию = Ложь;
	
	Возврат Описание;	
КонецФункции

Функция Справка() Экспорт
	Справка = ЭлементыМоделиОписанияПредставлений.НовыйСправка();	
	Справка.Имя = ИмяПредставления();
	Справка.Описание = "Обеспечивает доступ к методу ""ЗарплатаКадрыОбщиеНаборыДанных.СоздатьВТПериоды"".
	|Позволяет получить таблицу дат в диапазоне от начала до окончания интервала, указанного в параметрах. 
	|Периодичность также задается в параметрах (ДЕНЬ, МЕСЯЦ, ГОД)";
	
	Возврат Справка;
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.Периоды";
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
	НачалоИнтервала = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты("НачалоИнтервала", ПараметрыВыполнения, Запрос.Параметры);
	ОкончаниеИнтервала = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты("ОкончаниеИнтервала", ПараметрыВыполнения, Запрос.Параметры);
	Периодичность = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты("Периодичность", ПараметрыВыполнения, Запрос.Параметры, Истина);
	ИспользоватьКонецПериода = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты("ИспользоватьКонецПериода", ПараметрыВыполнения, Запрос.Параметры, Истина);
		
	ИмяПоляПериод = ПараметрыВыполнения.ПсевдонимыПолей.Получить("Период");
	Если ИмяПоляПериод = Неопределено Тогда
		ИмяПоляПериод = "Период";
	КонецЕсли;
	
	ЗарплатаКадрыОбщиеНаборыДанных.СоздатьВТПериоды(
		Запрос.МенеджерВременныхТаблиц, 
		НачалоИнтервала, 
		ОкончаниеИнтервала,
		Периодичность,
		ИмяПоляПериод, 
		ПараметрыВыполнения.ИмяВТРезультат, 
		ИспользоватьКонецПериода);	
		
	Возврат Неопределено;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТабуляции) Экспорт
	Утилиты = ГенерацияИсполняемогоКодаПредставленийУтилиты;
	
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	УстанавливаемыеПараметры = Новый Структура();
	УстанавливаемыеПараметры.Вставить("НачалоИнтервала", "НачалоИнтервала");
	УстанавливаемыеПараметры.Вставить("ОкончаниеИнтервала", "ОкончаниеИнтервала");
	УстанавливаемыеПараметры.Вставить("Периодичность", "Периодичность");
	УстанавливаемыеПараметры.Вставить("ИспользоватьКонецПериода", "ИспользоватьКонецПериода");
	
	Утилиты.КодПрисвоенияПараметровВТекстовыйДокумент(
		ТекстовыйДокумент, 
		ПараметрыВыполнения, 
		ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ИмяПредставления()), 
		УстанавливаемыеПараметры, 
		ТекущиеТабуляции,
		Истина);
	
	ИмяПоляПериод = ПараметрыВыполнения.ПсевдонимыПолей.Получить("Период");
	Если ИмяПоляПериод = Неопределено Тогда
		ИмяПоляПериод = "Период";
	КонецЕсли;
	
	Строка = "ИмяПоляПериод = " + Утилиты.ПримитивноеЗначениеВСтроку(ИмяПоляПериод) + ";";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = "ЗарплатаКадрыОбщиеНаборыДанных.СоздатьВТПериоды(
	|	Запрос.МенеджерВременныхТаблиц, 
	|	НачалоИнтервала, 
	|	ОкончаниеИнтервала,
	|	Периодичность,
	|	ИмяПоляПериод, 
	|	""" + ПараметрыВыполнения.ИмяВТРезультат + """, 
	|	ИспользоватьКонецПериода);";	
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
	
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
	УстанавливаемыеПараметры.Вставить("НачалоИнтервала", "НачалоИнтервала");
	УстанавливаемыеПараметры.Вставить("ОкончаниеИнтервала", "ОкончаниеИнтервала");
	УстанавливаемыеПараметры.Вставить("Периодичность", "Периодичность");
	УстанавливаемыеПараметры.Вставить("ИспользоватьКонецПериода", "ИспользоватьКонецПериода");
	
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
