#Область СлужебныеПроцедурыИФункции

Функция НовыйГруппаДоступныхВременныхТаблиц() Экспорт
	ГруппаДоступныхВременныхТаблиц = Новый Структура;
	ГруппаДоступныхВременныхТаблиц.Вставить("Тип", "ГруппаДоступныхВременныхТаблиц");  
	
	Возврат ГруппаДоступныхВременныхТаблиц; 
КонецФункции   

Функция НовыйПолеВложеннойТаблицы() Экспорт 
	Возврат Новый Структура("Тип, Имя, ТипЗначения, Роль, Поля", "ПолеВложеннойТаблицы");
КонецФункции	  

Функция НовыйПолеТаблицы() Экспорт 
	Возврат Новый Структура("Тип, Имя, ТипЗначения, Роль, Поля", "ДоступноеПолеТаблицы")	
КонецФункции	

Функция НовыйГруппаВсеПоля() Экспорт
	ГруппаДоступныхВременныхТаблиц = Новый Структура;
	ГруппаДоступныхВременныхТаблиц.Вставить("Тип", "ГруппаВсеПоля");     
	ГруппаДоступныхВременныхТаблиц.Вставить("Пустой", Истина);
	
	Возврат ГруппаДоступныхВременныхТаблиц; 
	
КонецФункции	

Процедура ДобавитьТаблицыЗапроса(УзелДереваТаблиц, ИсточникиДанных, ДоступныеТаблицыИБ) Экспорт 
	УзелДереваТаблиц.ПолучитьЭлементы().Очистить(); 
	
	Индекс = 0;
	Для Каждого Источник Из ИсточникиДанных.Элементы Цикл  
		УзелИсточника = ДобавитьТаблицу(УзелДереваТаблиц, Источник, ДоступныеТаблицыИБ);
		Если УзелИсточника.Свойство("ИдентификаторИсточника") Тогда
			УзелИсточника.ИдентификаторИсточника = Источник.ИдентификаторИсточника;
		КонецЕсли;	
		Если УзелИсточника.Свойство("ИндексИсточника") Тогда
			УзелИсточника.ИндексИсточника = Индекс;
		КонецЕсли;	
		Индекс = Индекс + 1;
	КонецЦикла;	  
КонецПроцедуры   

Функция ДобавитьТаблицу(УзелДереваТаблиц, ОписаниеИсточника, ДоступныеТаблицыИБ) Экспорт 
	Если ОписаниеИсточника.Источник.Тип = "ИсточникДанныхТаблица" Тогда
		НовыйУзел = УзелДереваТаблиц.ПолучитьЭлементы().Добавить();
		НовыйУзел.Имя = ОписаниеИсточника.Источник.ИмяТаблицы;
 		НовыйУзел.Представление = ОписаниеИсточника.Источник.Псевдоним;
		НовыйУзел.Псевдоним = ОписаниеИсточника.Источник.Псевдоним;
		
		ТаблицаИБ = ДоступныеТаблицыИБ.Найти(ОписаниеИсточника.Источник.ИмяТаблицы);
		Если ТипЗнч(ТаблицаИБ) = Тип("ДоступнаяТаблицаСхемыЗапроса") Тогда
			НовыйУзел.Картинка = ИндексКартинки(НовыйУзел.Имя); 
			НовыйУзел.ТипЗначения = ОписаниеИсточника.Источник.Тип;   
		ИначеЕсли ТипЗнч(ТаблицаИБ) = Тип("ДоступнаяВложеннаяТаблицаСхемыЗапроса") Тогда
        	НовыйУзел.Картинка = 29; 
			НовыйУзел.ТипЗначения = "ДоступнаяВложеннаяТаблицаСхемыЗапроса";
		Иначе
			НовыйУзел.Картинка = ИндексКартинки(НовыйУзел.Имя);
		КонецЕсли;		
	ИначеЕсли ОписаниеИсточника.Источник.Тип = "ИсточникДанныхВложенныйЗапрос" Тогда
		НовыйУзел = УзелДереваТаблиц.ПолучитьЭлементы().Добавить();
		НовыйУзел.ТипЗначения = ОписаниеИсточника.Источник.Тип;
		НовыйУзел.Имя = ОписаниеИсточника.Источник.Псевдоним;
		НовыйУзел.Картинка = ИндексКартинки("ВложенныйЗапрос");
 		НовыйУзел.Представление = ОписаниеИсточника.Источник.Псевдоним;   
		
		НовыйУзел.Псевдоним = ОписаниеИсточника.Источник.Псевдоним;
	ИначеЕсли ОписаниеИсточника.Источник.Тип = "ИсточникДанныхВременнаяТаблица" Тогда
		НовыйУзел = УзелДереваТаблиц.ПолучитьЭлементы().Добавить();
		НовыйУзел.ТипЗначения = ОписаниеИсточника.Источник.Тип;
		НовыйУзел.Имя = ОписаниеИсточника.Источник.ИмяТаблицы;
		НовыйУзел.Картинка = ИндексКартинки("ВременнаяТаблица");
 		НовыйУзел.Представление = ОписаниеИсточника.Источник.Псевдоним; 
		
		НовыйУзел.Псевдоним = ОписаниеИсточника.Источник.Псевдоним;
	ИначеЕсли ОписаниеИсточника.Источник.Тип = "ИсточникДанныхТаблицаЗначений" Тогда
		НовыйУзел = УзелДереваТаблиц.ПолучитьЭлементы().Добавить();
		НовыйУзел.ТипЗначения = ОписаниеИсточника.Источник.Тип;
		НовыйУзел.Имя = ОписаниеИсточника.Источник.ИмяТаблицы;
		НовыйУзел.Картинка = ИндексКартинки("ВременнаяТаблица");
 		НовыйУзел.Представление = "&" + ОписаниеИсточника.Псевдоним;    
		
		НовыйУзел.Псевдоним = ОписаниеИсточника.Источник.Псевдоним;     
	ИначеЕсли ОписаниеИсточника.Источник.Тип = "ИсполняемоеПредставление" Тогда	 
		НовыйУзел = УзелДереваТаблиц.ПолучитьЭлементы().Добавить();
		НовыйУзел.Имя = ОписаниеИсточника.Источник.ИмяТаблицы;
		НовыйУзел.Картинка = ИндексКартинки("ВременнаяТаблица");
 		НовыйУзел.Представление = ОписаниеИсточника.Источник.Псевдоним;  
		НовыйУзел.ТипЗначения = ОписаниеИсточника.Источник.Тип;
		НовыйУзел.ЭтоИсполняемоеПредставление = Истина;
		
		НовыйУзел.Псевдоним = ОписаниеИсточника.Источник.Псевдоним;

	Иначе
		Возврат Неопределено;
	КонецЕсли;		
		
	НовыйУзел.ПолучитьЭлементы().Добавить();   
		
	Возврат НовыйУзел;	
КонецФункции 

// TODO нужна возможность не добавлять вложенные таблицы
Процедура ЗаполнитьДочерниеЭлементыДереваДоступныхТаблиц(Идентификатор, ДеревоТаблиц, ОператорЗапроса, ДоступныеТаблицыИБ, ОписаниеДоступныхВТ) Экспорт
	Строка = ДеревоТаблиц.НайтиПоИдентификатору(Идентификатор);
	
	ДочерниеЭлементы = Строка.ПолучитьЭлементы();
	Если Не (ДочерниеЭлементы.Количество() = 1
		И Не ЗначениеЗаполнено(ДочерниеЭлементы[0].Имя)) Тогда                                                
		
		Возврат;
	КонецЕсли;	
	ДочерниеЭлементы.Очистить();                     
		
	Если КонструкторЗапросовКлиентСерверФормы.СодержитТип(Строка.ТипЗначения, Тип("ДоступнаяТаблицаСхемыЗапроса")) 
		Или КонструкторЗапросовКлиентСерверФормы.СодержитТип(Строка.ТипЗначения, Тип("ДоступнаяВложеннаяТаблицаСхемыЗапроса")) 
		Или КонструкторЗапросовКлиентСерверФормы.СодержитТип(Строка.ТипЗначения, "ДоступнаяВложеннаяТаблицаСхемыЗапроса")
		Или КонструкторЗапросовКлиентСерверФормы.СодержитТип(Строка.ТипЗначения, "ИсточникДанныхТаблица") Тогда 
		
		ДоступнаяТаблица = ДоступныеТаблицыИБ.Найти(Строка.Имя);
		Если ДоступнаяТаблица <> Неопределено Тогда
			ДобавитьЭлементыВДеревоТаблиц(Строка, ДоступнаяТаблица.Поля, ДоступныеТаблицыИБ);
		КонецЕсли;  
	ИначеЕсли ЭтоПоле(Строка) Тогда
		Поля = ДоступныеВложенныеПоляПоОписаниюТипа(Строка.ТипЗначенияПоля, ДоступныеТаблицыИБ);	
		ДобавитьЭлементыВДеревоТаблиц(Строка, Поля, ДоступныеТаблицыИБ);	    
	ИначеЕсли Строка.ЭтоГруппаИсполняемыхПредставлений Тогда
		ИдентификаторРодителя = Неопределено;
		Если Строка.Имя <> "Представления" Тогда
			ИдентификаторРодителя =  Строка.Имя;   
		КонецЕсли;	
		ЭлементыИсполняемыхПредставлений = ЭлементыИерархииИсполняемыхПредставлений(ИдентификаторРодителя);
		ДобавитьЭлементыВДеревоТаблиц(Строка, ЭлементыИсполняемыхПредставлений, ДоступныеТаблицыИБ); 
	ИначеЕсли Строка.ЭтоГруппаВременныхТаблиц Тогда
		ДобавитьЭлементыВДеревоТаблиц(Строка, ОписаниеДоступныхВТ, ДоступныеТаблицыИБ);  
	ИначеЕсли КонструкторЗапросовКлиентСерверФормы.СодержитТип(Строка.ТипЗначения, Тип("ОписаниеВременнойТаблицыСхемыЗапроса")) 
		Или КонструкторЗапросовКлиентСерверФормы.СодержитТип(Строка.ТипЗначения, "ИсточникДанныхВременнаяТаблица") 
		Или КонструкторЗапросовКлиентСерверФормы.СодержитТип(Строка.ТипЗначения, "ИсточникДанныхТаблицаЗначений") Тогда    
		
		Если Строка.Свойство("ИндексИсточника") Тогда
			ОписаниеВТ = ОператорЗапроса.Источники.Элементы[Строка.ИндексИсточника].Источник.ОписаниеВТ;
		Иначе
			ОписаниеВТ = ОписаниеДоступнойВТ(ОписаниеДоступныхВТ, Строка.Имя);
		КонецЕсли;
		Поля = ПоляВременнойТаблицы(ОписаниеВТ);
		ДобавитьЭлементыВДеревоТаблиц(Строка, Поля, ДоступныеТаблицыИБ);
	ИначеЕсли Строка.ЭтоИсполняемоеПредставление Тогда
		ОписаниеПредставления = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(Строка.Имя);
		ДобавитьЭлементыВДеревоТаблиц(Строка, ОписаниеПредставления.Поля, ДоступныеТаблицыИБ);	   
	ИначеЕсли КонструкторЗапросовКлиентСерверФормы.СодержитТип(Строка.ТипЗначения, "ИсточникДанныхВложенныйЗапрос") Тогда
		ПоляВложенногоЗапроса = ПоляВложенногоЗапроса(ОператорЗапроса, Строка.Псевдоним);   
		ДобавитьЭлементыВДеревоТаблиц(Строка, ПоляВложенногоЗапроса, ДоступныеТаблицыИБ);
	КонецЕсли;				
КонецПроцедуры 

Процедура ДобавитьЭлементыВДеревоТаблиц(Узел, ДочерниеЭлементы, ДоступныеТаблицыИБ) Экспорт   
	Для Каждого ПодчиненныйЭлемент Из ДочерниеЭлементы Цикл 
		ДобавитьЭлементВДеревоТаблиц(Узел, ПодчиненныйЭлемент, ДоступныеТаблицыИБ);		
	КонецЦикла;		
КонецПроцедуры	

Процедура ЗаполнитьВыбранныеПоляЗапроса(ТекущийУзел, ВыбранныеПоляЗапроса, ОператорЗапроса) Экспорт 
	Генератор = ГенерацияТекстовЗапросов.СоздатьГенераторТекстовВыражений(Новый Массив());
	Генератор.УстановитьИсточники(ОператорЗапроса.Источники.Элементы);
	Индекс = 0;
	Для Каждого Поле Из ВыбранныеПоляЗапроса Цикл	
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();
		НовыйУзел.Представление = ГенерацияТекстовЗапросов.ВыражениеВСтроку(Поле.Выражение, Генератор);
		НовыйУзел.ТипЗначенияПоля = Поле.ТипЗначения;  
		НовыйУзел.ТипЗначения = Поле.Тип; 
		НовыйУзел.Картинка = 22;	
		НовыйУзел.ИндексПоля = Индекс;
		Индекс = Индекс + 1; 
	КонецЦикла;	
КонецПроцедуры	

Функция ДобавитьЭлементВДеревоТаблиц(ТекущийУзел, Элемент, ДоступныеТаблицыИБ, Уровень = 0) Экспорт 
	Уровень = Уровень + 1;  
	НовыйУзел = Неопределено;
	Если ТипЗнч(Элемент) = Тип("ДоступныеТаблицыСхемыЗапроса") Тогда 
		ДочерниеЭлементы = Элемент;              
		НовыйУзел = ТекущийУзел;   
	ИначеЕсли ТипЗнч(Элемент) = Тип("ГруппаДоступныхТаблицСхемыЗапроса") Тогда 
		ДочерниеЭлементы = Элемент.Состав;                                  
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();
		НовыйУзел.Представление = Элемент.Представление;
		НовыйУзел.Имя = Элемент.Представление;
		НовыйУзел.Картинка = КонструкторЗапросовФормы.ИндексКартинки(НовыйУзел.Имя); 
		НовыйУзел.ТипЗначения = Новый ОписаниеТипов("ГруппаДоступныхТаблицСхемыЗапроса");
	ИначеЕсли ТипЗнч(Элемент) = Тип("ДоступнаяТаблицаСхемыЗапроса") Тогда 
		Если СтрЗаканчиваетсяНа(Элемент.Имя, ".Изменения") Тогда
			Возврат НовыйУзел;
		КонецЕсли;	
		
		ДочерниеЭлементы = Новый Массив;        
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();
		НовыйУзел.Имя = Элемент.Имя;
		НовыйУзел.Картинка = ИндексКартинки(НовыйУзел.Имя);

		ЧастиПредставления = СтрРазделить(Элемент.Имя, ".");
		Если ЧастиПредставления.Количество() = 3 Тогда
			НовыйУзел.Представление = ЧастиПредставления[1] + ЧастиПредставления[2];	
		Иначе
			НовыйУзел.Представление = ЧастиПредставления[ЧастиПредставления.ВГраница()];  	
		КонецЕсли;
		НовыйУзел.ТипЗначения = Новый ОписаниеТипов("ДоступнаяТаблицаСхемыЗапроса");
		
		НовыйУзел.ПолучитьЭлементы().Добавить();
	ИначеЕсли ТипЗнч(Элемент) = Тип("ДоступнаяВложеннаяТаблицаСхемыЗапроса") Then
		ДочерниеЭлементы = Новый Массив; 
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();  
		НовыйУзел.ТипЗначения = "ДоступнаяВложеннаяТаблицаСхемыЗапроса";
		НовыйУзел.Представление = Элемент.Имя;
		НовыйУзел.Имя = Элемент.Имя;
		
		НовыйУзел.Картинка = 29;
		НовыйУзел.ПолучитьЭлементы().Добавить();
	ИначеЕсли ТипЗнч(Элемент) = Тип("ДоступноеПолеСхемыЗапроса")
		Или (ТипЗнч(Элемент) = Тип("Структура")
			И Элемент.Тип = "ДоступноеПолеТаблицы") Тогда  
			
		ДочерниеЭлементы = Новый Массив;
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();
		НовыйУзел.Представление = Элемент.Имя;
		НовыйУзел.Имя = Элемент.Имя;
		НовыйУзел.ТипЗначенияПоля = Элемент.ТипЗначения;   
		
		НовыйУзел.ТипЗначения = "ДоступноеПолеТаблицы";	
			
		Если  Элемент.Роль = Неопределено Тогда
			НовыйУзел.Картинка = 22;	
		ИначеЕсли Элемент.Роль.Измерение Тогда
			НовыйУзел.Картинка = 27;
		ИначеЕсли Элемент.Роль.Ресурс Then
			НовыйУзел.Картинка = 23; 
		Иначе
			НовыйУзел.Картинка = 22;	
		КонецЕсли;            
		Если Элемент.Поля.Количество() Тогда
			НовыйУзел.ПолучитьЭлементы().Добавить();
		КонецЕсли;	         
	ИначеЕсли ТипЗнч(Элемент) = Тип("Структура")
		И (Элемент.Тип = "ПолеПредставления" 
		Или Элемент.Тип = "ПолеВложеннойТаблицы") Тогда
		
		ДочерниеЭлементы = Новый Массив;
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();
		НовыйУзел.Представление = Элемент.Имя;
		НовыйУзел.Имя = Элемент.Имя;  
		НовыйУзел.ТипЗначения = Элемент.Тип;
		НовыйУзел.ТипЗначенияПоля = Элемент.ТипЗначения;  
		НовыйУзел.Картинка = 22;
		
		Если ДоступныеВложенныеПоляПоОписаниюТипа(Элемент.ТипЗначения, ДоступныеТаблицыИБ).Количество() > 0 Тогда
			НовыйУзел.ПолучитьЭлементы().Добавить();
		КонецЕсли;				
	ИначеЕсли ТипЗнч(Элемент) = Тип("Структура")
		И Элемент.Тип = "ЭлементИерархииИсполняемыхПредставлений" Тогда	 
		
		ДочерниеЭлементы = Новый Массив;
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();
		НовыйУзел.ТипЗначения = Элемент.Тип;
		НовыйУзел.Представление = Элемент.Наименование;
		НовыйУзел.Имя = Элемент.Идентификатор;	
		Если Элемент.ЭтоГруппа Тогда
			НовыйУзел.Картинка = 20;      
			НовыйУзел.ЭтоГруппаИсполняемыхПредставлений = Истина;
		Иначе
			НовыйУзел.Картинка = 18;
			НовыйУзел.ЭтоИсполняемоеПредставление = Истина;
		КонецЕсли;
		
		НовыйУзел.ПолучитьЭлементы().Добавить();	 
	ИначеЕсли ТипЗнч(Элемент) = Тип("Структура")
		И Элемент.Тип = "ГруппаДоступныхВременныхТаблиц" Тогда	 
		
		ДочерниеЭлементы = Новый Массив;
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить(); 
		НовыйУзел.ТипЗначения = Элемент.Тип;
		НовыйУзел.Представление = "Временные таблицы";
		НовыйУзел.Имя = "ВременныеТаблицы";	
		НовыйУзел.Картинка = 20;      
		НовыйУзел.ЭтоГруппаВременныхТаблиц = Истина;
		
		НовыйУзел.ПолучитьЭлементы().Добавить();
	ИначеЕсли ТипЗнч(Элемент) = Тип("Структура")
		И Элемент.Тип = "ОписаниеВременнойТаблицы" Тогда	 
		
		ДочерниеЭлементы = Новый Массив;
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();    
		НовыйУзел.Представление = Элемент.Имя;
		НовыйУзел.Имя = Элемент.Имя;	
		НовыйУзел.Картинка = 18;      
		НовыйУзел.ТипЗначения = Новый ОписаниеТипов("ОписаниеВременнойТаблицыСхемыЗапроса");
		
		НовыйУзел.ПолучитьЭлементы().Добавить();	
	
	ИначеЕсли ТипЗнч(Элемент) = Тип("ДоступныеПоляСхемыЗапроса") Тогда 
		ДочерниеЭлементы = Элемент;  
		НовыйУзел = ТекущийУзел;       
	ИначеЕсли ТипЗнч(Элемент) = Тип("Структура")
		И Элемент.Тип = "ГруппаВсеПоля" Тогда	 
		
		ДочерниеЭлементы = Новый Массив;
		
		НовыйУзел = ТекущийУзел.ПолучитьЭлементы().Добавить();
		НовыйУзел.Представление = "Все поля";
		НовыйУзел.Имя = "Все поля";	    
		НовыйУзел.ТипЗначения = Элемент.Тип;
		
		Если Не Элемент.Пустой Тогда
			НовыйУзел.ПолучитьЭлементы().Добавить();
		КонецЕсли;	
	Иначе
		Возврат НовыйУзел;
	КонецЕсли;
	
	ДобавитьЭлементыВДеревоТаблиц(НовыйУзел, ДочерниеЭлементы, ДоступныеТаблицыИБ); 
	
	Уровень = Уровень - 1;
	
	Возврат НовыйУзел;
КонецФункции	

Функция МодельЗапросаИзВременногоХранилища(Форма, ДляИзменения = Ложь) Экспорт 
	Модель = ПолучитьИзВременногоХранилища(Форма.АдресМоделиЗапроса);
	Если Не ДляИзменения Тогда
		МодельЗапросаВоВременноеХранилище(Форма, Модель);	
	КонецЕсли;
	
	Возврат Модель;
КонецФункции	   

Процедура МодельЗапросаВоВременноеХранилище(Форма, Модель) Экспорт 
	Форма.АдресМоделиЗапроса = ПоместитьВоВременноеХранилище(Модель, Форма.УникальныйИдентификатор);
КонецПроцедуры	  

Функция ОписаниеДоступныхВТИзВременногоХранилища(Форма, ДляИзменения = Ложь) Экспорт 
	ОписаниеДоступныхВТ = ПолучитьИзВременногоХранилища(Форма.АдресСпискаДоступныхВТ);
	Если Не ДляИзменения Тогда
		ОписаниеДоступныхВТВоВременноеХранилище(Форма, ОписаниеДоступныхВТ);	
	КонецЕсли;
	
	Возврат ОписаниеДоступныхВТ;
КонецФункции	   

Процедура ОписаниеДоступныхВТВоВременноеХранилище(Форма, ОписаниеДоступныхВТ) Экспорт 
	Форма.АдресСпискаДоступныхВТ = ПоместитьВоВременноеХранилище(ОписаниеДоступныхВТ, Форма.УникальныйИдентификатор);
КонецПроцедуры	  

Функция ТекущийОператорЗапроса(Форма, ДляИзменения = Ложь) Экспорт  
	Запрос = ТекущийЗапрос(Форма); 
	Возврат Запрос.Операторы[Форма.ИндексОператораЗапроса];
КонецФункции

Функция ТекущийЗапрос(Форма, ДляИзменения = Ложь) Экспорт
	Модель = МодельЗапросаИзВременногоХранилища(Форма, ДляИзменения);  
	Если Модель.Тип = "ЗапросВыбора" Тогда
		Возврат Модель;
	Иначе	
		Возврат Модель.Элементы[Форма.ИндексЗапроса]; 
	КонецЕсли;	
КонецФункции

Функция ДоступныеВложенныеПоляПоОписаниюТипа(ОписаниеТипа, ДоступныеТаблицыИБ)
	Если ОписаниеТипа = Неопределено Тогда
		Возврат Новый Массив();
	КонецЕсли;		
	
	ТипыПолей = Новый Соответствие;  
	НаличиеПодчиненныхПолей = Новый Соответствие;
	ДоступныеВложенныеПоля = Новый Массив;
	Для Каждого Тип Из ОписаниеТипа.Типы() Цикл
		МетаданныеТипа = Метаданные.НайтиПоТипу(Тип);
		Если МетаданныеТипа = Неопределено Тогда
			Продолжить;
		КонецЕсли;
		
		ТаблицаИБ = ДоступныеТаблицыИБ.Найти(МетаданныеТипа.ПолноеИмя());
		Если ТаблицаИБ = Неопределено Тогда
			Продолжить;
		КонецЕсли;
		
		Для Каждого Поле Из ТаблицаИБ.Поля Цикл 
			Если ТипЗнч(Поле) = Тип("ДоступнаяВложеннаяТаблицаСхемыЗапроса") Тогда
				Продолжить;
			КонецЕсли;	
			ОписаниеТипаВложенногоПоля = ТипыПолей.Получить(Поле.Имя);
			Если ОписаниеТипаВложенногоПоля = Неопределено Тогда
				ОписаниеТипаВложенногоПоля = Поле.ТипЗначения; 
				ДоступноеПоле = НовыйПолеТаблицы(); 
				ДоступноеПоле.Имя = Поле.Имя;
				ДоступныеВложенныеПоля.Добавить(ДоступноеПоле);
			Иначе
				ОписаниеТипаВложенногоПоля = Новый ОписаниеТипов(ОписаниеТипаВложенногоПоля, Поле.ТипЗначения.Типы());
			КонецЕсли;
			ТипыПолей.Вставить(Поле.Имя, ОписаниеТипаВложенногоПоля);   
			
			Если Поле.Поля.Количество() <> 0 Тогда
				НаличиеПодчиненныхПолей.Вставить(Поле.Имя, Истина);
			КонецЕсли;	
		КонецЦикла;		
	КонецЦикла;	 
	
	Для Каждого Поле Из ДоступныеВложенныеПоля Цикл
		Поле.ТипЗначения = ТипыПолей[Поле.Имя];  
		Поле.Поля = Новый Массив;
		Если НаличиеПодчиненныхПолей.Получить(Поле.Имя) = Истина Тогда
			Поле.Поля.Добавить("");
		КонецЕсли;	
	КонецЦикла;
	
	Возврат ДоступныеВложенныеПоля;
КонецФункции  

Функция ОписаниеДоступнойВТ(ОписаниеДоступныхВТ, ИмяВТ)
	Для Каждого ОписаниеВТ Из ОписаниеДоступныхВТ Цикл
		Если ОписаниеВТ.Имя = ИмяВТ Тогда
			Возврат ОписаниеВТ;
		КонецЕсли;
	КонецЦикла;	
	
	Возврат Неопределено;
КонецФункции

Функция ПоляВременнойТаблицы(ОписаниеВТ)
	Поля = Новый Массив;
	Если ОписаниеВТ = Неопределено Тогда
		Возврат Поля;
	КонецЕсли;	
	
	Для Каждого ИмяПоля Из ОписаниеВТ.ПорядокКолонок Цикл
		Поле = НовыйПолеВложеннойТаблицы(); 
		Поле.Имя = ИмяПоля;
		Поле.ТипЗначения = ОписаниеВТ.Колонки[ИмяПоля]; 
		
		Поля.Добавить(Поле);
	КонецЦикла;	
	
	Возврат Поля;
КонецФункции

Функция ПоляВложенногоЗапроса(ОператорЗапроса, Псевдоним) 
	Поля = Новый Массив;
	
	Для Каждого Эдемент Из ОператорЗапроса.Источники.Элементы Цикл
		Если Эдемент.Источник.Тип = "ИсточникДанныхВложенныйЗапрос"
			И Эдемент.Источник.Псевдоним = Псевдоним Тогда
			
			Для Каждого Колонка Из Эдемент.Источник.ЗапросВыбора.Колонки Цикл 
				Поле = НовыйПолеВложеннойТаблицы(); 
				Поле.Имя = Колонка.Имя;
				Поле.ТипЗначения = Колонка.ТипЗначения;
				
				Поля.Добавить(Поле);
			КонецЦикла;	
			
			Прервать;
		КонецЕсли; 
	КонецЦикла;	
	
	Возврат Поля;
КонецФункции	

Функция НовыйЭлементИерархииИсполняемыхПредставлений() Экспорт
	ГруппаИсполняемыхПредставлений = Новый Структура;
	ГруппаИсполняемыхПредставлений.Вставить("Тип", "ЭлементИерархииИсполняемыхПредставлений");
	ГруппаИсполняемыхПредставлений.Вставить("Идентификатор", ""); 
	ГруппаИсполняемыхПредставлений.Вставить("ЭтоГруппа", Ложь);
	ГруппаИсполняемыхПредставлений.Вставить("Наименование", "");   
	
	Возврат ГруппаИсполняемыхПредставлений;
КонецФункции	

Функция ЭлементыИерархииИсполняемыхПредставлений(ИдентификаторРодителя = Неопределено) Экспорт 
	ЭлементыИерархии = Новый Массив;
	Если ИдентификаторРодителя = Неопределено Тогда    
		ИменаГрупп = ПоставщикИсполняемыхПредставлений.ГруппыИсполняемыхПредставлений();
		Для Каждого ИмяГруппы Из ИменаГрупп Цикл
			Группа = НовыйЭлементИерархииИсполняемыхПредставлений(); 
			ЭлементыИерархии.Добавить(Группа);
			Группа.Идентификатор = ИмяГруппы;
			Группа.ЭтоГруппа = Истина;  
			Группа.Наименование = ИмяГруппы;
		КонецЦикла;
	Иначе
		ИменаВложенныхГрупп = ПоставщикИсполняемыхПредставлений.ИменаДочернихГрупп(ИдентификаторРодителя);
		Для Каждого ИмяГруппы Из ИменаВложенныхГрупп Цикл
			ЧастиИмени = СтрРазделить(ИмяГруппы, ".");
			
			Группа = НовыйЭлементИерархииИсполняемыхПредставлений(); 
			ЭлементыИерархии.Добавить(Группа);
			Группа.Идентификатор = ИмяГруппы;
			Группа.ЭтоГруппа = Истина;  
			Группа.Наименование = ЧастиИмени[ЧастиИмени.ВГраница()];
		КонецЦикла;
		
		ИменаИсполняемыхПредставлений = ПоставщикИсполняемыхПредставлений.ИменаПредставленийВходящихВГруппу(ИдентификаторРодителя);
		Для Каждого ИмяПредставления Из ИменаИсполняемыхПредставлений Цикл
			ЧастиИмени = СтрРазделить(ИмяПредставления, ".");
			
			Элемент = НовыйЭлементИерархииИсполняемыхПредставлений(); 
			ЭлементыИерархии.Добавить(Элемент);
			Элемент.Идентификатор = ИмяПредставления;
			Элемент.ЭтоГруппа = Ложь;  
			Элемент.Наименование = ЧастиИмени[ЧастиИмени.ВГраница()]; 
		КонецЦикла;
		
	КонецЕсли;	
	
	Возврат ЭлементыИерархии;
КонецФункции

Функция ИндексКартинки(ИмяЭлемента) Экспорт
	КартинкиПоТипам = КонструкторЗапросовФормыПовтИсп.КартинкиПоТипамЭлементов();
	
	ЧастиИмени = СтрРазделить(ИмяЭлемента, ".");
	
	Возврат КартинкиПоТипам.Получить(ЧастиИмени[0]);
КонецФункции  

Функция ЭтоПоле(СтрокаТаблицы) Экспорт 
	Если КонструкторЗапросовКлиентСерверФормы.СодержитТип(СтрокаТаблицы.ТипЗначения, Тип("ДоступноеПолеСхемыЗапроса")) Тогда
		Возврат Истина;
	Иначе
		Возврат КонструкторЗапросовКлиентСерверФормы.ЭтоПоле(СтрокаТаблицы);		
	КонецЕсли;		
КонецФункции 
	
#КонецОбласти