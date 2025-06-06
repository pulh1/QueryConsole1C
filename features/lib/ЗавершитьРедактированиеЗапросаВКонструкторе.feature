﻿#language: ru

@tree
@ExportScenarios
@IgnoreOnCIMainBuild

Функционал: Завершение редактирования текущего запроса

Сценарий: Я завершаю редактирование текущего запроса в конструкторе
	Когда открылось окно "Конструктор запросов *"
	И я нажимаю на кнопку с именем 'OK'
	И я выполняю код встроенного языка
	"""bsl
		Если Контекст.СтэкНомерТекущегоОператора.Количество() > 0 Тогда
			Контекст.НомерТекущегоОператора = Контекст.СтэкНомерТекущегоОператора[Контекст.СтэкНомерТекущегоОператора.ВГраница()];
			Контекст.СтэкНомерТекущегоОператора.Удалить(Контекст.СтэкНомерТекущегоОператора.ВГраница());
		Иначе
			Контекст.НомерТекущегоОператора = 1;
		КонецЕсли;
	"""
