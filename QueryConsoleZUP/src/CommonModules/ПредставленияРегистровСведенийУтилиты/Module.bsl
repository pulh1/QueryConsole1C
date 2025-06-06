
#Область СлужебныеПроцедурыИФункции

Функция ДоступныеПоляРегистраСведений(МетаданныеРегистра) Экспорт
	Поля = Новый Массив;
	
	Для Каждого Измерение Из МетаданныеРегистра.Измерения Цикл
		Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
		Поле.Имя = Измерение.Имя;
		Поле.ТипЗначения = Измерение.Тип; 
		Поля.Добавить(Поле);	
	КонецЦикла;	
	
	Для Каждого Ресурс Из МетаданныеРегистра.Ресурсы Цикл
		Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
		Поле.Имя = Ресурс.Имя;
		Поле.ТипЗначения =  Ресурс.Тип; 
		Поля.Добавить(Поле); 
	КонецЦикла;
	
	Для Каждого Реквизит Из МетаданныеРегистра.Реквизиты Цикл
		Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
		Поле.Имя =  Реквизит.Имя;
		Поле.ТипЗначения =  Реквизит.Тип; 
		Поля.Добавить(Поле); 
	КонецЦикла;	

	Возврат Поля	
КонецФункции

Функция ИзмеренияРегистраСведений(МетаданныеРегистра) Экспорт
	Измерения = Новый Массив;
	
	Для Каждого Измерение Из МетаданныеРегистра.Измерения Цикл
		Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра(); 
		Поле.Имя = Измерение.Имя; 
		Поле.Обязательный = Ложь; 

		Измерения.Добавить(Поле);	
	КонецЦикла;	
	
	Возврат Измерения;	
КонецФункции

Функция ОписаниеПредставленияПоИмени(ИмяПредставления, ИменаОбработокИсполняемыхПредставлений) Экспорт
	Для Каждого ИмяОбработки Из ИменаОбработокИсполняемыхПредставлений Цикл
		Если Не ЭтоОбработкаИсполняемогоПредставленияРегистраСведений(ИмяОбработки) Тогда
			Продолжить;
		КонецЕсли;
		ПостфиксПредставления = СтрЗаменить(ИмяОбработки, "ПредставлениеРегистрСведений", "");
		ИмяРегистра = Сред(ИмяПредставления, СтрДлина("ИсполняемоеПредставление.РегистрСведений.") + 1);
		ИмяРегистра = Лев(ИмяРегистра, СтрДлина(ИмяРегистра) - СтрДлина(ПостфиксПредставления) - 1);
		Если ВРег(ИмяПредставления) = ВРег("ИсполняемоеПредставление.РегистрСведений." + ИмяРегистра + "." + ПостфиксПредставления) Тогда
			Описание = Обработки[ИмяОбработки].Описание(ИмяРегистра);
			Описание.ИмяОбработчика = ИмяОбработки;
			Возврат Описание;
		КонецЕсли;
	КонецЦикла;	
	
	Возврат Неопределено;
КонецФункции

Функция ИменаПредставленийРегистра(ИмяРегистра, ИменаОбработокИсполняемыхПредставлений) Экспорт
	ИменаПредставленийРегистра = Новый Массив();
	Для Каждого ИмяОбработки Из ИменаОбработокИсполняемыхПредставлений Цикл
		Если ЭтоОбработкаИсполняемогоПредставленияРегистраСведений(ИмяОбработки) Тогда
			МетаданныеРегистра = Метаданные.НайтиПоПолномуИмени(ИмяРегистра);
			Описание = Обработки[ИмяОбработки].Описание(МетаданныеРегистра.Имя);
			Если Описание <> Неопределено Тогда
				ИменаПредставленийРегистра.Добавить(Описание.Имя);
			КонецЕсли;	
		КонецЕсли;
	КонецЦикла;
	Возврат ИменаПредставленийРегистра;
КонецФункции

Функция ЭтоОбработкаИсполняемогоПредставленияРегистраСведений(ИмяОбработки)
	Возврат СтрНачинаетсяС(ИмяОбработки, "ПредставлениеРегистрСведений");
КонецФункции

Функция ДоступенИнтервальныйРегистрСведений(ИмяРегистра) Экспорт
	Возврат Метаданные.РегистрыСведений.Найти(ИнтервальныеРегистрыБЗК.ИмяИнтервальногоРегистра(ИмяРегистра)) <> Неопределено;
КонецФункции

#КонецОбласти
