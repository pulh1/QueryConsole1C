
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления(); 
	
	Описание.ПоддерживаютсяИндексы = Ложь;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;; 
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ИмяВТДляСКД = "Представления_РабочиеМестаСотрудников";  
	
	Описание.ОписаниеВТФильтр =  ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр();
	
	Описание.ОписаниеВТФильтр.Обязательный = Ложь; 
	
	Описание.ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр = Истина;;   
	Описание.ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы = Истина;
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Сотрудник";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Сотрудники");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФизическоеЛицо";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ФизическиеЛица");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Период";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ГоловнаяОрганизация";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Организации");
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
	Поле.Имя = "Должность";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Должности");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДолжностьПоШтатномуРасписанию";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ШтатноеРасписание");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "КоличествоСтавок";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВидДоговора";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.ВидыДоговоровССотрудниками");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РольСотрудника";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.РолиСотрудников");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ГоловнойСотрудник";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Сотрудники");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВидСобытия";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.ВидыКадровыхСобытий");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДокументОснование";
	Поле.ТипЗначения = Метаданные.РегистрыСведений.ПериодыДействияДоговоровГражданскоПравовогоХарактера.Измерения.ДокументОснование.Тип;
	Поле.ТипЗначения = Новый ОписаниеТипов(
		Поле.ТипЗначения,
		Метаданные.РегистрыСведений.КадроваяИсторияСотрудников.СтандартныеРеквизиты.Регистратор.Тип.Типы());
	Описание.Поля.Добавить(Поле);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "Сотрудник";
	ПолеФильтра.Обязательный = Ложь;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "НачалоПериода";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "ОкончаниеПериода";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "Организация"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("СправочникСсылка.Организации");
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "ОтбиратьПоГоловнойОрганизации"; 
	Параметр.ДопустимПараметрЗапроса = Истина;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Ложь;
	
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
	
	Возврат Описание;	
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.РабочиеМестаСотрудников";
КонецФункции

Функция Исполнить(ПараметрыВыполнения, Запрос) Экспорт
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	ИмяВТРезультат = ПараметрыВыполнения.ИмяВТРезультат;
	
	ПараметрыПолученияДанных = КадровыйУчет.ПараметрыДляЗапросВТРабочиеМестаСотрудниковПоВременнойТаблице();
	ПараметрыПолученияДанных.ИмяВТСотрудникиПериоды = ОписаниеФильтра.ИмяВТ;
	
	ПараметрыПолученияДанных.ИмяПоляСотрудник = ОписаниеФильтра.ПсевдонимыПолей.Получить("Сотрудник");
	ПараметрыПолученияДанных.ИмяПоляНачалоПериода = ОписаниеФильтра.ПсевдонимыПолей.Получить("НачалоПериода");
	ПараметрыПолученияДанных.ИмяПоляОкончаниеПериода = ОписаниеФильтра.ПсевдонимыПолей.Получить("ОкончаниеПериода");
	
	УстанавливаемыеПараметры = Новый Структура();
	УстанавливаемыеПараметры.Вставить("ФормироватьСПериодичностьДень", "ПериодВОдинДень");
	УстанавливаемыеПараметры.Вставить("Организация");
	УстанавливаемыеПараметры.Вставить("ОтбиратьПоГоловнойОрганизации");
	УстанавливаемыеПараметры.Вставить("Подразделение");
	УстанавливаемыеПараметры.Вставить("РаботникиПоТрудовымДоговорам");
	УстанавливаемыеПараметры.Вставить("ПодработкиРаботниковПоТрудовымДоговорам");
	УстанавливаемыеПараметры.Вставить("РаботникиПоДоговорамГПХ");
	УстанавливаемыеПараметры.Вставить("ВключаяУволенныхНаНачалоПериода");
	
	ИсполнительПредставленийУтилиты.УстановитьЗначениеПараметров(
		ПараметрыПолученияДанных, 
		ПараметрыВыполнения, 
		Запрос.Параметры, 
		УстанавливаемыеПараметры);
	
	КадровыйУчет.СоздатьВТРабочиеМестаСотрудников(
		Запрос.МенеджерВременныхТаблиц, 
		ПараметрыВыполнения.ТолькоРазрешенные, 
		ПараметрыПолученияДанных,
		ИмяВТРезультат);
		
	Возврат Неопределено;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТаблцляции) Экспорт
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	ИмяВТРезультат = ПараметрыВыполнения.ИмяВТРезультат;
	
	Строка = "ПараметрыПолученияДанных = КадровыйУчет.ПараметрыДляЗапросВТРабочиеМестаСотрудниковПоВременнойТаблице();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Строка = "ПараметрыПолученияДанных.ИмяПоляСотрудник = "
		+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ОписаниеФильтра.ПсевдонимыПолей.Получить("Сотрудник"))
		+ ";";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Строка = "ПараметрыПолученияДанных.ИмяПоляНачалоПериода = "
		+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ОписаниеФильтра.ПсевдонимыПолей.Получить("НачалоПериода"))
		+ ";";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Строка = "ПараметрыПолученияДанных.ИмяПоляОкончаниеПериода = "
		+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ОписаниеФильтра.ПсевдонимыПолей.Получить("ОкончаниеПериода"))
		+ ";";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	
	Строка = ГенерацияИсполняемогоКодаПредставленийУтилиты.СтрокаПрисвоенияЗначения(
		"ПараметрыПолученияДанных.ИмяВТСотрудникиПериоды", 
		ПараметрыВыполнения.ОписаниеВТФильтр.ИмяВТ,
		ТекущиеТаблцляции);	
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	УстанавливаемыеПараметры = Новый Структура();
	УстанавливаемыеПараметры.Вставить("ФормироватьСПериодичностьДень", "ПараметрыПолученияДанных.ПериодВОдинДень");
	УстанавливаемыеПараметры.Вставить("Организация", "ПараметрыПолученияДанных.Организация");
	УстанавливаемыеПараметры.Вставить("ОтбиратьПоГоловнойОрганизации", "ПараметрыПолученияДанных.ОтбиратьПоГоловнойОрганизации");
	УстанавливаемыеПараметры.Вставить("Подразделение", "ПараметрыПолученияДанных.Подразделение");
	УстанавливаемыеПараметры.Вставить("РаботникиПоТрудовымДоговорам", "ПараметрыПолученияДанных.РаботникиПоТрудовымДоговорам");
	УстанавливаемыеПараметры.Вставить("ПодработкиРаботниковПоТрудовымДоговорам", "ПараметрыПолученияДанных.ПодработкиРаботниковПоТрудовымДоговорам");
	УстанавливаемыеПараметры.Вставить("РаботникиПоДоговорамГПХ", "ПараметрыПолученияДанных.РаботникиПоДоговорамГПХ");
	УстанавливаемыеПараметры.Вставить("ВключаяУволенныхНаНачалоПериода", "ПараметрыПолученияДанных.ВключаяУволенныхНаНачалоПериода");
	
	ГенерацияИсполняемогоКодаПредставленийУтилиты.КодПрисвоенияПараметровВТекстовыйДокумент(
		ТекстовыйДокумент, 
		ПараметрыВыполнения, 
		Описание(), 
		УстанавливаемыеПараметры,
		ТекущиеТаблцляции);
	
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + "КадровыйУчет.СоздатьВТРабочиеМестаСотрудников(");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + "Запрос.МенеджерВременныхТаблиц,");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ТолькоРазрешенные) + ",");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + "ПараметрыПолученияДанных,");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ИмяВТРезультат) + ");");
		
	Возврат ТекстовыйДокумент.ПолучитьТекст();
КонецФункции

Функция ТекстЗапросаДляСКД(ПараметрыВыполнения) Экспорт
	Если ПараметрыВыполнения.ОписаниеФильтра.ПсевдонимыПолей.Получить("Сотрудник") = Неопределено Тогда
		ВызватьИсключение "Для формирования кода представления " + ИмяПредставления() 	
			+ "в ВТ фильтре обязательно должно быть указано поле Сотрудник.";
	КонецЕсли;
	
	Описание = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ПараметрыВыполнения.ИмяИсполняемогоПредставления);
	
	Модель = ГенерацияИсполняемогоКодаПредставленийУтилиты.МодельЗапросаДляСКД(ПараметрыВыполнения, Описание);
	Построитель = МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель);
	
	УстанавливаемыеПараметры = Новый Структура();
	УстанавливаемыеПараметры.Вставить("ФормироватьСПериодичностьДень", "ПериодВОдинДень");
	УстанавливаемыеПараметры.Вставить("Организация", "Организация");
	УстанавливаемыеПараметры.Вставить("ОтбиратьПоГоловнойОрганизации", "ОтбиратьПоГоловнойОрганизации");
	УстанавливаемыеПараметры.Вставить("Подразделение", "Подразделение");
	УстанавливаемыеПараметры.Вставить("РаботникиПоТрудовымДоговорам", "РаботникиПоТрудовымДоговорам");
	УстанавливаемыеПараметры.Вставить("ПодработкиРаботниковПоТрудовымДоговорам", "ПодработкиРаботниковПоТрудовымДоговорам");
	УстанавливаемыеПараметры.Вставить("РаботникиПоДоговорамГПХ", "РаботникиПоДоговорамГПХ");
	УстанавливаемыеПараметры.Вставить("ВключаяУволенныхНаНачалоПериода", "ВключаяУволенныхНаНачалоПериода");
	
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
