﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Добавление оператора запроса 

Сценарий: Я добавляю объединяемый запрос без дублирования записей
	И Я добавляю объединяемый запрос
	И в таблице "Объединения" я перехожу к последней строке
	И в таблице 'Объединения' я активизирую поле с именем 'ОбъединенияБезДубликатов'
	И в таблице "Объединения" я устанавливаю флаг с именем "ОбъединенияБезДубликатов"
	