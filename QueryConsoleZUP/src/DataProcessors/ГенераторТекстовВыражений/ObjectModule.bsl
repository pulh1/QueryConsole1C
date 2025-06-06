
#Если Не (ТолстыйКлиентУправляемоеПриложение) Тогда

Перем Источники;
Перем ИсточникиВнешнегоЗапроса;
Перем Колонки;
Перем МассивСтрок;
Перем ВыводитьПсевдонимыИсточников;

#Область СлужебныйПрограммныйИнтерфейс

// Установить источники.
// 
// Параметры:
//  ИсточникиОператора - Массив из см. ЭлементыМоделиЗапроса.НовыйИсточник
Процедура УстановитьИсточники(ИсточникиОператора) Экспорт
	Источники.Очистить();
	Источники = МодельЗапросаУтилиты.МассивСтруктурВСоответствие(ИсточникиОператора, "ИдентификаторИсточника");
КонецПроцедуры

// Установить колонки.
// 
// Параметры:
//  УстанавливаемыеКолонки - Массив из см. ЭлементыМоделиЗапроса.НовыйКолонкаЗапроса
Процедура УстановитьКолонки(УстанавливаемыеКолонки) Экспорт
	Колонки.Очистить();
	Для Каждого Колонка Из УстанавливаемыеКолонки Цикл
		Колонки.Вставить(Колонка.Идентификатор, Колонка);
	КонецЦикла;	
КонецПроцедуры

// Установить массив строк.
// 
// Параметры:
//  УстаналиваемыйМассив - Массив из Строка
Процедура УстановитьМассивСтрок(УстаналиваемыйМассив) Экспорт
	МассивСтрок = УстаналиваемыйМассив;
КонецПроцедуры

// Установить источники внешнего запроса.
// 
// Параметры:
//  УстанавливаемыеИсточники - Соответствие из КлючИЗначение:
//		* Ключ - Строка
//		* Значение - см. ЭлементыМоделиЗапроса.НовыйИсточник
Процедура УстановитьИсточникиВнешнегоЗапроса(УстанавливаемыеИсточники) Экспорт
	ИсточникиВнешнегоЗапроса.Очистить();
	Для Каждого КлючЗначение Из УстанавливаемыеИсточники Цикл
		ИсточникиВнешнегоЗапроса.Вставить(КлючЗначение.Ключ, КлючЗначение.Значение);
	КонецЦикла;
КонецПроцедуры

Процедура УстановитьВыводПсевдонимовИсточников(Выводить) Экспорт
	ВыводитьПсевдонимыИсточников = Выводить;
КонецПроцедуры

Процедура ВыражениеВМассивСтрок(Выражение, Знач Табуляции, Родитель = Неопределено) Экспорт
	Если Выражение.Тип = "ВыражениеМоделиЗапроса" Тогда
		ВыражениеВМассивСтрок(Выражение.Значение, Табуляции, Родитель);	 
	ИначеЕсли Выражение.Тип = "СсылкаНаКолонкуЗапроса" Тогда
		МассивСтрок.Добавить(Колонки[Выражение.Идентификатор].Имя);
	ИначеЕсли Выражение.Тип = "ПолеИсточника" Тогда
		Источник = Источники.Получить(Выражение.ИдентификаторИсточника);
		Если Источник = Неопределено Тогда
			Источник = ИсточникиВнешнегоЗапроса.Получить(Выражение.ИдентификаторИсточника);
		КонецЕсли;
		Если ВыводитьПсевдонимыИсточников Тогда
			Псевдоним = Источник.Источник.Псевдоним; 
			МассивСтрок.Добавить(Псевдоним);
			МассивСтрок.Добавить("."); 
		КонецЕсли;
		МассивСтрок.Добавить(Выражение.ИмяПоля);
	ИначеЕсли Выражение.Тип = "БинарнаяОперация" Тогда
		БинарнаяОперацияВМассивСтрок(Выражение, Табуляции, Родитель);
	ИначеЕсли Выражение.Тип = "ОператорМежду" Тогда
		ВыражениеВМассивСтрок(Выражение.Операнд, Табуляции);	
		Если Выражение.Инверсия Тогда
			МассивСтрок.Добавить(" НЕ");
		КонецЕсли;	
		МассивСтрок.Добавить(" МЕЖДУ ");
		ВыражениеВМассивСтрок(Выражение.НачалоИнтервала, Табуляции);
		МассивСтрок.Добавить(" И ");
		ВыражениеВМассивСтрок(Выражение.КонецИнтервала, Табуляции);
	ИначеЕсли Выражение.Тип = "ОператорПроверкиТипа" Тогда
		ВыражениеВМассивСтрок(Выражение.Операнд, Табуляции);	
		МассивСтрок.Добавить(" ССЫЛКА ");
		ВыражениеВМассивСтрок(Выражение.ТипСсылочногоПоля, "");
	ИначеЕсли Выражение.Тип = "ОператорПроверкиНаNULL" Тогда
		ВыражениеВМассивСтрок(Выражение.Операнд, Табуляции);	
		МассивСтрок.Добавить(" ЕСТЬ ");
		Если Выражение.Инверсия Тогда
			МассивСтрок.Добавить(" НЕ");
		КонецЕсли;	
		МассивСтрок.Добавить(" NULL");	
	ИначеЕсли Выражение.Тип = "ОператорВ" Тогда
		ВыражениеВМассивСтрок(Выражение.Операнд, Табуляции);	
		Если Выражение.Инверсия Тогда
			МассивСтрок.Добавить(" НЕ");
		КонецЕсли;	
		МассивСтрок.Добавить(" В");	
		Если Выражение.Иерархия Тогда
			МассивСтрок.Добавить(" ИЕРАРХИИ");
		КонецЕсли;
		МассивСтрок.Добавить(" (");
		Если Выражение.Список.Тип = "СписокВыражений" Тогда
			СписокВыраженийВВМассивСтрок(Выражение.Список, Табуляции);
		Иначе
			ГенераторТекстаЗапроса = ГенерацияТекстовЗапросов.СоздатьГенераторТекстаЗапроса(
				Выражение.Список, 
				МассивСтрок,
				Источники);
		
			ГенераторТекстаЗапроса.ЗапросВыбораВМассивСтрок(Табуляции);
		КонецЕсли;
		МассивСтрок.Добавить(")");
	ИначеЕсли Выражение.Тип = "ЛогическоеОтрицание" Тогда
		Для Сч = 1 По Выражение.Количество Цикл
			МассивСтрок.Добавить("НЕ ");
		КонецЦикла;		
		ВыражениеВМассивСтрок(Выражение.Выражение, "");
	ИначеЕсли Выражение.Тип = "УнарнаяОперация" Тогда
		Для Каждого Знак Из Выражение.Знаки Цикл
			МассивСтрок.Добавить(Знак);	
		КонецЦикла;	
		ВыражениеВМассивСтрок(Выражение.Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ОператорПодобно" Тогда
		ВыражениеВМассивСтрок(Выражение.Операнд, Табуляции);	
		Если Выражение.Инверсия Тогда
			МассивСтрок.Добавить(" НЕ");
		КонецЕсли;	
		МассивСтрок.Добавить(" ПОДОБНО ");	
		ВыражениеВМассивСтрок(Выражение.Шаблон, "");
	ИначеЕсли Выражение.Тип = "Разыменование" Тогда
		ЭтоПервыйЭлемент = Истина;
		Для Каждого ЭлементРазвыменованя Из Выражение.Элементы Цикл
			Если ЭтоПервыйЭлемент Тогда
				ЭтоПервыйЭлемент = Ложь;
			Иначе
				МассивСтрок.Добавить(".");	
			КонецЕсли;	
			Если ТипЗнч(ЭлементРазвыменованя) = Тип("Строка") Тогда
				МассивСтрок.Добавить(ЭлементРазвыменованя);	
			ИначеЕсли ЭлементРазвыменованя.Тип = "ПолеИсточника" Тогда
				ВыражениеВМассивСтрок(ЭлементРазвыменованя, Табуляции);
			ИначеЕсли ЭлементРазвыменованя.Тип = "ПриведениеТипа" Тогда
				ВыражениеВМассивСтрок(ЭлементРазвыменованя, Табуляции);
			ИначеЕсли ЭлементРазвыменованя.Тип = "СписокВыражений" Тогда
				МассивСтрок.Добавить("(");
				СписокВыраженийВВМассивСтрок(ЭлементРазвыменованя, Табуляции);  
				МассивСтрок.Добавить(")");
			ИначеЕсли ЭлементРазвыменованя.Тип = "ПоляВложеннойТаблицы" Тогда
				МассивСтрок.Добавить("(");
				СписокПолейСПсевдонимамиВМассивСтрок(ЭлементРазвыменованя.Элементы, Табуляции + Символы.Таб);
				МассивСтрок.Добавить(")");
			КонецЕсли;	
		КонецЦикла;		
	ИначеЕсли Выражение.Тип = "ПриведениеТипа" Тогда
		МассивСтрок.Добавить("ВЫРАЗИТЬ(");
		ВыражениеВМассивСтрок(Выражение.Выражение, Табуляции);
		МассивСтрок.Добавить(" КАК ");
		ВыражениеВМассивСтрок(Выражение.ОписаниеТипа, Табуляции);
		МассивСтрок.Добавить(")");
	ИначеЕсли Выражение.Тип = "ТипСсылочногоПоля" Тогда
		МассивСтрок.Добавить(Выражение.Группа);
		МассивСтрок.Добавить(".");
		МассивСтрок.Добавить(Выражение.Таблица);	
	ИначеЕсли Выражение.Тип = "ОписаниеТипаБулево" Тогда
		МассивСтрок.Добавить("БУЛЕВО");
	ИначеЕсли Выражение.Тип = "ОписаниеТипаДата" Тогда
		МассивСтрок.Добавить("ДАТА");
	ИначеЕсли Выражение.Тип = "ОписаниеТипаЧисло" Тогда
		МассивСтрок.Добавить("ЧИСЛО");	
		Если Выражение.Длина <> 0
			Или Выражение.Точность <> 0 Тогда
			
			МассивСтрок.Добавить("(");
			МассивСтрок.Добавить(Формат(Выражение.Длина, "ЧН=0; ЧГ="));
			МассивСтрок.Добавить(", ");
			МассивСтрок.Добавить(Формат(Выражение.Точность, "ЧН=0; ЧГ="));
			МассивСтрок.Добавить(")");
		КонецЕсли;	
	ИначеЕсли Выражение.Тип = "ОписаниеТипаСтрока" Тогда
		МассивСтрок.Добавить("СТРОКА");	
		Если Выражение.Длина <> 0 Тогда
			
			МассивСтрок.Добавить("(");
			МассивСтрок.Добавить(Формат(Выражение.Длина, "ЧН=0; ЧГ="));
			МассивСтрок.Добавить(")");
		КонецЕсли;	
	ИначеЕсли Выражение.Тип = "Выбор" Тогда	
		ОператорВыбораВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "Константа" Тогда	
		КонстантаВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ПараметрЗапроса" Тогда	
		МассивСтрок.Добавить("&");
		МассивСтрок.Добавить(Выражение.Имя);
	ИначеЕсли Выражение.Тип = "АгрегатнаяФункция" Тогда
		МассивСтрок.Добавить(ВРег(Выражение.ИмяФункции));
		МассивСтрок.Добавить("(");
		ВыражениеВМассивСтрок(Выражение.Аргумент, Табуляции + Символы.Таб);
		МассивСтрок.Добавить(")");
	ИначеЕсли Выражение.Тип = "АгрегатнаяФункцияКоличество" Тогда
		МассивСтрок.Добавить("КОЛИЧЕСТВО");
		МассивСтрок.Добавить("(");
		Если Выражение.Различные Тогда
			МассивСтрок.Добавить("РАЗЛИЧНЫЕ ");
		КонецЕсли;	
		Если Выражение.Аргумент = "*" Тогда
			МассивСтрок.Добавить("*");
		Иначе	
			ВыражениеВМассивСтрок(Выражение.Аргумент, Табуляции + Символы.Таб);
		КонецЕсли;	
		МассивСтрок.Добавить(")");
	ИначеЕсли Выражение.Тип = "ФункцияЧастьПериодаЧислом" Тогда
		ФункцияФункцияЧастьПериодаЧисломВМассивСтрок(Выражение, Табуляции);	
	ИначеЕсли Выражение.Тип = "ФункцияНачалоПериода" Тогда
		ФункцияНачалоПериодаВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ФункцияКонецПериода" Тогда
		ФункцияКонецПериодаВМассивСтрок(Выражение, Табуляции);	
	ИначеЕсли Выражение.Тип = "ФункцияДобавитьКДате" Тогда
		ФункцияДобавитьКДатеВМассивСтрок(Выражение, Табуляции);	
	ИначеЕсли Выражение.Тип = "ФункцияДатаВремя" Тогда
		ФункцияДатаВремяВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ФункцияIsNull" Тогда
		ФункцияIsNullВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ФункцияПредставление" Тогда
		ФункцияПредставлениеВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ФункцияПредставлениеСсылки" Тогда
		ФункцияПредставлениеСсылкиВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ФункцияТипЗначения" Тогда
		ФункцияТипЗначенияВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ФункцияЗначение" Тогда
		ФункцияЗначениеВМассивСтрок(Выражение, Табуляции);	
	ИначеЕсли Выражение.Тип = "ФункцияТип" Тогда
		ФункцияТипВМассивСтрок(Выражение, Табуляции);
	ИначеЕсли Выражение.Тип = "ФункцияРазностьДат" Тогда 	
		ФункцияРазностьДатВМассивСтрок(Выражение, Табуляции);
	КонецЕсли;	
КонецПроцедуры	

Процедура БинарнаяОперацияВМассивСтрок(Выражение, Знач Табуляции, Родитель, ТабуляцияДляПравойЧасти = Ложь)
	// TODO Проверяем такие выражения
	
	//ВЫБРАТЬ
	//	ИСТИНА
	//			И (ИСТИНА
	//				ИЛИ ИСТИНА)
	//		ИЛИ ИСТИНА
	//			И ИСТИНА
	//		ИЛИ ИСТИНА КАК Поле1
	
//	Если Выражение.Операция = "И" Тогда
//		ЧастиВыраженияПоИ = МодельЗапросаУтилиты.УсловиеВМассивВыраженийПоИ(Выражение);
//		ВыражениеВМассивСтрок(ЧастиВыраженияПоИ[0], Табуляции, Родитель);
//		Для Индекс = 1 По ЧастиВыраженияПоИ.ВГраница() Цикл
//			МассивСтрок.Добавить(Символы.ПС);	
//			МассивСтрок.Добавить(Табуляции + "И ");
//			ВыражениеВМассивСтрок(ЧастиВыраженияПоИ[Индекс], Табуляции, Родитель);
//		КонецЦикла;
//	Иначе
	ВыражениеВМассивСтрок(Выражение.ЛеваяЧасть, Табуляции, Выражение);
	ТекущиеТабуляции = Табуляции;
	Если Выражение.Операция = "ИЛИ" 
		Или Выражение.Операция = "И"  Тогда
		
		МассивСтрок.Добавить(Символы.ПС);
		
		Если Родитель <> Неопределено
			И Родитель.Тип = "БинарнаяОперация"
			И Родитель.Операция <> Выражение.Операция Тогда
			
			ТекущиеТабуляции = ТекущиеТабуляции + Символы.Таб;
		ИначеЕсли Родитель = Неопределено 
			И Выражение.Операция = "ИЛИ" 
			И Не ТабуляцияДляПравойЧасти Тогда
			
			ТекущиеТабуляции = ТекущиеТабуляции + Символы.Таб;	
		КонецЕсли;	
		
//		Если Родитель = Неопределено
//			Или Родитель.Тип <> "БинарнаяОперация" Тогда
//			//ТекущиеТабуляции = ТекущиеТабуляции + Символы.Таб;
//		ИначеЕсли Родитель.Операция = "ИЛИ"
//			И Выражение.Операция = "И" Тогда
//			
//			ТекущиеТабуляции = ТекущиеТабуляции + Символы.Таб;
//			//МассивСтрок.Добавить(Символы.Таб);
//		КонецЕсли;	
		МассивСтрок.Добавить(ТекущиеТабуляции);
	Иначе
		МассивСтрок.Добавить(" ");
	КонецЕсли;
	
	МассивСтрок.Добавить(Выражение.Операция);
	МассивСтрок.Добавить(" ");
	ВыражениеВМассивСтрок(Выражение.ПраваяЧасть, ТекущиеТабуляции, Выражение);
//	КонецЕсли;
КонецПроцедуры

Процедура СписокВыраженийВВМассивСтрок(СписокВыражений, Табуляции) Экспорт
	МассивВыраженийВМассивСтрок(СписокВыражений.Элементы, Табуляции);	
КонецПроцедуры

Процедура СписокВыраженийВВМассивСтрокСПереносами(СписокВыражений, Табуляции) Экспорт
	Сч = 1;
	Для Каждого Выражение Из СписокВыражений Цикл
		МассивСтрок.Добавить(Символы.ПС);
		МассивСтрок.Добавить(Табуляции);
		ВыражениеВМассивСтрок(Выражение, Табуляции);
		Если Сч <> СписокВыражений.Количество() Тогда
			МассивСтрок.Добавить(",");
		КонецЕсли;
		Сч = Сч + 1;
	КонецЦикла;		
КонецПроцедуры

Процедура МассивВыраженийВМассивСтрок(МассивВыражений, Табуляции) Экспорт
	ЭтоПервоеВыражение = Истина;
	Для Каждого Выражение Из МассивВыражений Цикл
		Если ЭтоПервоеВыражение Тогда
			ЭтоПервоеВыражение = Ложь;
		Иначе
			МассивСтрок.Добавить(", ");
		КонецЕсли;		
		ВыражениеВМассивСтрок(Выражение, Табуляции);
	КонецЦикла;			
КонецПроцедуры

#КонецОбласти

#Область СлужебныеПроцедурыИФункции

Процедура СписокПолейСПсевдонимамиВМассивСтрок(ВыбираемыеПоля, Табуляции) Экспорт
	МассивСтрок.Добавить(Символы.ПС);
	
	ТекущиеТабуляции = Табуляции + Символы.Таб;
	
	ЭтоПервоеПоле = Истина;
	Для Каждого Поле Из ВыбираемыеПоля Цикл
		Если ЭтоПервоеПоле Тогда
			ЭтоПервоеПоле = Ложь;
		Иначе
			МассивСтрок.Добавить(",");
			МассивСтрок.Добавить(Символы.ПС);
		КонецЕсли;	
		МассивСтрок.Добавить(ТекущиеТабуляции);
		Если Поле.Выражение = "*" Тогда
			МассивСтрок.Добавить("*");	
			Продолжить;
		КонецЕсли;	
		
		ВыражениеВМассивСтрок( Поле.Выражение, ТекущиеТабуляции);
		
		Если Поле.Псевдоним = Неопределено Тогда
			Псевдоним = Неопределено;
		Иначе 
			Псевдоним = Поле.Псевдоним; 	
		КонецЕсли;	
		
		Если Псевдоним <> Неопределено Тогда
			МассивСтрок.Добавить(" КАК ");
			МассивСтрок.Добавить(Псевдоним);
		КонецЕсли;	
			
	КонецЦикла;	
КонецПроцедуры	

Процедура ОператорВыбораВМассивСтрок(ОператорВыбор, Табуляции)
	МассивСтрок.Добавить("ВЫБОР");
	Если ОператорВыбор.ВыражениеВыбора <> Неопределено Тогда
		МассивСтрок.Добавить(" ");
		ВыражениеВМассивСтрок(ОператорВыбор.ВыражениеВыбора, Табуляции);
	КонецЕсли;
	
	ТекущиеТабуляции = Табуляции + Символы.Таб;
	Для Каждого Альтернатива Из ОператорВыбор.АльтернативыВыбора Цикл
		МассивСтрок.Добавить(Символы.ПС);
		МассивСтрок.Добавить(ТекущиеТабуляции);
		МассивСтрок.Добавить("КОГДА ");
		ВыражениеВМассивСтрок(Альтернатива.Условие, ТекущиеТабуляции + Символы.Таб);
		МассивСтрок.Добавить(Символы.ПС);
		МассивСтрок.Добавить(ТекущиеТабуляции + Символы.Таб);
		МассивСтрок.Добавить("ТОГДА ");
		ВыражениеВМассивСтрок(Альтернатива.Действие, ТекущиеТабуляции + Символы.Таб + Символы.Таб);
	КонецЦикла;
	
	Если ОператорВыбор.Иначе <> Неопределено Тогда
		МассивСтрок.Добавить(Символы.ПС);
		МассивСтрок.Добавить(ТекущиеТабуляции);
		МассивСтрок.Добавить("ИНАЧЕ ");
		ВыражениеВМассивСтрок(ОператорВыбор.Иначе, ТекущиеТабуляции + Символы.Таб);
	КонецЕсли;	
	
	МассивСтрок.Добавить(Символы.ПС);
	МассивСтрок.Добавить(Табуляции);
	МассивСтрок.Добавить("КОНЕЦ");	
КонецПроцедуры	

Процедура КонстантаВМассивСтрок(Константа, Табуляции)
	Если ТипЗнч(Константа.Значение) = Тип("Строка") Тогда
		МассивСтрок.Добавить("""");
		МассивСтрок.Добавить(Константа.Значение);
		МассивСтрок.Добавить("""");
	ИначеЕсли ТипЗнч(Константа.Значение) = Тип("Число") Тогда
		МассивСтрок.Добавить(Формат(Константа.Значение, "ЧН=0; ЧГ="));
	ИначеЕсли Константа.Значение = Истина Тогда
		МассивСтрок.Добавить("ИСТИНА");
	ИначеЕсли Константа.Значение = Ложь Тогда
		МассивСтрок.Добавить("ЛОЖЬ");
	ИначеЕсли Константа.Значение = Null Тогда
		МассивСтрок.Добавить("NULL");
	ИначеЕсли Константа.Значение = Неопределено Тогда
		МассивСтрок.Добавить("НЕОПРЕДЕЛЕНО");	
	КонецЕсли;	
КонецПроцедуры	

Процедура ФункцияТипВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("ТИП(");
	ВыражениеВМассивСтрок(ОписаниеФункции.Аргумент, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(")");	
КонецПроцедуры

Процедура ФункцияЗначениеВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("ЗНАЧЕНИЕ(");
	ЭтоПервыйЭлемент = Истина;
	Для Каждого Элемент Из ОписаниеФункции.ЧастиПути Цикл
		Если ЭтоПервыйЭлемент Тогда
			ЭтоПервыйЭлемент = Ложь;
		Иначе
			МассивСтрок.Добавить(".");
		КонецЕсли;
		МассивСтрок.Добавить(Элемент);
	КонецЦикла;	
	МассивСтрок.Добавить(")");	
КонецПроцедуры

Процедура ФункцияДатаВремяВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("ДАТАВРЕМЯ(");
	ЭтоПервыйПараметр = Истина;
	Для Каждого Аргумент Из ОписаниеФункции.Аргументы Цикл
		Если ЭтоПервыйПараметр Тогда
			ЭтоПервыйПараметр = Ложь;
		Иначе
			МассивСтрок.Добавить(", ");
		КонецЕсли;
		МассивСтрок.Добавить(Формат(Аргумент, "ЧН=0; ЧГ="));
	КонецЦикла;	
	МассивСтрок.Добавить(")");	
КонецПроцедуры

Процедура ФункцияТипЗначенияВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("ТИПЗНАЧЕНИЯ(");
	ВыражениеВМассивСтрок(ОписаниеФункции.Аргумент, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(")");	
КонецПроцедуры

Процедура ФункцияПредставлениеВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("ПРЕДСТАВЛЕНИЕ(");
	ВыражениеВМассивСтрок(ОписаниеФункции.Аргумент, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(")");	
КонецПроцедуры

Процедура ФункцияПредставлениеСсылкиВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("ПРЕДСТАВЛЕНИЕССЫЛКИ(");
	ВыражениеВМассивСтрок(ОписаниеФункции.Аргумент, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(")");	
КонецПроцедуры

Процедура ФункцияIsNullВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("ЕСТЬNULL(");
	ВыражениеВМассивСтрок(ОписаниеФункции.ПроверяемоеЗначение, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(", ");
	ВыражениеВМассивСтрок(ОписаниеФункции.Действие, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(")");	
КонецПроцедуры

Процедура ФункцияРазностьДатВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("РАЗНОСТЬДАТ(");
	ВыражениеВМассивСтрок(ОписаниеФункции.Дата1, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(", ");
	ВыражениеВМассивСтрок(ОписаниеФункции.Дата2, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(", ");
	МассивСтрок.Добавить(ВРег(ОписаниеФункции.ТипПериода));
	МассивСтрок.Добавить(")");	
КонецПроцедуры

Процедура ФункцияДобавитьКДатеВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("ДОБАВИТЬКДАТЕ(");
	ВыражениеВМассивСтрок(ОписаниеФункции.Дата, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(", ");
	МассивСтрок.Добавить(ВРег(ОписаниеФункции.ТипПериода));
	МассивСтрок.Добавить(", ");
	ВыражениеВМассивСтрок(ОписаниеФункции.Сдвиг, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(")");	
КонецПроцедуры	

Процедура ФункцияНачалоПериодаВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("НАЧАЛОПЕРИОДА(");
	ВыражениеВМассивСтрок(ОписаниеФункции.Дата, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(", ");
	МассивСтрок.Добавить(ВРег(ОписаниеФункции.ТипПериода));
	МассивСтрок.Добавить(")");
КонецПроцедуры	

Процедура ФункцияКонецПериодаВМассивСтрок(ОписаниеФункции, Табуляции)
	МассивСтрок.Добавить("КОНЕЦПЕРИОДА(");
	ВыражениеВМассивСтрок(ОписаниеФункции.Дата, Табуляции + Символы.Таб);
	МассивСтрок.Добавить(", ");
	МассивСтрок.Добавить(ВРег(ОписаниеФункции.ТипПериода));
	МассивСтрок.Добавить(")");
КонецПроцедуры

Процедура ФункцияФункцияЧастьПериодаЧисломВМассивСтрок(ОписаниеФункциия, Табуляции)
	МассивСтрок.Добавить(ВРег(ОписаниеФункциия.ИмяФункции));
	МассивСтрок.Добавить("(");
	ВыражениеВМассивСтрок(ОписаниеФункциия.Аргумент, Табуляции + Символы.Таб);	
	МассивСтрок.Добавить(")");
КонецПроцедуры	

Процедура СписокВыраженийУпорядочиванияВМассивСтрок(ВыраженияУпорядочивания, Знач Табуляции) Экспорт
	ЭтоПервоеВыражение = Истина;
	Для Каждого ЭлементУпорядочивания Из ВыраженияУпорядочивания Цикл
		Если ЭтоПервоеВыражение Тогда
			ЭтоПервоеВыражение = Ложь;
			МассивСтрок.Добавить(Табуляции);
		Иначе
			МассивСтрок.Добавить(",");
			МассивСтрок.Добавить(Символы.ПС);
			МассивСтрок.Добавить(Табуляции);	
		КонецЕсли;
		
		ВыражениеВМассивСтрок(ЭлементУпорядочивания.Выражение, Табуляции);

		Если ЭлементУпорядочивания.Иерархия Тогда
			МассивСтрок.Добавить(" ИЕРАРХИЯ");
		КонецЕсли;
		
		Если ЭлементУпорядочивания.Направление = "Убыв" Тогда
			МассивСтрок.Добавить(" УБЫВ");
		КонецЕсли;	
	КонецЦикла;		
КонецПроцедуры	

// TODO нужна функция ЧислоСтрокой, т.к. мы не должны зависеть от локали 

#КонецОбласти

Источники = Новый Соответствие();
ИсточникиВнешнегоЗапроса = Новый Соответствие();
Колонки = Новый Соответствие();
ВыводитьПсевдонимыИсточников = Истина;

#Иначе
ВызватьИсключение НСтр("ru = 'Недопустимый вызов объекта на клиенте.'");
#КонецЕсли
