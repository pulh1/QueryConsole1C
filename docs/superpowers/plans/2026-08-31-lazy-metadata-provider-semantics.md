# Lazy Metadata Provider Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Убрать построение полного описания таблицы из semantic hot path, сохранив полный контракт для явного UI-раскрытия.

**Architecture:** Реестр маршрутизирует новые точечные операции `НайтиТаблицу` и `НайтиПоле` напрямую в provider. Standard provider использует `ДоступныеТаблицы.Найти` и `Поля.Найти`, executable provider — raw `ПоляПоИменам`; полные описания и их cache остаются provider-owned и вызываются только явно.

**Tech Stack:** 1С:Предприятие 8.3.24+, русский BSL, EDT-проект расширения, YAxUnit, EDT-MCP, runtime benchmark harness.

**Spec:** `docs/superpowers/specs/2026-08-31-lazy-metadata-provider-semantics-design.md`

## Global Constraints

- Все BSL-чтения и записи выполнять через EDT-MCP с актуальным `contentHash` и `expectedHash`.
- Перед каждой production-правкой сначала добавить тест и увидеть ожидаемый RED.
- Не создавать `СхемаЗапроса` или `ДоступныеТаблицыИБ` в semantic context.
- Один standard provider владеет одной `СхемаЗапроса` на корневой semantic lifecycle.
- Реестр не кэширует descriptions и не вызывает `ТаблицаСуществует` перед точечной делегацией.
- Unknown segment, table и field возвращают `Неопределено`; negative cache не вводится.
- Временные таблицы, вложенные запросы, таблицы значений и aliases разрешаются локально до реестра.
- UI, parser, lexer, AST и `ПоставщикИсполняемыхПредставлений` не менять.
- Перед каждым timed benchmark подтвердить отсутствие debugger, targets, breakpoints, `dbgs` и listener на port 1550.
- Четыре существующих untracked JSON baseline/feature сохранить без перезаписи.

---

### Task 1: Краткое описание и точечный контракт реестра

**Files:**
- Modify: `QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl`
- Modify: `QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/ObjectModule.bsl`
- Modify: `yaxunit/src/DataProcessors/КОНС_ПоставщикМетаданныхТаблицШпион/ObjectModule.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Produces: `МетаданныеТаблицЗапроса.НовоеКраткоеОписаниеТаблицы(...)` с пятью свойствами.
- Produces: `Реестр.НайтиТаблицу(ИмяТаблицы)` и `Реестр.НайтиПоле(ИмяТаблицы, ИмяПоля)`.
- Produces: spy methods и counters для наблюдения трёх независимых операций.

- [ ] **Step 1: Добавить RED-тест фабрики краткого описания**

  Зарегистрировать и добавить `КраткоеОписаниеТаблицыНеСодержитПоляИПараметры`:

```bsl
//@skip-check server-execution-safe-mode
Описание = Вычислить("МетаданныеТаблицЗапроса.НовоеКраткоеОписаниеТаблицы(
	|""Кадры.Сотрудники"", ""Кадры"", ""Служебный"", ""Сотрудники"")");
ЮТест.ОжидаетЧто(Описание.Количество()).Равно(5);
ЮТест.ОжидаетЧто(Описание.Свойство("Поля")).ЭтоЛожь();
ЮТест.ОжидаетЧто(Описание.Свойство("Параметры")).ЭтоЛожь();
```

- [ ] **Step 2: Запустить exact test и подтвердить RED**

  EDT-MCP `run_yaxunit_tests`:

```text
launchConfigurationName="QueryConsoleZUP Semantic Tests"
extensions=["YAXUNIT"]
tests=["КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО.КраткоеОписаниеТаблицыНеСодержитПоляИПараметры"]
timeout=60
updateBeforeLaunch=true
updateScope="extension:QueryConsoleZUP_YAxUnit"
```

  Expected: FAIL из-за отсутствующей `НовоеКраткоеОписаниеТаблицы`.

- [ ] **Step 3: Реализовать минимальную фабрику**

```bsl
Функция НовоеКраткоеОписаниеТаблицы(
	ИмяТаблицы = "", ИмяПоставщика = "", ВидИсточника = "", Представление = "") Экспорт

	Возврат Новый Структура(
		"ИмяТаблицы, ИмяПоставщика, ВидИсточника, Представление, ДанныеПоставщика",
		ИмяТаблицы, ИмяПоставщика, ВидИсточника, Представление, Неопределено);

КонецФункции
```

- [ ] **Step 4: Расширить spy и добавить RED-тесты прямой делегации**

  Добавить counters `СчетчикПоисковТаблицы` и `СчетчикПоисковПоля`; методы spy:

```bsl
Функция НайтиТаблицу(ИмяТаблицы) Экспорт
	СчетчикПоисковТаблицы = СчетчикПоисковТаблицы + 1;
	Возврат СуществующиеТаблицы.Получить(ВРег(ИмяТаблицы));
КонецФункции

Функция НайтиПоле(ИмяТаблицы, ИмяПоля) Экспорт
	СчетчикПоисковПоля = СчетчикПоисковПоля + 1;
	ОписаниеТаблицы = СуществующиеТаблицы.Получить(ВРег(ИмяТаблицы));
	Если ОписаниеТаблицы = Неопределено Тогда
		Возврат Неопределено;
	КонецЕсли;
	Для Каждого Поле Из ОписаниеТаблицы.Поля Цикл
		Если ВРег(Поле.Имя) = ВРег(ИмяПоля) Тогда
			Возврат Поле;
		КонецЕсли;
	КонецЦикла;
	Возврат Неопределено;
КонецФункции
```

  Тесты вызывают `Реестр.НайтиТаблицу` и `Реестр.НайтиПоле`, проверяют результат, соответствующий counter `= 1`, а `КоличествоПроверокСуществования()` и `КоличествоПолученийОписания()` — `= 0`.

- [ ] **Step 5: Запустить два exact test и подтвердить RED**

  Вызвать `run_yaxunit_tests` с tests:

```text
КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО.РеестрДелегируетПоискТаблицыБезПолногоОписания
КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО.РеестрДелегируетПоискПоляБезПолногоОписания
```

  Expected: FAIL из-за отсутствующих методов реестра.

- [ ] **Step 6: Добавить минимальные методы реестра**

```bsl
Функция НайтиТаблицу(ИмяТаблицы) Экспорт
	Поставщик = ПоставщикТаблицы(ИмяТаблицы);
	Если Поставщик = Неопределено Тогда
		Возврат Неопределено;
	КонецЕсли;
	Возврат Поставщик.НайтиТаблицу(ИмяТаблицы);
КонецФункции

Функция НайтиПоле(ИмяТаблицы, ИмяПоля) Экспорт
	Поставщик = ПоставщикТаблицы(ИмяТаблицы);
	Если Поставщик = Неопределено Тогда
		Возврат Неопределено;
	КонецЕсли;
	Возврат Поставщик.НайтиПоле(ИмяТаблицы, ИмяПоля);
КонецФункции
```

- [ ] **Step 7: Запустить три exact test, перечитать модули и проверить diagnostics delta**

  Expected: 3/3 PASS; EDT syntax write checks successful; новых diagnostics у четырёх объектов нет.

- [ ] **Step 8: Commit**

```powershell
git add -- QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/ObjectModule.bsl yaxunit/src/DataProcessors/КОНС_ПоставщикМетаданныхТаблицШпион/ObjectModule.bsl yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl
git commit -m "feat: add lazy metadata lookup contract"
```

---

### Task 2: Ленивый standard provider

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц/ObjectModule.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Consumes: `НовоеКраткоеОписаниеТаблицы`.
- Produces: provider methods `НайтиТаблицу` and `НайтиПоле`.
- Preserves: full `ОписаниеТаблицы` including fields and parameters.

- [ ] **Step 1: Добавить RED-тесты обычного поля, вложенной ветви и лёгкой таблицы**

```bsl
Поставщик = НовыйСтандартныйПоставщик();
Таблица = Поставщик.НайтиТаблицу("Документ.НачислениеЗарплаты");
ЮТест.ОжидаетЧто(Таблица.Количество()).Равно(5);
ЮТест.ОжидаетЧто(Таблица.Свойство("Поля")).ЭтоЛожь();

ОбычноеПоле = Поставщик.НайтиПоле("Документ.НачислениеЗарплаты", "Ссылка");
ЮТест.ОжидаетЧто(ОбычноеПоле.ВидПоля).Равно("ОбычноеПоле");

ВложеннаяТаблица = Поставщик.НайтиПоле("Документ.НачислениеЗарплаты", "Начисления");
ЮТест.ОжидаетЧто(ВложеннаяТаблица.ВидПоля).Равно("ВложеннаяТаблица");
ЮТест.ОжидаетЧто(ВложеннаяТаблица.Поля.Количество() > 0).ЭтоИстина();
```

  Повторить lookup обычного поля с другим регистром и проверить возврат того же cached descriptor. Неизвестные table/field должны вернуть `Неопределено`.

- [ ] **Step 2: Запустить exact tests и подтвердить RED**

  Expected: FAIL из-за отсутствующих provider methods.

- [ ] **Step 3: Реализовать два provider-owned positive cache и точечный lookup**

  В `Инициализировать()` создать `КраткиеОписанияТаблицПоИменам` и `ОписанияПолейПоИменам`. `НайтиТаблицу` делает один `ДоступныеТаблицыПоставщика.Найти`, создаёт 5-field descriptor и сохраняет platform table в `ДанныеПоставщика`. `НайтиПоле` сначала ищет table, затем `ДоступнаяТаблица.Поля.Найти(ИмяПоля)` и вызывает существующий `ПреобразоватьПоле` только для найденного элемента.

```bsl
ДоступноеПоле = ДоступнаяТаблица.Поля.Найти(ИмяПоля);
Если ДоступноеПоле = Неопределено Тогда
	Возврат Неопределено;
КонецЕсли;
Описание = ПреобразоватьПоле(ДоступноеПоле);
```

  Ключи обоих уровней нормализовать через `ВРег`; неизвестные значения не вставлять.

- [ ] **Step 4: Запустить новые tests и весь module suite**

  `run_yaxunit_tests` с module `КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО`, `timeout=120`, `updateScope="extension:QueryConsoleZUP_YAxUnit"`.

  Expected: все tests PASS; существующие full-description/parameter/cache tests остаются зелёными.

- [ ] **Step 5: Перечитать provider, revalidate object и проверить diagnostic delta**

  Revalidate `DataProcessor.ПоставщикМетаданныхСтандартныхТаблиц`; новых diagnostics нет.

- [ ] **Step 6: Commit**

```powershell
git add -- QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц/ObjectModule.bsl yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl
git commit -m "perf: resolve standard metadata lazily"
```

---

### Task 3: Ленивый executable provider

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Produces: lightweight `НайтиТаблицу` and indexed `НайтиПоле`.
- Preserves: raw provider reuse and full `ОписаниеТаблицы` conversion.

- [ ] **Step 1: Добавить RED-тест реального executable lookup**

  Для существующего `...НарастающиеИтоги` проверить: 5-field table descriptor без `Поля`; `ДанныеПоставщика` равны raw description; поле из raw `ПоляПоИменам` найдено без учёта регистра; unknown table/field дают `Неопределено`.

- [ ] **Step 2: Запустить exact test и подтвердить RED**

  Expected: FAIL из-за отсутствующих methods.

- [ ] **Step 3: Реализовать lightweight lookup и raw-index field lookup**

```bsl
СыроеОписание = ПоставщикИсполняемыхПредставлений
	.ОписаниеПредставленияПоИмениТаблицы(ИмяТаблицы);
ПоляПоИменам = ПолучитьСвойство(СыроеОписание, "ПоляПоИменам", Неопределено);
Если ПоляПоИменам = Неопределено Тогда
	Возврат Неопределено;
КонецЕсли;
СыроеПоле = ПоляПоИменам.Получить(ВРег(ИмяПоля));
```

  Конвертировать только `СыроеПоле`; хранить lightweight/field positive caches в adapter instance. Не добавлять второй raw cache и не менять `ПоставщикИсполняемыхПредставлений`.

- [ ] **Step 4: Запустить exact test и весь provider suite**

  Expected: PASS, включая существующие full fields/parameters tests.

- [ ] **Step 5: Перечитать provider, revalidate object и проверить diagnostic delta**

- [ ] **Step 6: Commit**

```powershell
git add -- QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl
git commit -m "perf: resolve executable metadata lazily"
```

---

### Task 4: Перевести semantic consumers на точечный контракт

**Files:**
- Modify: `QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl`
- Modify: `QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl`
- Modify: `QueryConsoleZUP/src/CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Consumes: registry `НайтиПоле` for semantic field resolution.
- Consumes: registry `НайтиТаблицу` for source classification and raw executable data.

- [ ] **Step 1: Добавить RED-тест observable semantic contract**

  Создать spy table с одним neutral field, registry и context; вызвать экспортный `НайтиПолеВИсточнике`. Проверить найденное поле, `КоличествоПоисковПоля() = 1`, `КоличествоПоисковТаблицы() = 0`, `КоличествоПолученийОписания() = 0`.

- [ ] **Step 2: Запустить exact test и подтвердить RED**

  Expected: FAIL, потому что consumer вызывает `ОписаниеТаблицы`, а не `НайтиПоле`.

- [ ] **Step 3: Минимально заменить semantic field path**

```bsl
Возврат Реестр.НайтиПоле(ИмяТаблицы, ИмяПоля);
```

  Сохранить guard `Реестр = Неопределено`.

- [ ] **Step 4: Перевести classification consumers**

  В `ДобавитьИсточник`, `УстановитьПараметрыИсполняемогоПредставления` и registry-ветке `ОбработатьИсточникЗапроса` заменить только `ОписаниеТаблицы(...)` на `НайтиТаблицу(...)`. Тексты ошибок, `ВидИсточника`, `ДанныеПоставщика` и legacy-ветку `ОбработатьИсточникЗапроса` не менять.

- [ ] **Step 5: Запустить provider + expression + builder/executable suites**

  Последовательно вызвать `run_yaxunit_tests`:

```text
modules=["КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО"]
modules=["КОНС_Обр_МодельВыражений_МО"]
modules=["КОНС_Обр_ПостроениеИГенерацияЗапросов_МО", "КОНС_Обр_ИсполняемыеПредставления_МО"]
```

  Для каждого: launch `QueryConsoleZUP Semantic Tests`, extension `YAXUNIT`, `updateBeforeLaunch=true`, `updateScope="extension:QueryConsoleZUP_YAxUnit"`, timeout 120. Expected: все tests PASS; unknown/local/nested/table-value/join behavior сохранено.

- [ ] **Step 6: Проверить отсутствие full lookup в canonical consumers поведением и usages**

  Observable spy test должен быть зелёным. EDT search `ОписаниеТаблицы(` должен оставить provider implementations, full-description tests и factory calls, но не три изменённых canonical call site.

- [ ] **Step 7: Перечитать три production module и сравнить diagnostic delta**

- [ ] **Step 8: Commit**

```powershell
git add -- QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl QueryConsoleZUP/src/CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl
git commit -m "perf: use lazy metadata in semantic consumers"
```

---

### Task 5: Provenance, независимое ревью и performance gate

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`
- Create: `docs/superpowers/matrices/2026-08-31-full-semantic-pipeline-lazy-baseline-1.json`
- Create: `docs/superpowers/matrices/2026-08-31-full-semantic-pipeline-lazy-baseline-2.json`
- Create: `docs/superpowers/matrices/2026-08-31-full-semantic-pipeline-lazy-feature-1.json`
- Create: `docs/superpowers/matrices/2026-08-31-full-semantic-pipeline-lazy-feature-2.json`
- Preserve: four existing `2026-08-31-full-semantic-pipeline-{baseline,feature}-{1,2}.json`

**Interfaces:**
- Produces: provenance-consistent benchmark description for the lazy feature commit.
- Produces: independent code-review verdict and A–B–B–A performance verdict.

- [ ] **Step 1: Рассчитать SHA-256 изменённых production artifacts**

  Хешировать нормализованный UTF-8/LF content production artifacts; не использовать git blob hash. Обновить соответствующие literals и feature id/commit в benchmark module через EDT-MCP. Добавить в provenance два изменённых, но ранее не перечисленных artifacts: `CommonModule.МетаданныеТаблицЗапроса` и `CommonModule.ОбработкаПредставлениеЗапросов`. Для baseline и feature каждый descriptor должен содержать hashes фактически загруженной ревизии.

- [ ] **Step 2: Запустить benchmark exact test как provenance smoke**

```text
tests=["КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineСемантическогоКонвейераФормируется"]
timeout=180
updateBeforeLaunch=true
updateScope="extension:QueryConsoleZUP_YAxUnit"
```

  Expected: PASS и новый JSON с согласованными artifact hashes.

- [ ] **Step 3: Выполнить независимое ревью diff**

  Reviewer использует `queryconsole-1c-review`, проверяет dynamic contract, server boundary, cache ownership, local sources, nested fields, raw executable data, error parity и отсутствие full conversion в hot path. Все Critical/Important устранить через новый RED→GREEN цикл; Minor либо исправить, либо явно зафиксировать.

- [ ] **Step 4: Выполнить финальные functional и EDT gates без debugger**

  Повторить provider, expression и builder/executable suites. Revalidate все изменённые production objects и test objects. Сравнить diagnostics с baseline до правок; сообщить существующий фон отдельно.

- [ ] **Step 5: Выполнить новую A–B–B–A серию**

  После каждой загрузки extension сделать excluded preconditioning run. Для каждого timed run использовать те же `semantic_contract` и `repeated_standard_source`, 3 warmups, 20 samples, batch target 25 ms. Перед каждым run подтвердить нулевой debugger state и отсутствие listener на port 1550.

  Сохранить все четыре новых raw result: baseline-1, feature-1, feature-2, baseline-2. Gate:

```text
feature median/call <= baseline median/call * 1.25 для обоих корпусов
feature p95/call <= baseline p95/call * 1.50 для обоих корпусов
```

  При сильном order effect не объявлять PASS, а повторить с симметричным preconditioning. Новые raw JSON сохранить отдельными файлами; существующие четыре JSON не менять.

- [ ] **Step 6: Commit benchmark provenance and evidence**

```powershell
git add -- yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl docs/superpowers/matrices/2026-08-31-full-semantic-pipeline-lazy-baseline-1.json docs/superpowers/matrices/2026-08-31-full-semantic-pipeline-lazy-feature-1.json docs/superpowers/matrices/2026-08-31-full-semantic-pipeline-lazy-feature-2.json docs/superpowers/matrices/2026-08-31-full-semantic-pipeline-lazy-baseline-2.json
git commit -m "test: verify lazy semantic metadata performance"
```

- [ ] **Step 7: Финальная проверка ветки**

  Проверить `git status --short`, `git diff --check`, фактические JUnit counts, diagnostic delta, independent review verdict и performance thresholds. Не считать четыре прежних untracked JSON ошибкой чистоты: после проверки добавить их отдельным evidence commit либо оставить нетронутыми с явным отчётом, не удаляя и не перезаписывая.
