﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Сворачивание всех строк дерева

Сценарий: В таблице "ИмяТаблицы" Я сворачиваю все строки
	И для каждой строки таблицы "ИмяТаблицы" я выполняю
		И в таблице "ИмяТаблицы" я сворачиваю текущую строку