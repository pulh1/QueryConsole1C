#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления(); 
	
	Описание.ПоддерживаютсяИндексы = Ложь;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;; 
	Описание.ДоступноВМеханизмеПредставленийСКД = Ложь;
	Описание.ИмяВТДляСКД = "Представления_ОтработанноеВремя";  
	Описание.ПоддерживаютсяИндексы = Ложь; 
	Описание.Подсказка = "Позволяет получить информацию об рабочем и нерабочем времени сотрудников, учтенном при расчете начислений.";
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Сотрудник";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Сотрудники");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "МесяцНачисления";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПериодДействия";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Регистратор";
	Поле.ТипЗначения = Метаданные.РегистрыНакопления.ОтработанноеВремяПоСотрудникам.СтандартныеРеквизиты.Регистратор.Тип;
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Организация";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Организации");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Подразделение";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ПодразделенияОрганизаций");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВидРасчета";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПланВидовРасчетаСсылка.Начисления");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Регистратор";
	Поле.ТипЗначения = Метаданные.РегистрыНакопления.ОтработанноеВремяПоСотрудникам.Реквизиты.ДокументОснование.Тип;
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДатаНачала";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВремяВЧасах";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОтработаноДней";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОтработаноЧасов";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОтработаноДнейВПериоде";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОтработаноЧасовВПериоде";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОплаченоДней";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОплаченоЧасов";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
		
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Истина;
	Параметр.Имя = "НачалоПериода"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Дата");
		
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Истина;
	Параметр.Имя = "ОкончаниеПериода"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Дата");
		
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "СписокСотрудников"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("СправочникСсылка.Сотрудники");
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "Организация"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("СправочникСсылка.Организации");

	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "Подразделение"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("СправочникСсылка.Организации");	
	
	Возврат Описание;	
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.ОплаченноеВремя";
КонецФункции

Функция Исполнить(ПараметрыВыполнения, Запрос) Экспорт
	ЗапросНачисленияУдержания = Новый Запрос();
	ЗапросНачисленияУдержания.МенеджерВременныхТаблиц = Запрос.МенеджерВременныхТаблиц;
	ЗапросНачисленияУдержания.Текст = 
	"ВЫБРАТЬ ПЕРВЫЕ 0
	|	датавремя(1, 1, 1) как МесяцНачисления,
	|	ЗНАЧЕНИЕ(Документ.НачислениеЗарплаты.ПустаяСсылка) как Регистратор,
	|	ЗНАЧЕНИЕ(Справочник.Сотрудники.ПустаяСсылка) как Сотрудник,
	|	ЗНАЧЕНИЕ(Справочник.Организации.ПустаяСсылка) как Организация,
	|	ЗНАЧЕНИЕ(Справочник.ПодразделенияОрганизаций.ПустаяСсылка) как Подразделение,
	|	ЗНАЧЕНИЕ(ПланВидовРасчета.Начисления.ПустаяСсылка) как ВидРасчета,
	|	0 как ИдентификаторСтроки,
	|	ЗНАЧЕНИЕ(Справочник.СтатьиФинансированияЗарплата.ПустаяСсылка) как СтатьяФинансирования,
	|	ЗНАЧЕНИЕ(Справочник.СтатьиРасходовЗарплата.ПустаяСсылка) как СтатьяРасходов
	|ПОМЕСТИТЬ ВТНачисленияУдержанияПустая";
	
	ЗапросНачисленияУдержания.Выполнить();
	
	НачалоПериода = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты(
		"НачалоПериода",
		ПараметрыВыполнения, 
		Запрос.Параметры);
		
	ОкончаниеПериода = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты(
		"ОкончаниеПериода",
		ПараметрыВыполнения, 
		Запрос.Параметры);
	
	ЗапросОплаченноеВремя = ЗарплатаКадрыОбщиеНаборыДанных.ЗапросВТПредставленияОтработанноеВремя(
		"ВТНачисленияУдержанияПустая", 
		НачалоПериода, 
		ОкончаниеПериода, 
		ПараметрыВыполнения.ИмяВТРезультат);
	
	// установим отборы
	
	Схема = Новый СхемаЗапроса();
	Схема.УстановитьТекстЗапроса(ЗапросОплаченноеВремя.Текст);
	Для Каждого ЗапросПакета Из Схема.ПакетЗапросов Цикл
		Если ТипЗнч(ЗапросПакета) = Тип("ЗапросВыбораСхемыЗапроса")
			И ЗапросПакета.ТаблицаДляПомещения = ПараметрыВыполнения.ИмяВТРезультат Тогда
				
			ЗапросПакета.ТаблицаДляПомещения = "";
			Колонки = ЗапросПакета.Колонки;
			Прервать;
		КонецЕсли;
	КонецЦикла;
	
	СКД = Новый СхемаКомпоновкиДанных();
	Источник = СКД.ИсточникиДанных.Добавить();
	Источник.Имя = "Источник";
	Источник.ТипИсточникаДанных = "local";
	НаборСКД = СКД.НаборыДанных.Добавить(Тип("НаборДанныхЗапросСхемыКомпоновкиДанных"));
	НаборСКД.АвтоЗаполнениеДоступныхПолей = Истина;
	НаборСКД.Запрос = Схема.ПолучитьТекстЗапроса();
	НаборСКД.Имя = "ОплаченноеВремя";
	НаборСКД.ИсточникДанных = Источник.Имя;
	НастройкиСКД = СКД.ВариантыНастроек.Добавить().Настройки;
	
	Группа = НастройкиСКД.Структура.Добавить(Тип("ГруппировкаКомпоновкиДанных"));
	
	Для Каждого Колонка Из Колонки Цикл
		Если ПараметрыВыполнения.ИспользуемыеПоля.Получить(ВРег(Колонка.Псевдоним)) <> Неопределено Тогда
			Поле = Группа.Выбор.Элементы.Добавить(Тип("ВыбранноеПолеКомпоновкиДанных"));
			Поле.Поле = Новый ПолеКомпоновкиДанных(Колонка.Псевдоним);
			Поле.Использование = Истина;
		КонецЕсли;
	КонецЦикла;
	
	ПараметрОрганизация = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("Организация");
	Если ПараметрОрганизация <> Неопределено Тогда
		Отбор = НастройкиСКД.Отбор.Элементы.Добавить(Тип("ЭлементОтбораКомпоновкиДанных"));	
		Отбор.Использование = Истина;
		Отбор.ВидСравнения = ВидСравненияКомпоновкиДанных.Равно;
		Отбор.ЛевоеЗначение = Новый ПолеКомпоновкиДанных("Организация");
		Отбор.ПравоеЗначение = Запрос.Параметры[ПараметрОрганизация.Значение];
	КонецЕсли;
	
	ПараметрПодразделение = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("Подразделение");
	Если ПараметрПодразделение <> Неопределено Тогда
		Отбор = НастройкиСКД.Отбор.Элементы.Добавить(Тип("ЭлементОтбораКомпоновкиДанных"));	
		Отбор.Использование = Истина;
		Отбор.ВидСравнения = ВидСравненияКомпоновкиДанных.Равно;
		Отбор.ЛевоеЗначение = Новый ПолеКомпоновкиДанных("Подразделение");
		Отбор.ПравоеЗначение = Запрос.Параметры[ПараметрПодразделение.Значение];
	КонецЕсли;
	
	ПараметрСписокСотрудников = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("СписокСотрудников");
	Если ПараметрСписокСотрудников <> Неопределено Тогда
		ЗначениеПараметра = Запрос.Параметры[ПараметрСписокСотрудников.Значение];
		Отбор = НастройкиСКД.Отбор.Элементы.Добавить(Тип("ЭлементОтбораКомпоновкиДанных"));	
		Отбор.Использование = Истина;
		Если ТипЗнч(ЗначениеПараметра) = Тип("СправочникСсылка.Сотрудники") Тогда
			Отбор.ВидСравнения = ВидСравненияКомпоновкиДанных.Равно;
		Иначе
			Отбор.ВидСравнения = ВидСравненияКомпоновкиДанных.ВСписке;	
		КонецЕсли;
		Отбор.ЛевоеЗначение = Новый ПолеКомпоновкиДанных("Сотрудник");
		Отбор.ПравоеЗначение = ЗначениеПараметра;
	КонецЕсли;
	
	КомпоновщикМакета = Новый КомпоновщикМакетаКомпоновкиДанных;
	МакетКомпоновкиДанных = КомпоновщикМакета.Выполнить(СКД, НастройкиСКД);	
	
	Схема.УстановитьТекстЗапроса(МакетКомпоновкиДанных.НаборыДанных[0].Запрос);
	Для Каждого ЗапросПакета Из Схема.ПакетЗапросов Цикл
		Если ТипЗнч(ЗапросПакета) = Тип("ЗапросВыбораСхемыЗапроса")
			И Не ЗначениеЗаполнено(ЗапросПакета.ТаблицаДляПомещения) Тогда
			
			ЗапросПакета.ТаблицаДляПомещения = ПараметрыВыполнения.ИмяВТРезультат;
			Колонки = ЗапросПакета.Колонки;
			
			ЗапросПакета.Операторы[0].Источники[0].Соединения[0].ТипСоединения = ТипСоединенияСхемыЗапроса.ЛевоеВнешнее;
			
			Прервать;
		КонецЕсли;
	КонецЦикла;
	
	ЗапросОплаченноеВремя.Текст = Схема.ПолучитьТекстЗапроса();
	Для Каждого Параметр Из МакетКомпоновкиДанных.ЗначенияПараметров Цикл
		ЗапросОплаченноеВремя.УстановитьПараметр(Параметр.Имя, Параметр.Значение);	
	КонецЦикла;
		
	ЗапросОплаченноеВремя.МенеджерВременныхТаблиц = Запрос.МенеджерВременныхТаблиц;
	ЗапросОплаченноеВремя.Выполнить();
	
	ЗарплатаКадры.УничтожитьВТ(Запрос.МенеджерВременныхТаблиц, "ВТНачисленияУдержанияПустая", Ложь);
	
	Возврат Неопределено;
КонецФункции

// Исполняемый код.
// 
// Параметры:
//  ПараметрыВыполнения - см. ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления
//  ТекущиеТабуляции - Строка
// 
// Возвращаемое значение:
//   - Строка 
Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТабуляции) Экспорт
	Утилиты = ГенерацияИсполняемогоКодаПредставленийУтилиты;
	
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	Строка = "ЗапросНачисленияУдержания = Новый Запрос();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	Строка = "ЗапросНачисленияУдержания.МенеджерВременныхТаблиц = Запрос.МенеджерВременныхТаблиц;";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	ТекстЗапроса = "ВЫБРАТЬ ПЕРВЫЕ 0
	|	датавремя(1, 1, 1) как МесяцНачисления,
	|	ЗНАЧЕНИЕ(Документ.НачислениеЗарплаты.ПустаяСсылка) как Регистратор,
	|	ЗНАЧЕНИЕ(Справочник.Сотрудники.ПустаяСсылка) как Сотрудник,
	|	ЗНАЧЕНИЕ(Справочник.Организации.ПустаяСсылка) как Организация,
	|	ЗНАЧЕНИЕ(Справочник.ПодразделенияОрганизаций.ПустаяСсылка) как Подразделение,
	|	ЗНАЧЕНИЕ(ПланВидовРасчета.Начисления.ПустаяСсылка) как ВидРасчета,
	|	0 как ИдентификаторСтроки,
	|	ЗНАЧЕНИЕ(Справочник.СтатьиФинансированияЗарплата.ПустаяСсылка) как СтатьяФинансирования,
	|	ЗНАЧЕНИЕ(Справочник.СтатьиРасходовЗарплата.ПустаяСсылка) как СтатьяРасходов
	|ПОМЕСТИТЬ ВТНачисленияУдержанияПустая";
	
	Строка = "ЗапросНачисленияУдержания.Текст = " + Символы.ПС 
		+ Утилиты.ПримитивноеЗначениеВСтроку(ТекстЗапроса) + ";";
	
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
	
	Строка = "ЗапросНачисленияУдержания.Выполнить();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	НачалоПериода = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("НачалоПериода");
	Если НачалоПериода.ЭтоПараметрЗапроса Тогда
		ИмяПараметраНачалоПериода = НачалоПериода.Значение;
	Иначе
		Строка = "НачалоПериода = "
			+  ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(НачалоПериода.Значение) + ";";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		ИмяПараметраНачалоПериода = "НачалоПериода";
	КонецЕсли;
	
	ОкончаниеПериода = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("ОкончаниеПериода");
	Если ОкончаниеПериода.ЭтоПараметрЗапроса Тогда
		ИмяПараметраОкончаниеПериода = ОкончаниеПериода.Значение;
	Иначе
		Строка = "ОкончаниеПериода = "
			+  ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ОкончаниеПериода.Значение) + ";";
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
		ИмяПараметраОкончаниеПериода = "ОкончаниеПериода";
	КонецЕсли;
	ТекстовыйДокумент.ДобавитьСтроку("");	
	
	Строка = "ЗапросОплаченноеВремя = ЗарплатаКадрыОбщиеНаборыДанных.ЗапросВТПредставленияОтработанноеВремя(
	|	""ВТНачисленияУдержанияПустая"", 
	|	" + ИмяПараметраНачалоПериода + ", 
	|	" + ИмяПараметраОкончаниеПериода + ", 
	|	" + Утилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ИмяВТРезультат) + ");";
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = "ИспользуемыеПоля = Новый Соответствие();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Для Каждого КлючЗначение Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		Строка = "ИспользуемыеПоля.Вставить(" + Утилиты.ПримитивноеЗначениеВСтроку(КлючЗначение.Ключ) + ", Истина);";		
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	КонецЦикла;
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = "Схема = Новый СхемаЗапроса();
	|Схема.УстановитьТекстЗапроса(ЗапросОплаченноеВремя.Текст);
	|Для Каждого ЗапросПакета Из Схема.ПакетЗапросов Цикл
	|	Если ТипЗнч(ЗапросПакета) = Тип(""ЗапросВыбораСхемыЗапроса"")
	|		И ЗапросПакета.ТаблицаДляПомещения = " + Утилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ИмяВТРезультат) + " Тогда
	|			
	|		ЗапросПакета.ТаблицаДляПомещения = """";
	|		Колонки = ЗапросПакета.Колонки;
	|		Прервать;
	|	КонецЕсли;
	|КонецЦикла;
	|
	|СКД = Новый СхемаКомпоновкиДанных();
	|Источник = СКД.ИсточникиДанных.Добавить();
	|Источник.Имя = ""Источник"";
	|Источник.ТипИсточникаДанных = ""local"";
	|НаборСКД = СКД.НаборыДанных.Добавить(Тип(""НаборДанныхЗапросСхемыКомпоновкиДанных""));
	|НаборСКД.АвтоЗаполнениеДоступныхПолей = Истина;
	|НаборСКД.Запрос = Схема.ПолучитьТекстЗапроса();
	|НаборСКД.Имя = ""ОплаченноеВремя"";
	|НаборСКД.ИсточникДанных = Источник.Имя;
	|НастройкиСКД = СКД.ВариантыНастроек.Добавить().Настройки;
	|
	|Группа = НастройкиСКД.Структура.Добавить(Тип(""ГруппировкаКомпоновкиДанных""));
	|
	|Для Каждого Колонка Из Колонки Цикл
	|	Если ИспользуемыеПоля.Получить(ВРег(Колонка.Псевдоним)) <> Неопределено Тогда
	|		Поле = Группа.Выбор.Элементы.Добавить(Тип(""ВыбранноеПолеКомпоновкиДанных""));
	|		Поле.Поле = Новый ПолеКомпоновкиДанных(Колонка.Псевдоним);
	|		Поле.Использование = Истина;
	|	КонецЕсли;
	|КонецЦикла;";
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	ИмяПараметраОрганизация = Неопределено;
	ИмяПараметраПодразделение = Неопределено;
	ИмяПараметраСписокСотрудников = Неопределено;
	
	ПараметрОрганизация = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("Организация");
	Если ПараметрОрганизация <> Неопределено Тогда
		ИмяПараметраОрганизация = ПараметрОрганизация.Значение;
	КонецЕсли;
	
	ПараметрПодразделение = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("Подразделение");
	Если ПараметрПодразделение <> Неопределено Тогда
		ИмяПараметраПодразделение = ПараметрПодразделение.Значение;
	КонецЕсли;
	
	ПараметрСписокСотрудников = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("СписокСотрудников");
	Если ПараметрСписокСотрудников <> Неопределено Тогда
		ИмяПараметраСписокСотрудников = ПараметрСписокСотрудников.Значение;
	КонецЕсли;
	
	Если ИмяПараметраОрганизация <> Неопределено Тогда
		Строка = "Отбор = НастройкиСКД.Отбор.Элементы.Добавить(Тип(""ЭлементОтбораКомпоновкиДанных""));	
		|Отбор.Использование = Истина;
		|Отбор.ВидСравнения = ВидСравненияКомпоновкиДанных.Равно;
		|Отбор.ЛевоеЗначение = Новый ПолеКомпоновкиДанных(""Организация"");
		|Отбор.ПравоеЗначение = " + ИмяПараметраОрганизация + ";";
		
		Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
		ТекстовыйДокумент.ДобавитьСтроку("");
	КонецЕсли;
	
	Если ИмяПараметраПодразделение <> Неопределено Тогда
		Строка = "Отбор = НастройкиСКД.Отбор.Элементы.Добавить(Тип(""ЭлементОтбораКомпоновкиДанных""));	
		|Отбор.Использование = Истина;
		|Отбор.ВидСравнения = ВидСравненияКомпоновкиДанных.Равно;
		|Отбор.ЛевоеЗначение = Новый ПолеКомпоновкиДанных(""Подразделение"");
		|Отбор.ПравоеЗначение = " + ИмяПараметраПодразделение + ";";
		
		Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
		ТекстовыйДокумент.ДобавитьСтроку("");
	КонецЕсли;
	
	Если ИмяПараметраСписокСотрудников <> Неопределено Тогда
		Строка = "Отбор = НастройкиСКД.Отбор.Элементы.Добавить(Тип(""ЭлементОтбораКомпоновкиДанных""));	
		|Отбор.Использование = Истина;
		|Если ТипЗнч(" + ИмяПараметраСписокСотрудников + ") = Тип(""СправочникСсылка.Сотрудники"") Тогда
		|	Отбор.ВидСравнения = ВидСравненияКомпоновкиДанных.Равно;
		|Иначе
		|	Отбор.ВидСравнения = ВидСравненияКомпоновкиДанных.ВСписке;	
		|КонецЕсли;
		|Отбор.ЛевоеЗначение = Новый ПолеКомпоновкиДанных(""Сотрудник"");
		|Отбор.ПравоеЗначение = " + ИмяПараметраСписокСотрудников + ";";
		
		Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
		ТекстовыйДокумент.ДобавитьСтроку("");
	КонецЕсли;
	
	Строка = "КомпоновщикМакета = Новый КомпоновщикМакетаКомпоновкиДанных;
	|МакетКомпоновкиДанных = КомпоновщикМакета.Выполнить(СКД, НастройкиСКД);	
	|
	|Схема.УстановитьТекстЗапроса(МакетКомпоновкиДанных.НаборыДанных[0].Запрос);
	|Для Каждого ЗапросПакета Из Схема.ПакетЗапросов Цикл
	|	Если ТипЗнч(ЗапросПакета) = Тип(""ЗапросВыбораСхемыЗапроса"")
	|		И Не ЗначениеЗаполнено(ЗапросПакета.ТаблицаДляПомещения) Тогда
	|		
	|		ЗапросПакета.ТаблицаДляПомещения = " + Утилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ИмяВТРезультат) + ";
	|		Колонки = ЗапросПакета.Колонки;
	|		
	|		ЗапросПакета.Операторы[0].Источники[0].Соединения[0].ТипСоединения = ТипСоединенияСхемыЗапроса.ЛевоеВнешнее;
	|		
	|		Прервать;
	|	КонецЕсли;
	|КонецЦикла;
	|
	|ЗапросОплаченноеВремя.Текст = Схема.ПолучитьТекстЗапроса();
	|Для Каждого Параметр Из МакетКомпоновкиДанных.ЗначенияПараметров Цикл
	|	ЗапросОплаченноеВремя.УстановитьПараметр(Параметр.Имя, Параметр.Значение);	
	|КонецЦикла;
	|	
	|ЗапросОплаченноеВремя.МенеджерВременныхТаблиц = Запрос.МенеджерВременныхТаблиц;
	|ЗапросОплаченноеВремя.Выполнить();
	|
	|ЗарплатаКадры.УничтожитьВТ(Запрос.МенеджерВременныхТаблиц, ""ВТНачисленияУдержанияПустая"", Ложь);";
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Возврат ТекстовыйДокумент.ПолучитьТекст();
КонецФункции

Функция ТекстЗапросаДляСКД(ПараметрыВыполнения) Экспорт
	ВызватьИсключение "";
КонецФункции

#КонецОбласти
#КонецЕсли