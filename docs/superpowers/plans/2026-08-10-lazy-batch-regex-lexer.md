# Lazy Batch-Regex Lexer Materialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Сохранить batch-regex recognition и заменить полный `Token[]` последовательной materialization одного токена в `СледующийТокен()`.

**Architecture:** `УстановитьОбрабатываемыйТекст()` сохраняет исходный текст, `Match[]`, переводы строк и начальное cursor state. `СледующийТокен()` lazily проверяет coverage, пропускает trivia и материализует один значимый match; непродвинутый cursor воспроизводит lexical error. Parser API и parser module не меняются.

**Tech Stack:** 1С:Предприятие 8.3.24+, русский BSL, EDT-MCP, YAxUnit, batch regex `СтрНайтиВсеПоРегулярномуВыражению()`.

## Global Constraints

- Не запускать performance benchmarks, profiler и parser performance diagnostics.
- Не изменять grammar, generated parser, parser lookahead, AST/model factory и semantics.
- Сохранить публичные методы `Инициализировать()`, `УстановитьОбрабатываемыйТекст()` и `СледующийТокен()`.
- Сохранить второй batch regex scan переводов строк `\r\n|\r|\n`.
- Не добавлять full `Token[]`, iterator framework, coroutine abstraction или test-only production API.
- Все BSL-записи выполнять через EDT-MCP с актуальным `contentHash`, затем перечитывать и ревалидировать объект.
- Не включать в коммиты существующие untracked runtime benchmark JSON files.

---

### Task 1: Восстановить legacy-правило `#` identifier

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`
- Modify: `QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl`

**Interfaces:**
- Consumes: текущий token contract `Класс="Слово"`, `Тип="ID_СРешеткой"`, исходная `Лексема`.
- Produces: `#1` и `#123Таблица` как один `ID_СРешеткой`; `#` и `#@` остаются lexical errors.

- [ ] **Step 1: Заменить ошибочный positive/negative test split**

В `ИсполняемыеСценарии()` заменить регистрацию `ЦифраПослеРешеткиОтклоняется` на две регистрации:

```bsl
.ДобавитьСерверныйТест("ЦифраПослеРешеткиДопускается")
	.СПараметрамиНаСервере("#1")
	.СПараметрамиНаСервере("#123Таблица")
.ДобавитьСерверныйТест("НекорректныйИдентификаторСРешеткойОтклоняется")
	.СПараметрамиНаСервере("#")
	.СПараметрамиНаСервере("#@")
```

Добавить реальные behavioral assertions:

```bsl
Процедура ЦифраПослеРешеткиДопускается(ИсходнаяЛексема) Экспорт
	Лексер = КОНС_ТестовыеФабрикиСлужебный.СоздатьЛексическийАнализатор(
		ИсходнаяЛексема);
	Токен = Лексер.СледующийТокен();

	ЮТест.ОжидаетЧто(Токен.Класс).Равно("Слово");
	ЮТест.ОжидаетЧто(Токен.Тип).Равно("ID_СРешеткой");
	ЮТест.ОжидаетЧто(Токен.Лексема).Равно(ИсходнаяЛексема);
КонецПроцедуры

Процедура НекорректныйИдентификаторСРешеткойОтклоняется(
	ИсходныйТекст) Экспорт

	Лексер = КОНС_ТестовыеФабрикиСлужебный.СоздатьЛексическийАнализатор(
		ИсходныйТекст);
	ЮТест.ОжидаетЧто(Лексер)
		.Метод("СледующийТокен")
		.ВыбрасываетИсключение("Некорректный идентификатор с #");
КонецПроцедуры
```

- [ ] **Step 2: Запустить только новые tests и подтвердить RED**

Через `run_yaxunit_tests` выполнить exact tests в конфигурации
`QueryConsoleZUP Тонкий клиент` с update scope
`extension:QueryConsoleZUP,extension:yaxunit`.

Expected: positive `#`-digit cases FAIL, потому что текущий regex оставляет gap
на позиции `#`; negative cases PASS. Ошибка discovery/Total=0 не считается RED.

- [ ] **Step 3: Минимально исправить regex fragment**

В `СформироватьШаблонТокенизации()` сформировать `ИдентификаторСРешеткой` из
одного или более символов полного continuation set:

```bsl
СимволыИдентификатора = "[A-Za-zА-Яа-яЁё_0-9]";
ИдентификаторСРешеткой = "#" + СимволыИдентификатора + "+";
Идентификатор = НачалоИдентификатора + СимволыИдентификатора + "*";
```

Сохранить порядок альтернатив: `ИдентификаторСРешеткой` раньше обычного
identifier.

- [ ] **Step 4: Подтвердить GREEN и отсутствие локальной регрессии**

Повторить два exact tests. Затем выполнить все параметры
`ИдентификаторКлассифицируется`, позиции временного identifier и invalid-input
tests. Expected: все PASS, `#`/`#@` сохраняют прежнюю диагностику.

- [ ] **Step 5: Revalidate и commit**

Перечитать оба BSL-модуля, выполнить точечную EDT revalidation и проверить
отсутствие новых ERROR diagnostics. Коммитить только два изменённых модуля:

```text
fix: restore legacy hash identifier compatibility
```

---

### Task 2: Зафиксировать observable lazy error contract

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`

**Interfaces:**
- Consumes: публичный lexer lifecycle.
- Produces: regression test, который ломается при eager gap validation в `УстановитьОбрабатываемыйТекст()` или при неверном продвижении cursor после ошибки.

- [ ] **Step 1: Усилить streaming error test далёким хвостом**

Заменить короткий fixture в `ОшибкаВыдаетсяПослеКорректногоПрефикса` на прямой
lifecycle без фабричного объединения установки и инициализации:

```bsl
Процедура ОшибкаВыдаетсяТолькоПриДостиженииCursor() Экспорт
	Лексер = Обработки.ЛексическийАнализатор.Создать();
	Лексер.Инициализировать();
	ИсходныйТекст =
		"ВЫБРАТЬ Первое, Второе" + Символы.ПС
		+ "// синтаксис в комментарии: ВЫБРАТЬ X = 1" + Символы.ПС
		+ "ИЗ Таблица @ Хвост";

	Лексер.УстановитьОбрабатываемыйТекст(ИсходныйТекст);

	ОжидаемыеТипы = Новый Массив;
	ОжидаемыеТипы.Добавить("ВЫБРАТЬ");
	ОжидаемыеТипы.Добавить("ID");
	ОжидаемыеТипы.Добавить(",");
	ОжидаемыеТипы.Добавить("ID");
	ОжидаемыеТипы.Добавить("ИЗ");
	ОжидаемыеТипы.Добавить("ID");

	Для Каждого ОжидаемыйТип Из ОжидаемыеТипы Цикл
		ЮТест.ОжидаетЧто(Лексер.СледующийТокен().Тип)
			.Равно(ОжидаемыйТип);
	КонецЦикла;

	ЮТест.ОжидаетЧто(Лексер)
		.Метод("СледующийТокен")
		.ВыбрасываетИсключение(
			"{(3, 12)}: Не удалось разобрать запрос");
КонецПроцедуры
```

До записи вручную пересчитать literal column по fixture и при необходимости
скорректировать только literal expectation. Не вычислять expected position
production helper-ом.

- [ ] **Step 2: Выполнить characterization run до production refactor**

Expected: test PASS на текущем deferred-error lexer. Это намеренная
характеризация observable contract, а не RED: внутреннюю materialization нельзя
наблюдать без нежелательного test-only API или performance assertion.

- [ ] **Step 3: Проверить mutation target теста**

Зафиксировать в task notes две мутации, которые тест обязан ловить:

- gap validation перенесена в `УстановитьОбрабатываемыйТекст()` — установка
  выбрасывает исключение до чтения префикса;
- cursor продвинут после ошибки — повторный existing test перестаёт получать
  то же исключение.

- [ ] **Step 4: Commit characterization test**

```text
test: cover lazy lexer error timing
```

---

### Task 3: Перенести materialization в `СледующийТокен()`

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl`

**Interfaces:**
- Consumes: `Match[]`, `ПозицияИсточника()`, token constructors и public lexer API.
- Produces: lazy `СледующийТокен()` без full `Token[]` и deferred error state.

- [ ] **Step 1: Заменить eager module state**

Заменить:

```bsl
Перем Токены;
Перем ИндексСледующегоТокена;
Перем ОтложеннаяОшибка;
```

на:

```bsl
Перем Совпадения;
Перем ИндексСледующегоСовпадения;
Перем ОжидаемаяПозиция;
Перем ПереводыСтрок;
Перем СостояниеПозиции;
```

`ИсходныйТекст` и `ПозицияEOF` оставить.

- [ ] **Step 2: Сократить установку текста до batch preparation**

Метод должен иметь форму:

```bsl
Процедура УстановитьОбрабатываемыйТекст(Текст) Экспорт
	ИсходныйТекст = Текст;
	Совпадения = СтрНайтиВсеПоРегулярномуВыражению(
		ИсходныйТекст, ШаблонТокенизации);
	ПереводыСтрок = СтрНайтиВсеПоРегулярномуВыражению(
		ИсходныйТекст, ШаблонПереводовСтрок);
	ИндексСледующегоСовпадения = 0;
	ОжидаемаяПозиция = 1;
	СостояниеПозиции = НовоеСостояниеПозиции();
	ПозицияEOF = ПозицияИсточника(
		СтрДлина(ИсходныйТекст) + 1,
		ПереводыСтрок,
		НовоеСостояниеПозиции());
КонецПроцедуры
```

Для `ПозицияEOF` использовать отдельное position state, чтобы не продвинуть
streaming `СостояниеПозиции` в конец при установке текста.

- [ ] **Step 3: Сделать materializer чистым по отношению к cursor**

Переименовать `МатериализоватьСовпадение` в
`ТокенИзСовпадения(Совпадение, Позиция)`. Функция:

- не читает и не меняет cursor;
- не добавляет token в массив;
- не пропускает trivia;
- возвращает один token;
- при conversion error вызывает совместимую lexical error в начале match.

Вынести trivia predicate:

```bsl
Функция ЭтоНезначащееСовпадение(Совпадение)
	ПервыйСимвол = Сред(
		ИсходныйТекст, Совпадение.НачальнаяПозиция, 1);
	Возврат СтрНайти(
		ПробельныеСимволыДляКлассификации, ПервыйСимвол) > 0
		Или ПервыйСимвол = "/"
			И Совпадение.Длина >= 2
			И Сред(
				ИсходныйТекст,
				Совпадение.НачальнаяПозиция + 1,
				1) = "/";
КонецФункции
```

- [ ] **Step 4: Заменить deferred error helper прямой диагностикой**

Переименовать `УстановитьОтложеннуюОшибку` в
`ВызватьЛексическуюОшибку(НачальнаяПозиция)`. Helper вычисляет позицию текущим
монотонным state, выбирает существующее сообщение и вызывает исключение.

Он не меняет match index или expected position. После возвращения из
исключения повторный вызов обрабатывает тот же gap/match.

- [ ] **Step 5: Реализовать lazy loop**

```bsl
Функция СледующийТокен() Экспорт
	Пока ИндексСледующегоСовпадения < Совпадения.Количество() Цикл
		Совпадение = Совпадения[ИндексСледующегоСовпадения];
		Если Совпадение.НачальнаяПозиция <> ОжидаемаяПозиция Тогда
			ВызватьЛексическуюОшибку(ОжидаемаяПозиция);
		КонецЕсли;

		Если ЭтоНезначащееСовпадение(Совпадение) Тогда
			ПродвинутьПослеСовпадения(Совпадение);
			Продолжить;
		КонецЕсли;

		Позиция = ПозицияИсточника(
			Совпадение.НачальнаяПозиция,
			ПереводыСтрок,
			СостояниеПозиции);
		Токен = ТокенИзСовпадения(Совпадение, Позиция);
		ПродвинутьПослеСовпадения(Совпадение);
		Возврат Токен;
	КонецЦикла;

	Если ОжидаемаяПозиция <> СтрДлина(ИсходныйТекст) + 1 Тогда
		ВызватьЛексическуюОшибку(ОжидаемаяПозиция);
	КонецЕсли;

	Возврат НовыйТокенEOF(ПозицияEOF);
КонецФункции
```

`ПродвинутьПослеСовпадения()` обновляет сначала expected end, затем match index.
Вызывать его только для trivia или после успешного token construction.

- [ ] **Step 6: Выполнить focused GREEN tests**

Запустить exact tests:

- `ОшибкаВыдаетсяТолькоПриДостиженииCursor`;
- `ПовторныйВызовПослеОшибкиПовторяетИсключение`;
- `EOFУказываетНаКонецИсходногоТекста`;
- `ПереводыСтрокОпределяютКоординаты`;
- `КомментарииНеВозвращаютсяКакТокены`;
- `СтроковаяКонстантаСохраняетЗначение`;
- `ЧисловаяКонстантаСохраняетЗначение`.

Expected: все PASS, failed/errors/skipped = 0.

- [ ] **Step 7: Re-read, revalidate и architecture review**

Проверить по актуальному EDT source:

- module state не содержит `Токены`, `ИндексСледующегоТокена` и
  `ОтложеннаяОшибка`;
- setter не вызывает token constructors, literal conversion или coverage
  validation;
- `СледующийТокен()` создаёт не более одного token на возврат;
- parser module не изменён;
- regex остаётся составным и читаемым.

Выполнить точечную revalidation production lexer и проверить новый ERROR delta.

- [ ] **Step 8: Commit production refactor**

```text
refactor: materialize lexer tokens lazily
```

---

### Task 4: Differential и integration verification

**Files:**
- Verify only: `QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl`
- Verify only: `QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl`
- Verify only: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`
- Create: `.superpowers/sdd/2026-08-10-lazy-batch-regex-lexer/final-report.md`

**Interfaces:**
- Consumes: completed lazy lexer and existing differential corpus.
- Produces: correctness evidence without performance data.

- [ ] **Step 1: Run full lexer suite**

Через `run_yaxunit_tests` выполнить модуль
`КОНС_Обр_ЛексическийАнализатор_МО`. Record total/passed/failed/errors/skipped.

- [ ] **Step 2: Run differential exact tests**

Выполнить четыре existing differential/numeric tests отдельно. Для `#1`
зафиксировать согласованное отличие от ошибочного current-batch behavior и
совпадение с historical lexer.

- [ ] **Step 3: Run parser suites**

Выполнить `КОНС_Обр_Парсер_МО` и `КОНС_Обр_ПарсерЗапросов_МО`. Parser source
не менять при GREEN результате.

- [ ] **Step 4: Verify QueryExamples coverage**

Подтвердить real-query coverage существующим differential test
`ЛексерыЭквивалентныНаРеальныхЗапросах` и parser-query suite. Не создавать
новый benchmark harness и не запускать runtime timing registrations.

- [ ] **Step 5: Correctness и readability review**

Проверить отдельно:

- gap в начале, середине и tail;
- comments, strings, numeric forms, `#` identifiers;
- CR/LF/CRLF и multiline strings;
- EOF и повторные вызовы после EOF;
- повторную ошибку без cursor advance;
- отсутствие token retention;
- имена и размер helpers;
- отсутствие parser/grammar/model изменений.

Исправления review проводить отдельными RED/GREEN циклами.

- [ ] **Step 6: Fresh final verification**

После последних исправлений повторить затронутые focused tests, полный lexer
suite, parser suites, EDT revalidation и targeted diagnostics. Не переиспользовать
старые результаты как финальные.

- [ ] **Step 7: Write final report**

Отчёт должен перечислить:

1. оставшееся lexer state;
2. работу setter;
3. работу `СледующийТокен()`;
4. coverage invariant;
5. lazy error timing;
6. source positions и EOF;
7. изменённые tests;
8. точные functional suite results;
9. отсутствие parser changes;
10. намеренное отсутствие performance benchmarks;
11. дефект прежних benchmark conditions: EDT launch имел
    `ATTR_SHOW_PERFORMANCE=true`.

- [ ] **Step 8: Final commit and push branch**

Проверить `git diff --check`, status, commit provenance и отсутствие случайно
добавленных runtime JSON files. Создать финальный commit только при наличии
review fixes/report changes и push текущей feature branch.
