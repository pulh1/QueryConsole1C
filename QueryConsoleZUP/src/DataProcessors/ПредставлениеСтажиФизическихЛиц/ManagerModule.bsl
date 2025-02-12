
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления();
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;
	Описание.ИмяВТДляСКД = "Представления_СтажиСотрудников";
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФизическоеЛицо";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ФизическиеЛица");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВидСтажа";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ВидыСтажа");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Период";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДатаОтсчета";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДатаОкончания";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РазмерМесяцев";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РазмерДней";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Прерван";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВсегоМесяцев";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Лет";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Месяцев";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Дней";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "НачалоБудущегоМесяца";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Описание.ОписаниеВТФильтр = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр();   
	Описание.ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы = Истина;
	Описание.ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр = Истина;   	
	Описание.ОписаниеВТФильтр.Обязательный = Истина;
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "ФизическоеЛицо";
	ПолеФильтра.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ФизическиеЛица");
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "Период";
	ПолеФильтра.ТипЗначения = Новый ОписаниеТипов("Дата");
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "ВидСтажа";
	ПолеФильтра.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ВидыСтажа");
	ПолеФильтра.Обязательный = Ложь;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	Возврат Описание;	
КонецФункции

Функция Справка() Экспорт
	Справка = ЭлементыМоделиОписанияПредставлений.НовыйСправка();	
	Справка.Имя = ИмяПредставления();
	Справка.Описание = "Обеспечивает доступ к методу ""КадровыйУчет.СоздатьВТСтажиФизическихЛиц"".
	|Позволяет получить стаж физических лиц рассчитанный на заданные даты.";
	
	Возврат Справка;
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.СтажиФизическихЛиц";
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
	
	ИмяПоляФизическоеЛицо = ОписаниеФильтра.ПсевдонимыПолей.Получить("ФизическоеЛицо");
	ИмяПоляПериод = ОписаниеФильтра.ПсевдонимыПолей.Получить("Период");
	ИмяПоляВидСтажа = ОписаниеФильтра.ПсевдонимыПолей.Получить("ВидСтажа");
	
	ПараметрыПолученияДанных = КадровыйУчетРасширенный.ОписательВременнойТаблицыОтборовДляВТСтажиФизическихЛиц(
		ОписаниеФильтра.ИмяВТ,
		ИмяПоляФизическоеЛицо,
		ИмяПоляПериод);
	ПараметрыПолученияДанных.ИмяПоляВидСтажа = ИмяПоляВидСтажа;
	
	КадровыйУчетРасширенный.СоздатьВТСтажиФизическихЛиц(
		Запрос.МенеджерВременныхТаблиц, 
		ПараметрыВыполнения.ТолькоРазрешенные, 
		ПараметрыПолученияДанных,
		ПараметрыВыполнения.ИмяВТРезультат);
		
	Возврат Неопределено;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТабуляции) Экспорт
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	ОписаниеФильтра = ПараметрыВыполнения.ОписаниеВТФильтр;
	ИмяПоляФизическоеЛицо = ОписаниеФильтра.ПсевдонимыПолей.Получить("ФизическоеЛицо");
	ИмяПоляПериод = ОписаниеФильтра.ПсевдонимыПолей.Получить("Период");
	ИмяПоляВидСтажа = ОписаниеФильтра.ПсевдонимыПолей.Получить("ВидСтажа");
	
	Строка = "ПараметрыПолученияДанных = КадровыйУчетРасширенный.ОписательВременнойТаблицыОтборовДляВТСтажиФизическихЛиц(
	|	""" + ОписаниеФильтра.ИмяВТ + """,
	|	""" + 	ИмяПоляФизическоеЛицо + """,
	|	""" + 	ИмяПоляПериод + """);
	|ПараметрыПолученияДанных.ИмяПоляВидСтажа = """ + ИмяПоляВидСтажа + """;
	|
	|КадровыйУчетРасширенный.СоздатьВТСтажиФизическихЛиц(
	|	Запрос.МенеджерВременныхТаблиц, 
	|	" + ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ТолькоРазрешенные) + ", 
	|	ПараметрыПолученияДанных,
	|	""" + ПараметрыВыполнения.ИмяВТРезультат + """);";
	
	ГенерацияИсполняемогоКодаПредставленийУтилиты.ВывестиМультиСтрокуВТекстовыйДокумент(ТекстовыйДокумент, Строка, ТекущиеТабуляции);
	
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
