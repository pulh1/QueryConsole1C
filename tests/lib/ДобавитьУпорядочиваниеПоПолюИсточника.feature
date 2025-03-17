﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Добавление упорядочивание по полю источника

Сценарий: Я добавляю упорядочивание по полю источника "Выражение" по "Направление"
	И я перехожу к закладке с именем 'ПорядокСтраница'
	И в таблице 'ПоляДляУпорядочивания' я сворачиваю строку:
		| "Поля"     |
		| "Все поля" |
	И я запоминаю строку "Выражение" в переменную "ПеременнаяВыражение"
	И В таблице "ПоляДляУпорядочивания" я перехожу к строке содержущей в поле "ПоляДляУпорядочиванияПредставление" выражение "Все поля.$ПеременнаяВыражение$" с учетом иерахии
	И в таблице 'ПоляДляУпорядочивания' я выбираю текущую строку
	И в таблице "Порядок" я перехожу к последней строке
	И в таблице 'Порядок' я активизирую поле с именем 'ПорядокНаправление'
	И в таблице 'Порядок' из выпадающего списка с именем 'ПорядокНаправление' я выбираю точное значение "Направление"
	И в таблице 'Порядок' я завершаю редактирование строки
		
	