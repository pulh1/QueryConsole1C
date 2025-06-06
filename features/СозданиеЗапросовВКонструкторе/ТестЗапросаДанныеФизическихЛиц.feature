﻿#language: ru

@tree

Функционал: Создание запроса"ТестЗапросаДанныеФизическихЛиц" в конструкторе

Как Администратор я хочу
создать запрос в конструкторе
чтобы получить нужные данные

Контекст:
	И я закрыл все окна клиентского приложения
	И Я запускаю сценарий открытия TestClient или подключаю уже существующий
	И я закрыл все окна клиентского приложения
Сценарий: создание запроса ТестЗапросаДанныеФизическихЛиц
	И Я открываю консоль запросов
	И Я открываю конструктор запросов
	* Добавление ИсполняемоеПредставление.ДанныеФизическихЛиц
		И Я добавляю источник "ИсполняемоеПредставление.ДанныеФизическихЛиц" в конструкторе запроса
		* Установка запроса фильтра
			И Я открываю конструктор запроса-фильтра исполняемого представления
			И Я добавляю источник "Справочник.ФизическиеЛица" как "ФизическиеЛица" в конструкторе запроса
			И Я добавляю поле запроса "ФизическиеЛица.Ссылка" как "ФизическоеЛицо" в конструкторе запроса
			И Через редактор выражений я добавляю поле запроса '&Период' как "Период"
			И Я завершаю редактирование текущего запроса в конструкторе
		И Я завершаю редактирование параметров исполняемого представления
		И Я устанавливаю Псевдоним "ДанныеФизическихЛиц" для текущего источника
	И Я добавляю поле запроса "ДанныеФизическихЛиц.ФизическоеЛицо" как "ФизическоеЛицо" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.Возраст" как "Возраст" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.Фамилия" как "Фамилия" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.Имя" как "Имя" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.Отчество" как "Отчество" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.ОбщийСтажЛет" как "ОбщийСтажЛет" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.ОбщийСтажМесяцев" как "ОбщийСтажМесяцев" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.ОбщийСтажДней" как "ОбщийСтажДней" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.Документы" как "Документы" в конструкторе запроса
	И Я добавляю поле запроса "ДанныеФизическихЛиц.ПолученныеОбразования" как "ПолученныеОбразования" в конструкторе запроса
	И Я завершаю редактирование текущего запроса в конструкторе
	* Проверка результата создания запроса
		Тогда Текст запроса в консоли соответствует эталону "files/ТестЗапросаДанныеФизическихЛиц.txt"
