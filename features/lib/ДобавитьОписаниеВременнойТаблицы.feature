﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Добавление описания временной таблицы 

Сценарий: Я добавляю описание временной таблицы "ИмяВременнойТаблицы" как "Псевдоним" с полями "ПоляВременнойТаблицы"
	И я перехожу к закладке с именем 'ТаблицыИПоляЗапроса'
	И в таблице 'Источники' я нажимаю на кнопку с именем 'ИсточникиСоздатьОписаниеВременнойТаблицы'
	Тогда открылось окно "Временная таблица"
	И в поле с именем 'ИмяТаблицы' я ввожу текст "ИмяВременнойТаблицы"
	И Я запоминаю строку 'ПоляВременнойТаблицы' в переменную "ПоляТаблицыПеременная"
	И для каждого значения "Поле" из таблицы в памяти "ПоляТаблицыПеременная"
		И в таблице 'Поля' я нажимаю на кнопку с именем 'Добавить'
		И в таблице 'Поля' в поле с именем 'ПоляИмя' я ввожу текст "$Поле$"
		И в таблице 'Поля' я завершаю редактирование строки
	И я нажимаю на кнопку с именем 'OK'
	И Я устанавливаю Псевдоним "Псевдоним" для текущего источника
			

		
		
		

		
		
		
