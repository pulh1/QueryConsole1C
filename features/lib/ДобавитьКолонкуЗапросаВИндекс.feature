﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Добавление колонки запроса в индекс

Сценарий: Я добавляю колонку запроса "ИмяКолонки" в индекс
	И я перехожу к закладке с именем 'ИндексСтраница'
	И в таблице 'ВсеПоляДляИндексации' я перехожу к строке:
		| "Поля"         |
		| "[ИмяКолонки]" |
	И в таблице 'ВсеПоляДляИндексации' я выбираю текущую строку
		
	