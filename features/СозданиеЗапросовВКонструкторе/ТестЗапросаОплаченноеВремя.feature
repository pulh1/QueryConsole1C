﻿#language: ru

@tree

Функционал: Создание запроса"ТестЗапросаОплаченноеВремя" в конструкторе

Как Администратор я хочу
создать запрос в конструкторе
чтобы получить нужные данные

Контекст:
	И я закрыл все окна клиентского приложения
	И Я запускаю сценарий открытия TestClient или подключаю уже существующий
	И я закрыл все окна клиентского приложения
Сценарий: создание запроса ТестЗапросаОплаченноеВремя
	И Я открываю консоль запросов
	И Я открываю конструктор запросов
	* Добавление ИсполняемоеПредставление.ОплаченноеВремя
		И Я добавляю источник "ИсполняемоеПредставление.ОплаченноеВремя" в конструкторе запроса
		И Я присваиваю параметр запроса "НачалоПериода" параметру "НачалоПериода" исполняемого представления
		И Я присваиваю параметр запроса "ОкончаниеПериода" параметру "ОкончаниеПериода" исполняемого представления
		И Я присваиваю параметр запроса "СписокСотр" параметру "СписокСотрудников" исполняемого представления
		И Я присваиваю параметр запроса "Организация" параметру "Организация" исполняемого представления
		И Я завершаю редактирование параметров исполняемого представления
		И Я устанавливаю Псевдоним "ОплаченноеВремя" для текущего источника
	И Я добавляю поле запроса "ОплаченноеВремя.Сотрудник" как "Сотрудник" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.МесяцНачисления" как "МесяцНачисления" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.ПериодДействия" как "ПериодДействия" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.Регистратор" как "Регистратор" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.Организация" как "Организация" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.Подразделение" как "Подразделение" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.ВидРасчета" как "ВидРасчета" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.Регистратор" как "Регистратор1" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.ДатаНачала" как "ДатаНачала" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.ВремяВЧасах" как "ВремяВЧасах" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.ОтработаноДней" как "ОтработаноДней" в конструкторе запроса
	И Я добавляю поле запроса "ОплаченноеВремя.ОтработаноЧасов" как "ОтработаноЧасов" в конструкторе запроса
	И Я завершаю редактирование текущего запроса в конструкторе
	* Проверка результата создания запроса
		Тогда Текст запроса в консоли соответствует эталону "files/ТестЗапросаОплаченноеВремя.txt"
