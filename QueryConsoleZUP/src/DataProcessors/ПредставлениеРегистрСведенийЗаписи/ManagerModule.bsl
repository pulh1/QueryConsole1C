
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание(ИмяРегистра) Экспорт
	МетаданныеРегистра = Метаданные.РегистрыСведений.Найти(ИмяРегистра);
	
	Если МетаданныеРегистра = Неопределено
		Или МетаданныеРегистра.ПериодичностьРегистраСведений = Метаданные.СвойстваОбъектов.ПериодичностьРегистраСведений.Непериодический Тогда
			
		Возврат Неопределено;
	КонецЕсли;
	
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления(ИмяРегистра);
	
	ПоляРегистра = ПредставленияРегистровСведенийУтилиты.ДостныеПоляРегистраСведений(МетаданныеРегистра);
  
	Описание.ПоддерживаютсяИндексы = Истина; 
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;  
	Описание.ПоддерживаетсяПолучениеРезультатаЗапроса = Истина;;
	Описание.ПоддерживаетсяПсевдонимыПолей = Истина;
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ИмяВТДляСКД = "Представления_ТаблицаРегистра_" + ИмяРегистра;
		
	Для Каждого Поле Из ПоляРегистра Цикл
		Описание.Поля.Добавить(Поле);
	КонецЦикла;	
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПериодЗаписи";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата"); 
	Описание.Поля.Добавить(Поле);
	
	Если МетаданныеРегистра.РежимЗаписи = Метаданные.СвойстваОбъектов.РежимЗаписиРегистра.ПодчинениеРегистратору Тогда
		Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
		Поле.Имя = "Регистратор";
		Поле.ТипЗначения = МетаданныеРегистра.СтандартныеРеквизиты.Регистратор.Тип; 
		Описание.Поля.Добавить(Поле);
	КонецЕсли;
		
	ПоляФильтра = ПредставленияРегистровСведенийУтилиты.ИзмеренияРегистраСведений(МетаданныеРегистра);  
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра(); 
	Поле.Имя = "ДатаНачала"; 
	Поле.Обязательный = Истина;
	ПоляФильтра.Вставить(0, Поле); 
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра(); 
	Поле.Имя = "ДатаОкончания"; 
	Поле.Обязательный = Истина;
	ПоляФильтра.Вставить(1, Поле);
	
	Описание.ОписаниеВТФильтр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр();
	
	Описание.ОписаниеВТФильтр.Обязательный = Истина; 
	
	Описание.ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы = Истина;
	Описание.ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр = Истина;   
	Описание.ОписаниеВТФильтр.ПоддерживаниетсяТЗФильтр = Истина; 	 
	Описание.ОписаниеВТФильтр.ПоляФильтра = ПоляФильтра; 
	
	ПараметрФормироватьСПериодичностьДень = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(ПараметрФормироватьСПериодичностьДень);

	ПараметрФормироватьСПериодичностьДень.Обязательный = Ложь;
	ПараметрФормироватьСПериодичностьДень.Имя = "ФормироватьСПериодичностьДень"; 
	ПараметрФормироватьСПериодичностьДень.ДопустимПараметрЗапроса = Ложь;; 
	ПараметрФормироватьСПериодичностьДень.ТипКонстанты = Новый ОписаниеТипов("Булево");
	ПараметрФормироватьСПериодичностьДень.ЗначениеПоУмолчанию = Истина;
		
	ПараметрВключатьЗаписиНаНачалоПериода = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(ПараметрВключатьЗаписиНаНачалоПериода);

	ПараметрВключатьЗаписиНаНачалоПериода.Обязательный = Ложь;
	ПараметрВключатьЗаписиНаНачалоПериода.Имя = "ВключатьЗаписиНаНачалоПериода"; 
	ПараметрВключатьЗаписиНаНачалоПериода.ДопустимПараметрЗапроса = Ложь;  
	ПараметрВключатьЗаписиНаНачалоПериода.ТипКонстанты = Новый ОписаниеТипов("Булево");	
	ПараметрФормироватьСПериодичностьДень.ЗначениеПоУмолчанию = Ложь;
		
	Для Каждого Ресурс Из МетаданныеРегистра.Ресурсы Цикл
		ОписаниеОтбора = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеОтбора();
		ОписаниеОтбора.Поле = Ресурс.Имя;
		ОписаниеОтбора.ДоступенДляСКД = Ложь;
		ОписаниеОтбора.ДоступноРазыменование = Истина;
		
		Описание.ДоступныеОтборы.Добавить(ОписаниеОтбора);	
	КонецЦикла;
	
	Для Каждого Реквизит Из МетаданныеРегистра.Реквизиты Цикл
		ОписаниеОтбора = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеОтбора();
		ОписаниеОтбора.Поле = Реквизит.Имя;
		ОписаниеОтбора.ДоступенДляСКД = Ложь;
		ОписаниеОтбора.ДоступноРазыменование = Истина;;
		
		Описание.ДоступныеОтборы.Добавить(ОписаниеОтбора);	
	КонецЦикла;	
		
		
	Возврат Описание;
КонецФункции

Функция ИмяПредставления(ИмяРегистра) Экспорт
	Возврат "ИсполняемоеПредставление.РегистрСведений." + ИмяРегистра + ".Записи";
КонецФункции

// Исполнить.
// 
// Параметры:
//  ПараметрыВыполнения - см. ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления
//  Запрос - Запрос
// 
// Возвращаемое значение:
// 	- РезультатЗапроса 
Функция Исполнить(ПараметрыВыполнения, Запрос) Экспорт
	ЧастиИмени = СтрРазделить(ПараметрыВыполнения.ИмяИсполняемогоПредставления, ".");
	ИмяРегистра = ЧастиИмени[ЧастиИмени.ВГраница() - 1];
	
	ВТФильтр = ПараметрыВыполнения.ОписаниеВТФильтр;
	Измерения = Новый Массив();
	Для Каждого КлючЗначение Из ВТФильтр.ПсевдонимыПолей Цикл
		Если ВРег(КлючЗначение.Ключ) <> "ПЕРИОД" Тогда
			Измерения.Добавить(КлючЗначение.Ключ);
		КонецЕсли;
	КонецЦикла;
		
	ОписаниеВТФильтр = ЗарплатаКадрыПериодическиеРегистры.ОписаниеФильтраДляСоздатьВТИмяРегистраПоВременнойТаблице(
		ВТФильтр.ИмяВТ,
		Измерения	
	);	
	ОписаниеВТФильтр.СоответствиеИзмеренийРегистраИзмерениямФильтра = ВТФильтр.ПсевдонимыПолей;
	
	ПараметрыПостроения = ЗарплатаКадрыПериодическиеРегистры.ПараметрыПостроенияДляСоздатьВТИмяРегистра();
	ПараметрыПостроения.ИндексироватьПо = ПараметрыВыполнения.Индексы;
	
	ПараметрФормироватьСПериодичносьюДень = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("ФормироватьСПериодичностьДень");
	Если ПараметрФормироватьСПериодичносьюДень <> Неопределено Тогда
		ПараметрыПостроения.ФормироватьСПериодичностьДень = ПараметрФормироватьСПериодичносьюДень.Значение;
	КонецЕсли;
	
	ПараметрВключатьЗаписиНаНачалоПериода= ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("ВключатьЗаписиНаНачалоПериода");
	Если ПараметрВключатьЗаписиНаНачалоПериода <> Неопределено Тогда
		ПараметрыПостроения.ВключатьЗаписиНаНачалоПериода = ПараметрВключатьЗаписиНаНачалоПериода.Значение;
	КонецЕсли;
	
	ИсполнительПредставленийЗУПУтилиты.ЗаполнитьКоллекциюОтборов(
		ПараметрыПостроения.Отборы, 
		ПараметрыВыполнения.Отборы, 
		Запрос.Параметры);
	
	Если ПараметрыПостроения.ВключатьЗаписиНаНачалоПериода Тогда
		ПараметрыПостроения.ОтборыЗаписейНаНачалоПериода = Новый Массив();
		ИсполнительПредставленийЗУПУтилиты.ЗаполнитьКоллекциюОтборов(
			ПараметрыПостроения.ОтборыЗаписейНаНачалоПериода, 
			ПараметрыВыполнения.Отборы, 
			Запрос.Параметры);
	КонецЕсли;
	
	ПараметрыПостроения.СоответствиеПсевдонимовПолей = ПараметрыВыполнения.ПсевдонисыПолей;
	ПараметрыПостроения.ИндексироватьПо = ПараметрыВыполнения.Индексы;
	
	Если ЗначениеЗаполнено(ПараметрыВыполнения.ИмяВТРезультат) Тогда
		ЗарплатаКадрыПериодическиеРегистры.СоздатьВТИмяРегистра(
			ИмяРегистра, 
			Запрос.МенеджерВременныхТаблиц,
			ПараметрыВыполнения.ТолькоРазрешенные, 
			ОписаниеВТФильтр,
			ПараметрыПостроения,
			ПараметрыВыполнения.ИмяВТРезультат);
		
		Возврат Неопределено;
	Иначе
		ЗапросСреза = ЗарплатаКадрыПериодическиеРегистры.ЗапросВТИмяРегистра(
			ИмяРегистра,
			ПараметрыВыполнения.ТолькоРазрешенные, 
			ОписаниеВТФильтр, 
			ПараметрыПостроения, 
			"");
		
		ЗапросСреза.МенеджерВременныхТаблиц = Запрос.МенеджерВременныхТаблиц;
		Возврат ЗапросСреза.Выполнить();	
	КонецЕсли;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, Знач ТекущиеТабуляции) Экспорт
	ЧастиИмени = СтрРазделить(ПараметрыВыполнения.ИмяИсполняемогоПредставления, ".");
	ИмяРегистра = ЧастиИмени[ЧастиИмени.ВГраница() - 1];
	
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	ВТФильтр = ПараметрыВыполнения.ОписаниеВТФильтр;
	
	Строка = "Измерения = Новый Массив();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	Строка = "СоответствиеИзмерений = Новый Соответствие();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Для Каждого КлючЗначение Из ВТФильтр.ПсевдонимыПолей Цикл
		Если ВРег(КлючЗначение.Ключ) <> "ПЕРИОД" Тогда
			Строка = "Измерения.Добавить(" + """" + КлючЗначение.Ключ + """);";
			ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		КонецЕсли;
		Строка = "СоответствиеИзмерений.Вставить(" + """" + КлючЗначение.Ключ + """, " + """" + КлючЗначение.Значение + """);";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	КонецЦикла;
//	МассивСтрок.ДобавитьСтроку(Символы.ПС);
	
	Строка = "ОписаниеВТФильтр = ЗарплатаКадрыПериодическиеРегистры.ОписаниеФильтраДляСоздатьВТИмяРегистраПоВременнойТаблице(";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + """" + ВТФильтр.ИмяВТ + """,");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + "Измерения);");
	
	Строка = "ОписаниеВТФильтр.СоответствиеИзмеренийРегистраИзмерениямФильтра = СоответствиеИзмерений;";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Строка = "ПараметрыПостроения = ЗарплатаКадрыПериодическиеРегистры.ПараметрыПостроенияДляСоздатьВТИмяРегистра();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	ТекстовыйДокумент.ДобавитьСтроку("");
	Строка = "ПараметрыПостроения.ИндексироватьПо = Новый Массив;";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	ГенерацияИсполняемогоКодаПредставленийУтилиты.КодЗаполненияКоллекцииИндексовВТекст(
		ТекстовыйДокумент, 
		"ПараметрыПостроения.ИндексироватьПо", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
	
	ТекстовыйДокумент.ДобавитьСтроку("");
	ГенерацияИсполняемогоКодаПредставленийУтилиты.КодЗаполненияПсевдонимовПолейВТекст(
		ТекстовыйДокумент, 
		"ПараметрыПостроения.СоответствиеПсевдонимовПолей", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);	
		
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисовенияПараметрыПеременной(
		"ПараметрыПостроения.ФормироватьСПериодичностьДень", 
		"ФормироватьСПериодичностьДень",
		ПараметрыВыполнения,
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисовенияПараметрыПеременной(
		"ПараметрыПостроения.ВключатьЗаписиНаНачалоПериода", 
		"ВключатьЗаписиНаНачалоПериода",
		ПараметрыВыполнения,
		ТекущиеТабуляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	ГенерацияИсполняемогоКодаПредставленийЗУПУтилиты.КодЗаполненияКоллекцииОтборовВМассивСтрок(
		ТекстовыйДокумент, 
		"ПараметрыПостроения.Отборы", 
		ПараметрыВыполнения.Отборы, 
		ТекущиеТабуляции);
	
	ПараметрВключатьЗаписиНаНачалоПериода= ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("ВключатьЗаписиНаНачалоПериода");
	Если ПараметрВключатьЗаписиНаНачалоПериода <> Неопределено 
		И ПараметрВключатьЗаписиНаНачалоПериода.Значение = Истина Тогда
		
		Строка = "ПараметрыПостроения.ОтборыЗаписейНаНачалоПериода = Новый Массив();";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		ГенерацияИсполняемогоКодаПредставленийЗУПУтилиты.КодЗаполненияКоллекцииОтборовВМассивСтрок(
			ТекстовыйДокумент, 
			"ПараметрыПостроения.ОтборыЗаписейНаНачалоПериода", 
			ПараметрыВыполнения.Отборы, 
			ТекущиеТабуляции);
	КонецЕсли;
	
	Если ЗначениеЗаполнено(ПараметрыВыполнения.ИмяВТРезультат) Тогда
		Строка = "ЗарплатаКадрыПериодическиеРегистры.СоздатьВТИмяРегистра(";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		Строка = """" + ИмяРегистра + """,";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + "Запрос.МенеджерВременныхТаблиц,");
		Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ТолькоРазрешенные) + ",";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + "ОписаниеВТФильтр,");
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + "ПараметрыПостроения,");
		Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ИмяВТРезультат) + ");";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
	Иначе
		Строка = "ЗапросЗаписи = ЗарплатаКадрыПериодическиеРегистры.ЗапросВТИмяРегистра(";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		Строка = """" + ИмяРегистра + """,";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ТолькоРазрешенные) + ",";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + "ОписаниеВТФильтр,");
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + "ПараметрыПостроения,");
		Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("") + ");";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Символы.Таб + Строка);
		Строка = "ЗапросЗаписи.МенеджерВременныхТаблиц = Запрос.МенеджерВременныхТаблиц;";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + "Возврат ЗапросЗаписи.Выполнить();");		
	КонецЕсли;
	
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
	ПараметрФормироватьСПериодичносьюДень = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("ФормироватьСПериодичностьДень");
	Если ПараметрФормироватьСПериодичносьюДень <> Неопределено Тогда
		ВыражениеПараметра = 
			ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ПараметрыПостроения_ФормироватьСПериодичностьДень") 
			+ " = "
			+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрФормироватьСПериодичносьюДень.Значение);
		
		Построитель.ДобавитьОтбор(ВыражениеПараметра);
	КонецЕсли; 
	
	ПараметрВключатьЗаписиНаНачалоПериода = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("ВключатьЗаписиНаНачалоПериода");
	Если ПараметрВключатьЗаписиНаНачалоПериода <> Неопределено Тогда
		ВыражениеПараметра = 
			ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ПараметрыПостроения_ВключатьЗаписиНаНачалоПериода") 
			+ " = "
			+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрВключатьЗаписиНаНачалоПериода.Значение);
		
		Построитель.ДобавитьОтбор(ВыражениеПараметра);
	КонецЕсли; 
	
	Запрос = Построитель.ПолучитьМодель().Элементы[0];
	ТекстЗапроса = ГенерацияТекстовЗапросов.ТекстЗапросаВыбора(Запрос);
	Возврат ТекстЗапроса;
КонецФункции

#КонецОбласти

#КонецЕсли
