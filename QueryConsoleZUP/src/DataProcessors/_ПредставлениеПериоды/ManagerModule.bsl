
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Представление = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления(); 
	Представление.Имя = ИмяПредставления();   
	Представление.ПоддерживаютсяИндексы = Истина; 
	Представление.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;  
			
	Поле = ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Период";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");	
	Представление.Поля.Добавить(Поле);
			
	ОписаниеПараметраНачало = ОписаниеИсполняемыхПредставленийУтилиты.ОписаниеПараметраКонстанта(
		"НачалоИнтервала", 
		ОписаниеИсполняемыхПредставленийУтилиты.ОписаниеТипаДата());  
	Представление.ОписаниеПараметров.Добавить(ОписаниеПараметраНачало);
							
	ОписаниеПараметраОкончание = ОписаниеИсполняемыхПредставленийУтилиты.ОписаниеПараметраКонстанта(
		"ОкончаниеИнтервала", 
		ОписаниеИсполняемыхПредставленийУтилиты.ОписаниеТипаДата());  
	Представление.ОписаниеПараметров.Добавить(ОписаниеПараметраОкончание);
	
	ОписаниеПараметраПериодичность = ОписаниеИсполняемыхПредставленийУтилиты.ОписаниеПараметраКонстанта(
		"Периодичность", Новый ОписаниеТипов("Строка"), 
		Истина, 
		"МЕСЯЦ");  
	
	Представление.ОписаниеПараметров.Добавить(ОписаниеПараметраПериодичность);
	 
	Возврат Представление;	
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.Периоды";
КонецФункции

#КонецОбласти

#КонецЕсли
