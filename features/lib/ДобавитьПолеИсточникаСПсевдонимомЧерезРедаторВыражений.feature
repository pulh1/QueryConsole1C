﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Добавление поля запрос в конструкторе запроса с псевдонимом

Сценарий: Через редактор выражений я добавляю поле запроса "Выражение" как "Псевдоним"
	И я перехожу к закладке с именем 'ТаблицыИПоляЗапроса'
	И я запоминаю строку "Выражение" в переменную "ПеременнаяВыражение"	
	И в таблице 'ПоляЗапроса' я нажимаю на кнопку с именем 'ПоляЗапросаДобавить'
	И В редакторе выражений я устанавливаю текст выражения "$ПеременнаяВыражение$"
	И Я устанавливаю "Псевдоним" для добавленного поля с выражением "Выражение"