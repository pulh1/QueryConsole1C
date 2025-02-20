#Область СлужебныеПроцедурыИФункции

// Это поле типа.
// 
// Параметры:
//  ТипПоля - ОписаниеТипов
//  ЦелевойТип - Тип
// 
// Возвращаемое значение:
//  Булево 
Функция ЭтоПолеТипа(ТипПоля, ЦелевойТип, УчитыватьПроизвольныйТипКакЦелевой = Истина) Экспорт
	Если ТипПоля.Типы().Количество() > 1 Тогда
		Возврат Ложь;
	ИначеЕсли ТипПоля.СодержитТип(ПроизвольныйТип())
		Или (УчитыватьПроизвольныйТипКакЦелевой  И ТипПоля.СодержитТип(ЦелевойТип)) Тогда
			
		Возврат Истина;
	Иначе
		Возврат Ложь;
	КонецЕсли;	
КонецФункции

Функция ПроизвольныйТип() Экспорт
	Возврат Тип("Массив");	
КонецФункции  

Функция ОписаниеПроивзольногоТипа() Экспорт
	Возврат Новый ОписаниеТипов("Массив")	
КонецФункции  

Функция СодержитПроизвольныйТип(ТипЗначения) Экспорт
	Возврат ТипЗначения.СодержитТип(ПроизвольныйТип());	
КонецФункции      

Функция ТипВыраженияУсловияКорректен(ТипЗначения) Экспорт  
	Возврат ТипЗначения.Типы().Количество() = 1 
		И (ТипЗначения.СодержитТип(Тип("Булево"))
		Или СодержитПроизвольныйТип(ТипЗначения));		
КонецФункции		

Процедура ПроверитьТипЗначенияВыраженияПоля(ТипЗначения, ТекстВыражения = Неопределено) Экспорт
	Если ТипЗначения <> Неопределено И ТипЗначения.СодержитТип(Тип("СписокЗначений")) Тогда
		ТекстИсключения = "Не корректный тип выражения для поля запроса";
		Если ТекстВыражения <> Неопределено Тогда
			ТекстИсключения = ТекстИсключения + "
			|" + ТекстВыражения;
		КонецЕсли;
		ТекстВыражения = ТекстВыражения + "
		|Поле запроса не может содержать списко выражений";
		ВызватьИсключение ТекстИсключения;		
	КонецЕсли;		
КонецПроцедуры	

Процедура ПроверитьТипВыраженияУсловия(ТипВыражения, ТекстВыражения) Экспорт
	Если Не ТипВыраженияУсловияКорректен(ТипВыражения) Тогда
		ТекстИсключения = "Не корректный тип выражения 
		|" + ТекстВыражения + "
		|Ожидается тип Булево";
		ВызватьИсключение ТекстИсключения;	
	КонецЕсли;		
КонецПроцедуры	

Функция ТипыРавны(ПервыйТип, ВторойТип) Экспорт
	Если ПервыйТип = Неопределено
		И ВторойТип = Неопределено Тогда
			
		Возврат Истина;
	ИначеЕсли ПервыйТип = Неопределено Или ВторойТип = Неопределено Тогда
		 Возврат Ложь;
	ИначеЕсли ПервыйТип.Типы().Количество() <> ВторойТип.Типы().Количество() Тогда
		Возврат Ложь;
	КонецЕсли;
	
	Для Каждого ПроверяемыйТип Из ВторойТип.Типы() Цикл
		Если Не ПервыйТип.СодержитТип(ПроверяемыйТип) Тогда
			Возврат Ложь;
		КонецЕсли;
	КонецЦикла;
		
	Возврат Истина;
КонецФункции

// Первый тип включает второй тип.
// 
// Параметры:
//  ПервыйТип - ОписаниеТипов
//  ВторойТип - ОписаниеТипов
Функция ПервыйТипВключаетВторойТип(ПервыйТип, ВторойТип) Экспорт
	Для Каждого ПроверяемыйТип Из ВторойТип.Типы() Цикл
		Если Не ПервыйТип.СодержитТип(ПроверяемыйТип) Тогда
			Возврат Ложь;
		КонецЕсли;
	КонецЦикла;
		
	Возврат Истина;
КонецФункции

#КонецОбласти