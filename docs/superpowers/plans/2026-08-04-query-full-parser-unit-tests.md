# Query Full Parser Unit Tests Implementation Plan

> **Execution:** use `superpowers:executing-plans` or
> `superpowers:subagent-driven-development`; execute tasks in order.

**Goal:** implement 89 executable synthetic and 12 curated corpus black-box YAxUnit
cases for
`Обработки.Парсер.Разобрать`, without changing parser/grammar/semantic code.

**Target arithmetic:** `Q00 1 + Q01–Q05 5 + Task3 23 + Task4 10 + Task5 7 +
Task6 15 + Task7 21 + Task8 3 + Task9 4 = 89`; `89 + X01–X12 = 101`.
These are represented-case totals: Task 3 contributes `11 GREEN M + 4 opt-in
RED M + 7 F + 1 N-ALIAS = 23`. Consequently the final main module has 85
synthetic and 12 corpus GREEN cases (`97`), while the four modifier REDs remain
isolated behind the existing future-grammar module gate; no blocker is counted
as GREEN. K01–K03 remain three separate GAP evidence rows outside executable
case arithmetic: they parsed, but export no public raw keyword value.

## Global constraints

- Production parser, grammar, `ЭлементыМоделиЗапроса` and semantic modules are
  read-only.
- Tests call only `КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер().Разобрать`.
- Metadata and module source writes use EDT-MCP guarded by current content hash.
- Task 1 contains the only artificial discovery RED.
- Tasks 2, 4–7, 8B and 9 each use one guarded write for the complete package.
  Task 3 is the only package task that touches two existing modules: exactly
  one guarded write to `КОНС_Обр_ПарсерЗапросов_МО` and exactly one guarded
  write to `КОНС_Обр_ПарсерБудущаяГрамматика_МО` (two writes total, no metadata
  object creation).
- Outside bootstrap Task 1 and the two-module Task 3 split, additional guarded
  writes are authorized only in bounded spike Task 1A and
  runtime-count/wiring Task 9B. Task 1A adds then removes probes; Task 9B
  replaces count probes with final corpus cases. Task 8A is already satisfied
  by Task 1A/R1 artifact evidence and authorizes no repeated probe write/run.
- Independent review round 1 explicitly authorizes one separate bounded
  remediation `Task 1A-R1` with exactly two additional guarded writes: add 17
  unique nonparameterized exact-case probes, then restore the exact Task 1
  source. This authorization is not reusable by later rounds or tasks.
- Exact F05 runtime evidence explicitly authorizes separate `Task 3-R1` with
  exactly one additional guarded write to `КОНС_Обр_ПарсерЗапросов_МО` only.
  It corrects the test's nested AST contract, is not reusable, and authorizes no
  additional write or rerun of `КОНС_Обр_ПарсерБудущаяГрамматика_МО`.
- Every launch uses `extensions=["YAXUNIT"]`, `updateBeforeLaunch=true`,
  `updateScope="extension:yaxunit"`.
- `clean_project`, full rebuild, `updateScope="all"`, all-extension update and
  whole-YAxUnit launch are forbidden.
- A production defect is recorded, not fixed. A failed alternative remains
  represented in the matrix and can move to opt-in future acceptance only after
  a separately observed RED.
- Preserve unrelated worktree changes.

Common module GREEN command:

```text
run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  extensions=["YAXUNIT"],
  modules=["КОНС_Обр_ПарсерЗапросов_МО"],
  updateBeforeLaunch=true,
  updateScope="extension:yaxunit",
  timeout=60
)
```

---

### Task 0: Strictly read-only alternative and corpus discovery

**Files:** read `Парсер/ObjectModule.bsl:236-1708`, FIRST-table,
`ЭлементыМоделиЗапроса/Module.bsl:57-601`, existing parser tests and all 42
`QueryExamples/*.q1c`.

**Interfaces:** consumes production source; produces an in-memory inventory of
67 reachable declarations, two exclusions, branch conditions, candidate inputs
and XML file list. It does not produce or modify a repository file.

- [ ] Run `git status --short` and preserve baseline.
- [ ] Confirm 67 reachable inventory rows plus two exclusions:
  `НеТерминалКакОпционально:1001` has no caller;
  `НеТерминалВыражениеСКДПараметр:1117` has only its self-recursive call and no
  external caller.
- [ ] Preserve the call-graph evidence: exact-name source search returns one
  occurrence for `НеТерминалКакОпционально(` (declaration) and two for
  `НеТерминалВыражениеСКДПараметр(` (declaration plus line 1126 self-call).
- [ ] Confirm raw factory fields/values through line 601.
- [ ] Parse XML read-only and confirm 42 unique relative filenames; do not run
  parser, EDT writes or YAxUnit in this task.
- [ ] Compare the 67 rows with the exact inventory in the design. Any mismatch
  blocks Task 1.

**Verification:** source searches only; no runtime claims.

**Commit:** none; Task 0 is read-only.

---

### Task 1: Create module, common helpers and one discovery RED

**Files:** create via EDT
`yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/**`; EDT-managed
`yaxunit/src/Configuration/Configuration.mdo`; update `yaxunit/UPSTREAM.md`.

**Interfaces:** consumes parser factory; produces YAxUnit set `ПарсерЗапросов`
and helpers used by every later task.

- [ ] Create server common module with no client/server-call/privileged flags.
- [ ] First guarded write contains only registration and the single bootstrap:

```bsl
Процедура ИсполняемыеСценарии() Экспорт
	ЮТТесты
		.ДобавитьТестовыйНабор("ПарсерЗапросов")
			.Тег("Парсер")
			.Тег("ПолныйЗапрос")
			.ДобавитьСерверныйТест("МинимальныйЗапросВыбораРазбирается");
КонецПроцедуры

Процедура МинимальныйЗапросВыбораРазбирается() Экспорт
	ЮТест.ОжидаетЧто(Истина)
		.Равно(Ложь, "RED: registration discovery");
КонецПроцедуры
```

- [ ] Run only that test; require `Total=1, Failed=1` and exact message.
- [ ] Second guarded write replaces it with the helpers and Q00:

```bsl
Функция РазобратьЗапросДляТеста(ИсходныйТекст)
	Парсер = КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер();
	Возврат Парсер.Разобрать(ИсходныйТекст);
КонецФункции

Функция ЕдинственныйЗапросВыбора(ИсходныйТекст)
	Пакет = РазобратьЗапросДляТеста(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Пакет.Тип).Равно("ПакетЗапросов");
	ЮТест.ОжидаетЧто(Пакет.Элементы.Количество()).Равно(1);
	Запрос = Пакет.Элементы[0];
	ЮТест.ОжидаетЧто(Запрос.Тип).Равно("ЗапросВыбора");
	Возврат Запрос;
КонецФункции

Функция ЕдинственныйОператор(ИсходныйТекст)
	Запрос = ЕдинственныйЗапросВыбора(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Запрос.Операторы.Количество()).Равно(1);
	Возврат Запрос.Операторы[0];
КонецФункции

Процедура ПроверитьСинтаксическуюОшибку(ИсходныйТекст, Фрагмент)
	Парсер = КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер();
	ЮТест.ОжидаетЧто(Парсер)
		.Метод("Разобрать", ЮТМетоды.МассивПараметров(ИсходныйТекст))
		.ВыбрасываетИсключение(Фрагмент);
КонецПроцедуры

Процедура МинимальныйЗапросВыбораРазбирается() Экспорт
	Оператор = ЕдинственныйОператор("ВЫБРАТЬ 1");
	ЮТест.ОжидаетЧто(Оператор.Тип).Равно("ОператорЗапроса");
	ЮТест.ОжидаетЧто(Оператор.ВыбираемыеПоля.Количество()).Равно(1);
	Поле = Оператор.ВыбираемыеПоля[0];
	ЮТест.ОжидаетЧто(Поле.Выражение.Тип).Равно("ВыражениеМоделиЗапроса");
	ЮТест.ОжидаетЧто(Поле.Выражение.Значение.Тип).Равно("Константа");
	ЮТест.ОжидаетЧто(Поле.Выражение.Значение.Значение).Равно(1);
КонецПроцедуры
```

- [ ] Run module GREEN, object diagnostics and `git diff --check`.

**Commit:** commit only module metadata/source, EDT registration and UPSTREAM:
`test: add full query parser test module`.

---

### Task 1A: Bounded runtime preflight after module creation

**Files:** temporarily modify the new test module; create
`docs/superpowers/matrices/2026-08-04-query-full-parser-runtime-preflight.md`.

**Interfaces:** consumes Task 0 candidates and Q00 helpers; produces a verified
artifact with exact input, result/error, report ID, raw AST path/value and ready
BSL registration literals for M01–M15, S01–S10, J06–J07, T11–T20, K01–K06
and E02. J06/J07 rows verify JOIN ownership and right-source indexing before
Task 5 consumes their generated literals.

- [ ] First authorized guarded write adds one parameterized probe:

```bsl
.ДобавитьСерверныйТест("RuntimePreflightРазбираетКандидат")
	.СПараметрамиНаСервере("M01", "ВЫБРАТЬ ПЕРВЫЕ 5 1")
	.СПараметрамиНаСервере("M02", "ВЫБРАТЬ РАЗЛИЧНЫЕ 1")
	.СПараметрамиНаСервере("M03", "ВЫБРАТЬ РАЗРЕШЕННЫЕ 1")
	.СПараметрамиНаСервере("J06", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 ЛЕВОЕ СОЕДИНЕНИЕ ВТ КАК Т2 ПО Т1.Ключ = Т2.Ключ")
	.СПараметрамиНаСервере("J07", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 ЛЕВОЕ СОЕДИНЕНИЕ (ВЫБРАТЬ 1 КАК Ключ) КАК Т2 ПО Т1.Ключ = Т2.Ключ ПРАВОЕ СОЕДИНЕНИЕ Каталог.Таблица3 КАК Т3 ПО Т2.Ключ = Т3.Ключ");

Процедура RuntimePreflightРазбираетКандидат(Идентификатор, ИсходныйТекст) Экспорт
	Пакет = РазобратьЗапросДляТеста(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Пакет.Элементы.Количество())
		.Равно(1, Идентификатор);
КонецПроцедуры

.ДобавитьСерверныйТест("RuntimePreflightКоординатаОшибки");

Процедура RuntimePreflightКоординатаОшибки() Экспорт
	Парсер = КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер();
	Парсер.Разобрать("ВЫБРАТЬ 1 2");
КонецПроцедуры
```

The guarded source expands this registration with every exact candidate from
the design: all fifteen modifier strings, ten source candidates, nine period
types plus bounded-period form, six SKD candidates and the exact J06/J07 strings
shown above: 43 registered parameter outcomes in total. The E02 probe
deliberately lets the real parser exception reach the temporary test report; it
is not an artificial assertion failure.

- [ ] Run only `RuntimePreflightРазбираетКандидат` with extension-only update.
  For failures run only the failing parameter case; do not mutate parser.
- [ ] Run `RuntimePreflightКоординатаОшибки` separately, require the exact input
  `ВЫБРАТЬ 1 2`, and copy the actual coordinate-bearing exception fragment and
  report ID into E02 artifact row. Do not predict the coordinate in this plan.
- [ ] The first guarded write already includes the temporary diagnostic
  procedure used for successful parses; do not add it in a third write. Record
  exact public path and value. For SKD record whether a public value actually
  distinguishes `ВЫБРАТЬ`, `УПОРЯДОЧИТЬ ПО`, `ИТОГИ ПО`.
- [ ] For J06 record `result=success` and exact values at
  `Пакет.Элементы[0].Операторы[0].Источники.Элементы.Количество()`,
  `.Источники.Элементы[0].Соединения.Количество()`, every
  `Тип`, `ТипСоединения`, `Опционально`, `Условие.Тип` and
  `Условие.Значение.Тип` path under `.Соединения[0]`, and
  `.Источники.Элементы[1].Источник.Тип`. Required observed values are `2`, `1`,
  `СоединенияИсточника`, `Левое`, `Ложь`, `ВыражениеМоделиЗапроса`,
  `БинарнаяОперация` and `ИсточникДанныхВременнаяТаблица`; any different value
  blocks Task 5 instead of being silently normalized.
- [ ] For J07 record `result=success` and the same fields for both
  `.Источники.Элементы[0].Соединения[0]` and `[1]`, plus right-source paths
  `.Источники.Элементы[1].Источник.Тип` and
  `.Источники.Элементы[2].Источник.Тип`. Required values are source count `3`,
  root JOIN count `2`; first JOIN
  `СоединенияИсточника/Левое/Ложь/ВыражениеМоделиЗапроса/БинарнаяОперация`;
  second JOIN
  `СоединенияИсточника/Правое/Ложь/ВыражениеМоделиЗапроса/БинарнаяОперация`;
  right-source types `ИсточникДанныхВложенныйЗапрос` and
  `ИсточникДанныхТаблица`. No JOIN path under `.Источники.Элементы[1]` is a
  substitute for either root path.
- [ ] Write the artifact. Every row has `ID | exact input | result | exact AST
  path/value | error fragment | report ID | generated BSL parameter call`.
  J06/J07 calls have exact parameter order `(ID, text, first join type, first
  optional, source count, first right-source type, root join count, second join
  type-or-Неопределено, second optional-or-Неопределено)` and are copied
  byte-for-byte into Task 5.
- [ ] Second and final authorized guarded write removes every probe. Run Q00
  GREEN to prove cleanup.

**Verification:** artifact has exactly 44 rows: 15 M, 10 S, 2 J, 10 T-period,
6 K and one E02 row. J06 reports 2 sources/1 root JOIN, J07 reports 3 sources/2
root JOINs and both indexed JOIN paths; no probe name remains in module; only
extension:yaxunit was updated.

**Commit:** commit only the runtime-preflight artifact after probe cleanup:
`test: record full parser runtime preflight`.

#### Task 1A-R1: review-authorized exact-case remediation

Independent review found that 17 non-pass rows lacked separate exact-filter
runs and that T11–T20/K02/K03 used an incorrect operator-level temporary helper.
It also established from production source that bare `Таблица3` is correctly a
temporary table; the metadata-table J07 candidate must use
`Каталог.Таблица3`.

- [x] First additional guarded write registers 17 unique nonparameterized
  methods for M06, M07, M10, M14, corrected J07, T11–T20, K02 and K03. T/K
  helpers read query-level public paths; J07 expects the dotted third source to
  be `ИсточникДанныхТаблица`.
- [x] Run every method separately with its exact module+method filter and the
  mandatory extension-only update. Record every report ID/result; do not use a
  parameterized-filter workaround.
- [x] Second additional guarded write restores exact Task 1 source/hash. Prove
  Q00 `1/1`, zero probes, unchanged production and zero diagnostic delta.
- [x] Replace remediation-covered artifact evidence/report IDs, correct E02's
  generated literal, and record no generated literal for M06/M10 because no AST
  exists.

**Commit:** `test: verify full parser preflight gaps`.

---

### Task 2: Q01–Q05 package/destroy — 5 cases

**Files:** modify only new test module.

**Interfaces:** consumes Q00 helpers; produces coverage for package continuation
variants, both package-query choices and destroy node.

- [ ] One guarded write adds exact registration and complete body:

```bsl
.ДобавитьСерверныйТест("ПакетныйCase")
	.СПараметрамиНаСервере("Q01", "ВЫБРАТЬ 1; ВЫБРАТЬ 2", 2, "ЗапросВыбора", "ЗапросВыбора")
	.СПараметрамиНаСервере("Q02", "ВЫБРАТЬ 1;", 1, "ЗапросВыбора", "ЗапросВыбора")
	.СПараметрамиНаСервере("Q03", "УНИЧТОЖИТЬ ВТ", 1, "ЗапросУничтожения", "ЗапросУничтожения")
	.СПараметрамиНаСервере("Q04", "ВЫБРАТЬ 1; УНИЧТОЖИТЬ ВТ", 2, "ЗапросВыбора", "ЗапросУничтожения")
	.СПараметрамиНаСервере("Q05", "УНИЧТОЖИТЬ ВТ; ВЫБРАТЬ 1", 2, "ЗапросУничтожения", "ЗапросВыбора");

Процедура ПакетныйCase(Идентификатор, ИсходныйТекст,
	ОжидаемоеКоличество, ПервыйТип, ПоследнийТип) Экспорт
	Пакет = РазобратьЗапросДляТеста(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Пакет.Элементы.Количество())
		.Равно(ОжидаемоеКоличество, Идентификатор);
	ЮТест.ОжидаетЧто(Пакет.Элементы[0].Тип).Равно(ПервыйТип, Идентификатор);
	Последний = Пакет.Элементы[Пакет.Элементы.Количество() - 1];
	ЮТест.ОжидаетЧто(Последний.Тип).Равно(ПоследнийТип, Идентификатор);
	Если Последний.Тип = "ЗапросУничтожения" Тогда
		ЮТест.ОжидаетЧто(Последний.ИмяТаблицы).Равно("ВТ", Идентификатор);
	КонецЕсли;
КонецПроцедуры
```

- [ ] Run module GREEN, diagnostics, `git diff --check`.

**Commit:** `test: cover query package parsing`.

---

### Task 3: M01–M15, F01–F07 and N-ALIAS — 23 cases

**Files:** modify existing `КОНС_Обр_ПарсерЗапросов_МО` and existing opt-in
`КОНС_Обр_ПарсерБудущаяГрамматика_МО`; do not create metadata objects.

**Interfaces:** consumes the verified Task 1A artifact. The main module receives
11 GREEN SELECT modifier orderings, both field alternatives, list/alias variants
and alias RED. Confirmed blockers M06/M07/M10/M14 remain represented as opt-in
acceptance REDs in the existing future-grammar module and are never registered
by the main module.

Exact modifier inputs, in ID order:

```text
M01 ВЫБРАТЬ ПЕРВЫЕ 5 1
M02 ВЫБРАТЬ РАЗЛИЧНЫЕ 1
M03 ВЫБРАТЬ РАЗРЕШЕННЫЕ 1
M04 ВЫБРАТЬ ПЕРВЫЕ 5 РАЗЛИЧНЫЕ 1
M05 ВЫБРАТЬ ПЕРВЫЕ 5 РАЗРЕШЕННЫЕ 1
M06 ВЫБРАТЬ ПЕРВЫЕ 5 РАЗЛИЧНЫЕ РАЗРЕШЕННЫЕ 1
M07 ВЫБРАТЬ ПЕРВЫЕ 5 РАЗРЕШЕННЫЕ РАЗЛИЧНЫЕ 1
M08 ВЫБРАТЬ РАЗЛИЧНЫЕ ПЕРВЫЕ 5 1
M09 ВЫБРАТЬ РАЗЛИЧНЫЕ РАЗРЕШЕННЫЕ 1
M10 ВЫБРАТЬ РАЗЛИЧНЫЕ ПЕРВЫЕ 5 РАЗРЕШЕННЫЕ 1
M11 ВЫБРАТЬ РАЗЛИЧНЫЕ РАЗРЕШЕННЫЕ ПЕРВЫЕ 5 1
M12 ВЫБРАТЬ РАЗРЕШЕННЫЕ ПЕРВЫЕ 5 1
M13 ВЫБРАТЬ РАЗРЕШЕННЫЕ РАЗЛИЧНЫЕ 1
M14 ВЫБРАТЬ РАЗРЕШЕННЫЕ ПЕРВЫЕ 5 РАЗЛИЧНЫЕ 1
M15 ВЫБРАТЬ РАЗРЕШЕННЫЕ РАЗЛИЧНЫЕ ПЕРВЫЕ 5 1
```

- Main-module GREEN IDs are M01–M05, M08, M09, M11–M13 and M15. Generate only
  these eleven `.СПараметрамиНаСервере` calls directly from verified artifact
  rows with parameters `(ID, exact text, first-or-Неопределено, distinct,
  allowed, exact allowed-property-name)` immediately after
  `.ДобавитьСерверныйТест("МодификаторCase")`. The main module must not register
  M06, M07, M10 or M14. Then add:

```bsl
.ДобавитьСерверныйТест("ПолеCase")
	.СПараметрамиНаСервере("F01", "ВЫБРАТЬ 1, 2", 2, "Константа", Неопределено, Неопределено)
	.СПараметрамиНаСервере("F02", "ВЫБРАТЬ 1 КАК Один", 1, "Константа", "Один", Неопределено)
	.СПараметрамиНаСервере("F03", "ВЫБРАТЬ 1 Один", 1, "Константа", "Один", Неопределено)
	.СПараметрамиНаСервере("F04", "ВЫБРАТЬ *", 1, "ВыражениеВсеПоля", Неопределено, Неопределено)
	.СПараметрамиНаСервере("F05", "ВЫБРАТЬ Т.* ИЗ Таблица КАК Т", 1, "Разыменование", Неопределено, "ВыражениеВсеПоляИсточника")
	.СПараметрамиНаСервере("F06", "ВЫБРАТЬ Т.Поле ИЗ Таблица КАК Т", 1, "Разыменование", Неопределено, Неопределено)
	.СПараметрамиНаСервере("F07", "ВЫБРАТЬ 1 КАК Один, 2 КАК Два", 2, "Константа", "Один", Неопределено)
.ДобавитьСерверныйТест("НезавершенныйПсевдонимВызываетИсключение");
```

Complete bodies:

```bsl
Процедура МодификаторCase(Идентификатор, ИсходныйТекст, ОжидаемыеПервые,
	ОжидаемыеРазличные, ОжидаемыеРазрешенные, СвойствоРазрешенные) Экспорт
	Оператор = ЕдинственныйОператор(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Оператор.КоличествоПолучаемыхЗаписей)
		.Равно(ОжидаемыеПервые, Идентификатор);
	ЮТест.ОжидаетЧто(Оператор.ВыбиратьРазличные)
		.Равно(ОжидаемыеРазличные, Идентификатор);
	ФактическиеРазрешенные = Неопределено;
	ЮТест.ОжидаетЧто(Оператор.Свойство(
		СвойствоРазрешенные, ФактическиеРазрешенные)).Равно(Истина, Идентификатор);
	ЮТест.ОжидаетЧто(ФактическиеРазрешенные)
		.Равно(ОжидаемыеРазрешенные, Идентификатор);
КонецПроцедуры

Процедура ПолеCase(Идентификатор, ИсходныйТекст, Количество,
	ТипЗначенияВыражения, Псевдоним,
	ТипПоследнегоЭлементаРазыменования) Экспорт
	Оператор = ЕдинственныйОператор(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Оператор.ВыбираемыеПоля.Количество())
		.Равно(Количество, Идентификатор);
	Поле = Оператор.ВыбираемыеПоля[0];
	ЮТест.ОжидаетЧто(Поле.Выражение.Тип)
		.Равно("ВыражениеМоделиЗапроса", Идентификатор);
	ЮТест.ОжидаетЧто(Поле.Выражение.Значение.Тип)
		.Равно(ТипЗначенияВыражения, Идентификатор);
	ЮТест.ОжидаетЧто(Поле.Псевдоним).Равно(Псевдоним, Идентификатор);
	Если ТипПоследнегоЭлементаРазыменования <> Неопределено Тогда
		ЭлементыРазыменования = Поле.Выражение.Значение.Элементы;
		ЮТест.ОжидаетЧто(ЭлементыРазыменования.Количество())
			.Равно(2, Идентификатор);
		ПоследнийЭлемент = ЭлементыРазыменования[ЭлементыРазыменования.Количество() - 1];
		ЮТест.ОжидаетЧто(ПоследнийЭлемент.Тип)
			.Равно(ТипПоследнегоЭлементаРазыменования, Идентификатор);
	КонецЕсли;
КонецПроцедуры

Процедура НезавершенныйПсевдонимВызываетИсключение() Экспорт
	ПроверитьСинтаксическуюОшибку("ВЫБРАТЬ 1 КАК", "Синтаксическая ошибка");
КонецПроцедуры
```

- In the existing future-grammar module, keep the explicit module-filter gate
  byte-for-byte unchanged. Extend only the registration chain after that gate
  with one parameterized full-query acceptance method and these four desired
  contracts:

```bsl
.ДобавитьСерверныйТест("МодификаторПолногоЗапросаБудущаяГрамматикаCase")
	.СПараметрамиНаСервере("M06", "ВЫБРАТЬ ПЕРВЫЕ 5 РАЗЛИЧНЫЕ РАЗРЕШЕННЫЕ 1", 5, Истина, Истина)
	.СПараметрамиНаСервере("M07", "ВЫБРАТЬ ПЕРВЫЕ 5 РАЗРЕШЕННЫЕ РАЗЛИЧНЫЕ 1", 5, Истина, Истина)
	.СПараметрамиНаСервере("M10", "ВЫБРАТЬ РАЗЛИЧНЫЕ ПЕРВЫЕ 5 РАЗРЕШЕННЫЕ 1", 5, Истина, Истина)
	.СПараметрамиНаСервере("M14", "ВЫБРАТЬ РАЗРЕШЕННЫЕ ПЕРВЫЕ 5 РАЗЛИЧНЫЕ 1", 5, Истина, Истина);
```

```bsl
Процедура МодификаторПолногоЗапросаБудущаяГрамматикаCase(
	Идентификатор, ИсходныйТекст, ОжидаемыеПервые,
	ОжидаемыеРазличные, ОжидаемыеРазрешенные) Экспорт

	Парсер = КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер();
	Пакет = Парсер.Разобрать(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Пакет.Тип).Равно("ПакетЗапросов", Идентификатор);
	ЮТест.ОжидаетЧто(Пакет.Элементы.Количество()).Равно(1, Идентификатор);
	Запрос = Пакет.Элементы[0];
	ЮТест.ОжидаетЧто(Запрос.Тип).Равно("ЗапросВыбора", Идентификатор);
	ЮТест.ОжидаетЧто(Запрос.Операторы.Количество()).Равно(1, Идентификатор);
	Оператор = Запрос.Операторы[0];
	ЮТест.ОжидаетЧто(Оператор.КоличествоПолучаемыхЗаписей)
		.Равно(ОжидаемыеПервые, Идентификатор);
	ЮТест.ОжидаетЧто(Оператор.ВыбиратьРазличные)
		.Равно(ОжидаемыеРазличные, Идентификатор);
	ФактическиеРазрешенные = Неопределено;
	ЮТест.ОжидаетЧто(Оператор.Свойство(
		"__ВыбиратьРазрешенные", ФактическиеРазрешенные))
		.Равно(Истина, Идентификатор);
	ЮТест.ОжидаетЧто(ФактическиеРазрешенные)
		.Равно(ОжидаемыеРазрешенные, Идентификатор);

КонецПроцедуры
```

  Runtime evidence in
  `docs/superpowers/matrices/2026-08-04-query-full-parser-runtime-preflight.md`
  is binding: M06/M10 remain errors from
  `Поле объекта не обнаружено (ВыбиратьРазрешенные)` (reports
  `696aabbdb_543b4d259945c4b680c30f7339fac3665b8fc262` and
  `5b86b1cc0_8912c057bb228f05ce83c2d39adedd835b733d32`); M07/M14 remain
  assertion failures because `ВыбиратьРазличные=Ложь` instead of desired
  `Истина` (reports `d8cfe1f1f_a05525b9f125c94d661adc63d2b86b36f58272aa` and
  `e522eafb6_f12ad5227705b0f2306214b2959313f133871e52`). Do not normalize these
  outcomes and do not change parser/grammar.
- [ ] Use exactly one guarded write per initially touched module (two total).
  The first exact main-module run after Q00 + Q01–Q05 + 11 M + 7 F + N-ALIAS
  produced `25 total / 24 passed / 1 failed`, mutable report path token
  `8b1dc2a30_0603d958d35f2ab1215dde45c14f531d32933588`; only F05 failed because
  the test expected leaf type `ВыражениеВсеПоляИсточника` at the root where the
  public AST exposes root type `Разыменование`. The exact opt-in future-module
  run produced the required `7 total / 0 passed / 4 failed / 3 errors`, report
  `725d8a737_36b73a2a69d631547d3c684d8ed3e380dfdcbf45`. Preserve that future
  module result without another write or rerun.

#### Task 3-R1: F05 nested source-all-fields contract

Conditional debug evidence `1785806808318-2` for exact F05 input
`ВЫБРАТЬ Т.* ИЗ Таблица КАК Т` proves this public structure:

- `Поле.Выражение.Тип=ВыражениеМоделиЗапроса`;
- `Поле.Выражение.Значение.Тип=Разыменование`;
- `Поле.Выражение.Значение.Элементы.Количество()=2`;
- `Поле.Выражение.Значение.Элементы[0]` is string `Т`;
- `Поле.Выражение.Значение.Элементы[1].Тип=ВыражениеВсеПоляИсточника`.

Production confirms the same boundary without modification:
`Парсер/ObjectModule.bsl:2442-2447` creates the `Разыменование` root and appends
the source identifier, `Парсер/ObjectModule.bsl:2494-2500` appends the
`ВыражениеВсеПоляИсточника` leaf,
`ЭлементыМоделиЗапроса/Module.bsl:183-185,541-544` defines both factory shapes,
and `ГенераторТекстовВыражений/ObjectModule.bsl:133-156` consumes the leaf from
inside `Разыменование.Элементы`.

- [ ] The separate review-authorized Task 3-R1 uses exactly one additional
  guarded write to `КОНС_Обр_ПарсерЗапросов_МО` only. Apply the six-argument F
  registrations and conditional nested assertion above. Do not write or rerun
  `КОНС_Обр_ПарсерБудущаяГрамматика_МО`; retain report
  `725d8a737_36b73a2a69d631547d3c684d8ed3e380dfdcbf45`.
- [ ] Run the exact main-module filter incrementally with
  `extensions=["YAXUNIT"]`, `updateBeforeLaunch=true` and
  `updateScope="extension:yaxunit"`; expected result is
  `25 total / 25 passed / 0 failed / 0 errors`. Run diagnostics and diff-check.
  Parser, grammar and factories remain read-only. Task 3 stays 23 represented
  cases, and target arithmetic remains 89 executable synthetic / 101 overall.
  EDT reuses this module's report path token between launches: after the final
  rerun its current content is `25/25`; the initial `24/25` launch output is
  preserved in tool history and the ignored Task 3 execution report, not as an
  immutable report file.

**Commit:** `test: cover select modifiers and fields`.

---

### Task 4: S01–S10 sources and parameters — 10 cases

**Files:** modify only new test module.

**Interfaces:** consumes the ten verified S rows from Task 1A; produces coverage
for four source kinds, joinable kinds, aliases, dereference, parameter list and
both explicit and implicit source aliases. It does not claim coverage for the
excluded `НеТерминалВыражениеСКДПараметр`.

This task uses the bounded-artifact alternative: no candidate or abbreviated
registration is legal. Copy the ten artifact-generated calls with exact text
and expected values immediately after
`.ДобавитьСерверныйТест("ИсточникCase")`.
S09 is exactly `ВЫБРАТЬ Т.Поле ИЗ Каталог.Таблица КАК Т`; S10 is exactly
`ВЫБРАТЬ Т.Поле ИЗ Каталог.Таблица Т`. Their expected alias is `Т`, and they
separately exercise explicit and bare source-alias syntax.

```bsl
Процедура ИсточникCase(Идентификатор, ИсходныйТекст, КоличествоИсточников,
	ТипИсточника, ИмяТаблицы, Псевдоним, КоличествоПараметров,
	ТипПервогоПараметра) Экспорт
	Оператор = ЕдинственныйОператор(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Оператор.Источники.Элементы.Количество())
		.Равно(КоличествоИсточников, Идентификатор);
	Данные = Оператор.Источники.Элементы[0].Источник;
	ЮТест.ОжидаетЧто(Данные.Тип).Равно(ТипИсточника, Идентификатор);
	Если Данные.Свойство("ИмяТаблицы") Тогда
		ЮТест.ОжидаетЧто(Данные.ИмяТаблицы).Равно(ИмяТаблицы, Идентификатор);
	КонецЕсли;
	ЮТест.ОжидаетЧто(Данные.Псевдоним).Равно(Псевдоним, Идентификатор);
	Если КоличествоПараметров > 0 Тогда
		ЮТест.ОжидаетЧто(Данные.Параметры.Количество())
			.Равно(КоличествоПараметров, Идентификатор);
		ЮТест.ОжидаетЧто(Данные.Параметры[0].Значение.Тип)
			.Равно(ТипПервогоПараметра, Идентификатор);
	КонецЕсли;
КонецПроцедуры
```

The runtime artifact must contain no S row attributed to
`НеТерминалВыражениеСКДПараметр`; that production appears only in the two-row
exclusion section of the coverage matrix.

- [ ] One guarded write, module GREEN, diagnostics, diff-check.

**Commit:** `test: cover full query sources`.

---

### Task 5: J01–J07 JOIN — 7 cases

**Files:** modify only new test module.

**Interfaces:** consumes verified temporary/nested source spellings from Task
1A and its verified J06/J07 topology rows; produces all four JOIN types,
normal/optional forms, chain and three joinable-source branches.

- [ ] Add seven exact calls; J06/J07 text is copied from artifact without
  modification:

```bsl
.ДобавитьСерверныйТест("СоединениеCase")
	.СПараметрамиНаСервере("J01", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 ЛЕВОЕ СОЕДИНЕНИЕ Каталог.Таблица2 КАК Т2 ПО Т1.Ключ = Т2.Ключ", "Левое", Ложь, 2, "ИсточникДанныхТаблица", 1, Неопределено, Неопределено)
	.СПараметрамиНаСервере("J02", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 ПРАВОЕ СОЕДИНЕНИЕ Каталог.Таблица2 КАК Т2 ПО Т1.Ключ = Т2.Ключ", "Правое", Ложь, 2, "ИсточникДанныхТаблица", 1, Неопределено, Неопределено)
	.СПараметрамиНаСервере("J03", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 ВНУТРЕННЕЕ СОЕДИНЕНИЕ Каталог.Таблица2 КАК Т2 ПО Т1.Ключ = Т2.Ключ", "Внутреннее", Ложь, 2, "ИсточникДанныхТаблица", 1, Неопределено, Неопределено)
	.СПараметрамиНаСервере("J04", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 ПОЛНОЕ СОЕДИНЕНИЕ Каталог.Таблица2 КАК Т2 ПО Т1.Ключ = Т2.Ключ", "Полное", Ложь, 2, "ИсточникДанныхТаблица", 1, Неопределено, Неопределено)
	.СПараметрамиНаСервере("J05", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 {ЛЕВОЕ СОЕДИНЕНИЕ Каталог.Таблица2 КАК Т2 ПО Т1.Ключ = Т2.Ключ}", "Левое", Истина, 2, "ИсточникДанныхТаблица", 1, Неопределено, Неопределено)
	.СПараметрамиНаСервере("J06", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 ЛЕВОЕ СОЕДИНЕНИЕ ВТ КАК Т2 ПО Т1.Ключ = Т2.Ключ", "Левое", Ложь, 2, "ИсточникДанныхВременнаяТаблица", 1, Неопределено, Неопределено)
	.СПараметрамиНаСервере("J07", "ВЫБРАТЬ 1 ИЗ Таблица1 КАК Т1 ЛЕВОЕ СОЕДИНЕНИЕ (ВЫБРАТЬ 1 КАК Ключ) КАК Т2 ПО Т1.Ключ = Т2.Ключ ПРАВОЕ СОЕДИНЕНИЕ Каталог.Таблица3 КАК Т3 ПО Т2.Ключ = Т3.Ключ", "Левое", Ложь, 3, "ИсточникДанныхВложенныйЗапрос", 2, "Правое", Ложь);
```

During guarded write replace J06 only if the artifact gives a different exact
temporary-table spelling; this is artifact consumption, not a new guess.

```bsl
Процедура СоединениеCase(Идентификатор, ИсходныйТекст, ТипСоединения,
	Опционально, КоличествоИсточников, ТипПравогоИсточника,
	КоличествоСоединений, ТипВторогоСоединения,
	ВтороеСоединениеОпционально) Экспорт
	Оператор = ЕдинственныйОператор(ИсходныйТекст);
	Корень = Оператор.Источники.Элементы[0];
	ЮТест.ОжидаетЧто(Оператор.Источники.Элементы.Количество())
		.Равно(КоличествоИсточников, Идентификатор);
	ЮТест.ОжидаетЧто(Корень.Соединения.Количество())
		.Равно(КоличествоСоединений, Идентификатор);
	Соединение = Корень.Соединения[0];
	ЮТест.ОжидаетЧто(Соединение.Тип).Равно("СоединенияИсточника", Идентификатор);
	ЮТест.ОжидаетЧто(Соединение.ТипСоединения).Равно(ТипСоединения, Идентификатор);
	ЮТест.ОжидаетЧто(Соединение.Опционально).Равно(Опционально, Идентификатор);
	ЮТест.ОжидаетЧто(Соединение.Условие.Тип)
		.Равно("ВыражениеМоделиЗапроса", Идентификатор);
	ЮТест.ОжидаетЧто(Соединение.Условие.Значение.Тип)
		.Равно("БинарнаяОперация", Идентификатор);
	ПравыйИсточник = Оператор.Источники.Элементы[1].Источник;
	ЮТест.ОжидаетЧто(ПравыйИсточник.Тип).Равно(ТипПравогоИсточника, Идентификатор);
	Если КоличествоСоединений = 2 Тогда
		ВтороеСоединение = Корень.Соединения[1];
		ЮТест.ОжидаетЧто(ВтороеСоединение.Тип)
			.Равно("СоединенияИсточника", Идентификатор);
		ЮТест.ОжидаетЧто(ВтороеСоединение.ТипСоединения)
			.Равно(ТипВторогоСоединения, Идентификатор);
		ЮТест.ОжидаетЧто(ВтороеСоединение.Опционально)
			.Равно(ВтороеСоединениеОпционально, Идентификатор);
		ЮТест.ОжидаетЧто(ВтороеСоединение.Условие.Тип)
			.Равно("ВыражениеМоделиЗапроса", Идентификатор);
		ЮТест.ОжидаетЧто(ВтороеСоединение.Условие.Значение.Тип)
			.Равно("БинарнаяОперация", Идентификатор);
		ЮТест.ОжидаетЧто(Оператор.Источники.Элементы[2].Источник.Тип)
			.Равно("ИсточникДанныхТаблица", Идентификатор);
	КонецЕсли;
КонецПроцедуры
```

- [ ] One guarded write, module GREEN, diagnostics, diff-check.

**Commit:** `test: cover full query joins`.

---

### Task 6: C01–C15 clauses, UNION and ORDER — 15 cases

**Files:** modify only new test module.

**Interfaces:** consumes common helpers; produces WHERE/GROUP/HAVING,
UNION/UNION ALL, ORDER default/explicit ВОЗР/УБЫВ/ИЕРАРХИЯ/list and negative
ORDER coverage.

- [ ] Add exact registrations:

```bsl
.ДобавитьСерверныйТест("УсловноеПредложениеCase")
	.СПараметрамиНаСервере("C01", "ВЫБРАТЬ Поле ИЗ Таблица ГДЕ Поле = 1", "WHERE")
	.СПараметрамиНаСервере("C03", "ВЫБРАТЬ Поле ИЗ Таблица СГРУППИРОВАТЬ ПО Поле ИМЕЮЩИЕ Поле > 0", "HAVING")
.ДобавитьСерверныйТест("СписокПредложенияCase")
	.СПараметрамиНаСервере("C02", "ВЫБРАТЬ Поле ИЗ Таблица СГРУППИРОВАТЬ ПО Поле", 1)
	.СПараметрамиНаСервере("C12", "ВЫБРАТЬ А, Б ИЗ Таблица СГРУППИРОВАТЬ ПО А, Б", 2)
.ДобавитьСерверныйТест("UnionCase")
	.СПараметрамиНаСервере("C04", "ВЫБРАТЬ 1 ОБЪЕДИНИТЬ ВЫБРАТЬ 2", 2, "Объединить", Неопределено)
	.СПараметрамиНаСервере("C05", "ВЫБРАТЬ 1 ОБЪЕДИНИТЬ ВСЕ ВЫБРАТЬ 2", 2, "ОбъединитьВсе", Неопределено)
	.СПараметрамиНаСервере("C13", "ВЫБРАТЬ 1 ОБЪЕДИНИТЬ ВСЕ ВЫБРАТЬ 2 ОБЪЕДИНИТЬ ВЫБРАТЬ 3", 3, "ОбъединитьВсе", "Объединить")
.ДобавитьСерверныйТест("OrderCase")
	.СПараметрамиНаСервере("C06", "ВЫБРАТЬ Поле ИЗ Таблица УПОРЯДОЧИТЬ ПО Поле", 1, "Возр", Ложь)
	.СПараметрамиНаСервере("C07", "ВЫБРАТЬ Поле ИЗ Таблица УПОРЯДОЧИТЬ ПО Поле ВОЗР", 1, "Возр", Ложь)
	.СПараметрамиНаСервере("C08", "ВЫБРАТЬ Поле ИЗ Таблица УПОРЯДОЧИТЬ ПО Поле УБЫВ", 1, "Убыв", Ложь)
	.СПараметрамиНаСервере("C09", "ВЫБРАТЬ Поле ИЗ Таблица УПОРЯДОЧИТЬ ПО Поле ИЕРАРХИЯ", 1, "Возр", Истина)
	.СПараметрамиНаСервере("C10", "ВЫБРАТЬ А, Б ИЗ Таблица УПОРЯДОЧИТЬ ПО А ВОЗР, Б УБЫВ", 2, "Возр", Ложь)
.ДобавитьСерверныйТест("АвтоупорядочиваниеРазбирается")
.ДобавитьСерверныйТест("КомбинацияПредложенийРазбирается")
.ДобавитьСерверныйТест("НезавершенныйOrderВызываетИсключение");
```

Complete bodies:

```bsl
Процедура УсловноеПредложениеCase(Идентификатор, ИсходныйТекст, Вид) Экспорт
	Оператор = ЕдинственныйОператор(ИсходныйТекст);
	Если Вид = "WHERE" Тогда
		Узел = Оператор.Отбор;
	Иначе
		Узел = Оператор.ОтборСгруппированных;
	КонецЕсли;
	ЮТест.ОжидаетЧто(Узел.Тип).Равно("ВыражениеМоделиЗапроса", Идентификатор);
	ЮТест.ОжидаетЧто(Узел.Значение.Тип).Равно("БинарнаяОперация", Идентификатор);
КонецПроцедуры

Процедура СписокПредложенияCase(Идентификатор, ИсходныйТекст, Количество) Экспорт
	Оператор = ЕдинственныйОператор(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Оператор.Группировка.Элементы.Количество())
		.Равно(Количество, Идентификатор);
КонецПроцедуры

Процедура UnionCase(Идентификатор, ИсходныйТекст, Количество,
	ТипВторогоОператора, ТипТретьегоОператора) Экспорт
	Запрос = ЕдинственныйЗапросВыбора(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Запрос.Операторы.Количество()).Равно(Количество, Идентификатор);
	ЮТест.ОжидаетЧто(Запрос.Операторы[1].ТипОбъединения)
		.Равно(ТипВторогоОператора, Идентификатор);
	Если Количество = 3 Тогда
		ЮТест.ОжидаетЧто(Запрос.Операторы[2].ТипОбъединения)
			.Равно(ТипТретьегоОператора, Идентификатор);
	КонецЕсли;
КонецПроцедуры

Процедура OrderCase(Идентификатор, ИсходныйТекст, Количество,
	Направление, Иерархия) Экспорт
	Запрос = ЕдинственныйЗапросВыбора(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Запрос.Порядок.Количество()).Равно(Количество, Идентификатор);
	ЮТест.ОжидаетЧто(Запрос.Порядок[0].Направление).Равно(Направление, Идентификатор);
	ЮТест.ОжидаетЧто(Запрос.Порядок[0].Иерархия).Равно(Иерархия, Идентификатор);
КонецПроцедуры

Процедура АвтоупорядочиваниеРазбирается() Экспорт
	Запрос = ЕдинственныйЗапросВыбора("ВЫБРАТЬ 1 АВТОУПОРЯДОЧИВАНИЕ");
	ЮТест.ОжидаетЧто(Запрос.Автопорядок).Равно(Истина, "C11");
КонецПроцедуры

Процедура КомбинацияПредложенийРазбирается() Экспорт
	Текст = "ВЫБРАТЬ Поле ИЗ Таблица ГДЕ Поле > 0 СГРУППИРОВАТЬ ПО Поле "
		+ "ИМЕЮЩИЕ Поле > 1 УПОРЯДОЧИТЬ ПО Поле ВОЗР АВТОУПОРЯДОЧИВАНИЕ";
	Запрос = ЕдинственныйЗапросВыбора(Текст);
	Оператор = Запрос.Операторы[0];
	ЮТест.ОжидаетЧто(Оператор.Отбор.Тип).Равно("ВыражениеМоделиЗапроса", "C14");
	ЮТест.ОжидаетЧто(Оператор.Группировка.Элементы.Количество()).Равно(1, "C14");
	ЮТест.ОжидаетЧто(Оператор.ОтборСгруппированных.Тип).Равно("ВыражениеМоделиЗапроса", "C14");
	ЮТест.ОжидаетЧто(Запрос.Порядок.Количество()).Равно(1, "C14");
	ЮТест.ОжидаетЧто(Запрос.Автопорядок).Равно(Истина, "C14");
КонецПроцедуры

Процедура НезавершенныйOrderВызываетИсключение() Экспорт
	ПроверитьСинтаксическуюОшибку("ВЫБРАТЬ 1 УПОРЯДОЧИТЬ ПО", "Синтаксическая ошибка");
КонецПроцедуры
```

- [ ] One guarded write, module GREEN, diagnostics, diff-check.

**Commit:** `test: cover query clauses union and order`.

---

### Task 7: T01–T21 PLACE, INDEX and TOTALS — 21 cases

**Files:** modify only new test module.

**Interfaces:** consumes verified T-period rows from Task 1A; produces all
TOTALS alternatives, every one of nine period keywords, bounds, PLACE/INDEX and
the dedicated TOTALS error.

- [ ] Add exact registrations:

```bsl
.ДобавитьСерверныйТест("ПомещениеРазбирается")
.ДобавитьСерверныйТест("ИндексРазбирается")
.ДобавитьСерверныйТест("ИтогиКоличествоCase")
	.СПараметрамиНаСервере("T03", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле", 1, 1)
	.СПараметрамиНаСервере("T04", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле), КОЛИЧЕСТВО(*) ПО Поле", 2, 1)
	.СПараметрамиНаСервере("T05", "ВЫБРАТЬ А, Б ИЗ Таблица ИТОГИ СУММА(А) ПО А, Б", 1, 2)
.ДобавитьСерверныйТест("ОбщиеИтогиРазбираются")
.ДобавитьСерверныйТест("ОпцииКонтрольнойТочкиCase")
	.СПараметрамиНаСервере("T07", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ИЕРАРХИЯ", "Иерархия", Неопределено)
	.СПараметрамиНаСервере("T08", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ТОЛЬКО ИЕРАРХИЯ", "ТолькоИерархия", Неопределено)
	.СПараметрамиНаСервере("T09", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле КАК Группа", Неопределено, "Группа")
	.СПараметрамиНаСервере("T10", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле Группа", Неопределено, "Группа")
.ДобавитьСерверныйТест("ПериодИтоговCase")
	.СПараметрамиНаСервере("T11", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(СЕКУНДА)", "СЕКУНДА")
	.СПараметрамиНаСервере("T12", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(МИНУТА)", "МИНУТА")
	.СПараметрамиНаСервере("T13", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(ЧАС)", "ЧАС")
	.СПараметрамиНаСервере("T14", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(ДЕНЬ)", "ДЕНЬ")
	.СПараметрамиНаСервере("T15", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(НЕДЕЛЯ)", "НЕДЕЛЯ")
	.СПараметрамиНаСервере("T16", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(МЕСЯЦ)", "МЕСЯЦ")
	.СПараметрамиНаСервере("T17", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(ГОД)", "ГОД")
	.СПараметрамиНаСервере("T18", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(ДЕКАДА)", "ДЕКАДА")
	.СПараметрамиНаСервере("T19", "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО Поле ПЕРИОДАМИ(ПОЛУГОДИЕ)", "ПОЛУГОДИЕ")
.ДобавитьСерверныйТест("ГраницыПериодаИтоговСохраняются")
.ДобавитьСерверныйТест("НезавершенныеИтогиВызываютИсключение");
```

T01/T02/T06/T20/T21 bodies and all parameterized bodies are complete:

```bsl
Процедура ПомещениеРазбирается() Экспорт
	Оператор = ЕдинственныйОператор("ВЫБРАТЬ 1 ПОМЕСТИТЬ ВТ");
	ЮТест.ОжидаетЧто(Оператор.__ТаблицаДляПомещения).Равно("ВТ", "T01");
КонецПроцедуры

Процедура ИндексРазбирается() Экспорт
	Запрос = ЕдинственныйЗапросВыбора(
		"ВЫБРАТЬ 1 КАК А, 2 КАК Б ПОМЕСТИТЬ ВТ ИНДЕКСИРОВАТЬ ПО А, Б");
	ЮТест.ОжидаетЧто(Запрос.Индекс.Элементы.Количество()).Равно(2, "T02");
КонецПроцедуры

Процедура ИтогиКоличествоCase(Идентификатор, ИсходныйТекст,
	КоличествоВыражений, КоличествоТочек) Экспорт
	Запрос = ЕдинственныйЗапросВыбора(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Запрос.ВыраженияИтогов.Количество())
		.Равно(КоличествоВыражений, Идентификатор);
	ЮТест.ОжидаетЧто(Запрос.КонтрольныеТочкиИтогов.Количество())
		.Равно(КоличествоТочек, Идентификатор);
КонецПроцедуры

Процедура ОбщиеИтогиРазбираются() Экспорт
	Запрос = ЕдинственныйЗапросВыбора(
		"ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) ПО ОБЩИЕ");
	ЮТест.ОжидаетЧто(Запрос.КонтрольныеТочкиИтогов[0].Тип)
		.Равно("ОбщиеИтоги", "T06");
КонецПроцедуры

Процедура ОпцииКонтрольнойТочкиCase(Идентификатор, ИсходныйТекст,
	ТипТочки, ИмяКолонки) Экспорт
	Точка = ЕдинственныйЗапросВыбора(ИсходныйТекст).КонтрольныеТочкиИтогов[0];
	ЮТест.ОжидаетЧто(Точка.ТипКонтрольнойТочки).Равно(ТипТочки, Идентификатор);
	ЮТест.ОжидаетЧто(Точка.ИмяКолонки).Равно(ИмяКолонки, Идентификатор);
КонецПроцедуры

Процедура ПериодИтоговCase(Идентификатор, ИсходныйТекст, ТипПериода) Экспорт
	Точка = ЕдинственныйЗапросВыбора(ИсходныйТекст).КонтрольныеТочкиИтогов[0];
	ЮТест.ОжидаетЧто(Точка.ТипДополненияПериодами).Равно(ТипПериода, Идентификатор);
КонецПроцедуры

Процедура ГраницыПериодаИтоговСохраняются() Экспорт
	Текст = "ВЫБРАТЬ Поле ИЗ Таблица ИТОГИ СУММА(Поле) "
		+ "ПО Поле ПЕРИОДАМИ(ДЕНЬ, &Начало, &Конец)";
	Точка = ЕдинственныйЗапросВыбора(Текст).КонтрольныеТочкиИтогов[0];
	ЮТест.ОжидаетЧто(Точка.НачалоПериодаДополнения.Тип)
		.Равно("ПараметрЗапроса", "T20");
	ЮТест.ОжидаетЧто(Точка.КонецПериодаДополнения.Тип)
		.Равно("ПараметрЗапроса", "T20");
КонецПроцедуры

Процедура НезавершенныеИтогиВызываютИсключение() Экспорт
	ПроверитьСинтаксическуюОшибку("ВЫБРАТЬ 1 ИТОГИ ПО", "Синтаксическая ошибка");
КонецПроцедуры
```

Before write, compare T11–T20 strings and paths byte-for-byte with Task 1A
artifact. A mismatch blocks the write; no silent syntax repair.

- [ ] One guarded write, module GREEN, diagnostics, diff-check.

**Commit:** `test: cover query totals and indexes`.

---

### Task 8A: SKD observability evidence handoff — already satisfied

**Files:** read only
`docs/superpowers/matrices/2026-08-04-query-full-parser-runtime-preflight.md`.
Do not modify the test module or rerun probes.

**Interfaces:** consumes the already verified Task 1A/R1 K rows. They are the
final observability decision; Task 8 must not repeat the bounded spike.

- [x] K01 parsed, but the public model retains only an ordinary selected-field
  count and no raw `{ВЫБРАТЬ ...}` keyword value; evidence report
  `6c649ae60_868ff428551077d66d0e36dedc1e676be56cd796` (`P`).
- [x] K02 parsed and exposes ordinary query-level `.Порядок`, but no raw
  `{УПОРЯДОЧИТЬ ПО ...}` keyword value; exact R1 report
  `c3c157af3_03e7803f1a883fed24d783bcc04184065bbb2170`.
- [x] K03 parsed and exposes ordinary query-level
  `.КонтрольныеТочкиИтогов`, but no raw `{ИТОГИ ПО ...}` keyword value; exact R1
  report `978e6a2ff_53d0af288cc5e7dd0ef045df268781cacadf4e41`.
- [x] K04/K05 are observable through `Оператор.ОтборыСКД`; K06 has an exact
  coordinate-bearing negative fragment. Their artifact evidence is report `P`;
  K06's exact caught fragment also has debug evidence `1785802760701-1` (`D2`).

K01–K03 remain GAP evidence rows outside the executable case budget. They have
no executable test, are never GREEN, and must not be replaced by an invented
field, a private `НеТерминалТипБлокаСКД` call, `Пакет.Тип`, or expected keyword
text used only in an assertion message. No Task 8A write, test run or commit is
required.

---

### Task 8B: K04–K06 observable SKD wiring — 3 cases

**Files:** modify only new test module.

**Interfaces:** consumes only observable K04/K05 and exact negative K06 from the
runtime-preflight artifact. It produces two SKD-WHERE assertions and one
malformed-block assertion; K01–K03 are not registered.

- [ ] In one guarded main-module write, add the artifact's exact calls:

```bsl
.ДобавитьСерверныйТест("ОтборСКДCase")
	.СПараметрамиНаСервере("K04", "ВЫБРАТЬ 1 ГДЕ 1 = 1 {ГДЕ 2}")
	.СПараметрамиНаСервере("K05", "ВЫБРАТЬ 1 {ГДЕ 2, 3}")
.ДобавитьСерверныйТест("ОшибкаБлокаСКДCase")
	.СПараметрамиНаСервере("K06", "ВЫБРАТЬ 1 {ГДЕ 2, 3");
```

- [ ] Add the complete observable bodies. They assert only artifact-backed
  public paths; no keyword field is invented:

```bsl
Процедура ОтборСКДCase(Идентификатор, ИсходныйТекст) Экспорт
	Оператор = ЕдинственныйОператор(ИсходныйТекст);
	Если Идентификатор = "K04" Тогда
		ОжидаемоеКоличество = 1;
	Иначе
		ОжидаемоеКоличество = 2;
	КонецЕсли;
	ЮТест.ОжидаетЧто(Оператор.ОтборыСКД.Количество())
		.Равно(ОжидаемоеКоличество, Идентификатор);
	Для Каждого ОтборСКД Из Оператор.ОтборыСКД Цикл
		ЮТест.ОжидаетЧто(ОтборСКД.Выражение.Значение.Тип)
			.Равно("Константа", Идентификатор);
	КонецЦикла;
КонецПроцедуры

Процедура ОшибкаБлокаСКДCase(Идентификатор, ИсходныйТекст) Экспорт
	ПроверитьСинтаксическуюОшибку(ИсходныйТекст,
		"{(1, 20)}: Синтаксическая ошибка. Ожидается ""}""");
КонецПроцедуры
```

- [ ] Run the exact main-module filter with extension-only incremental update.
  Task 7 leaves the main module at `78/78`; Task 8 adds three cases, so expected
  result is `81 total / 81 passed / 0 failed / 0 errors`. Run diagnostics and
  diff-check. Preserve the existing exact future-module result
  `7 total / 0 passed / 4 failed / 3 errors`, report
  `725d8a737_36b73a2a69d631547d3c684d8ed3e380dfdcbf45`; Task 8 requires no
  future-module write or rerun.

**Commit:** `test: cover observable query SKD extensions`.

---

### Task 9: E01–E04 parser errors and reuse — 4 cases

**Files:** modify only new test module.

**Interfaces:** consumes common helpers; produces empty-input error, coordinate,
reuse and recovery coverage. Alias/ORDER/TOTALS/SKD errors remain in their own
tasks and are not duplicated here.

- [ ] One guarded write adds registration and complete bodies:

```bsl
.ДобавитьСерверныйТест("ПустойПолныйЗапросВызываетИсключение")
.ДобавитьСерверныйТест("ОшибкаПолногоЗапросаСодержитКоординату")
	// Единственный параметр E02 копируется из verified artifact Task 1A:
	// exact input "ВЫБРАТЬ 1 2" + фактически наблюдённый coordinate fragment.
.ДобавитьСерверныйТест("ПарсерПовторноРазбираетПолныеЗапросы")
.ДобавитьСерверныйТест("ПарсерВосстанавливаетсяПослеОшибкиПолногоЗапроса");

Процедура ПустойПолныйЗапросВызываетИсключение() Экспорт
	ПроверитьСинтаксическуюОшибку("", "Синтаксическая ошибка");
КонецПроцедуры

Процедура ОшибкаПолногоЗапросаСодержитКоординату(
	ИсходныйТекст, ПроверенныйФрагментКоординаты) Экспорт
	ПроверитьСинтаксическуюОшибку(ИсходныйТекст, ПроверенныйФрагментКоординаты);
КонецПроцедуры

Процедура ПарсерПовторноРазбираетПолныеЗапросы() Экспорт
	Парсер = КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер();
	Первый = Парсер.Разобрать("ВЫБРАТЬ 1");
	Второй = Парсер.Разобрать("ВЫБРАТЬ 2; УНИЧТОЖИТЬ ВТ");
	ЮТест.ОжидаетЧто(Первый.Элементы.Количество()).Равно(1, "E03");
	ЮТест.ОжидаетЧто(Второй.Элементы.Количество()).Равно(2, "E03");
КонецПроцедуры

Процедура ПарсерВосстанавливаетсяПослеОшибкиПолногоЗапроса() Экспорт
	Парсер = КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер();
	ЮТест.ОжидаетЧто(Парсер)
		.Метод("Разобрать", ЮТМетоды.МассивПараметров("ВЫБРАТЬ 1,"))
		.ВыбрасываетИсключение("Синтаксическая ошибка");
	Пакет = Парсер.Разобрать("ВЫБРАТЬ 2");
	ЮТест.ОжидаетЧто(Пакет.Элементы.Количество()).Равно(1, "E04");
КонецПроцедуры
```

Before the single Task 9 write, append exactly one
`.СПараметрамиНаСервере("ВЫБРАТЬ 1 2", ПроверенныйФрагментКоординаты)` generated
by E02 artifact row to `ОшибкаПолногоЗапросаСодержитКоординату`. The fragment
must be copied byte-for-byte with its Task 1A report ID; the plan contains no
predicted coordinate.

- [ ] One guarded write, module GREEN. Task 8 leaves the main-module synthetic
  report at 81; these four cases raise it to exactly 85. Together with the four
  Task 3 opt-in modifier RED cases, represented executable synthetic coverage
  is exactly 89.

**Commit:** `test: cover full parser errors and reuse`.

---

### Task 9A: Reproducible corpus source preparation

**Files:** read 42 `QueryExamples/*.q1c`; create
`docs/superpowers/matrices/2026-08-04-query-full-parser-corpus-source.md` and
`docs/superpowers/matrices/2026-08-04-query-full-parser-corpus-registration.bsl.txt`.

**Interfaces:** consumes all 42 XML files; produces a 42-row corpus decision
matrix and an exact 12-line BSL registration fragment consumed by Task 9B. It
deliberately does not produce a pre-wire package-element count.

The approved allowlist and stable case order are fixed; clustering must not
silently replace a selected file:

| ID | Relative path |
|---|---|
| X01 | `QueryExamples/ТестВТПериоды.q1c` |
| X02 | `QueryExamples/ТестЗапросОстаткиОтпусков.q1c` |
| X03 | `QueryExamples/ТестСотрудникиОрганизацииПоВТФизлица.q1c` |
| X04 | `QueryExamples/СведенияОДоходахНДФЛНарастающийИтог.q1c` |
| X05 | `QueryExamples/ТестИндексыИПсевдониымПолей.q1c` |
| X06 | `QueryExamples/СрезСОтборами.q1c` |
| X07 | `QueryExamples/ТестЗапросаНачисленияУдержания_И_КадроваяИстория.q1c` |
| X08 | `QueryExamples/ДанныеУчетаВремениПоПШР.q1c` |
| X09 | `QueryExamples/ДвеТаблицыКадровыхДанныхВОдномЗапросе.q1c` |
| X10 | `QueryExamples/ТестКадровыеДанныеСПараметрами_БезФормированияДопЗапроса.q1c` |
| X11 | `QueryExamples/ДанныеОВремениИИнтервалыРегистра.q1c` |
| X12 | `QueryExamples/ТестКадровыеДанныеБезИспользованияВТ.q1c` |

- [ ] For each file, XML-decode the first `<query><text>` and separately read
  relative filename key and first-query XML `name`. Inventory all 42 rows in
  path order with decoded character count, line count, SHA-256, cluster evidence
  and either `selected: Xnn` or one exact exclusion reason.
- [ ] Canonicalize text for hashing to UTF-8 without BOM and LF newlines; compute
  SHA-256 after XML entity decoding.
- [ ] Preserve the approved read-only clustering evidence in the decision
  matrix: 42 total files, one exact-duplicate group of three files, and eight
  near-duplicate groups with normalized similarity `>= 0.94`. An exact-duplicate
  exclusion names the retained path and shared SHA-256; a near-duplicate
  exclusion names the retained path and exact similarity; every remaining
  non-selected row says `excluded: outside approved curated 12 after clustering`.
- [ ] Record `QueryExamples/ТестПакетЗапрсов.q1c` as
  `excluded: oversized stress outlier` with the observed selection evidence
  `8170 chars / 173 lines / 13 SELECT / 8 JOIN / 6 packages`; record that the
  next-largest file has 4183 chars. The six-package observation is selection
  evidence only and is not used as `RuntimeVerifiedCount`.
- [ ] Escape BSL deterministically: replace each `"` with `""`; represent every
  LF as `" + Символы.ПС + "`; preserve empty lines and tabs; never re-encode
  decoded `&` as `&amp;`.
- [ ] Do not count top-level package elements before wiring. A delimiter-only
  algorithm cannot reliably distinguish semicolons in comments/string literals
  or nested query constructs without recreating the production lexer/parser;
  invoking that parser is forbidden in Task 9A.
- [ ] Emit exactly 12
  `.СПараметрамиНаСервере(Key, XmlName, EscapedText, Sha256)` lines for
  X01–X12 only, in the fixed table order. `Key` is the exact relative path; the
  excluded 30 rows never enter the registration fragment.
- [ ] Verify 42 unique paths, 42 non-empty names/texts, 42 SHA-256 values, exactly
  12 selected rows, 30 excluded rows and exactly 12 generated calls. Generate
  both artifacts twice, then once from the reverse 42-file input order while
  sorting the matrix by path and registrations by X ID. Require byte-identical
  outputs and identical SHA-256 hashes in all three runs.

**Verification:** hash decoded text back from each of the 12 generated BSL
literals and compare to its selected row; verify no excluded path appears in a
registration; `git diff --check` both artifacts.

**Commit:** `test: prepare reproducible query example corpus`.

---

### Task 9B: X01–X12 curated corpus wiring

**Files:** consume and update the two Task 9A artifacts; modify new test module;
update corpus-source matrix with runtime columns.

**Interfaces:** consumes the 12 exact escaped literals/checksums; first produces
12 temporary runtime-count probes, then 12 final cases with verified counts.

- [ ] First authorized guarded write pastes the generated 12 four-argument calls
  after this temporary registration:

```bsl
.ДобавитьСерверныйТест("RuntimeCountПервогоЗапросаПримера")

Процедура RuntimeCountПервогоЗапросаПримера(КлючФайла, ИмяЗапросаXML,
	ИсходныйТекст, Sha256) Экспорт
	Пакет = РазобратьЗапросДляТеста(ИсходныйТекст);
	ВызватьИсключение "RUNTIME_COUNT|" + КлючФайла + "|"
		+ Строка(Пакет.Элементы.Количество()) + "|" + Sha256;
КонецПроцедуры
```

- [ ] Run only the temporary method with extension-only update. Every
  successfully parsed input ends in a controlled `RUNTIME_COUNT` error. Record
  exactly 12 counts and 12 probe report IDs on selected X01–X12 rows. A parser
  error lacks that prefix and blocks the second write; excluded rows receive no
  runtime count or report ID.
- [ ] Update `corpus-registration.bsl.txt` deterministically: append the recorded
  `RuntimeVerifiedCount` as the fifth literal of each of the same 12 calls.
  Preserve key/name/text/hash bytes and verify all 12 selected SHA-256 values
  again.
- [ ] Second authorized guarded write removes the temporary registration/body
  and installs the updated 12 five-argument calls after
  `.ДобавитьСерверныйТест("ПервыйЗапросПримераРазбирается")` with this complete
  final body:

```bsl
Процедура ПервыйЗапросПримераРазбирается(КлючФайла, ИмяЗапросаXML,
	ИсходныйТекст, Sha256, RuntimeVerifiedCount) Экспорт
	ЮТест.ОжидаетЧто(ПустаяСтрока(КлючФайла)).Равно(Ложь);
	ЮТест.ОжидаетЧто(ПустаяСтрока(ИмяЗапросаXML)).Равно(Ложь);
	ЮТест.ОжидаетЧто(ПустаяСтрока(ИсходныйТекст)).Равно(Ложь);
	Пакет = РазобратьЗапросДляТеста(ИсходныйТекст);
	ЮТест.ОжидаетЧто(Пакет.Тип).Равно("ПакетЗапросов", КлючФайла + Sha256);
	ЮТест.ОжидаетЧто(Пакет.Элементы.Количество())
		.Равно(RuntimeVerifiedCount, КлючФайла + ": runtime count changed");
	Для Каждого Элемент Из Пакет.Элементы Цикл
		ЮТест.ОжидаетЧто(ПустаяСтрока(Элемент.Тип)).Равно(Ложь, КлючФайла);
	КонецЦикла;
КонецПроцедуры
```

`Sha256` is traceability input, not recomputed by an invented BSL API. Exact
text integrity is reverified outside BSL before both writes.

- [ ] Run final corpus test, then whole module. No parser-independent pre-wire
  count field or claim exists.
- [ ] Record exactly 12 final-case report IDs on X01–X12 rows. Expected main
  whole-module total rises from 85 to 97 only after all 12 runtime cases pass.
  Together with the four opt-in modifier RED cases, represented executable
  coverage is `97 + 4 = 101`.

**Verification:** module GREEN, matrix has exactly 12 runtime-count probe report
IDs and 12 final-case report IDs, generated fragment has exactly 12
five-argument calls, diagnostics and diff-check.

**Commit:** `test: add curated query example parser corpus`.

---

### Task 10: Coverage matrices, review and conditional fix-cycle

**Files:** create/update production, corpus, runtime and future-grammar matrices;
conditionally modify new test module and
`docs/superpowers/specs/2026-08-04-query-full-parser-unit-tests-design.md` when
a confirmed review fix changes case arithmetic, alternative mapping or scope.

**Interfaces:** consumes all reports/artifacts and the 67-row design inventory;
produces final evidence and an independent reviewer verdict.

- [ ] Expand every reachable design inventory row to one row per alternative
  with exact input, raw AST path, case ID and status. Keep both exclusions
  (`КакОпционально`: no caller; `ВыражениеСКДПараметр`: self-recursion only)
  separate and do not assign them test IDs.
- [ ] Record existing opt-in REDs `--1`, `НЕДЕЛЯ(&Дата)`, `1 +` and Task 3
  modifier REDs M06/M07/M10/M14; do not run any of them in the main GREEN.
- [ ] Preserve K01–K03 as three separate artifact-backed observability GAP
  evidence rows outside the executable case budget. They retain their K IDs
  and report references, have no executable tests and never receive GREEN.
- [ ] Preserve all 42 corpus decision rows: exactly 12 selected X01–X12 rows
  have executable cases and runtime/final report IDs; each of the 30 excluded
  rows retains its exact duplicate, near-duplicate, outlier or curated-allowlist
  exclusion reason and never receives an executable case or GREEN.
- [ ] Run Q00 smoke (`Total=1`) and whole new main module (`Total=97`) with only
  extension:yaxunit update. Separately run the exact future-grammar module
  filter and require the known RED distribution
  `7 total / 0 passed / 4 failed / 3 errors`; collect diagnostics,
  `git diff --check`, status. Represented executable arithmetic is `97` main
  GREEN plus four Task 3 modifier REDs, exactly `101`; the three pre-existing
  future-grammar REDs remain outside this target budget.
- [ ] Independent reviewer reads actual module and all matrices. Prompt requires
  checking every branch, fifteen modifier orders, nine periods, explicit ВОЗР,
  raw/semantic boundary, SKD keyword observability, the fixed 12-file corpus
  allowlist, all 30 exclusion reasons and corpus hash/escaping determinism.
- [ ] For confirmed findings only, perform one bounded guarded write of the test
  module, one module GREEN and matrix updates. If counts/mapping/scope change,
  update the design in the same fix-cycle and re-run diff-check. If no confirmed
  finding exists, perform no write.

**Verification:** report actual procedure count and case arithmetic separately;
do not declare readiness—the independent reviewer decides.

**Commit:** commit only reviewed matrices and any confirmed conditional design
update: `docs: record full parser coverage review`.
