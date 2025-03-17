﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Сравнение строк без учета форматирования 

Сценарий: Я сравниваю строки "Строка1" и "Строка2" без учета форматирования
	
	И я запоминаю строку "Строка1" в переменную "ПеременнаяСтрока1"	
	И я запоминаю строку "Строка2" в переменную "ПеременнаяСтрока2"	
	И я выполняю код встроенного языка на сервере без контекста с передачей переменных
	"""bsl
		Строка1 = НРег(СтрЗаменить(Контекст.ПеременнаяСтрока1, Символы.ПС, " "));
		Строка2 = НРег(СтрЗаменить(Контекст.ПеременнаяСтрока2, Символы.ПС, " "));
		Строка1 = СтрЗаменитьПоРегулярномуВыражению(Строка1, "[\s|\\n]+", " ", Истина, Истина);
		Строка2 = СтрЗаменитьПоРегулярномуВыражению(Строка2, "[\s|\\n]+", " ", Истина, Истина);
		
		Контекст.Вставить("СтрокиРавны", Число(Строка1=Строка2))
	"""	
		