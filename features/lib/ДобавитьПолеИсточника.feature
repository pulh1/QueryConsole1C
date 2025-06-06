﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Добавление поля запроса в конструкторе запроса

Сценарий: Я добавляю поле запроса "Выражение" в конструкторе запроса
	И я перехожу к закладке с именем 'ТаблицыИПоляЗапроса'
	И В таблице "Источники" Я сворачиваю все строки
	И я запоминаю строку "Выражение" в переменную "ПеременнаяВыражение"
	И Я запоминаю значение выражения 'СтрРазделить($ПеременнаяВыражение$, ".").Количество()' в переменную "КоличествоЭлементов"
	Если  переменная "КоличествоЭлементов" имеет значение 2 Тогда
		И Я по выражению "[Выражение]" сохраняю псевдоним источника и имя поля в переменные "Псевдоним" и "Поле"
		И в таблице 'Источники' я разворачиваю строку:
			| "Таблицы" |
			| "$Псевдоним$" |
		И в таблице 'Источники' я перехожу к строке:
			| "Таблицы"                       |
			| "$Поле$" |
		И в таблице 'Источники' я активизирую поле с именем 'ИсточникиПредставление'
	Иначе
		И В таблице "Источники" я перехожу к строке содержущей в поле "ИсточникиПредставление" выражение "$ПеременнаяВыражение$" с учетом иерахии
	И в таблице 'Источники' я выбираю текущую строку
	