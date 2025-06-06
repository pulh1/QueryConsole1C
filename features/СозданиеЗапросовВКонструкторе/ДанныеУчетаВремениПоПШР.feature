﻿#language: ru

@tree

Функционал: Создание запроса"ДанныеУчетаВремениПоПШР" в конструкторе

Как Администратор я хочу
создать запрос в конструкторе
чтобы получить нужные данные

Контекст:
	И я закрыл все окна клиентского приложения
	И Я запускаю сценарий открытия TestClient или подключаю уже существующий
	И я закрыл все окна клиентского приложения
Сценарий: создание запроса ДанныеУчетаВремениПоПШР
	И Я открываю консоль запросов
	И Я открываю конструктор запросов
	* Создание временной таблицы ВТСотрудники
		* Добавление ИсполняемоеПредставление.СотрудникиОрганизации
			И Я добавляю источник "ИсполняемоеПредставление.СотрудникиОрганизации" в конструкторе запроса
			И Я присваиваю параметр запроса "Организация" параметру "Организация" исполняемого представления
			И Я присваиваю параметр запроса "ДатаНачала" параметру "НачалоПериода" исполняемого представления
			И Я присваиваю значение выражения 'Истина' параметру "РаботникиПоТрудовымДоговорам" исполняемого представления
			И Я присваиваю значение выражения 'Нет' параметру "ПодработкиРаботниковПоТрудовымДоговорам" исполняемого представления
			И Я присваиваю значение выражения 'Нет' параметру "РаботникиПоДоговорамГПХ" исполняемого представления
			И Я завершаю редактирование параметров исполняемого представления
			И Я устанавливаю Псевдоним "СотрудникиОрганизации" для текущего источника
		И Я добавляю поле запроса "СотрудникиОрганизации.Сотрудник" как "Сотрудник" в конструкторе запроса
		И Я устанавливаю имя создаваемой временной таблицы "ВТСотрудники"
	* Создание запроса получения данных
		И Я добавляю запрос получения данных
		* Добавление ИсполняемоеПредставление.ДанныеУчетаВремениСотрудников
			И Я добавляю источник "ИсполняемоеПредставление.ДанныеУчетаВремениСотрудников" в конструкторе запроса
			И Я присваиваю параметр запроса "ДатаНачала" параметру "ДатаНачала" исполняемого представления
			И Я присваиваю параметр запроса "ДатаОкончания" параметру "ДатаОкончания" исполняемого представления
			И Я присваиваю параметр запроса "ДатаНачала" параметру "ДатаАктуальности" исполняемого представления
			* Установка запроса фильтра
				И Я открываю конструктор запроса-фильтра исполняемого представления
				И Я запоминаю в переменную "ПоляВТ" значение
				|'Поле'|
				|'Сотрудник'|
				И Я добавляю описание временной таблицы "ВТСотрудники" как "ВТСотрудники" с полями "$ПоляВТ$"
				И Я добавляю поле запроса "ВТСотрудники.Сотрудник" как "Сотрудник" в конструкторе запроса
				И Через редактор выражений я добавляю поле запроса '&ДатаНачала' как "ДатаНачала"
				И Через редактор выражений я добавляю поле запроса '&ДатаОкончания' как "ДатаОкончания"
				И Я завершаю редактирование текущего запроса в конструкторе
			И Я завершаю редактирование параметров исполняемого представления
			И Я устанавливаю Псевдоним "ДанныеУчетаВремениСотрудников" для текущего источника
		* Добавление ИсполняемоеПредставление.РегистрСведений.КадроваяИсторияСотрудников.Периоды
			И Я добавляю источник "ИсполняемоеПредставление.РегистрСведений.КадроваяИсторияСотрудников.Периоды" в конструкторе запроса
			И Я присваиваю значение выражения 'Истина' параметру "ФормироватьСПериодичностьДень" исполняемого представления
			И Я присваиваю значение выражения 'Истина' параметру "ВключатьЗаписиНаНачалоПериода" исполняемого представления
			* Установка запроса фильтра
				И Я открываю конструктор запроса-фильтра исполняемого представления
				И Я запоминаю в переменную "ПоляВТ" значение
				|'Поле'|
				|'Сотрудник'|
				И Я добавляю описание временной таблицы "ВТСотрудники" как "ВТСотрудники" с полями "$ПоляВТ$"
				И Я добавляю поле запроса "ВТСотрудники.Сотрудник" как "Сотрудник" в конструкторе запроса
				И Через редактор выражений я добавляю поле запроса '&ДатаНачала' как "ДатаНачала"
				И Через редактор выражений я добавляю поле запроса '&ДатаОкончания' как "ДатаОкончания"
				И Я завершаю редактирование текущего запроса в конструкторе
			И Я завершаю редактирование параметров исполняемого представления
			И Я устанавливаю Псевдоним "КадроваяИсторияСотрудниковПериоды" для текущего источника
		И Я запоминаю в переменную "УсловиеСвязи" значение
		"""
		ДанныеУчетаВремениСотрудников.Сотрудник = КадроваяИсторияСотрудниковПериоды.Сотрудник
		И ДанныеУчетаВремениСотрудников.Дата МЕЖДУ КадроваяИсторияСотрудниковПериоды.НачалоПериода И КадроваяИсторияСотрудниковПериоды.КонецПериода
		"""
		И Я устанавливаю "Левое" соединение источника "ДанныеУчетаВремениСотрудников" с источником "КадроваяИсторияСотрудниковПериоды" по условию '$УсловиеСвязи$'
		И Я добавляю поле запроса "КадроваяИсторияСотрудниковПериоды.ДолжностьПоШтатномуРасписанию" как "ДолжностьПоШтатномуРасписанию" в конструкторе запроса
		И Я добавляю поле запроса "ДанныеУчетаВремениСотрудников.ВидУчетаВремени" как "ВидУчетаВремени" в конструкторе запроса
		И Я добавляю поле запроса "ДанныеУчетаВремениСотрудников.Дни" как "Дни" в конструкторе запроса
		И Я добавляю поле запроса "ДанныеУчетаВремениСотрудников.Часы" как "Часы" в конструкторе запроса
		И Я добавляю группировку по выражению 'КадроваяИсторияСотрудниковПериоды.ДолжностьПоШтатномуРасписанию' поля запроса
		И Я добавляю группировку по выражению 'ДанныеУчетаВремениСотрудников.ВидУчетаВремени' поля запроса
		И Я устанавливаю агрегатную функцию "СУММА" для поля с выражением 'ДанныеУчетаВремениСотрудников.Дни'
		И Я устанавливаю агрегатную функцию "СУММА" для поля с выражением 'ДанныеУчетаВремениСотрудников.Часы'
		И Я добавляю упорядочивание по колонке запроса "ДолжностьПоШтатномуРасписанию" по "Возрастание"
		И Я добавляю упорядочивание по колонке запроса "ВидУчетаВремени" по "Возрастание"
	И Я завершаю редактирование текущего запроса в конструкторе
	* Проверка результата создания запроса
		Тогда Текст запроса в консоли соответствует эталону "files/ДанныеУчетаВремениПоПШР.txt"
