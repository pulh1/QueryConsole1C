
#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда
	
#Область СлужебныеПроцедурыИФункции

Функция Описание() Экспорт
	Описание = ЭлементыМоделиОписанияПредставлений.НовыйОписаниеПредставления();
	Описание.Имя = ИмяПредставления(); 
	
	Описание.ПоддерживаютсяИндексы = Ложь;
	Описание.ПоддерживаетсяУказаниеИмяВТРезультат = Истина;
	Описание.ДоступноВМеханизмеПредставленийСКД = Истина;
	Описание.ИмяВТДляСКД = "Представления_ШтатноеРасписание";  
	Описание.ПоддерживаютсяИндексы = Ложь;
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПозицияШтатногоРасписания";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ШтатноеРасписание");
	Описание.Поля.Добавить(Поле); 
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Наименование";
	Поле.ТипЗначения = Новый ОписаниеТипов("Строка");
	Описание.Поля.Добавить(Поле); 
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "НаименованиеПолное";
	Поле.ТипЗначения = Новый ОписаниеТипов("Строка");
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
	Поле.Имя = "РайонныйКоэффициент";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Утверждена";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДатаУтверждения";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Закрыта";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДатаЗакрытия";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Описание";
	Поле.ТипЗначения = Новый ОписаниеТипов("Строка");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "УсловияПриема";
	Поле.ТипЗначения = Новый ОписаниеТипов("Строка");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ГрафикРаботыСотрудников";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ГрафикиРаботыСотрудников");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ТарифнаяСетка";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ТарифныеСетки");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РазрядКатегория";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.РазрядыКатегорииДолжностей");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ТарифнаяСеткаНадбавки";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ТарифныеСетки");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РазрядКатегорияНадбавки";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.РазрядыКатегорииДолжностей");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "СпособОтраженияЗарплатыВБухучете";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.СпособыОтраженияЗарплатыВБухУчете");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОтношениеКЕНВД";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.ОтношениеКЕНВДЗатратНаЗарплату");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "СтатьяФинансирования";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.СтатьиФинансированияЗарплата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВзимаютсяВзносыЗаЗанятыхНаРаботахСДосрочнойПенсией";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.ВидыРаботСДосрочнойПенсией");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОснованиеДосрочногоНазначенияПенсии";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ОснованияДосрочногоНазначенияПенсии");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОсобыеУсловияТрудаПФР";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ОсобыеУсловияТрудаПФР");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "КодПозицииСпискаПФР";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.СпискиПрофессийДолжностейЛьготногоПенсионногоОбеспечения");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ТрудоваяФункция";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ТрудовыеФункции");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ХарактерВыполняемыхРаботПФР";
	Поле.ТипЗначения = Новый ОписаниеТипов("Строка");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПервичныеДокументыПФР";
	Поле.ТипЗначения = Новый ОписаниеТипов("Строка");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВидСтажаЛетныхЭкипажей";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.ВидыСтажаЛетныхЭкипажей");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВидСтажаШахтеров";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.ВидыСтажаШахтеров");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВыплачиваетсяНадбавкаЗаВредность";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПроцентНадбавкиЗаВредность";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОкладТарифМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТМакс";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТПозицииМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТПозицииМакс";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РайонныйКоэффициентРазмерМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РайонныйКоэффициентРазмерМакс";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "СевернаяНадбавкаРазмерМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "СевернаяНадбавкаРазмерМакс";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "НадбавкаЗаВредностьРазмерМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "НадбавкаЗаВредностьРазмерМакс";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ОкладТариф";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТ";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТПозиции";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РайонныйКоэффициентРазмер";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "СевернаяНадбавкаРазмер";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "НадбавкаЗаВредностьРазмер";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Если ПолучитьФункциональнуюОпцию("ИспользоватьИсториюИзмененияШтатногоРасписания") Тогда
		Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
		Поле.Имя = "Регистратор";
		Поле.ТипЗначения = Метаданные.РегистрыСведений.ИсторияИспользованияШтатногоРасписания.СтандартныеРеквизиты.Регистратор.Тип;
		Описание.Поля.Добавить(Поле);
	КонецЕсли;
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПрименятьСевернуюНадбавку";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПроцентСевернойНадбавки";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПроцентСевернойНадбавки";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "КлассУсловийТруда";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПеречислениеСсылка.КлассыУсловийТрудаПоРезультатамСпециальнойОценки");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "КлассУсловийТрудаПериод";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "КлассУсловийТрудаДатаРегистрацииИзменений";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "КлассУсловийТрудаДатаРегистрацииИзменений";
	Поле.ТипЗначения = Новый ОписаниеТипов("Дата");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Занято";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ЗанятаПостоянно";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ЗанятаВременно";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПодработкаПостоянно";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ПодработкаВременно";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "СовмещенаПостоянно";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "СовмещенаВременно";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Забронирована";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ВременноОсвобождена";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "МестоВСтруктуреПредприятия";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.СтруктураПредприятия");
	Поле.ДоступноПриНаличииПодсистемы = "ЗарплатаКадрыПриложения.ОрганизационнаяСтруктура";
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТУправленческийМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поле.ДоступноПриНаличииПодсистемы = "ЗарплатаКадрыКорпоративнаяПодсистемы.УправленческаяЗарплата";
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТУправленческийМакс";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поле.ДоступноПриНаличииПодсистемы = "ЗарплатаКадрыКорпоративнаяПодсистемы.УправленческаяЗарплата";
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ФОТУправленческий";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поле.ДоступноПриНаличииПодсистемы = "ЗарплатаКадрыКорпоративнаяПодсистемы.УправленческаяЗарплата";
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ИспользоватьУправленческиеНачисления";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Поле.ДоступноПриНаличииПодсистемы = "ЗарплатаКадрыКорпоративнаяПодсистемы.УправленческаяЗарплата";
	Описание.Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ДоначислятьДоУправленческогоУчета";
	Поле.ТипЗначения = Новый ОписаниеТипов("Булево");
	Поле.ДоступноПриНаличииПодсистемы = "ЗарплатаКадрыКорпоративнаяПодсистемы.УправленческаяЗарплата";
	Описание.Поля.Добавить(Поле);
	
	Для Каждого Поле Из ОписаниеПолейСведенийОНачислениях() Цикл
		Описание.Поля.Добавить(Поле);
	КонецЦикла;
	
	Описание.ОписаниеВТФильтр =  ЭлементыМоделиОписанияПредставлений.НовыйОписаниеВТФильтр();
	Описание.ОписаниеВТФильтр.Обязательный = Истина; 
	Описание.ОписаниеВТФильтр.ПоддерживаютсяПсевдонимы = Истина;
	Описание.ОписаниеВТФильтр.ПоддерживаетсяИмяВТФильтр = Истина;    
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "Период";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	ПолеФильтра =  ЭлементыМоделиОписанияПредставлений.НовыйПолеФильтра();  
	ПолеФильтра.Имя = "ПозицияШтатногоРасписания";
	ПолеФильтра.Обязательный = Истина;	
	Описание.ОписаниеВТФильтр.ПоляФильтра.Добавить(ПолеФильтра);
	
	// дополнять данными о РК, северной надбавке и т.п	
	ОписаниеПараметра =  ОписаниеИсполняемыхПредставленийУтилиты.ОписаниеПараметраКонстанта(
		"ПолноеОписаниеНачислений", 
		Новый ОписаниеТипов("Булево"), 
		Ложь, 
		Ложь,
		Ложь);
	Описание.ОписаниеПараметров.Добавить(ОписаниеПараметра);		
		
	// TODO добавиить проверку соотв. подсистем
	ОписаниеПараметра =  ОписаниеИсполняемыхПредставленийУтилиты.ОписаниеПараметраКонстанта(
		"Льготы", 
		Новый ОписаниеТипов("Булево"), 
		Ложь, 
		Ложь,
		Ложь);	
	Описание.ОписаниеПараметров.Добавить(ОписаниеПараметра);
	
	ОписаниеПараметра =  ОписаниеИсполняемыхПредставленийУтилиты.ОписаниеПараметраКонстанта(
		"УправленческиеНачисления", 
		Новый ОписаниеТипов("Булево"), 
		Ложь, 
		Ложь,
		Ложь);	
	Описание.ОписаниеПараметров.Добавить(ОписаниеПараметра);
	
	Возврат Описание;	
КонецФункции

Функция ИмяПредставления() Экспорт
	Возврат "ИсполняемоеПредставление.ДанныеПозицийШтатногоРасписания";
КонецФункции

// Исполнить.
// 
// Параметры:
//  ПараметрыВыполнения - см. ЭлементыМоделиИсполненияПредставлений.НовыйПараметрыВыполненияПредставления
//  Запрос - Запрос
// 
// Возвращаемое значение:
// 	РезультатЗапроса, Неопределено 
Функция Исполнить(ПараметрыВыполнения, Запрос) Экспорт
	ПараметрыПолученияДанных = УправлениеШтатнымРасписанием.ПараметрыПостроенияВТШтатноеРасписаниеПоТаблицеФильтра(
		ПараметрыВыполнения.ОписаниеВТФильтр.ИмяВТ);
	
	ПараметрыПолученияДанных.ИмяПоляПериод = ПараметрыВыполнения.ОписаниеВТФильтр.ПсевдонимыПолей.Получить("Период");
	ПараметрыПолученияДанных.ИмяПоляПозицияШтатногоРасписания 
		= ПараметрыВыполнения.ОписаниеВТФильтр.ПсевдонимыПолей.Получить("ПозицияШтатногоРасписания");
	
	ПараметрПолноеОписаниеНачислений = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("ПараметрПолноеОписаниеНачислений");
	Если ПараметрПолноеОписаниеНачислений <> Неопределено Тогда
		ПараметрыПолученияДанных.ПараметрПолноеОписаниеНачислений = ПараметрПолноеОписаниеНачислений.Значение;
	КонецЕсли;	
	
	ПараметрЛьготы = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("Льготы");
	Если ПараметрЛьготы <> Неопределено Тогда
		ПараметрыПолученияДанных.Льготы = ПараметрЛьготы.Значение;
	КонецЕсли;	
	
	ПараметрУправленческиеНачисления = ПараметрыВыполнения.ЗначенияПараметровКонстант.Получить("УправленческиеНачисления");
	Если ПараметрУправленческиеНачисления <> Неопределено Тогда
		ПараметрыПолученияДанных.УправленческиеНачисления = ПараметрУправленческиеНачисления.Значение;
	КонецЕсли;	
	
	ПоляНачислений = Новый Соответствие();
	Для Каждого Поле Из ОписаниеПолейСведенийОНачислениях() Цикл
		ПоляНачислений.Вставить(ВРег(Поле.Имя), Истина);	
	КонецЦикла;
			
	Поля = Новый Массив();
	Для Каждого Поле Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		Если ПоляНачислений.Получить(Поле.Ключ) = Неопределено Тогда
			Поля.Добавить(Поле.Ключ);	
		Иначе
			ПараметрыПолученияДанных.ДополнитьОписаниемНачислений = Истина;
		КонецЕсли;	
	КонецЦикла;	
		
	УправлениеШтатнымРасписанием.СоздатьВТШтатноеРасписание(
		Запрос.МенеджерВременныхТаблиц, 
		ПараметрыВыполнения.ТолькоРазрешенные, 
		ПараметрыПолученияДанных, 
		Поля, 
		ПараметрыВыполнения.ИмяВТРезультат);
		
	Возврат Неопределено;
КонецФункции

Функция ИсполняемыйКод(ПараметрыВыполнения, ТекущиеТаблцляции) Экспорт
	ТекстовыйДокумент = Новый ТекстовыйДокумент();
	
	Строка = "ПараметрыПолученияДанных = УправлениеШтатнымРасписанием.ПараметрыПостроенияВТШтатноеРасписаниеПоТаблицеФильтра("
		+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ОписаниеВТФильтр.ИмяВТ)
		+ ");";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	ИмяПоляПериод = ПараметрыВыполнения.ОписаниеВТФильтр.ПсевдонимыПолей.Получить("Период");
	ИмяПоляПозицияШтатногоРасписания 
		= ПараметрыВыполнения.ОписаниеВТФильтр.ПсевдонимыПолей.Получить("ПозицияШтатногоРасписания");
	
	Строка = "ПараметрыПолученияДанных.ИмяПоляПериод = " 
		+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ИмяПоляПериод)
		+ ";";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	
	Строка = "ПараметрыПолученияДанных.ИмяПоляПозицияШтатногоРасписания = " 
		+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ИмяПоляПозицияШтатногоРасписания)
		+ ";";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	ПоляНачислений = Новый Соответствие();
	Для Каждого Поле Из ОписаниеПолейСведенийОНачислениях() Цикл
		ПоляНачислений.Вставить(ВРег(Поле.Имя), Истина);	
	КонецЦикла;
			
	ДополнитьОписаниемНачислений = Ложь;
	
	Строка = "Поля = Новый Массив();";
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	Для Каждого Поле Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		Если ПоляНачислений.Получить(Поле.Ключ) = Неопределено Тогда
			Строка = "Поля.Добавить(" 
				+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(Поле.Ключ) + ");";	
			ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
		Иначе
			ДополнитьОписаниемНачислений = Истина;
		КонецЕсли;	
	КонецЦикла;		
	ТекстовыйДокумент.ДобавитьСтроку("");
		
	Если ДополнитьОписаниемНачислений Тогда
		Строка = "ПараметрыПолученияДанных.ДополнитьОписаниемНачислений = Истина;"; 	
		ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Строка);
	КонецЕсли;
	
	ИменаПараметров = Новый Структура();
	ИменаПараметров.Вставить("Льготы", "ПараметрыПолученияДанных.Льготы");
	ИменаПараметров.Вставить("УправленческиеНачисления", "ПараметрыПолученияДанных.УправленческиеНачисления");
	
	ГенерацияИсполняемогоКодаПредставленийУтилиты.КодПрисвоенияПараметровВТекстовыйДокумент(
		ТекстовыйДокумент, 
		ПараметрыВыполнения, 
		Описание(), 
		ИменаПараметров,
		ТекущиеТаблцляции);
	
	ТекстовыйДокумент.ДобавитьСтроку("");
	
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + "УправлениеШтатнымРасписанием.СоздатьВТШтатноеРасписание(");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + "Запрос.МенеджерВременныхТаблиц,");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ТолькоРазрешенные) + ",");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + "ПараметрыПолученияДанных,");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб + "Поля,");
	ТекстовыйДокумент.ДобавитьСтроку(ТекущиеТаблцляции + Символы.Таб 
		+ ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку(ПараметрыВыполнения.ИмяВТРезультат) + ");");
		
	Возврат ТекстовыйДокумент.ПолучитьТекст();
КонецФункции

Функция ТекстЗапросаДляСКД(ПараметрыВыполнения) Экспорт
	Описание = ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмени(ПараметрыВыполнения.ИмяИсполняемогоПредставления);
	
	Модель = ГенерацияИсполняемогоКодаПредставленийУтилиты.МодельЗапросаДляСКД(ПараметрыВыполнения, Описание);
	Построитель = МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель);
	
	УстанавливаемыеПараметры = Новый Структура();
	УстанавливаемыеПараметры.Вставить("Льготы", "Льготы");
	УстанавливаемыеПараметры.Вставить("УправленческиеНачисления", "УправленческиеНачисления");
	
	ГенерацияИсполняемогоКодаПредставленийУтилиты.УстановитьПараметраПредставленияВМодельЗапросаДляСКД(
		Построитель, 
		ПараметрыВыполнения, 
		Описание, 
		УстанавливаемыеПараметры);
		
	ПоляНачислений = Новый Соответствие();
	Для Каждого Поле Из ОписаниеПолейСведенийОНачислениях() Цикл
		ПоляНачислений.Вставить(ВРег(Поле.Имя), Истина);	
	КонецЦикла;
			
	Для Каждого Поле Из ПараметрыВыполнения.ИспользуемыеПоля Цикл
		// TODO в типовой в случае полученмя сведений о начислениях используется другой запрос, с ограниченным количеством сведений о позиции		
		Если ПоляНачислений.Получить(Поле.Ключ) <> Неопределено Тогда
			ВызватьИсключение "Представление " + ИмяПредставления() + " в режиме генерации кода для СКД не позволяет получать сведения о начислениях";
		КонецЕсли;	
	КонецЦикла;		
		
	Выражение = ГенерацияИсполняемогоКодаПредставленийУтилиты.ПримитивноеЗначениеВСтроку("ДополнитьОписаниемНачислений")
				+ " = ЛОЖЬ";
			
	Построитель.ДобавитьОтбор(Выражение);
	
	Запрос = Построитель.ПолучитьМодель().Элементы[0];
	ТекстЗапроса = ГенерацияТекстовЗапросов.ТекстЗапросаВыбора(Запрос);
	Возврат ТекстЗапроса;
КонецФункции

Функция ОписаниеПолейСведенийОНачислениях()
	Поля = Новый Массив();
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Начисление";
	Поле.ТипЗначения = Новый ОписаниеТипов("ПланВидовРасчетаСсылка.Начисления");
	Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Показатель";
	Поле.ТипЗначения = Новый ОписаниеТипов("СправочникСсылка.ПоказателиРасчетаЗарплаты");
	Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РазмерМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "РазмерМакс";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ЗначениеМин";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "ЗначениеМакс";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Размер";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поля.Добавить(Поле);
	
	Поле =  ЭлементыМоделиОписанияПредставлений.НовыйПолеПредставления();
	Поле.Имя = "Значение";
	Поле.ТипЗначения = Новый ОписаниеТипов("Число");
	Поля.Добавить(Поле);
	
	Возврат Поля;
КонецФункции

#КонецОбласти

#КонецЕсли
