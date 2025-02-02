#Область СлужебныеПроцедурыИФункции

Функция СоздатьПостроительМодели(МодельЗапроса, ИндексЗапроса = 0, ИндексОператораЗапроса = 0, СписокДоступныхВТ = Неопределено) Экспорт
	УстановитьПривилегированныйРежим(Истина);
	Построитель = Обработки.ПостроительМоделиЗапроса.Создать();
	УстановитьПривилегированныйРежим(Ложь);
	
	Возврат Построитель.Инициализировать(МодельЗапроса, ИндексЗапроса, ИндексОператораЗапроса, СписокДоступныхВТ);
КонецФункции

Функция СоздатьПакетЗапросов() Экспорт
	МодельЗапроса = ЭлементыМоделиЗапроса.НовыйПакетЗапросов();
	Построитель = СоздатьПостроительМодели(МодельЗапроса, -1, -1);
	Возврат Построитель.ДобавитьЗапросВыбора().ПолучитьМодель();
КонецФункции

Функция СоздатьВложенныйЗапрос() Экспорт
	МодельЗапроса = ЭлементыМоделиЗапроса.НовыйЗапросВыбора();
	Построитель = СоздатьПостроительМодели(МодельЗапроса, -1, -1);
	Возврат Построитель.ДобавитьОператорЗапроса().ПолучитьМодель();	
КонецФункции

// Используемые поля источников.
// 
// Параметры:
//  ЗапросВыбора - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
//  ИндексОператора - Число
// 
// Возвращаемое значение:
//  Соответствие из КлючИЗначение:
//	* Ключ - УникальныйИдентификатор
//	* Значение - Строка
Функция ИспользуемыеПоляИсточников(ЗапросВыбора, ИндексОператора) Экспорт
	ИспользуемыеПоля = Новый Соответствие();
	
	Оператор = ЗапросВыбора.Операторы[ИндексОператора];
	
	Для Каждого Поле Из Оператор.ВыбираемыеПоля Цикл
		ЗаполнитьИспользуемыеПоляИзВыражения(ИспользуемыеПоля, Поле.Выражение);		
	КонецЦикла;
	
	Для Каждого Источник Из Оператор.Источники.Элементы Цикл
		Для Каждого Соединение Из Источник.Соединения Цикл
			ЗаполнитьИспользуемыеПоляИзВыражения(ИспользуемыеПоля, Соединение.Условие);	
		КонецЦикла;
	КонецЦикла;
	
	Для Каждого Группировка Из Оператор.Группировка.Элементы Цикл
		ЗаполнитьИспользуемыеПоляИзВыражения(ИспользуемыеПоля, Группировка);			
	КонецЦикла;
	
	Для Каждого ВыражениеМодели Из Оператор.Отбор Цикл
		ЗаполнитьИспользуемыеПоляИзВыражения(ИспользуемыеПоля, ВыражениеМодели);
	КонецЦикла;
	Для Каждого ВыражениеМодели Из Оператор.ОтборСгруппированных Цикл
		ЗаполнитьИспользуемыеПоляИзВыражения(ИспользуемыеПоля, ВыражениеМодели);
	КонецЦикла;
	
	Для Каждого ЭлементПорялка Из ЗапросВыбора.Порядок Цикл
		ЗаполнитьИспользуемыеПоляИзВыражения(ИспользуемыеПоля, ЭлементПорялка.Выражение);
	КонецЦикла;	
	
	Для Каждого КонтрольнаяТочка Из ЗапросВыбора.КонтрольныеТочкиИтогов Цикл
		ЗаполнитьИспользуемыеПоляИзВыражения(ИспользуемыеПоля, КонтрольнаяТочка.Выражение);
	КонецЦикла;	
	
	Возврат ИспользуемыеПоля;
КонецФункции

// Получить используемые параметры.
// 
// Параметры:
//  ТекстЗапроса - Строка
// 
// Возвращаемое значение:
//  Соответствие из КлючИЗначение:
//  * Ключ - Строка
//  * Значение - см. ЭлементыМоделиЗапроса.НовыйОписаниеПараметраЗапроса
Функция ПолучитьИспользуемыеПараметры(ТекстЗапроса) Экспорт
	МодельЗапроса = ОбработкаМоделиЗапроса.РазобратьЗапрос(ТекстЗапроса);
	ИспользуемыеПараметрыЗапроса = Новый Соответствие();
	Для Каждого ЗапросПакета Из МодельЗапроса.Элементы Цикл
		Если ЗапросПакета.Тип = "ЗапросВыбора" Тогда
			ЗаполнитьИспользуемыеВЗапросеПараметры(ИспользуемыеПараметрыЗапроса, ЗапросПакета);	
		КонецЕсли;
	КонецЦикла;
	
	Результат = Новый Массив();
	Для Каждого КлючЗначение Из ИспользуемыеПараметрыЗапроса Цикл
	 	Результат.Добавить(КлючЗначение.Значение);
	КонецЦикла;
	 
	Возврат Результат;
КонецФункции

Функция НеобходимаГруппировка(ОператорЗапроса) Экспорт
	Если ЗначениеЗаполнено(ОператорЗапроса.ОтборСгруппированных) Тогда
		Возврат Истина;
	КонецЕсли;	  
	
	КоличествоАгригируемыхПолей = КоличествоАгригируемыхПолей(ОператорЗапроса.ВыбираемыеПоля); 
	Возврат КоличествоАгригируемыхПолей > 0
		И КоличествоАгригируемыхПолей <> ОператорЗапроса.ВыбираемыеПоля.Количество()
КонецФункции	

Функция ДополнительныеПоляГруппировки(ОператорЗапроса) Экспорт 
	ДополнительныеПоляГруппировки = Новый Массив;
	
	ПоляИсточниковГруппировки = Новый Соответствие;
	
	Для Каждого ЭлементГруппировки Из ОператорЗапроса.Группировка.Элементы Цикл
		ПолеИсточника = ОбработкаМоделиЗапроса.ПолеИстчоникаИзВыражения(ЭлементГруппировки);
		Если ПолеИсточника <> Неопределено Тогда
			ПоляИсточниковГруппировки.Вставить(Строка(ПолеИсточника.ИдентификаторИсточника) + "." + ВРег(ПолеИсточника.ИмяПоля), Истина);
		КонецЕсли;		
	КонецЦикла;	
	
	ОставшиесяПоля = Новый Массив;
	Для Каждого Поле Из ОператорЗапроса.ВыбираемыеПоля Цикл
		Если Поле.Выражение.ИспользуетсяАгрегатнаяФункция Тогда
			Продолжить;
		КонецЕсли;
		
		ПолеИсточника = ОбработкаМоделиЗапроса.ПолеИстчоникаИзВыражения(Поле.Выражение);
		Если ПолеИсточника = Неопределено Тогда
			ОставшиесяПоля.Добавить(Поле);
			Продолжить;	
		КонецЕсли;
		
		Ключ = Строка(ПолеИсточника.ИдентификаторИсточника) + "." + ВРег(ПолеИсточника.ИмяПоля); 
		Если ПоляИсточниковГруппировки.Получить(Ключ) <> Истина Тогда
			ДополнительныеПоляГруппировки.Добавить(Поле.Выражение);
			ПоляИсточниковГруппировки.Вставить(Ключ, Истина);
		КонецЕсли;	
	КонецЦикла;	
	
	Для Каждого Поле Из ОставшиесяПоля Цикл 
		ДобавлятьВГруппировку = Ложь;
		Для Каждого КлючЗначение Из Поле.Выражение.ПоляИсточников Цикл
			Если ПоляИсточниковГруппировки.Получить(КлючЗначение.Ключ) = Неопределено Тогда
				ДобавлятьВГруппировку = Истина;
				Прервать;
			КонецЕсли;			
		КонецЦикла;  
		
		Если ДобавлятьВГруппировку Тогда
			Если Не ПолеВходитВГруппировку(Поле.Выражение, ОператорЗапроса.Группировка.Элементы) Тогда
				ДополнительныеПоляГруппировки.Добавить(Поле.Выражение);
			КонецЕсли;	
		КонецЕсли;		
	КонецЦикла;	
	
	Возврат ДополнительныеПоляГруппировки;
КонецФункции	

Функция КонтекстОбработкиВыражения(ОператорЗапроса, ИндексПакетаЗапроса) Экспорт
	Контекст = ОбработкаМоделиЗапроса.КонтекстОбработкиВыражения();	
	Контекст.ИндексЗапросаПакета = ИндексПакетаЗапроса;
	
	Для Каждого Источник Из ОператорЗапроса.Источники.Элементы Цикл
		Контекст.ИсточникиПоИдентификаторам.Вставить(Источник.ИдентификаторИсточника, Источник);
		Контекст.ИспользуемыеТаблицы.Вставить(ВРег(Источник.Источник.Псевдоним), Источник);
	КонецЦикла;   
	
	Возврат Контекст; 
КонецФункции

Функция АгрегатнаяФункцияДляВыражения(Выражение, Контекст) Экспорт 
	КопияВыражения = СкопироватьЭлементМоделиЗапроса(Выражение);
	ОбработкаМоделиЗапроса.ОбработатьВыражение(КопияВыражения.Значение, Контекст, КопияВыражения);
	Возврат АгрегаттнаяФункцияПоТипуЗначения(КопияВыражения.ТипЗначения);
КонецФункции	

Функция АгрегаттнаяФункцияПоТипуЗначения(ТипЗначения) Экспорт
	Если ТипЗначения.Типы().Количество() = 1
		И ТипЗначения.СодержитТип(Тип("Число")) Тогда
		
		АгрегатнаяФункция = ЭлементыМоделиЗапроса.НовыйАгрегатнаяФункция();  
		АгрегатнаяФункция.ИмяФункции = "СУММА";
	Иначе
		АгрегатнаяФункция = ЭлементыМоделиЗапроса.НовыйАгрегатнаяФункцияКоличество();
		АгрегатнаяФункция.Различные = Истина;
	КонецЕсли;   
		
	Возврат АгрегатнаяФункция;
КонецФункции

Функция СписокВыбораАгрегируемогоПоля(Выражение, ОператорЗапроса, ИндексЗапроса) Экспорт
	СписокВыбора = Новый СписокЗначений();
	
	КопияЗначенияВыражения = СкопироватьЭлементМоделиЗапроса(Выражение.Значение);
	КопияВыражения = ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса();
	КопияВыражения.Значение = КопияЗначенияВыражения;
	
	ИспользованиеАгрегатныхФункций = НайтиИспользованиеАгрегатныхФункций(КопияВыражения);
	
	Если ИспользованиеАгрегатныхФункций.Количество() <> 1 Тогда
		Возврат СписокВыбора;
	КонецЕсли;
	
	// TODO не корректный список выбора
	ИспользованиеФункции = ИспользованиеАгрегатныхФункций[0];
		
	Аргумент = ИспользованиеАгрегатныхФункций[0].ВыражениеАгрегатнойФункции.Аргумент;
	ВыражениеАргумента = ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса();
	ВыражениеАргумента.Значение = Аргумент;
	
	Контекст = КонтекстОбработкиВыражения(ОператорЗапроса, ИндексЗапроса);
	ОбработкаМоделиЗапроса.ОбработатьВыражение(ВыражениеАргумента.Значение, Контекст, ВыражениеАргумента);
	
	ГенераторТекстов = ГенерацияТекстовЗапросов.СоздатьГенераторТекстовВыражений();
	ГенераторТекстов.УстановитьИсточники(ОператорЗапроса.Источники.Элементы);
	
	
	АгрегатнаяФункция = ЭлементыМоделиЗапроса.НовыйАгрегатнаяФункцияКоличество();
	АгрегатнаяФункция.Аргумент = Аргумент;
	ИспользованиеФункции.Родитель[ИспользованиеФункции.СвойствоРодителя] = АгрегатнаяФункция;
	Представление = ГенерацияТекстовЗапросов.ВыражениеВСтроку(КопияВыражения, ГенераторТекстов);
	СписокВыбора.Добавить("КОЛИЧЕСТВО", Представление);
	
	АгрегатнаяФункция.Различные = Истина;
	Представление = ГенерацияТекстовЗапросов.ВыражениеВСтроку(КопияВыражения, ГенераторТекстов);
	СписокВыбора.Добавить("КОЛИЧЕСТВО_РАЗЛИЧНЫЕ", Представление);
	
	АгрегатнаяФункция = ЭлементыМоделиЗапроса.НовыйАгрегатнаяФункция();
	АгрегатнаяФункция.Аргумент = Аргумент;
	АгрегатнаяФункция.ИмяФункции = "МИНИМУМ";
	ИспользованиеФункции.Родитель[ИспользованиеФункции.СвойствоРодителя] = АгрегатнаяФункция;
	Представление = ГенерацияТекстовЗапросов.ВыражениеВСтроку(КопияВыражения, ГенераторТекстов);
	СписокВыбора.Добавить("МИНИМУМ", Представление);
	
	АгрегатнаяФункция.ИмяФункции = "МАКСИМУМ";
	Представление = ГенерацияТекстовЗапросов.ВыражениеВСтроку(КопияВыражения, ГенераторТекстов);
	СписокВыбора.Добавить("МАКСИМУМ", Представление);
	
	Если МодельЗапросаТипы.ЭтоПолеТипа(ВыражениеАргумента.ТипЗначения, Тип("Число")) Тогда
		АгрегатнаяФункция.ИмяФункции = "СУММА";
		Представление = ГенерацияТекстовЗапросов.ВыражениеВСтроку(КопияВыражения, ГенераторТекстов);
		СписокВыбора.Добавить("СУММА", Представление);
		
		АгрегатнаяФункция.ИмяФункции = "СРЕДНЕЕ";
		Представление = ГенерацияТекстовЗапросов.ВыражениеВСтроку(КопияВыражения, ГенераторТекстов);
		СписокВыбора.Добавить("СРЕДНЕЕ", Представление);
	КонецЕсли;   
	
	Возврат СписокВыбора;
КонецФункции

Функция НайтиПоляПоВыражению(Оператор, Выражение) Экспорт  
	Индексы = Новый Массив;
	Для Индекс = 0 По Оператор.ВыбираемыеПоля.ВГраница() Цикл
		ВыражениеПоля = Оператор.ВыбираемыеПоля[Индекс].Выражение;
		Если ВыраженияМоделиЗапросаРавны(ВыражениеПоля, Выражение) Тогда
			Индексы.Добавить(Индекс);
		КонецЕсли;		
	КонецЦикла;
	
	Возврат Индексы;
КонецФункции  

Функция НайтиПолеОператораПоВыражению(Оператор, Выражение) Экспорт
	Индексы = НайтиПоляПоВыражению(Оператор, Выражение);
	
	Если ЗначениеЗаполнено(Индексы) Тогда
		Возврат Индексы[0];
	Иначе
		Возврат Неопределено;
	КонецЕсли;
КонецФункции

Функция ВыраженияМоделиЗапросаРавны(Выражение1, Выражение2) Экспорт 
	Если Выражение1.ПоляИсточников.Количество() <> Выражение2.ПоляИсточников.Количество() Тогда
		Возврат Ложь;	
	КонецЕсли;	
	
	Для Каждого КлючЗначение Из Выражение1.ПоляИсточников Цикл
		Если Выражение2.ПоляИсточников.Получить(КлючЗначение.Ключ) = Неопределено Тогда
			Возврат Ложь;
		КонецЕсли;	
	КонецЦикла;	   
	
	Возврат ВыраженияРавны(Выражение1.Значение, Выражение2.Значение); 
КонецФункции	

Функция ВыраженияРавны(Выражение1, Выражение2) Экспорт
	Если ТипЗнч(Выражение1) <> ТипЗнч(Выражение2) Тогда
		Возврат Ложь;
	КонецЕсли;
	
	Если ТипЗнч(Выражение1) = Тип("Структура") Тогда
		Возврат СтруктурыРавны(Выражение1, Выражение2);
	ИначеЕсли ТипЗнч(Выражение1) = Тип("Массив") Тогда
		Возврат МассивыРавны(Выражение1, Выражение2);
	ИначеЕсли ТипЗнч(Выражение1) = Тип("Строка") Тогда
		Возврат ВРег(Выражение1) = ВРег(Выражение2);
	Иначе
		Возврат Выражение1 = Выражение2;
	КонецЕсли;	
КонецФункции  

Функция СкопироватьЭлементМоделиЗапроса(ЭлементМодели) Экспорт
	Если ТипЗнч(ЭлементМодели) = Тип("Массив") Тогда
		Возврат СкопироватьМассив(ЭлементМодели);
	ИначеЕсли ТипЗнч(ЭлементМодели) = Тип("Соответствие") Тогда
		Возврат СкопироватьСоответствие(ЭлементМодели);
	ИначеЕсли ТипЗнч(ЭлементМодели) = Тип("Структура") Тогда	
		Если ЭлементМодели.Тип = "ОписаниеВременнойТаблицы" Тогда
			Возврат ЭлементМодели;
		КонецЕсли;
		
		Копия = СкопироватьСтруктуру(ЭлементМодели);
		Если Копия.Тип = "ЗапросВыбора" Тогда
			Для Каждого Колонка Из Копия.Колонки Цикл
				Копия.КолонкиПоПсевдонимам.Вставить(ВРег(Колонка.Имя), Колонка); 
			КонецЦикла;
		КонецЕсли;
		Возврат Копия;
	Иначе
		Возврат ЭлементМодели;
	КонецЕсли;	
КонецФункции 

// Поля оператора по псевдонимам.
// 
// Параметры:
//  ОператорЗапроса см. ЭлементыМоделиЗапроса.НовыйОператорЗапроса
// 
// Возвращаемое значение:
//  Соответствие из КлючИЗначение:
//   * Ключ - Строка
//   * Значение - см. ЭлементыМоделиЗапроса.НовыйПолеЗапроса 
//	 
Функция ПоляОператораПоПсевдонимам(ОператорЗапроса) Экспорт
	ПоляПоПсевдонимам = Новый Соответствие();
	
	Для Каждого Поле Из ОператорЗапроса.ВыбираемыеПоля Цикл
		ПоляПоПсевдонимам.Вставить(ВРег(Поле.Псевдоним), Поле);
	КонецЦикла;
	
	Возврат ПоляПоПсевдонимам;
КонецФункции

// Поля оператора по псевдонимам.
// 
// Параметры:
//  ЗапросВыбора см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
// 
// Возвращаемое значение:
//  Массив из см. ПоляОператораПоПсевдонимам
Функция ПоляОператоровПоПсевдонимам(ЗапросВыбора) Экспорт
	ПоляОператоровПоПсевдонимам = Новый Массив();
	
	Для Каждого Оператор Из ЗапросВыбора.Операторы Цикл
		ПоляОператоровПоПсевдонимам.Добавить(ПоляОператораПоПсевдонимам(Оператор));
	КонецЦикла;
	
	Возврат ПоляОператоровПоПсевдонимам
КонецФункции

// Поля оператора по псевдонимам.
// 
// Параметры:
//  ОператорЗапроса см. ЭлементыМоделиЗапроса.НовыйОператорЗапроса
// 
// Возвращаемое значение:
//  Массив из см. ПоляОператораПоПсевдонимам
Функция ОписаниеВТ(ЗапросВыбора) Экспорт
	ПоляОператоровПоПсевдонимам = Новый Массив();
	
	Для Каждого Оператор Из ЗапросВыбора.Операторы Цикл
		ПоляОператоровПоПсевдонимам.Добавить(ПоляОператораПоПсевдонимам(Оператор));
	КонецЦикла;
	
	Возврат ПоляОператоровПоПсевдонимам
КонецФункции

// Новый использование агрегатной функции.
// 
// Возвращаемое значение:
//  Структура - Новый использование агрегатной функции:
// * Родитель - Произвольный
// * СвойствоРодителя - 
// 	- Строка
// 	- Число
// * ВыражениеАгрегатнойФункции - Произвольный
Функция НовыйИспользованиеАгрегатнойФункции()
	ИспользованиеАгрегатнойФункции = Новый Структура();
	ИспользованиеАгрегатнойФункции.Вставить("Родитель");	
	ИспользованиеАгрегатнойФункции.Вставить("СвойствоРодителя");
	ИспользованиеАгрегатнойФункции.Вставить("ВыражениеАгрегатнойФункции");
	
	Возврат ИспользованиеАгрегатнойФункции;
КонецФункции

// Найти использование агрегатных функций.
// 
// Параметры:
//  Выражение - Произвольный
// 
// Возвращаемое значение:
//  Массив из см. НовыйИспользованиеАгрегатнойФункции
Функция НайтиИспользованиеАгрегатныхФункций(Выражение) Экспорт
	ИспользованиеАгрегатныхФункций = Новый Массив();
	НайтиИспользованиеАгрегатныхФункцийРекурсивно(ИспользованиеАгрегатныхФункций, Выражение);
	Возврат ИспользованиеАгрегатныхФункций;		
КонецФункции

Функция ВременнаяТаблицаДоступнаВЗапросе(ОписаниеВТ, ИндексЗапросаПакета) Экспорт
	Возврат ОписаниеВТ.ИндексЗапросаСоздания <> -1
		И ОписаниеВТ.ИндексЗапросаСоздания < ИндексЗапросаПакета
		И (ОписаниеВТ.ИндексЗапросаУничтожения = -1
		Или ОписаниеВТ.ИндексЗапросаУничтожения > ИндексЗапросаПакета);	
КонецФункции

Функция НайтиИспользованиеАгрегатныхФункцийРекурсивно(ИспользованиеАгрегатныхФункций, Выражение)
	Если ТипЗнч(Выражение) = Тип("Структура") Тогда
		Для Каждого КлючЗначение Из Выражение Цикл
			Если ЭтоАгрегатнаяФункция(КлючЗначение.Значение) Тогда
				Использование = НовыйИспользованиеАгрегатнойФункции();
				Использование.ВыражениеАгрегатнойФункции = КлючЗначение.Значение;
				Использование.Родитель = Выражение;
				Использование.СвойствоРодителя = КлючЗначение.Ключ;
				
				ИспользованиеАгрегатныхФункций.Добавить(Использование);	
			ИначеЕсли ТипЗнч(КлючЗначение.Значение) = Тип("Массив") 
				Или ТипЗнч(КлючЗначение.Значение) = Тип("Структура") Тогда 
				
				НайтиИспользованиеАгрегатныхФункцийРекурсивно(ИспользованиеАгрегатныхФункций, КлючЗначение.Значение);
			КонецЕсли;
		КонецЦикла;	
	ИначеЕсли ТипЗнч(Выражение) = Тип("Массив") Тогда 
		Для Индекс = 0 По Выражение.ВГраница() Цикл
			Элемент = Выражение[Индекс];
			Если ЭтоАгрегатнаяФункция(Элемент) Тогда
				Использование = НовыйИспользованиеАгрегатнойФункции();
				Использование.ВыражениеАгрегатнойФункции = Элемент;
				Использование.Родитель = Выражение;
				Использование.СвойствоРодителя = Индекс;
				
				ИспользованиеАгрегатныхФункций.Добавить(Использование);
			ИначеЕсли ТипЗнч(Элемент) = Тип("Массив") Или ТипЗнч(Элемент) = Тип("Структура") Тогда 
				НайтиИспользованиеАгрегатныхФункцийРекурсивно(ИспользованиеАгрегатныхФункций, Элемент);	
			КонецЕсли;		
		КонецЦикла;		
	КонецЕсли;
КонецФункции

Функция ЭтоАгрегатнаяФункция(Выражение)
	Если ТипЗнч(Выражение) <> Тип("Структура")
		Или Не Выражение.Свойство("Тип") Тогда
			
		Возврат Ложь;
	КонецЕсли;
	
	Если Выражение.Тип = "АгрегатнаяФункция"
		Или Выражение.Тип = "АгрегатнаяФункцияКоличество" Тогда
			
		Возврат Истина;
	КонецЕсли;
		
	Возврат Ложь;
КонецФункции

Функция ИндексИсточникаЗапросаПоПсевдонику(ОператорЗапроса, ПсевдлонимИсточника) Экспорт
	Для Индекс = 0 По ОператорЗапроса.Источники.Элементы.ВГраница() Цикл     
		СтрокаИсточника = ОператорЗапроса.Источники.Элементы[Индекс]; 
		Если ВРег(СтрокаИсточника.Источник.Псевдоним) = ВРег(ПсевдлонимИсточника) Тогда
			Возврат Индекс;
		КонецЕсли;
	КонецЦикла;	
	
	Возврат Неопределено;
КонецФункции  

// Источник запроса по псевдонику.
// 
// Параметры:
//  ОператорЗапроса - см. ЭлементыМоделиЗапроса.НовыйОператорЗапроса
//  ПсевдлонимИсточника - Строка
// 
// Возвращаемое значение:
//  Неопределено - см. ЭлементыМоделиЗапроса.НовыйИсточник
Функция ИсточникЗапросаПоПсевдонику(ОператорЗапроса, ПсевдлонимИсточника) Экспорт
	Индекс = ИндексИсточникаЗапросаПоПсевдонику(ОператорЗапроса, ПсевдлонимИсточника);
	Если Индекс = Неопределено Тогда
		Возврат Неопределено;
	Иначе
		Возврат ОператорЗапроса.Источники.Элементы[Индекс];
	КонецЕсли;	
КонецФункции

Функция ИндексСоединения(ИсточникЗапроса, ИдентифкаторПрисоединяемойТаблицы) Экспорт
	Для Индекс = 0 По ИсточникЗапроса.Соединения.ВГраница() Цикл
		Соединение = ИсточникЗапроса.Соединения[Индекс];
		Если Соединение.Источник = ИдентифкаторПрисоединяемойТаблицы Тогда
			Возврат Индекс;
		КонецЕсли;	
	КонецЦикла;
	
	Возврат Неопределено;
КонецФункции	

Функция НайтиСоединение(ОператорЗапроса, ПсевдонимПрисоединяемойТаблицы, ПсевдонимВладельцаСвязи, ИсточникиПоИдентификаторам) Экспорт 
	Источник = ИсточникЗапросаПоПсевдонику(ОператорЗапроса, ПсевдонимВладельцаСвязи); 
	Для Каждого Соединение Из Источник.Соединения Цикл
		Если ВРег(ИсточникиПоИдентификаторам[Соединение.Источник].Источник.Псевдоним) = ВРег(ПсевдонимПрисоединяемойТаблицы) Тогда
			Возврат Соединение;
		КонецЕсли;
	КонецЦикла;
	
	Возврат Неопределено;
КонецФункции  

Функция НайтиЭлементыСпискаВыраженийПоЗначению(СписокВыражений, Выражение) Экспорт  
	Индексы = Новый Массив;
	Для Индекс = 0 По СписокВыражений.Элементы.ВГраница() Цикл
		ВыражениеПоля = СписокВыражений.Элементы[Индекс];
		Если ВыраженияМоделиЗапросаРавны(ВыражениеПоля, Выражение) Тогда
			Индексы.Добавить(Индекс);
		КонецЕсли;		
	КонецЦикла;
	
	Возврат Индексы;
КонецФункции

Функция СгенерироватьПсевдонимИсточника(ПсевдонимБезПостфикса, ОператорЗапроса) Экспорт
	ИспользуемыеПсевдонимы = Новый Массив;
	
	Для Каждого ИсточникОператора Из ОператорЗапроса.Источники.Элементы Цикл
		ИспользуемыеПсевдонимы.Добавить(ВРег(ИсточникОператора.Источник.Псевдоним));		
	КонецЦикла;	
	
	Возврат СгенерироватьПсевдоним(ПсевдонимБезПостфикса, ИспользуемыеПсевдонимы);
КонецФункции  

// Сгенерировать псевдоним выбираемого поля.
// 
// Параметры:
//  Выражение - см. ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса
//  ОператорЗапроса  см. ЭлементыМоделиЗапроса.НовыйОператорЗапроса
// 
// Возвращаемое значение:
//  Строка - Сгенерировать псевдоним выбираемого поля
Функция СгенерироватьПсевдонимВыбираемогоПоля(Выражение, ОператорЗапроса) Экспорт
	Если Выражение.Значение.Тип = "АгрегатнаяФункция"
		Или Выражение.Значение.Тип = "АгрегатнаяФункцияКоличество" Тогда
		
		ТекущееВыражение = Выражение.Значение.Аргумент;
	Иначе
		ТекущееВыражение = Выражение.Значение;
	КонецЕсли;	
	
	Если ТекущееВыражение.Тип = "Разыменование" Тогда  
		ПоследнийЭлемент = ТекущееВыражение.Элементы[ТекущееВыражение.Элементы.ВГраница()]; 
		Если ТипЗнч(ПоследнийЭлемент) = Тип("Строка") Тогда
			ПсевдонимБезПостфикса = ПоследнийЭлемент;			
		ИначеЕсли ПоследнийЭлемент.Тип = "ПолеИсточника" Тогда   
			ПсевдонимБезПостфикса = ПоследнийЭлемент.ИмяПоля; 
		Иначе
			ПсевдонимБезПостфикса = "Выражение";	
		КонецЕсли;	
	ИначеЕсли ТекущееВыражение.Тип = "ПараметрЗапроса" Тогда 
		ПсевдонимБезПостфикса = ТекущееВыражение.Имя;
	Иначе
		ПсевдонимБезПостфикса = "Выражение";
	КонецЕсли;  
	
	Возврат СгенерироватьПсевдонимПоляЗапроса(ПсевдонимБезПостфикса, ОператорЗапроса); 
КонецФункции	

Функция СгенерироватьПсевдонимПоляЗапроса(ПсевдонимБезПостфикса, ОператорЗапроса)
	ИспользуемыеПсевдонимы = Новый Массив;
	
	Для Каждого Поле Из ОператорЗапроса.ВыбираемыеПоля Цикл
		ИспользуемыеПсевдонимы.Добавить(ВРег(Поле.Псевдоним));		
	КонецЦикла;	
	
	Возврат СгенерироватьПсевдоним(ПсевдонимБезПостфикса, ИспользуемыеПсевдонимы);
КонецФункции 

Функция СгенерироватьПсевдоним(ПсевдонимБезПостфикса, ИспользуемыеПсевдонимы)
	Постфикс = 0;
	Пока Истина Цикл
		Псевдоним = ПсевдонимБезПостфикса + Формат(Постфикс, "ЧГ=");
		Если ИспользуемыеПсевдонимы.Найти(ВРег(Псевдоним)) = Неопределено Тогда
			Возврат Псевдоним;
		КонецЕсли;   
		Постфикс = Постфикс + 1;
	КонецЦикла;	
КонецФункции    

// Сортировать источники.
// 
// Параметры:
//  Источники - Массив из см. ЭлементыМоделиЗапроса.НовыйИсточник
// 
// Возвращаемое значение:
// 	Массив из см. ЭлементыМоделиЗапроса.НовыйИсточник 
Функция СортироватьИсточникиПоИерархии(Источники) Экспорт
	ОтсортированныеИсточники = Новый Массив();
	
	УзлыПоИд = Новый Соответствие();
	ИсточникиПоИд = МассивСтруктурВСоответствие(Источники, "ИдентификаторИсточника");
	УровниИсточников = Новый ТаблицаЗначений();
	УровниИсточников.Колонки.Добавить("Источник");
	УровниИсточников.Колонки.Добавить("Уровень", Новый ОписаниеТипов("Число"));
	УровниИсточников.Колонки.Добавить("ТекущийПорядок", Новый ОписаниеТипов("Число"));
	Индекс = 0;
	Для Каждого Источник Из Источники Цикл
		УзелИсточника = Новый Структура("Идентифкатор, ДочерниеЭлементы", Источник.ИдентификаторИсточника, Новый Массив());
		УзлыПоИд.Вставить(Источник.ИдентификаторИсточника, УзелИсточника);
		СтрокаТЗ = УровниИсточников.Добавить();
		СтрокаТЗ.Источник = Источник.ИдентификаторИсточника;
		СтрокаТЗ.ТекущийПорядок = Индекс;
		Индекс = Индекс + 1;
	КонецЦикла;
	
	Для Каждого Источник Из Источники Цикл
		УзелИсточника = УзлыПоИд.Получить(Источник.ИдентификаторИсточника);
		Для Каждого Соединение Из Источник.Соединения Цикл
			УзелИсточника.ДочерниеЭлементы.Добавить(УзлыПоИд.Получить(Соединение.Источник));	
		КонецЦикла;
	КонецЦикла;
	
	Для Каждого Источник Из Источники Цикл
		УзелИсточника = УзлыПоИд.Получить(Источник.ИдентификаторИсточника);
		ЗаполнитьУровниИсточникво(УзелИсточника, УровниИсточников);
	КонецЦикла;
	
	УровниИсточников.Сортировать("Уровень, ТекущийПорядок");
	Для Каждого СтрокаТЗ Из УровниИсточников Цикл
		ОтсортированныеИсточники.Добавить(ИсточникиПоИд.Получить(СтрокаТЗ.Источник));
	КонецЦикла;
	
	Возврат ОтсортированныеИсточники;
КонецФункции

Процедура ЗаполнитьУровниИсточникво(УзелИсточника, УровниИсточников, Знач ТекущийУровень = 0)
	СтрокаТЗ = УровниИсточников.Найти(УзелИсточника.Идентифкатор, "Источник");
	СтрокаТЗ.Уровень = ТекущийУровень;
	ТекущийУровень = ТекущийУровень + 1;
	Для Каждого ПодчиненныйУзел Из УзелИсточника.ДочерниеЭлементы Цикл
		ЗаполнитьУровниИсточникво(ПодчиненныйУзел, УровниИсточников, ТекущийУровень);
	КонецЦикла;	
КонецПроцедуры

Функция МассивСтруктурВСоответствие(Массив, ИмяКлюча) Экспорт
	Соответствие = Новый Соответствие;	
	
	Для Каждого Элемент Из Массив Цикл
		Соответствие.Вставить(Элемент[ИмяКлюча], Элемент);
	КонецЦикла;
	
	Возврат Соответствие;
КонецФункции	

// Выражение в массив выражений по И.
// 
// Параметры:
//  Выражение - см. ЭлементыМоделиЗапроса.НовыйБинарнаяОперация
// 
// Возвращаемое значение:
// 	Массив из Произвольный 
Функция УсловиеВМассивВыраженийПоИ(Выражение) Экспорт
	МассивВыражений = Новый Массив();
	ЗаполнитьМассивВыраженийПоИ(МассивВыражений, Выражение);
	
	Возврат МассивВыражений;		
КонецФункции

Функция ОписаниеВременнойТаблицы(Запрос, ИндексЗапроса) Экспорт 
	ОписаниеВременнойТаблицы = ЭлементыМоделиЗапроса.НовыйОписаниеВременнойТаблицы(); 
	ОписаниеВременнойТаблицы.ИндексЗапросаСоздания = ИндексЗапроса;
	ОписаниеВременнойТаблицы.Имя = Запрос.ТаблицаДляПомещения;
	Для Каждого Колонка Из Запрос.Колонки Цикл
		ДобавитьПолеВОписаниеВТ(ОписаниеВременнойТаблицы, Колонка);
	КонецЦикла;	
	
	Возврат ОписаниеВременнойТаблицы;
КонецФункции	

Процедура ДобавитьПолеВОписаниеВТ(ОписаниеВТ, Колонка) Экспорт
	ОписаниеВТ.Колонки.Вставить(ВРег(Колонка.Имя), Колонка.ТипЗначения);	
	ОписаниеВТ.ПорядокКолонок.Добавить(Колонка.Имя);
КонецПроцедуры

Процедура УдалитьПолеИзОписаниеВТ(ОписаниеВТ, Колонка) Экспорт
	ОписаниеВТ.Колонки.Удалить(ВРег(Колонка.Имя));
	ОписаниеВТ.ПорядокКолонок.Удалить(ОписаниеВТ.ПорядокКолонок.Найти(Колонка.Имя));	
КонецПроцедуры

// Описание доступных временных таблиц.
// 
// Параметры:
//  МодельЗапроса - см. ЭлементыМоделиЗапроса.НовыйПакетЗапросов
//  ИндексТекущегоЗапроса - Число
// 
// Возвращаемое значение:
//  Массив из см. ЭлементыМоделиЗапроса.НовыйОписаниеВременнойТаблицы
Функция ОписаниеДоступныхВременныхТаблиц(МодельЗапроса, ИндексТекущегоЗапроса) Экспорт
	ОписаниеДоступныхВременныхТаблиц = Новый Массив;
	
	Для Каждого Запрос Из МодельЗапроса.Элементы Цикл
		Если Запрос.Тип = "ЗапросВыбора"
			И Запрос.ОписаниеВТ <> Неопределено
			И Запрос.ОписаниеВТ.ИндексЗапросаСоздания >= 0
			И Запрос.ОписаниеВТ.ИндексЗапросаСоздания < ИндексТекущегоЗапроса 
			И (Запрос.ОписаниеВТ.ИндексЗапросаУничтожения = -1 
			Или Запрос.ОписаниеВТ.ИндексЗапросаУничтожения > ИндексТекущегоЗапроса) Тогда
			
			ОписаниеДоступныхВременныхТаблиц.Добавить(Запрос.ОписаниеВТ);
		КонецЕсли;
	КонецЦикла;
		
	Возврат ОписаниеДоступныхВременныхТаблиц;
КонецФункции

Функция НайтиОписаниеДоступнойВТ(СписокВТ, ИмяВТ, ИндексЗапроса) Экспорт
	Для Каждого ОписаниеВТ Из СписокВТ Цикл
		Если ОписаниеВТ <> Неопределено 
			И ВРег(ОписаниеВТ.Имя) = ВРег(ИмяВТ) 
			И ВременнаяТаблицаДоступнаВЗапросе(ОписаниеВТ, ИндексЗапроса)Тогда
		
			Возврат ОписаниеВТ;
		КонецЕсли;
	КонецЦикла;
	
	Возврат Неопределено;
КонецФункции

Функция СтруктурыРавны(Структура1, Структура2)
	Если Структура1.Количество() <> Структура2.Количество() Тогда
		Возврат Ложь;
	КонецЕсли;	
	
	Для Каждого КлючЗначение Из Структура1 Цикл
		Если Не Структура2.Свойство(КлючЗначение.Ключ) Тогда
			Возврат Ложь;
		КонецЕсли;
		
		Если Не ВыраженияРавны(КлючЗначение.Значение, Структура2[КлючЗначение.Ключ]) Тогда
			Возврат Ложь;
		КонецЕсли;	
	КонецЦикла;	
	
	Возврат Истина;
КонецФункции    

Функция МассивыРавны(Массив1, Массив2)
	Если Массив1.Количество() <> Массив2.Количество() Тогда
		Возврат Ложь;
	КонецЕсли;	
	
	Индекс = 0;
	Для Каждого Элемент Из Массив1 Цикл		
		Если Не ВыраженияРавны(Элемент, Массив2[Индекс]) Тогда
			Возврат Ложь;
		КонецЕсли;	  
		Индекс = Индекс + 1;
	КонецЦикла;	
	
	Возврат Истина;
КонецФункции

Функция СкопироватьМассив(Массив)
	Копия = Новый Массив;
	
	Для Каждого Элемент Из Массив Цикл
		Копия.Добавить(СкопироватьЭлементМоделиЗапроса(Элемент));	
	КонецЦикла;	 
	
	Возврат Копия;
КонецФункции

Функция СкопироватьСоответствие(Соответствие)
	Копия = Новый Соответствие;
	
	Для Каждого Элемент Из Соответствие Цикл 
		Копия.Вставить(СкопироватьЭлементМоделиЗапроса(Элемент.Ключ), СкопироватьЭлементМоделиЗапроса(Элемент.Значение)); 	
	КонецЦикла;	 
	
	Возврат Копия;
КонецФункции  

Функция СкопироватьСтруктуру(Соответствие) 
	Копия = Новый Структура;
	
	Для Каждого Элемент Из Соответствие Цикл 
		Копия.Вставить(Элемент.Ключ, СкопироватьЭлементМоделиЗапроса(Элемент.Значение)); 	
	КонецЦикла;	 
	
	Возврат Копия;
КонецФункции

// Дополнить соответствие.
// 
// Параметры:
//  Приемник - Соответствие из Произвольный, Произвольный
//  Источник - Соответствие из Произвольный, Произвольный
Процедура ДополнитьСоответствие(Приемник, Источник) Экспорт
	Для Каждого КлючЗначение Из Источник Цикл
		Приемник.Вставить(КлючЗначение.Ключ, КлючЗначение.Значение);
	КонецЦикла;
КонецПроцедуры

Функция ВозможноПолучениеПервыхЗаписей(ЗапросВыбора, КоличествоЗаписей, ЭтоВложенныйЗапрос) Экспорт
	Если (ЗначениеЗаполнено(ЗапросВыбора.ТаблицаДляПомещения)
		Или ЭтоВложенныйЗапрос)
		И КоличествоЗаписей <> Неопределено
		И Не ЗначениеЗаполнено(ЗапросВыбора.Порядок) Тогда
			
		Возврат Ложь;
	Иначе
		Возврат Истина;
	КонецЕсли;
КонецФункции

Процедура ЗаполнитьМассивВыраженийПоИ(МассивВыражений, Выражение)
	Если Выражение.Тип <> "БинарнаяОперация"
		Или Выражение.Операция <> "И" Тогда
		
		МассивВыражений.Добавить(Выражение);
	Иначе
		ЗаполнитьМассивВыраженийПоИ(МассивВыражений, Выражение.ЛеваяЧасть);	
		ЗаполнитьМассивВыраженийПоИ(МассивВыражений, Выражение.ПраваяЧасть);	
	КонецЕсли;			
КонецПроцедуры

Функция КоличествоАгригируемыхПолей(ВыбираемыеПоля)
	Количество = 0;
	Для Каждого Поле Из ВыбираемыеПоля Цикл
		Если Поле.Выражение.ИспользуетсяАгрегатнаяФункция Тогда
			Количество = Количество + 1;
		КонецЕсли;
	КонецЦикла;
	
	Возврат Количество;
КонецФункции

Функция ПолеВходитВГруппировку(Выражение, ЭлементыГруппировки)
	Для Каждого ВыражениеГруппировки Из ЭлементыГруппировки Цикл
		Если ВыраженияМоделиЗапросаРавны(Выражение, ВыражениеГруппировки) Тогда
			Возврат Истина
		КонецЕсли;	
	КонецЦикла;	
	
	Возврат Ложь;
КонецФункции

// Выражение использует поля.
// 
// Параметры:
//  Выражение - см. ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса
//  СписокПолей Список полей
// 
// Возвращаемое значение:
// 	Булево
//  
Функция ВыражениеИспользуетПоля(Выражение, СписокПолей) Экспорт
	Для Каждого Поле Из СписокПолей Цикл
		Если Выражение.ПоляИсточников.Получить(Поле) <> Неопределено Тогда
			Возврат Истина;
		КонецЕсли;
	КонецЦикла;
		
	Возврат Ложь;
КонецФункции

// Выражение использует поля источника.
// 
// Параметры:
//  Выражение - см. ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса
//  ИдентификаторИсточника - УникальныйИдентификатор
// 
// Возвращаемое значение:
// 	Булево
//  
Функция ВыражениеИспользуетПоляИсточника(Выражение, ИдентификаторИсточника) Экспорт
	ИдентификаторИсточникаСтрокой = Строка(ИдентификаторИсточника);
	Для Каждого КлючЗначение Из Выражение.ПоляИсточников Цикл
		Части = СтрРазделить(КлючЗначение.Ключ, ".");
		Если Части[0] = ИдентификаторИсточникаСтрокой Тогда
			Возврат Истина;
		КонецЕсли;	
	КонецЦикла;
	
	Возврат Ложь;
КонецФункции

// Заполнить используемые в запросе параметры.
// 
// Параметры:
//  ИспользуемыеПараметры - Соответствие из КлючИЗначение:
//  * Ключ - Строка
//  * Значение - см. ЭлементыМоделиЗапроса.НовыйОписаниеПараметраЗапроса
//  ЗапросВыбора - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
Процедура ЗаполнитьИспользуемыеВЗапросеПараметры(ИспользуемыеПараметры, ЗапросВыбора)
	Для Каждого Оператор Из ЗапросВыбора.Операторы Цикл
		ЗаполнитьИспользуемыеВОператореПараметры(ИспользуемыеПараметры, Оператор);
	КонецЦикла;
	
	Для Каждого ЭлементПорядка Из ЗапросВыбора.Порядок Цикл
		ЗаполнитьИспользуемыеВВыраженииПараметры(ИспользуемыеПараметры, ЭлементПорядка.Выражение);
	КонецЦикла;		
	
	Для Каждого КонтрольнаяТочка Из ЗапросВыбора.КонтрольныеТочкиИтогов Цикл
		ЗаполнитьИспользуемыеВВыраженииПараметры(ИспользуемыеПараметры, КонтрольнаяТочка.Выражение);
	КонецЦикла;		
КонецПроцедуры

// Заполнить используемые в операторе параметры.
// 
// Параметры:
//  ИспользуемыеПараметры - Соответствие из КлючИЗначение:
//  * Ключ - Строка
//  * Значение - см. ЭлементыМоделиЗапроса.НовыйОписаниеПараметраЗапроса
//  ОператорЗапроса - см. ЭлементыМоделиЗапроса.НовыйОператорЗапроса
Процедура ЗаполнитьИспользуемыеВОператореПараметры(ИспользуемыеПараметры, ОператорЗапроса)
	Для Каждого Источник Из ОператорЗапроса.Источники.Элементы Цикл
		Если Источник.Источник.Тип = "ИсточникДанныхВложенныйЗапрос" Тогда
			 ЗаполнитьИспользуемыеВЗапросеПараметры(ИспользуемыеПараметры, Источник.Источник.ЗапросВыбора);
		ИначеЕсли Источник.Источник.Тип = "ИсполняемоеПредставление" Тогда 	
			ЗаполнитьИспользуемыеВИсполняемомоПредставленииПараметры(ИспользуемыеПараметры, Источник.Источник);		
		КонецЕсли;
		
		Для Каждого Соединение Из Источник.Соединения Цикл
			ЗаполнитьИспользуемыеВВыраженииПараметры(ИспользуемыеПараметры, Соединение.Условие);			
		КонецЦикла;
	КонецЦикла;		
	
	Для Каждого Поле Из ОператорЗапроса.ВыбираемыеПоля Цикл
		ЗаполнитьИспользуемыеВВыраженииПараметры(ИспользуемыеПараметры, Поле.Выражение);	
	КонецЦикла;
	
	Для Каждого Группировка Из ОператорЗапроса.Группировка.Элементы Цикл
		ЗаполнитьИспользуемыеВВыраженииПараметры(ИспользуемыеПараметры, Группировка);	
	КонецЦикла;
	
	Для Каждого Отбор Из ОператорЗапроса.Отбор Цикл
		ЗаполнитьИспользуемыеВВыраженииПараметры(ИспользуемыеПараметры, Отбор);	
	КонецЦикла;
	
	Для Каждого Отбор Из ОператорЗапроса.ОтборСгруппированных Цикл
		ЗаполнитьИспользуемыеВВыраженииПараметры(ИспользуемыеПараметры, Отбор);	
	КонецЦикла;
КонецПроцедуры

// Заполнить используемые в исполняемомо представлении параметры.
// 
// Параметры:
//  ИспользуемыеПараметры - Соответствие из КлючИЗначение:
//  * Ключ - Строка
//  * Значение - см. ЭлементыМоделиЗапроса.НовыйОписаниеПараметраЗапроса
//  Источник - см. ЭлементыМоделиЗапроса.НовыйИсполняемоеПредставление
Процедура ЗаполнитьИспользуемыеВИсполняемомоПредставленииПараметры(ИспользуемыеПараметры, Источник)
	Если Источник.ВТФильтр <> Неопределено Тогда
		ЗаполнитьИспользуемыеВЗапросеПараметры(ИспользуемыеПараметры, Источник.ВТФильтр.ЗапросВыбора);
	КонецЕсли;
	
	ОписаниеПредставления = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(Источник.ИмяТаблицы);	
	Для Каждого Параметр Из Источник.Параметры Цикл
		Если Параметр.ЭтоПараметрЗапроса Тогда
			ОписаниеПараметраПредставления = ОписаниеПредставления.ПараметрыПоИменам.Получить(ВРег(Параметр.Имя));
			ОписаниеПараметраЗапроса = ЭлементыМоделиЗапроса.НовыйОписаниеПараметраЗапроса();
			ОписаниеПараметраЗапроса.Имя = ОписаниеПараметраПредставления.Имя;
			ОписаниеПараметраЗапроса.ТипЗначения = ОписаниеПараметраПредставления.ТипКонстанты;
			
			ИспользуемыеПараметры.Вставить(ВРег(Параметр.Имя), ОписаниеПараметраЗапроса);
		КонецЕсли;
	КонецЦикла;
КонецПроцедуры

// Заполнить используемые в выражении параметры.
// 
// Параметры:
//  ИспользуемыеПараметры - Соответствие из КлючИЗначение:
//  * Ключ - Строка
//  * Значение - см. ЭлементыМоделиЗапроса.НовыйОписаниеПараметраЗапроса
//  Выражение - см. ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса
Процедура ЗаполнитьИспользуемыеВВыраженииПараметры(ИспользуемыеПараметры, Выражение)
	Для Каждого КлючЗначение Из Выражение.ПараметрыЗапроса Цикл
		ИспользуемыеПараметры.Вставить(КлючЗначение.Ключ, КлючЗначение.Значение);	
	КонецЦикла; 	
КонецПроцедуры

Процедура ЗаполнитьИспользуемыеПоляИзВыражения(ИспользуемыеПоля, ВыражениеМодели)
	Если ВыражениеМодели = Неопределено Тогда
		Возврат;
	КонецЕсли;
	
	Для	Каждого КлючЗначение Из ВыражениеМодели.ПоляИсточников Цикл
		ЧастиИмениПоля = СтрРазделить(КлючЗначение.Ключ, ".");
		ИдентификаторИсточника = Новый УникальныйИдентификатор(ЧастиИмениПоля[0]);
		ИспользуемыеПоляИсточника = ИспользуемыеПоля.Получить(ИдентификаторИсточника);
		Если ИспользуемыеПоляИсточника = Неопределено Тогда
			ИспользуемыеПоляИсточника = Новый Соответствие();
			ИспользуемыеПоля.Вставить(ИдентификаторИсточника, ИспользуемыеПоляИсточника); 
		КонецЕсли;
		ИспользуемыеПоляИсточника.Вставить(ВРег(ЧастиИмениПоля[1]), ЧастиИмениПоля[1]);
	КонецЦикла;
КонецПроцедуры

#КонецОбласти