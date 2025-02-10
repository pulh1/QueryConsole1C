#Область СлужебныеПроцедурыИФункции

Функция ВыполнитьПакетЗапросов(ТекстЗапроса, ЗначенияПараметров) Экспорт
	Контекст = КонтекстИсполнения();

	Исполнитель = Обработки.ИсполнительПредставлений.Создать();
	Исполнитель.Инициализировать(ЗначенияПараметров);
	Контекст.Исполнитель = Исполнитель;	
	
	Возврат ИсполнитьУзелПакетЗапросов(ТекстЗапроса, Контекст);
КонецФункции

Функция ПолучитьИсполняемыйКод(ТекстЗапроса, ЗначенияПараметров) Экспорт
	Контекст = КонтекстИсполнения();

	Генератор = Обработки.ГенераторКодаИсполняемыхПредставлений.Создать();
	Генератор.Инициализировать(ЗначенияПараметров);
	Контекст.Исполнитель = Генератор;	
	
	ИсполнитьУзелПакетЗапросов(ТекстЗапроса, Контекст);	
	
	Возврат Генератор.ИсполняемыйКод();
КонецФункции

Функция ПолучитьТекстЗапросаДляСКД(ТекстЗапроса, ЗначенияПараметров) Экспорт
	Контекст = КонтекстИсполнения();
	Контекст.ГенерацияЗапросаДляСКД = Истина;

	Генератор = Обработки.ГенераторКодаЗапросовДляСКД.Создать();
	Генератор.Инициализировать(ЗначенияПараметров);
	Контекст.Исполнитель = Генератор;	
	
	ИсполнитьУзелПакетЗапросов(ТекстЗапроса, Контекст);	
	
	Возврат Генератор.КодЗапросаДляСКД();
КонецФункции

// Исполнить пакет запросов.
// 
// Параметры:
//  ТекстЗапроса - Строка
//  Контекст - см. КонтекстИсполнения
//  
// Возвращаемое значение:
// 	Произвольный 
Функция ИсполнитьУзелПакетЗапросов(ТекстЗапроса, Контекст) 	
	МодельЗапроса = ОбработкаМоделиЗапроса.РазобратьЗапрос(ТекстЗапроса);
	
	Результат = Неопределено;
	Для Каждого ЗапросПакета Из МодельЗапроса.Элементы Цикл
		Если ЗапросПакета.Тип = "ЗапросУничтожения" Тогда
			Контекст.Исполнитель.ИсполнитьУзелЗапросУничтожения(ЗапросПакета);
			
			Если ЗапросПакета.ОписаниеВТ <> Неопределено Тогда
				ИмяТаблицы = ЗапросПакета.ОписаниеВТ.Имя;
			Иначе
				ИмяТаблицы = ЗапросПакета.ИмяТаблицы;
			КонецЕсли;	
			
			Если Контекст.ИспользуемыеИменаВТ.Получить(ВРег(ИмяТаблицы)) <> Неопределено Тогда
				Контекст.ИспользуемыеИменаВТ.Удалить(ВРег(ИмяТаблицы));
			КонецЕсли;	
			Если Контекст.ДоступныеДляУдаленияВТ.Получить(ВРег(ИмяТаблицы)) <> Неопределено Тогда
				Контекст.ДоступныеДляУдаленияВТ.Удалить(ВРег(ИмяТаблицы));
			КонецЕсли;	
		Иначе
			//@skip-check query-in-loop
			Результат = ВыполнитьЗапрос(ЗапросПакета, Контекст);	
			Если ЗапросПакета.ОписаниеВТ <> Неопределено Тогда
				ИмяТаблицы = ЗапросПакета.ОписаниеВТ.Имя;
			Иначе
				ИмяТаблицы = ЗапросПакета.ТаблицаДляПомещения;
			КонецЕсли;	
			Если ЗначениеЗаполнено(ИмяТаблицы) Тогда
				Контекст.ИспользуемыеИменаВТ.Вставить(ВРег(ИмяТаблицы));
			КонецЕсли;
		КонецЕсли;		
	КонецЦикла;
	
	Возврат Результат;
КонецФункции

// Выполнить запрос.
// 
// Параметры:
//  ЗапросПакета - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
//  Контекст - см. КонтекстИсполнения
//  ВыполнятьБезусловно - Булево
//   
// Возвращаемое значение:
//  РезультатЗапроса
Функция ВыполнитьЗапрос(ЗапросПакета, Контекст,  ВыполнятьБезусловно = Ложь)
	Если Не ВыполнятьЗапрос(ЗапросПакета, Контекст) И Не ВыполнятьБезусловно Тогда
		ПараметрыВыполнения = ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления();
		ИспользуемыеПоляПоИсточникам = МодельЗапросаУтилиты.ИспользуемыеПоляИсточников(
			ЗапросПакета, 
			0);
		ПараметрыВыполнения.ИспользуемыеПоля = 
			ИспользуемыеПоляПоИсточникам.Получить(ЗапросПакета.Операторы[0].Источники.Элементы[0].ИдентификаторИсточника);
			
		Если ПараметрыВыполнения.ИспользуемыеПоля = Неопределено Тогда
			ПараметрыВыполнения.ИспользуемыеПоля = Новый Соответствие();
		КонецЕсли;	
		ПараметрыВыполнения.ТолькоРазрешенные = ЗапросПакета.ВыбиратьРазрешенные;
		
		ОтборыПредставления = ОтборИсполняемыхПредставленийИзОператораЗапроса(
			ЗапросПакета.Операторы[0], 
			Контекст.ГенерацияЗапросаДляСКД).Получить(ЗапросПакета.Операторы[0].Источники.Элементы[0].ИдентификаторИсточника);
		
		Если ОтборыПредставления <> Неопределено Тогда
			ПараметрыВыполнения.Отборы = ОтборыПредставления;	
		КонецЕсли;
			
		ПараметрыВыполнения.ПсевдонимыПолей = ПсевдонимыПолей(ЗапросПакета.Операторы[0]);	
		ПараметрыВыполнения.Индексы = ИспользуемыеИндексы(ЗапросПакета);
		
		Если Контекст.ГенерацияЗапросаДляСКД Тогда
			ПараметрыВыполнения.ИмяВТРезультат = СгенерироватьИмяВТДляПредставления(
				ЗапросПакета.Операторы[0].Источники.Элементы[0].Источник, 
				Контекст);
		Иначе			
			ПараметрыВыполнения.ИмяВТРезультат = ЗапросПакета.ТаблицаДляПомещения;
		КонецЕсли;
		
		Результат = ВыполнитьИсполняемоеПредставление(
			ЗапросПакета.Операторы[0].Источники.Элементы[0].Источник,
			ПараметрыВыполнения,
			Контекст);
		
		Если ЗначениеЗаполнено(ЗапросПакета.ТаблицаДляПомещения) Тогда
			ЗапросПакета.ТаблицаДляПомещения = ПараметрыВыполнения.ИмяВТРезультат;	
			ЗапросПакета.ОписаниеВТ.Имя = ПараметрыВыполнения.ИмяВТРезультат;
		КонецЕсли;	
		
		Возврат Результат;
	КонецЕсли;
	
	ОбработатьЗапрос(ЗапросПакета, Контекст);
	
	Возврат Контекст.Исполнитель.ИсполнитьУзелЗапросВыбора(ЗапросПакета);
КонецФункции

// Обработать запрос.
// 
// Параметры:
//  ЗапросПакета - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
//  Контекст - см. КонтекстИсполнения
Процедура ОбработатьЗапрос(ЗапросПакета, Контекст)
	Для Индекс = 0 По ЗапросПакета.Операторы.ВГраница() Цикл
		ОбработатьОператор(ЗапросПакета, Индекс, Контекст);	
	КонецЦикла;	
КонецПроцедуры

// Обработать оператор.
// 
// Параметры:
//  ЗапросПакета - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
//  ИндексОператора - Число 
//  Контекст - см. КонтекстИсполнения
Процедура ОбработатьОператор(ЗапросПакета, ИндексОператора, Контекст)
	Оператор = ЗапросПакета.Операторы[ИндексОператора];
	ОтборИсполняемыхПредставлений = ОтборИсполняемыхПредставленийИзОператораЗапроса(Оператор, Контекст.ГенерацияЗапросаДляСКД);
	
	ИспользуемыеПоляПоИсточникам = Неопределено;
	Для Каждого Источник Из Оператор.Источники.Элементы Цикл
		Если Источник.Источник.Тип = "ИсточникДанныхВложенныйЗапрос" Тогда
			ОбработатьЗапрос(Источник.Источник, Контекст);
		ИначеЕсли Источник.Источник.Тип = "ИсполняемоеПредставление" Тогда 
			Если ИспользуемыеПоляПоИсточникам = Неопределено Тогда
				ИспользуемыеПоляПоИсточникам = МодельЗапросаУтилиты.ИспользуемыеПоляИсточников(ЗапросПакета, ИндексОператора);
			КонецЕсли;
			
			ПараметрыВыполнения = ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления();
			ПараметрыВыполнения.ТолькоРазрешенные = ЗапросПакета.ВыбиратьРазрешенные;
			ПараметрыВыполнения.ИспользуемыеПоля = ИспользуемыеПоляПоИсточникам.Получить(Источник.ИдентификаторИсточника);
			Если ПараметрыВыполнения.ИспользуемыеПоля = Неопределено Тогда
				ПараметрыВыполнения.ИспользуемыеПоля = Новый Соответствие();
			КонецЕсли;	 
			
			ОтборыПредставления = ОтборИсполняемыхПредставлений.Получить(Источник.ИдентификаторИсточника);
			Если ОтборыПредставления <> Неопределено Тогда
				ПараметрыВыполнения.Отборы = ОтборыПредставления;
			КонецЕсли;	
			
			ПараметрыВыполнения.ИмяВТРезультат = СгенерироватьИмяВТДляПредставления(Источник.Источник, Контекст);
			
			// TODO освобождать имя уже после выполнения всего запроса

			ВыполнитьИсполняемоеПредставление(Источник.Источник, ПараметрыВыполнения, Контекст);
			Псевдоним = Источник.Источник.Псевдоним;	
			Источник.Источник = ЭлементыМоделиЗапроса.НовыйИсточникДанныхВременнаяТаблица();
			Источник.Источник.ИмяТаблицы = ПараметрыВыполнения.ИмяВТРезультат;
			Источник.Источник.Псевдоним = Псевдоним;
		КонецЕсли;		
	КонецЦикла;	
КонецПроцедуры

// Выполнить исполняемое представление.
// 
// Параметры:
//  ИсполняемоеПредставление - см. ЭлементыМоделиЗапроса.НовыйИсполняемоеПредставление
//  ПараметрыИсполнения - см. ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления
//  Контекст - см. КонтекстИсполнения
//  ФормироватьВТ - Булево
Функция ВыполнитьИсполняемоеПредставление(ИсполняемоеПредставление, ПараметрыИсполнения, Контекст)
	ОбработатьИсполняемоеПредставление(ИсполняемоеПредставление, ПараметрыИсполнения, Контекст);
	
	Результат = Контекст.Исполнитель.ИсполнитьУзелИсполняемоеПредставление(ИсполняемоеПредставление, ПараметрыИсполнения);
	Если ЗначениеЗаполнено(ПараметрыИсполнения.ИмяВТРезультат) Тогда
		Контекст.ИспользуемыеИменаВТ.Вставить(ВРег(ПараметрыИсполнения.ИмяВТРезультат), Истина);	
	КонецЕсли;
	
	Возврат Результат;
КонецФункции

// Обработать исполняемое представление.
// 
// Параметры:
//  ИсполняемоеПредставление - см. ЭлементыМоделиЗапроса.НовыйИсполняемоеПредставление
//  ПараметрыВыполненияПредставления - см. ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления
//  Контекст - см. КонтекстИсполнения
Процедура ОбработатьИсполняемоеПредставление(ИсполняемоеПредставление, ПараметрыВыполненияПредставления, Контекст)	
	ОписаниеПредставления = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ИсполняемоеПредставление.ИмяТаблицы);
	ПараметрыВыполненияПредставления.ИмяИсполняемогоПредставления = ИсполняемоеПредставление.ИмяТаблицы;
	
	Если ИсполняемоеПредставление.ВТФильтр <> Неопределено Тогда
		ОписаниеВТФильтр = ОбработатьПараметрВТФильтр(ИсполняемоеПредставление, ОписаниеПредставления, Контекст);
		ПараметрыВыполненияПредставления.ОписаниеВТФильтр = ОписаниеВТФильтр;
	КонецЕсли;
	
	Для Каждого ПараметрПредставления Из ИсполняемоеПредставление.Параметры Цикл
		Константа = ЭлементыМоделиИсполненияПредставлений.НовыйЗначениеПараметраКонстанта();	
		Константа.Значение = ПараметрПредставления.Значение;
		Константа.ЭтоПараметрЗапроса = ПараметрПредставления.ЭтоПараметрЗапроса;
		ПараметрыВыполненияПредставления.ЗначенияПараметровКонстант.Вставить(ПараметрПредставления.Имя, Константа);
	КонецЦикла;
КонецПроцедуры

// Обработать параметр ВТФильтр.
// 
// Параметры:
//  ИсполняемоеПредставление - см. ЭлементыМоделиЗапроса.НовыйИсполняемоеПредставление
//  ОписаниеПредставления - см. ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления
//  Контекст - см. КонтекстИсполнения
// 
// Возвращаемое значение:
//  см. ЭлементыМоделиИсполненияПредставлений.НовыйОписаниеВТФильтр
Функция ОбработатьПараметрВТФильтр(ИсполняемоеПредставление, ОписаниеПредставления, Контекст)
	ОписаниеВТФильтр = ЭлементыМоделиИсполненияПредставлений.НовыйОписаниеВТФильтр();
	
	ВТФильтр = ИсполняемоеПредставление.ВТФильтр;	
	ОписаниеПараметраВТФильтр = ОписаниеПредставления.ОписаниеВТФильтр;
		
	Если Не СоздатьВТФильтр(ВТФильтр.ЗапросВыбора, ВТФильтр.Поля, ОписаниеПараметраВТФильтр, Контекст.ГенерацияЗапросаДляСКД) Тогда	
		Если ОписаниеПараметраВТФильтр.ПоддерживаютсяПсевдонимы Тогда
			ОписаниеВТФильтр.ПсевдонимыПолей = ПсевдонимыПолейВТФильтр(ВТФильтр.ЗапросВыбора, ВТФильтр.Поля, Ложь);
		КонецЕсли;
			
		ОписаниеВТФильтр.ИмяВТ = ВТФильтр.ЗапросВыбора.Операторы[0].Источники.Элементы[0].Источник.ИмяТаблицы;
			
		Возврат ОписаниеВТФильтр;
	КонецЕсли;
	
	Если ОписаниеПараметраВТФильтр.ПоддерживаетсяИмяВТФильтр Тогда
		ОписаниеВТФильтр.ИмяВТ = ИмяВТФильтр(ИсполняемоеПредставление.Псевдоним, Контекст);
		Контекст.ИспользуемыеИменаВТ.Вставить(ВРег(ОписаниеВТФильтр.ИмяВТ), Истина);	
		Контекст.ДоступныеДляУдаленияВТ.Вставить(ВРег(ОписаниеВТФильтр.ИмяВТ), Истина);	
	Иначе
		Если Контекст.ИспользуемыеИменаВТ.Получить(ВРег(ОписаниеПараметраВТФильтр.ИмяВТПоУмолчанию)) <> Неопределено 
			И Контекст.ДоступныеДляУдаленияВТ.Получить(ВРег(ОписаниеПараметраВТФильтр.ИмяВТПоУмолчанию)) = Неопределено Тогда
				
			ВызватьИсключение "Не возможно создать ВТФильтр для исполняемого представления " + ИсполняемоеПредставление.ИмяТаблицы + "
			|ВТ с именем " + ОписаниеПараметраВТФильтр.ИмяВТПоУмолчанию + " была ранее создана в пакете запросов";	
		КонецЕсли;
		
		Если Контекст.ДоступныеДляУдаленияВТ.Получить(ВРег(ОписаниеПараметраВТФильтр.ИмяВТПоУмолчанию)) <> Неопределено Тогда
			Контекст.Исполнитель.ИсполнитьУзелУничтожитьВТ(ОписаниеПараметраВТФильтр.ИмяВТПоУмолчанию);
			Контекст.ИспользуемыеИменаВТ.Удалить(ВРег(ОписаниеПараметраВТФильтр.ИмяВТПоУмолчанию));
			Контекст.ДоступныеДляУдаленияВТ.Удалить(ВРег(ОписаниеПараметраВТФильтр.ИмяВТПоУмолчанию));	
		КонецЕсли;
		ОписаниеВТФильтр.ИмяВТ = ОписаниеПараметраВТФильтр.ИмяВТПоУмолчанию;
		Контекст.ИспользуемыеИменаВТ.Вставить(ОписаниеВТФильтр.ИмяВТ, Истина);
		Контекст.ДоступныеДляУдаленияВТ.Вставить(ВРег(ОписаниеВТФильтр.ИмяВТ), Истина);
	КонецЕсли;
	
	Модель = ЭлементыМоделиЗапроса.НовыйПакетЗапросов();
	Модель.Элементы.Добавить(ВТФильтр.ЗапросВыбора);
	Построитель = МодельЗапросаУтилиты
		.СоздатьПостроительМодели(Модель)
		.УстановитьИмяВременнойТаблицы(ОписаниеВТФильтр.ИмяВТ);
	
	Если ОписаниеПараметраВТФильтр.ПоддерживаютсяПсевдонимы
		И Не Контекст.ГенерацияЗапросаДляСКД Тогда
			
		ОписаниеВТФильтр.ПсевдонимыПолей = ПсевдонимыПолейВТФильтр(ВТФильтр.ЗапросВыбора, ВТФильтр.Поля);	
	Иначе
		Для Индекс = 0 По ВТФильтр.Поля.ВГраница() Цикл
			Построитель.ИзменитьПсевдонимПоля(Индекс, ВТФильтр.Поля[Индекс]) 
		КонецЦикла;	
		ВТФильтр.ЗапросВыбора = Построитель.ПолучитьМодель();
	КонецЕсли;
	
	ВТФильтр.ЗапросВыбора = Построитель.ПолучитьМодель().Элементы[0];
	
	ВыполнитьЗапрос(ВТФильтр.ЗапросВыбора, Контекст, Истина);
	
	Возврат ОписаниеВТФильтр;
КонецФункции

// Выполнять запрос.
// 
// Параметры:
//  ЗапросВТФильтр - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
//  ПоляФильтра - Массив из Строка
//  ОписаниеПараметра - см. ЭлементыМоделиОписанияПредставлений.НовыйОписаниеТипаПараметраВТФильтр 
// УчитыватьПсевдонимыПолейЗапроса - Булево
// 
// Возвращаемое значение:
//  Соответствие из Строка, Строка
Функция ПсевдонимыПолейВТФильтр(ЗапросВТФильтр, ПоляФильтра, УчитыватьПсевдонимыПолейЗапроса = Истина)
	ПсевдонимыПолей = Новый Соответствие(); 
	
	Для Индекс = 0 По ПоляФильтра.ВГраница() Цикл
		Если УчитыватьПсевдонимыПолейЗапроса Тогда
			ПсевдонимыПолей.Вставить(ПоляФильтра[Индекс], ЗапросВТФильтр.Колонки[Индекс].Имя);	
		Иначе
			ПолеВТ = ЗапросВТФильтр.Операторы[0].ВыбираемыеПоля[Индекс].Выражение.Значение.Элементы[0].ИмяПоля;
			ПсевдонимыПолей.Вставить(ПоляФильтра[Индекс], ПолеВТ);
		КонецЕсли;
	КонецЦикла;
		
	Возврат ПсевдонимыПолей;
КонецФункции

// Выполнять запрос.
// 
// Параметры:
//  ЗапросВыбора - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
//  Контекст - см. КонтекстИсполнения
// 
// Возвращаемое значение:
//  Булево - Выполнять запрос
Функция ВыполнятьЗапрос(ЗапросВыбора, Контекст)
	Если Не ЗапросВыбора.Операторы.Количество() = 1 Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если ЗапросВыбора.Автопорядок Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если ЗначениеЗаполнено(ЗапросВыбора.ВыраженияИтогов) Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если ЗначениеЗаполнено(ЗапросВыбора.Порядок) Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если ЗначениеЗаполнено(ЗапросВыбора.КонтрольныеТочкиИтогов) Тогда
		Возврат Истина;
	КонецЕсли;
	
	Оператор = ЗапросВыбора.Операторы[0];	
	
	Если Оператор.ВыбиратьРазличные Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если ЗначениеЗаполнено(Оператор.КоличествоПолучаемыхЗаписей) Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если Оператор.Источники.Элементы.Количество() <> 1 Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если Не Оператор.Источники.Элементы[0].Источник.Тип = "ИсполняемоеПредставление" Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если ЗначениеЗаполнено(Оператор.Группировка.Элементы) Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если ЗначениеЗаполнено(Оператор.ОтборСгруппированных) Тогда
		Возврат Истина;
	КонецЕсли;	
	
	ИсполняемоеПредставление = Оператор.Источники.Элементы[0].Источник;
	ОписаниеПредставления = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ИсполняемоеПредставление.ИмяТаблицы);
	
	Если Не ЗначениеЗаполнено(ЗапросВыбора.ТаблицаДляПомещения)
		И (Не ОписаниеПредставления.ПоддерживаетсяПолучениеРезультатаЗапроса
		Или Контекст.ГенерацияЗапросаДляСКД) Тогда
			
		Возврат Истина;
	КонецЕсли;
	
	Если ЗначениеЗаполнено(ЗапросВыбора.ТаблицаДляПомещения) Тогда
		Если Не ОписаниеПредставления.ПоддерживаетсяУказаниеИмяВТРезультат
			И ЗапросВыбора.ТаблицаДляПомещения <> ОписаниеПредставления.ИмяФормируемойВТПоУмолчанию Тогда
			
			Возврат Истина;
		КонецЕсли; 
	КонецЕсли; 
	
	Если ЗначениеЗаполнено(ЗапросВыбора.Индекс.Элементы)
		И Не ОписаниеПредставления.ПоддерживаютсяИндексы Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если ЗначениеЗаполнено(Оператор.Отбор)
		И Не ПредставлениеПоддерживаетВсеОтборы(
			ОписаниеПредставления, 
			Оператор.Отбор, 
			Оператор.Источники.Элементы[0].ИдентификаторИсточника, 
			Контекст.ГенерацияЗапросаДляСКД) Тогда
		
		Возврат Истина;
	КонецЕсли;
	
	Для Каждого Поле Из Оператор.ВыбираемыеПоля Цикл
		Если Не Поле.Выражение.Значение.Тип = "Разыменование" Тогда
			Возврат Истина;
		КонецЕсли;	
		Если Не Поле.Выражение.Значение.Элементы.Количество() = 1 Тогда
			Возврат Истина;
		КонецЕсли;	
		Если Не ТипЗнч(Поле.Выражение.Значение.Элементы[0]) = Тип("Структура")  Тогда
			Возврат Истина;
		КонецЕсли;	
		Если Не Поле.Выражение.Значение.Элементы[0].Тип = "ПолеИсточника" Тогда
			Возврат Истина;
		КонецЕсли;	
		
		Если Не ВРег(Поле.Выражение.Значение.Элементы[0].ИмяПоля) = ВРег(Поле.Псевдоним)
			И Не ОписаниеПредставления.ПоддерживаетсяПсевдонимыПолей Тогда
			Возврат Истина;
		КонецЕсли;
	КонецЦикла;	
	
	Возврат Ложь;
КонецФункции

// Представление поддерживает все отборы.
// 
// Параметры:
//  ОписаниеПредставления - см. ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления
//  ПроверяемыеОтборы - Массив из см. ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса
//  ИдентификаторИсточника - УникальныйИдентификатор
//  ДляСКД - Булево
// 
// Возвращаемое значение:
// 	Булево 
Функция ПредставлениеПоддерживаетВсеОтборы(ОписаниеПредставления, ПроверяемыеОтборы, ИдентификаторИсточника, ДляСКД)
	ОписаниеОтборовПоИменам = ОписаниеОтборовПоИменамПолей(ОписаниеПредставления, ДляСКД);
	
	Для Каждого ВыражениеОтбора Из ПроверяемыеОтборы Цикл
		ЭлементОтбора = РазобратьВыражениеОтбора(ВыражениеОтбора);
		Если ЭлементОтбора = Неопределено Тогда
			Возврат Ложь;
		КонецЕсли;
		Если Не ПредставлениеПоддерживаетОтбор(ЭлементОтбора, ОписаниеОтборовПоИменам, ИдентификаторИсточника, ДляСКД) Тогда
			Возврат Ложь;
		КонецЕсли;
	КонецЦикла;
	
	Возврат Истина;
КонецФункции

Функция ПредставлениеПоддерживаетОтбор(ЭлементОтбора, ОписаниеОтборовПоИменам, ИдентификаторИсточника, ДляСКД)
	Если ЭлементОтбора.ЗначениеОтбора.ЭтоПараметрЗапроса
		И ДляСКД Тогда
			
		Возврат Ложь;
	КонецЕсли;
		
	Если ЭлементОтбора.ПутьКПолю[0] <> ИдентификаторИсточника Тогда
		Возврат Ложь;
	КонецЕсли;
	
	Если ДляСКД И ЭлементОтбора.ВидСравнения <> "=" Тогда
		Возврат Ложь;
	КонецЕсли;
	
	ОписаниеДоступногоОтбора = ОписаниеОтборовПоИменам.Получить(ВРег(ЭлементОтбора.ПутьКПолю[1]));
	Если ОписаниеДоступногоОтбора = Неопределено Тогда
		Возврат Ложь;
	КонецЕсли;
	
	Если (Не ОписаниеДоступногоОтбора.ДоступноРазыменование Или ДляСКД)
		И ЭлементОтбора.ПутьКПолю.Количество() > 2 Тогда
			
		Возврат Ложь;
	КонецЕсли;	
	
	Возврат Истина;
КонецФункции

// Отбор исполняемых представлений из оператора запроса.
// 
// Параметры:
//  ОператорЗапроса - см. ЭлементыМоделиЗапроса.НовыйОператорЗапроса
//  ДляСКД - Булево
// 
// Возвращаемое значение:
//  
Функция ОтборИсполняемыхПредставленийИзОператораЗапроса(ОператорЗапроса, ДляСКД)
	ОтборИсполняемыхПредставлений = Новый Соответствие();
	
	Если ОператорЗапроса.Отбор = Неопределено Тогда
		Возврат Новый Соответствие();
	КонецЕсли;
	
	ЭлементыОтбора = Новый Соответствие();;
	
	Для Каждого ВыражениеОтбора Из ОператорЗапроса.Отбор Цикл
		ЭлементОтбора = РазобратьВыражениеОтбора(ВыражениеОтбора);
		Если ЭлементОтбора <> Неопределено Тогда
			ЭлементыОтбора.Вставить(ЭлементОтбора, ВыражениеОтбора);
		КонецЕсли;
	КонецЦикла;
	
	Для Каждого Источник Из ОператорЗапроса.Источники.Элементы Цикл
		Если Источник.Источник.Тип <> "ИсполняемоеПредставление" Тогда
			Продолжить;
		КонецЕсли;
		ОписаниеПредставления = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(Источник.Источник.ИмяТаблицы);
		ОписаниеОтборовПоИменамПолей = ОписаниеОтборовПоИменамПолей(ОписаниеПредставления, ДляСКД);	
		
		ЭлементыОтбораПредставления = Новый Массив();
		ОтборИсполняемыхПредставлений.Вставить(Источник.ИдентификаторИсточника, ЭлементыОтбораПредставления);
		
		Для Каждого КлючЗначение Из ЭлементыОтбора Цикл
			Если ПредставлениеПоддерживаетОтбор(КлючЗначение.Ключ, ОписаниеОтборовПоИменамПолей, Источник.ИдентификаторИсточника, ДляСКД) Тогда
				КлючЗначение.Ключ.ПутьКПолю.Удалить(0);
				ЭлементыОтбораПредставления.Добавить(КлючЗначение.Ключ);	
				ОператорЗапроса.Отбор.Удалить(ОператорЗапроса.Отбор.Найти(КлючЗначение.Значение));
			КонецЕсли;	
		КонецЦикла;
		
		Если ЭлементыОтбораПредставления.Количество() = 0 Тогда
			ОтборИсполняемыхПредставлений.Удалить(Источник.ИдентификаторИсточника);
		Иначе
			Для Каждого Элемент Из ЭлементыОтбораПредставления Цикл
				ЭлементыОтбора.Удалить(Элемент);
			КонецЦикла;		
		КонецЕсли;	
	КонецЦикла;		
	
	Возврат ОтборИсполняемыхПредставлений;
КонецФункции

Функция ОписаниеОтборовПоИменамПолей(ОписаниеПредставления, ДляСКД)
	ОписаниеОтборовПоИменам = Новый Соответствие();
	
	Для Каждого ОписаниеОтбора Из ОписаниеПредставления.ДоступныеОтборы Цикл
		Если ДляСКД И Не ОписаниеОтбора.ДоступенДляСКД Тогда
			Продолжить;
		КонецЕсли;
		
		ОписаниеОтборовПоИменам.Вставить(ВРег(ОписаниеОтбора.Поле), ОписаниеОтбора);
	КонецЦикла;
		
	Возврат ОписаниеОтборовПоИменам;
КонецФункции

// Выполнять запрос.
// 
// Параметры:
//  ЗапросВТФильтр - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
//  ПоляФильтра - Массив из Строка
//  ОписаниеВТФильтр - см. ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр
//  ДляСКД - Булево
// 
// Возвращаемое значение:
//  Булево - Выполнять запрос
Функция СоздатьВТФильтр(ЗапросВТФильтр, ПоляФильтра, ОписаниеВТФильтр, ДляСКД)
	Если Не ЗапросВТФильтр.Операторы.Количество() = 1 Тогда
		Возврат Истина;
	КонецЕсли;
	
	Оператор = ЗапросВТФильтр.Операторы[0];	
	
	Если ЗапросВТФильтр.ВыбиратьРазрешенные Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если ЗапросВТФильтр.ВыбиратьРазрешенные Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если Оператор.ВыбиратьРазличные Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если ЗначениеЗаполнено(ЗапросВТФильтр.Порядок) Тогда
		Возврат Истина;	
	КонецЕсли;
	
	Если ЗначениеЗаполнено(ЗапросВТФильтр.Индекс.Элементы) Тогда
		Возврат Истина;	
	КонецЕсли;
	
	Если ЗначениеЗаполнено(Оператор.КоличествоПолучаемыхЗаписей) Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если Оператор.Источники.Элементы.Количество() <> 1 Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если Не Оператор.Источники.Элементы[0].Источник.Тип = "ИсточникДанныхВременнаяТаблица" Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если Не ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр 
		И ВРег(Оператор.Источники.Элементы[0].Источник.ИмяТаблицы) <> ВРег(ОписаниеВТФильтр.ИмяВТПоУмолчанию) Тогда
		Возврат Истина;
	КонецЕсли;
	
	Если ЗначениеЗаполнено(Оператор.Отбор) Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если ЗначениеЗаполнено(Оператор.Группировка.Элементы) Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Если ЗначениеЗаполнено(Оператор.ОтборСгруппированных) Тогда
		Возврат Истина;
	КонецЕсли;	
	
	Индекс = 0;
	Для Каждого Поле Из Оператор.ВыбираемыеПоля Цикл
		Если Не Поле.Выражение.Значение.Тип = "Разыменование" Тогда
			Возврат Истина;
		КонецЕсли;	 
		Если Поле.Выражение.Значение.Элементы.Количество() <> 1 Тогда
			Возврат Истина;
		КонецЕсли;
		Если ТипЗнч(Поле.Выражение.Значение.Элементы[0]) <> Тип("Структура") Тогда
			Возврат Истина;
		КонецЕсли;
		Если Поле.Выражение.Значение.Элементы[0].Тип <> "ПолеИсточника" Тогда
			Возврат Истина;
		КонецЕсли;
		
		ПолеИсточника = Поле.Выражение.Значение.Элементы[0];
		
		Если (Не ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы Или ДляСКД)
			И ВРег(ПолеИсточника.ИмяПоля) <> ВРег(ПоляФильтра[Индекс]) Тогда
				
			Возврат Истина;
		КонецЕсли;
		Индекс = Индекс + 1;
	КонецЦикла;
		
	Возврат Ложь;
КонецФункции	

// Контекст исполнения.
// 
// Возвращаемое значение:
//  Структура - Контекст исполнения:
// * ИспользуемыеИменаВТ - Соответствие из Строка, Булево 
// * ДоступныеДляУдаленияВТ - Соответствие из Строка, Булево  
// * Исполнитель - см. ОбработкаОбъект.ТестОбработкиПредставлений
// * ГенерацияЗапросаДляСКД - Булево
Функция КонтекстИсполнения()
	Контекст = Новый Структура();
	Контекст.Вставить("ИспользуемыеИменаВТ", Новый Соответствие);
	Контекст.Вставить("ДоступныеДляУдаленияВТ", Новый Соответствие);
	Контекст.Вставить("Исполнитель");
	Контекст.Вставить("ГенерацияЗапросаДляСКД", Ложь);
	
	//@skip-check constructor-function-return-section
	Возврат Контекст;
КонецФункции

// Имя ВТФильтр.
// 
// Параметры:
//  ПсевдонимИсполняемогоПредставления - Строка
//  ИмяПараметра - Строка
//  Контекст - см. КонтекстИсполнения
// 
// Возвращаемое значение:
//  Строка - Имя ВТФильтр
Функция ИмяВТФильтр(ПсевдонимИсполняемогоПредставления, Контекст)
	ИмяВТБезПостфикса = "ВТФильтр" + ПсевдонимИсполняемогоПредставления;	
	
	Возврат СгенерироватьСвободноеИмяВТ(ИмяВТБезПостфикса, Контекст);
КонецФункции

Функция СгенерироватьСвободноеИмяВТ(Знач ИмяВТБезПостфикса, Контекст, Разделитель = "")
	Если Контекст.ИспользуемыеИменаВТ.Получить(ВРег(ИмяВТБезПостфикса)) = Неопределено Тогда
		Возврат ИмяВТБезПостфикса;
	КонецЕсли;
	
	Номер = 1;
	Пока Истина Цикл
		ИмяВТ = ИмяВТБезПостфикса + Разделитель + Формат(Номер);
		Если Контекст.ИспользуемыеИменаВТ.Получить(ВРег(ИмяВТ)) = Неопределено Тогда
			Возврат ИмяВТ;
		КонецЕсли;
		Номер = Номер + 1;
	КонецЦикла;
КонецФункции

Функция РазобратьВыражениеОтбора(ВыражениеОтбора)
	Выражение = ВыражениеОтбора.Значение;
	Если Выражение.Тип = "БинарнаяОперация"
		И (Выражение.Операция = "="
			Или Выражение.Операция = "<>"
			Или Выражение.Операция = ">"
			Или Выражение.Операция = "<"
			Или Выражение.Операция = "<="
			Или Выражение.Операция = ">=") Тогда  
			
			ПутьКПолю = ПутьКПолюИзВыраженияОтбора(Выражение.ЛеваяЧасть);
			Если ПутьКПолю = Неопределено Тогда
				Возврат Неопределено;
			КонецЕсли;			
			
			ЗначениеОтбора = ЗначениеОтбора(Выражение.ПраваяЧасть);
			Если ЗначениеОтбора = Неопределено Тогда
				Возврат Неопределено;
			КонецЕсли;
			
			ЭлементОтбора = ЭлементыМоделиИсполненияПредставлений.НовыйЭлементОтбора();
			ЭлементОтбора.ВидСравнения = Выражение.Операция;
			ЭлементОтбора.ПутьКПолю = ПутьКПолю;
			ЭлементОтбора.ЗначениеОтбора = ЗначениеОтбора;
			
			Возврат ЭлементОтбора;
	ИначеЕсли Выражение.Тип = "ОператорВ" Тогда
		Если Выражение.Инверсия Тогда
			ВидСравненияОтбора = "НЕ В";
		Иначе
			ВидСравненияОтбора = "В";	
		КонецЕсли;
		
		Если Выражение.Иерахия Тогда
			ВидСравненияОтбора = ВидСравненияОтбора + " ИЕРАРХИИ"	
		КонецЕсли;  
		
		ПутьКПолю = ПутьКПолюИзВыраженияОтбора(Выражение.Операнд);
		Если ПутьКПолю = Неопределено Тогда
			Возврат Неопределено;
		КонецЕсли;
		
		Если Выражение.Список.Тип <> "СписокВыражений"
			Или Выражение.Список.Элементы.Количество() <> 1 Тогда
				
			Возврат Неопределено;
		КонецЕсли;		
		
		ЗначениеОтбора = ЗначениеОтбора(Выражение.Список.Элементы[0]);
		Если ЗначениеОтбора = Неопределено Тогда
			Возврат Неопределено;
		КонецЕсли;		
		
		ЭлементОтбора = ЭлементыМоделиИсполненияПредставлений.НовыйЭлементОтбора();
		ЭлементОтбора.ВидСравнения = ВидСравненияОтбора;
		ЭлементОтбора.ПутьКПолю = ПутьКПолю;
		ЭлементОтбора.ЗначениеОтбора = ЗначениеОтбора;
		
		Возврат ЭлементОтбора;
	ИначеЕсли Выражение.Тип = "Разыменование"
		И МодельЗапросаТипы.ЭтоПолеТипа(ВыражениеОтбора.ТипЗначения, Тип("Булево")) Тогда 
			
		ПутьКПолю = ПутьКПолюИзВыраженияОтбора(Выражение);
		Если ПутьКПолю  = Неопределено Тогда
			Возврат Неопределено;	
		КонецЕсли;
		
		ЭлементОтбора = ЭлементыМоделиИсполненияПредставлений.НовыйЭлементОтбора();
		ЭлементОтбора.ПутьКПолю = ПутьКПолю;
		ЭлементОтбора.ВидСравнения = "=";
		ЭлементОтбора.ЗначениеОтбора = ЭлементыМоделиИсполненияПредставлений.НовыйЗначениеОтбора();
		ЭлементОтбора.ЗначениеОтбора.Значение = Истина;
		
		Возврат ЭлементОтбора;
	КонецЕсли; 	
	
	Возврат Неопределено;
КонецФункции

Функция ПутьКПолюИзВыраженияОтбора(Выражение)
	Если Выражение.Тип <> "Разыменование" Тогда
		Возврат Неопределено;
	КонецЕсли;
	
	Если Выражение.Элементы[0].Тип <> "ПолеИсточника" Тогда
		Возврат Неопределено;
	КонецЕсли;
	
	ПутьКПолю = Новый Массив();
	ПутьКПолю.Добавить(Выражение.Элементы[0].ИдентификаторИсточника);
	ПутьКПолю.Добавить(Выражение.Элементы[0].ИмяПоля);
	
	Для Индекс = 1 По Выражение.Элементы.ВГраница() Цикл
		Если ТипЗнч(Выражение.Элементы[Индекс]) = Тип("Строка") Тогда
			ПутьКПолю.Добавить(Выражение.Элементы[Индекс]);
		Иначе
		 	Возврат Неопределено;
	 	КонецЕсли;
	КонецЦикла;
	
	Возврат ПутьКПолю;		
КонецФункции

Функция ЗначениеОтбора(Выражение)
	Если Выражение.Тип = "Константа" Тогда
		ЗначениеОтбора = ЭлементыМоделиИсполненияПредставлений.НовыйЗначениеОтбора(); 
		ЗначениеОтбора.Значение = Выражение.Значение;
		ЗначениеОтбора.ЭтоПараметрЗапроса = Ложь;
		
		Возврат ЗначениеОтбора;
	ИначеЕсли Выражение.Тип = "ПараметрЗапроса" Тогда
		ЗначениеОтбора = ЭлементыМоделиИсполненияПредставлений.НовыйЗначениеОтбора(); 
		ЗначениеОтбора.Значение = Выражение.Имя;
		ЗначениеОтбора.ЭтоПараметрЗапроса = Истина;
		
		Возврат ЗначениеОтбора;
	Иначе
		Возврат Неопределено;
	КонецЕсли;
КонецФункции

Функция СгенерироватьИмяВТДляПредставления(ИсполняемоеПредставление, Контекст)
	Описание = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ИсполняемоеПредставление.ИмяТаблицы);
	Если Не Описание.ПоддерживаетсяУказаниеИмяВТРезультат Тогда
		Если Контекст.ГенерацияЗапросаДляСКД Тогда
			ИмяВТ = Описание.ИмяВТДляСКД;
		Иначе
			ИмяВТ = Описание.ИмяФормируемойВТПоУмолчанию;
		КонецЕсли;
		
		Если Контекст.ИспользуемыеИменаВТ.Получить(ВРег(ИмяВТ)) <> Неопределено Тогда
			// TODO попробовать удалить ВТ если она доступна к удалению
			ВызватьИсключение "Не возможно выполнить исполняемое представление " + Описание.Имя + ".
			|Представление не поддерживает указание имени формируемой ВТ, а временная таблица " + ИмяВТ + " уже существует";
		КонецЕсли;
		
		Возврат ИмяВТ;	
	Иначе
		Если Контекст.ГенерацияЗапросаДляСКД Тогда
			Возврат СгенерироватьСвободноеИмяВТ(Описание.ИмяВТДляСКД, Контекст, "_");	
		Иначе
			Возврат СгенерироватьСвободноеИмяВТ("ВТ" + ИсполняемоеПредставление.Псевдоним, Контекст);	
		КонецЕсли;	
	КонецЕсли;
КонецФункции

// Псевдонимы полей.
// 
// Параметры:
//  ОператорЗапроса - см. ЭлементыМоделиЗапроса.НовыйОператорЗапроса
// 
// Возвращаемое значение: 
// - Соответствие из КлючИЗначение:
// 	* Ключ - Строка
// 	* Значение - Строка
Функция ПсевдонимыПолей(ОператорЗапроса)
	ПсевдонимыПолей = Новый Соответствие();
	Для Каждого Поле Из ОператорЗапроса.ВыбираемыеПоля Цикл
		Если Поле.Выражение.Значение.Тип = "Разыменование"
			И Поле.Выражение.Значение.Элементы.Количество() = 1
			И Поле.Выражение.Значение.Элементы[0].Тип = "ПолеИсточника"
			И ВРег(Поле.Выражение.Значение.Элементы[0].ИмяПоля) <> ВРег(Поле.Псевдоним) Тогда
			
			ПсевдонимыПолей.Вставить(Поле.Выражение.Значение.Элементы[0].ИмяПоля, Поле.Псевдоним);
		КонецЕсли;		
	КонецЦикла;
	
	Возврат ПсевдонимыПолей;
КонецФункции

// Используемые индексы.
// 
// Параметры:
//  ЗапросВыбора - см. ЭлементыМоделиЗапроса.НовыйЗапросВыбора
// 
// Возвращаемое значение:
// 	- Массив из Строка 
Функция ИспользуемыеИндексы(ЗапросВыбора)
	Индексы = Новый Массив();
	КолонкиПоИдентификаторам = МодельЗапросаУтилиты.МассивСтруктурВСоответствие(ЗапросВыбора.Колонки, "Идентификатор");
	Для Каждого ИндексируемоеПоле Из ЗапросВыбора.Индекс.Элементы Цикл
		Индексы.Добавить(КолонкиПоИдентификаторам[ИндексируемоеПоле.Идентификатор].Имя);
	КонецЦикла;	
	
	Возврат Индексы;
КонецФункции

#КонецОбласти