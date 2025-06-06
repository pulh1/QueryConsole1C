
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления(); 
	
	Описание.ПоддерживаютсяИндексы = Ложь;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина; 
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ИмяВТДляСКД = "ОбщиеЗапросы_НачисленияУдержанияАвансом";  
	Описание.ПоддерживаютсяИндексы = Ложь; 
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Сотрудник";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Сотрудники");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ГоловнойСотрудник";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.Сотрудники");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФизическоеЛицо";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ФизическиеЛица");
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
	Поле.Имя = "Группа";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.ГруппыНачисленияУдержанияВыплаты");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВидРасчета";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПланВидовРасчетаСсылка.Начисления");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Сумма";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
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
	Поле.Имя = "ОтработаноДней";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОтработаноЧасов";
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
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВремяВЧасах";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Показатель";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ПоказателиРасчетаЗарплаты");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Значение";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПорядокПоказателей";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Сторно";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПриоритетВидаРасчета";
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
	Параметр.ТипКонстанты = Новый ОписаниеТипов("СправочникСсылка.ПодразделенияОрганизаций");	
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "ВыводитьПериодыНачислений"; 
	Параметр.ДопустимПараметрЗапроса = Ложь;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Истина;
	
	// Основной показатель
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "ВыводитьОсновнойПоказательНачисленийИУдержаний"; 
	Параметр.ДопустимПараметрЗапроса = Ложь;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Истина;
	
	Параметр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПараметраКонстанта();
	Описание.ОписаниеПараметров.Добавить(Параметр);
	Параметр.Обязательный = Ложь;
	Параметр.Имя = "ВыводитьВсеПоказателиНачисленийИУдержаний"; 
	Параметр.ДопустимПараметрЗапроса = Ложь;
	Параметр.ТипКонстанты = Новый ОписаниеТипов("Булево");
	Параметр.ЗначениеПоУмолчанию = Ложь;
	
	
	Возврат Описание;	
КонецФункции

Функция Справка() Экспорт
	Справка = ЭлементыМоделиОписанияПредставлений.НовыйСправка();	
	Справка.Имя = ИмяПредставления();
	Справка.Описание = "Обеспечивает доступ к результату запроса, используемого в типовом отчете ""Анализ начислений и удержаний в аванс””.
	|Предоставляет информацию о начисления, удержаниях, выплатах в аванс и сальдо взаиморасчетов.";
	
	Возврат Справка;
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.НачисленияУдержанияВыплатыАвансом";
КонецФункции

Функция Исполнить(ПараметрыВыполнения, Запрос) Экспорт
	ТекстЗапроса = ЗарплатаКадрыОбщиеНаборыДанныхПовтИсп.ПолучитьТекстОбщегоЗапроса(
		"НачисленияУдержанияАвансом", 
		ПараметрыВыполнения.ТолькоРазрешенные);
		
	СКД = Новый СхемаКомпоновкиДанных();
	Источник = СКД.ИсточникиДанных.Добавить();
	Источник.Имя = "Источник";
	Источник.ТипИсточникаДанных = "local";
	НаборСКД = СКД.НаборыДанных.Добавить(Тип("НаборДанныхЗапросСхемыКомпоновкиДанных"));
	НаборСКД.ИсточникДанных = "Источник";
	НаборСКД.Имя = "НачисленияУдержания";
	НаборСКД.Запрос = ТекстЗапроса;
	
	ЗарплатаКадрыОбщиеНаборыДанных.ЗаменитьПредставленияЗапросов(СКД.НаборыДанных, СКД);
	
	ЗапросНачисленияУдержания = Новый Запрос(НаборСКД.Запрос);
	ЗапросНачисленияУдержания.МенеджерВременныхТаблиц = Запрос.МенеджерВременныхТаблиц;
	
	НачалоПериода = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты(
		"НачалоПериода",
		ПараметрыВыполнения, 
		Запрос.Параметры);
		
	ОкончаниеПериода = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты(
		"ОкончаниеПериода",
		ПараметрыВыполнения, 
		Запрос.Параметры);
		
	ВыводитьПоказателиНачисленийИУдержаний = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты(
		"ВыводитьОсновнойПоказательНачисленийИУдержаний",
		ПараметрыВыполнения, 
		Запрос.Параметры,
		Истина);
		
	ВыводитьВсеПоказателиНачисленийИУдержаний = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты(
		"ВыводитьВсеПоказателиНачисленийИУдержаний",
		ПараметрыВыполнения, 
		Запрос.Параметры,
		Истина);
		
	ВыводитьПериодыНачислений = ИсполнительПредставленийУтилиты.ЗначениеПараметраКонстанты(
		"ВыводитьПериодыНачислений",
		ПараметрыВыполнения, 
		Запрос.Параметры,
		Истина);
		
	ЗапросНачисленияУдержания.УстановитьПараметр("НачалоПериода", НачалоПериода);
	ЗапросНачисленияУдержания.УстановитьПараметр("КонецПериода", ОкончаниеПериода);
	ЗапросНачисленияУдержания.УстановитьПараметр("ВыводитьПоказателиНачисленийИУдержаний", ВыводитьПоказателиНачисленийИУдержаний);
	ЗапросНачисленияУдержания.УстановитьПараметр("ВыводитьВсеПоказателиНачисленийИУдержаний", ВыводитьВсеПоказателиНачисленийИУдержаний);
	ЗапросНачисленияУдержания.УстановитьПараметр("ВыводитьПериодыНачислений", ВыводитьПериодыНачислений);
	ЗапросНачисленияУдержания.УстановитьПараметр("ИсключаемыеСсылки", Новый Массив());
	ЗапросНачисленияУдержания.УстановитьПараметр("ДетализироватьНачисленияПоСреднемуЗаработку", Ложь);
	
	Для Каждого Параметр Из СКД.Параметры Цикл
		ЗапросНачисленияУдержания.УстановитьПараметр(Параметр.Имя, Параметр.Значение);
	КонецЦикла;
	
	// установим отборы
	
	Схема = Новый СхемаЗапроса();
	Схема.УстановитьТекстЗапроса(ЗапросНачисленияУдержания.Текст);
	Для Каждого ЗапросПакета Из Схема.ПакетЗапросов Цикл
		Если ТипЗнч(ЗапросПакета) = Тип("ЗапросВыбораСхемыЗапроса")
			И ЗапросПакета.ТаблицаДляПомещения = "ОбщиеЗапросы_НачисленияУдержанияАвансом" Тогда
				
			ЗапросПакета.ТаблицаДляПомещения = "";
			Колонки = ЗапросПакета.Колонки;
			Прервать;
		КонецЕсли;
	КонецЦикла;
	НаборСКД.Запрос = Схема.ПолучитьТекстЗапроса();
	
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
			Прервать;
		КонецЕсли;
	КонецЦикла;
	
	ЗапросНачисленияУдержания.Текст = Схема.ПолучитьТекстЗапроса();
	Для Каждого Параметр Из МакетКомпоновкиДанных.ЗначенияПараметров Цикл
		ЗапросНачисленияУдержания.УстановитьПараметр(Параметр.Имя, Параметр.Значение);	
	КонецЦикла;
		
	ЗапросНачисленияУдержания.Выполнить();
	
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
	
	Строка = "ТекстЗапроса = ЗарплатаКадрыОбщиеНаборыДанныхПовтИсп.ПолучитьТекстОбщегоЗапроса(
	|	""НачисленияУдержанияАвансом"", 
	|	" + Утилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ТолькоРазрешенные) + ");
	|
	|СКД = Новый СхемаКомпоновкиДанных();
	|Источник = СКД.ИсточникиДанных.Добавить();
	|Источник.Имя = ""Источник"";
	|Источник.ТипИсточникаДанных = ""local"";
	|НаборСКД = СКД.НаборыДанных.Добавить(Тип(""НаборДанныхЗапросСхемыКомпоновкиДанных""));
	|НаборСКД.ИсточникДанных = ""Источник"";
	|НаборСКД.Запрос = ТекстЗапроса;
	|
	|ЗарплатаКадрыОбщиеНаборыДанных.ЗаменитьПредставленияЗапросов(СКД.НаборыДанных, СКД);
	|
	|ЗапросНачисленияУдержания = Новый Запрос(НаборСКД.Запрос);
	|ЗапросНачисленияУдержания.МенеджерВременныхТаблиц = Запрос.МенеджерВременныхТаблиц;";
	
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = Утилиты.СтрокаПрисвоенияПараметровПеременной(
		"НачалоПериода", 
		"НачалоПериода", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = Утилиты.СтрокаПрисвоенияПараметровПеременной(
		"ОкончаниеПериода", 
		"ОкончаниеПериода", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции);
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = Утилиты.СтрокаПрисвоенияПараметровПеременной(
		"ВыводитьОсновнойПоказательНачисленийИУдержаний", 
		"ВыводитьОсновнойПоказательНачисленийИУдержаний", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции,
		Истина);
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = Утилиты.СтрокаПрисвоенияПараметровПеременной(
		"ВыводитьВсеПоказателиНачисленийИУдержаний", 
		"ВыводитьВсеПоказателиНачисленийИУдержаний", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции,
		Истина);
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	
	Строка = Утилиты.СтрокаПрисвоенияПараметровПеременной(
		"ВыводитьПериодыНачислений", 
		"ВыводитьПериодыНачислений", 
		ПараметрыВыполнения, 
		ТекущиеТабуляции,
		Истина);
	ТекстовыйДокумент.ДобавитьСтроку(Строка);
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = "ЗапросНачисленияУдержания.УстановитьПараметр(""НачалоПериода"", НачалоПериода);
	|ЗапросНачисленияУдержания.УстановитьПараметр(""КонецПериода"", ОкончаниеПериода);
	|ЗапросНачисленияУдержания.УстановитьПараметр(""ВыводитьПоказателиНачисленийИУдержаний"", ВыводитьОсновнойПоказательНачисленийИУдержаний);
	|ЗапросНачисленияУдержания.УстановитьПараметр(""ВыводитьВсеПоказателиНачисленийИУдержаний"", ВыводитьВсеПоказателиНачисленийИУдержаний);
	|ЗапросНачисленияУдержания.УстановитьПараметр(""ВыводитьПериодыНачислений"", ВыводитьПериодыНачислений);
	|ЗапросНачисленияУдержания.УстановитьПараметр(""ИсключаемыеСсылки"", Новый Массив());
	|ЗапросНачисленияУдержания.УстановитьПараметр(""ДетализироватьНачисленияПоСреднемуЗаработку"", Ложь);
	|
	|Для Каждого Параметр Из СКД.Параметры Цикл
	|	ЗапросНачисленияУдержания.УстановитьПараметр(Параметр.Имя, Параметр.Значение);
	|КонецЦикла;
	|
	|// установим отборы
	|
	|Схема = Новый СхемаЗапроса();
	|Схема.УстановитьТекстЗапроса(ЗапросНачисленияУдержания.Текст);
	|Для Каждого ЗапросПакета Из Схема.ПакетЗапросов Цикл
	|	Если ТипЗнч(ЗапросПакета) = Тип(""ЗапросВыбораСхемыЗапроса"")
	|		И ЗапросПакета.ТаблицаДляПомещения = ""ОбщиеЗапросы_НачисленияУдержанияАвансом"" Тогда
	|			
	|		ЗапросПакета.ТаблицаДляПомещения = """";
	|		Колонки = ЗапросПакета.Колонки;
	|		Прервать;
	|	КонецЕсли;
	|КонецЦикла;
	|НаборСКД.Запрос = Схема.ПолучитьТекстЗапроса();
	|
	|НастройкиСКД = СКД.ВариантыНастроек.Добавить().Настройки;
	|Группа = НастройкиСКД.Структура.Добавить(Тип(""ГруппировкаКомпоновкиДанных""));";
	
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = "ИспользуемыеПоля = Новый Соответствие();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	
	Для Каждого КлючЗначение Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		Строка = "ИспользуемыеПоля.Вставить(" + Утилиты.ПримитивноеЗначениеВСтроку(КлючЗначение.Ключ) + ", Истина);";		
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТабуляции + Строка);
	КонецЦикла;
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	Строка = "Для Каждого Колонка Из Колонки Цикл
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
	|		
	|		ЗапросПакета.Операторы[0].Источники[0].Соединения[0].ТипСоединения = ТипСоединенияСхемыЗапроса.ЛевоеВнешнее;
	|		
	|		Прервать;
	|	КонецЕсли;
	|КонецЦикла;
	|
	|ЗапросНачисленияУдержания.Текст = Схема.ПолучитьТекстЗапроса();
	|Для Каждого Параметр Из МакетКомпоновкиДанных.ЗначенияПараметров Цикл
	|	ЗапросНачисленияУдержания.УстановитьПараметр(Параметр.Имя, Параметр.Значение);	
	|КонецЦикла;
	|	
	|ЗапросНачисленияУдержания.Выполнить();";
	
	Утилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);

	Возврат ТекстовыйДокумент.ПолучитьТекст();
КонецФункции

Функция ТекстЗапросаДляСКД(ПараметрыВыполнения) Экспорт
	Описание = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ПараметрыВыполнения.ИмяИсполняемогоПредставления);
	
	Модель = ГенерацияИсполняемогоКодаПредставленийУтилиты.МодельЗапросаДляСКД(ПараметрыВыполнения, Описание);
	Построитель = МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель);
	
	Выражение = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("НачалоПериода") 
		+ " = &НачалоПериода";
	Построитель.ДобавитьОтбор(Выражение);
	
	Выражение = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("КонецПериода") 
		+ " = &КонецПериода";
	Построитель.ДобавитьОтбор(Выражение);
	
	Выражение = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ИсключаемыеСсылки") 
		+ " = &ИсключаемыеСсылки";
	Построитель.ДобавитьОтбор(Выражение);
	
	Выражение = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ВыводитьПоказателиНачисленийИУдержаний") 
		+ " = &ВыводитьПоказателиНачисленийИУдержаний";
	Построитель.ДобавитьОтбор(Выражение);
	
	Выражение = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ВыводитьВсеПоказателиНачисленийИУдержаний") 
		+ " = &ВыводитьВсеПоказателиНачисленийИУдержаний";
	Построитель.ДобавитьОтбор(Выражение);
	
	Выражение = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ВыводитьПериодыНачислений") 
		+ " = &ВыводитьПериодыНачислений";
	Построитель.ДобавитьОтбор(Выражение);
	
	Выражение = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ДетализироватьНачисленияПоСреднемуЗаработку") 
		+ " = &ДетализироватьНачисленияПоСреднемуЗаработку";
	Построитель.ДобавитьОтбор(Выражение);
	
	ГенерацияИсполняемогоКодаПредставленийУтилиты.УстановитьПараметраПредставленияВМодельЗапросаДляСКД(
		Построитель, 
		ПараметрыВыполнения, 
		Описание, 
		Новый Структура());
			
	Запрос = Построитель.ПолучитьМодель().Элементы[0];
	ТекстЗапроса = ГенерацияТекстовЗапросов.ТекстЗапросаВыбора(Запрос);
	Возврат ТекстЗапроса;
КонецФункции

#КонецОбласти

#КонецЕсли
