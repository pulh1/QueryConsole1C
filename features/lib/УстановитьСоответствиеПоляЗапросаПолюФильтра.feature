﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Установка соответствия поля запросу полю фильтра

Сценарий: Я устанавливаю соответствие поля "ПолеЗапроса" полю фильтра "ПолеФильтраПараметр"
	И в таблице 'ПоляФильтра' я перехожу к строке:
		| "ПолеФильтра" |
		| "[ПолеФильтраПараметр]"  |
	Если элемент "ПолеФильтраИспользование" присутствует на форме Тогда
		И в таблице 'ПоляФильтра' я устанавливаю флаг с именем 'ПолеФильтраИспользование'			
	И в таблице 'ПоляФильтра' я активизирую поле с именем 'ПолеИсточника'
	И в таблице 'ПоляФильтра' я выбираю текущую строку
	И в таблице 'ПоляФильтра' из выпадающего списка с именем 'ПолеИсточника' я выбираю точное значение "[ПолеЗапроса]"
	И в таблице 'ПоляФильтра' я завершаю редактирование строки
	
	