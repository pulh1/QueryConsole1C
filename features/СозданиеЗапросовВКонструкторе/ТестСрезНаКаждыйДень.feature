﻿#language: ru

@tree

Функционал: Создание запроса"ТестСрезНаКаждыйДень" в конструкторе

Как Администратор я хочу
создать запрос в конструкторе
чтобы получить нужные данные

Контекст:
	И я закрыл все окна клиентского приложения
	И Я запускаю сценарий открытия TestClient или подключаю уже существующий
	И я закрыл все окна клиентского приложения
Сценарий: создание запроса ТестСрезНаКаждыйДень
	И Я открываю консоль запросов
	И Я открываю конструктор запросов
	* Добавление ИсполняемоеПредставление.РегистрСведений.КадроваяИсторияСотрудников.СрезПоследних
		И Я добавляю источник "ИсполняемоеПредставление.РегистрСведений.КадроваяИсторияСотрудников.СрезПоследних" в конструкторе запроса
		* Установка запроса фильтра
			И Я открываю конструктор запроса-фильтра исполняемого представления
			* Добавление ИсполняемоеПредставление.Периоды
				И Я добавляю источник "ИсполняемоеПредставление.Периоды" в конструкторе запроса
				И Я присваиваю параметр запроса "ДатаНачала" параметру "НачалоИнтервала" исполняемого представления
				И Я присваиваю параметр запроса "ДатаОкончания" параметру "ОкончаниеИнтервала" исполняемого представления
				И Я присваиваю значение выражения 'ДЕНЬ' параметру "Периодичность" исполняемого представления
				И Я завершаю редактирование параметров исполняемого представления
				И Я устанавливаю Псевдоним "Периоды" для текущего источника
			И Я добавляю источник "Справочник.Сотрудники" как "Сотрудники" в конструкторе запроса
			И Я добавляю поле запроса "Периоды.Период" как "Период" в конструкторе запроса
			И Я добавляю поле запроса "Сотрудники.Ссылка" как "Ссылка" в конструкторе запроса
			И Через редактор выражений я добавляю условие 'Сотрудники.Ссылка = &Сотрудник'
			И Я завершаю редактирование текущего запроса в конструкторе
			И Я устанавливаю соответствие поля "Ссылка" полю фильтра "Сотрудник"
		И Я завершаю редактирование параметров исполняемого представления
		И Я устанавливаю Псевдоним "КадроваяИсторияСотрудниковСрезПоследних" для текущего источника
	И Я добавляю поле запроса "КадроваяИсторияСотрудниковСрезПоследних.Сотрудник" как "Сотрудник" в конструкторе запроса
	И Я добавляю поле запроса "КадроваяИсторияСотрудниковСрезПоследних.Подразделение" как "Подразделение" в конструкторе запроса
	И Я добавляю поле запроса "КадроваяИсторияСотрудниковСрезПоследних.Должность" как "Должность" в конструкторе запроса
	И Я добавляю поле запроса "КадроваяИсторияСотрудниковСрезПоследних.Период" как "Период" в конструкторе запроса
	И Я добавляю упорядочивание по колонке запроса "Сотрудник" по "Возрастание"
	И Я добавляю упорядочивание по колонке запроса "Период" по "Возрастание"
	И Я завершаю редактирование текущего запроса в конструкторе
	* Проверка результата создания запроса
		Тогда Текст запроса в консоли соответствует эталону "files/ТестСрезНаКаждыйДень.txt"
