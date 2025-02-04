#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления();
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;
	Описание.ИмяВТДляСКД = "Представления_КадровыеДанныеСотрудников";
	
	Описание.Поля = ПредставленияКадровогоУчетаУтилиты.ОписаниеПолейКадровыхДанныхСотрудниоков();
	
	Описание.ОписаниеВТФильтр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр();   
	Описание.ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы = Истина;;
	Описание.ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр = Истина;   	 
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "Сотрудник";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	 
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "Период";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	ПараметрФормироватьСПериодичностьДень = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(ПараметрФормироватьСПериодичностьДень);

	ПараметрФормироватьСПериодичностьДень.Обязательный = Ложь;
	ПараметрФормироватьСПериодичностьДень.Имя = "ФормироватьСПериодичностьДень"; 
	ПараметрФормироватьСПериодичностьДень.ДопустимПараметрЗапроса = Ложь;
	ПараметрФормироватьСПериодичностьДень.ЗначениеПоУмолчанию = Ложь;
	ПараметрФормироватьСПериодичностьДень.ТипКонстанты = Новый ОписаниеТипов("Булево");
	
	Возврат Описание;	
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.ДанныеСотрудников";
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
	
	ФормироватьСПериодичностьДень = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты(
		"ФормироватьСПериодичностьДень", 
		ПараметрыВыполнения, 
		Запрос.Параметры,
		Истина);
	
	ИменаПолейФильтра = ОписаниеФильтра.ПсевдонимыПолей.Получить("Сотрудник") + "," + 
		ОписаниеФильтра.ПсевдонимыПолей.Получить("Период");
	
	ОписаниеФильтра = КадровыйУчет.ОписательВременныхТаблицДляСоздатьВТКадровыеДанныеСотрудников(
		Запрос.МенеджерВременныхТаблиц, 
		ИмяВТФильтр,
		ИменаПолейФильтра);	
	
	ОписаниеФильтра.ИмяВТКадровыеДанныеСотрудников = ИмяВТРезультат;
	КадровыйУчет.СоздатьВТКадровыеДанныеСотрудников(
		ОписаниеФильтра, 
		ПараметрыВыполнения.ТолькоРазрешенные, 
		Поля,,
		ФормироватьСПериодичностьДень);
		
	Возврат Неопределено;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТаблцляции) Экспорт
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	
	Строка = "Поля = Новый Массив();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Для Каждого Поле Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		Строка = "Поля.Добавить(""" + Поле.Ключ + """);";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	КонецЦикла;	
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияЗначения("ИмяВТФильтр", ОписаниеФильтра.ИмяВТ);
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияПараметровПеременной(
		"ФормироватьСПериодичностьДень",
		"ФормироватьСПериодичностьДень", 
		ПараметрыВыполнения, 
		ТекущиеТаблцляции,
		Истина);	
	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	ИменаПолейФильтра = ОписаниеФильтра.ПсевдонимыПолей.Получить("Сотрудник") + "," + 
		ОписаниеФильтра.ПсевдонимыПолей.Получить("Период");
		
	Строка = "ИменаПолейФильтра = """ + ИменаПолейФильтра + """;"; 
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Строка  = "ОписаниеФильтра = КадровыйУчет.ОписательВременныхТаблицДляСоздатьВТКадровыеДанныеСотрудников(";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	Строка = "Запрос.МенеджерВременныхТаблиц,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + Строка);
	Строка = "ИмяВТФильтр,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + Строка);
	Строка = "ИменаПолейФильтра);";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияЗначения("ОписаниеФильтра.ИмяВТКадровыеДанныеСотрудников", ПараметрыВыполнения.ИмяВТРезультат);
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияЗначения("ТолькоРазрешенные", ПараметрыВыполнения.ТолькоРазрешенные);
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Строка  = "КадровыйУчет.СоздатьВТКадровыеДанныеСотрудников(";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	Строка = "ОписаниеФильтра,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + Строка);
	Строка = "ТолькоРазрешенные,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + Строка);
	Строка = "Поля,,";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + Строка);
	Строка = "ФормироватьСПериодичностьДень);";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + Строка);
	
		
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
			ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ФормироватьСПериодичностьДень") 
			+ " = "
			+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрФормироватьСПериодичносьюДень.Значение);
		
		Построитель.ДобавитьОтбор(ВыражениеПараметра);
	КонецЕсли; 
	
	Запрос = Построитель.ПолучитьМодель().Элементы[0];
	ТекстЗапроса = ГенерацияТекстовЗапросов.ТекстЗапросаВыбора(Запрос);
	Возврат ТекстЗапроса;
КонецФункции



#КонецОбласти
#КонецЕсли