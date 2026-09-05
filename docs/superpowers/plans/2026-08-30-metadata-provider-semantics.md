# Metadata Provider Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ввести единый реестр поставщиков метаданных именованных таблиц и перевести на нейтральные описания семантический анализ, обработку исполняемых представлений и построитель модели без изменения поведения локальных источников.

**Architecture:** Один stateful-реестр создаётся на верхнеуровневый lifecycle и неизменно индексирует два stateful provider-а по первому сегменту имени. Стандартный provider единолично владеет `СхемаЗапроса.ДоступныеТаблицы`, provider исполняемых представлений адаптирует существующий repeated provider, а stateless common module создаёт нейтральные структуры. Временные таблицы, вложенные запросы, таблицы значений и aliases остаются в локальном semantic context.

**Tech Stack:** 1С:Предприятие 8.3.24+, Russian BSL, EDT 2026.1, EDT-MCP, YAxUnit 25.12, onec-runtime MCP как вспомогательный probe-контур.

**Spec:** `docs/superpowers/specs/2026-08-30-metadata-provider-semantics-ui-design.md`

## Global Constraints

- Новые production metadata objects называются без `КОНС_`: `РеестрПоставщиковМетаданныхТаблиц`, `ПоставщикМетаданныхСтандартныхТаблиц`, `ПоставщикМетаданныхИсполняемыхПредставлений`, `МетаданныеТаблицЗапроса`.
- Метаданные создаются и регистрируются только EDT-MCP; `.mdo` и `Configuration.mdo` вручную не редактируются.
- BSL записывается точечно через EDT-MCP с актуальным `contentHash`, затем перечитывается и ревалидируется.
- Production code следует RED-GREEN-REFACTOR: каждый observable behavior сначала появляется в падающем YAxUnit-тесте.
- Реестр не содержит provider-а временных таблиц и не выполняет `ТаблицаСуществует()` перед `ОписаниеТаблицы()`.
- При наличии реестра неизвестная таблица не получает legacy fallback.
- `ДанныеПоставщика` остаётся server-only и не участвует в transport DTO.
- Existing `ПоставщикИсполняемыхПредставленийПовтИсп` остаётся единственным raw cache исполняемых представлений.
- Для текущего runtime подтверждены свойства параметра платформы `Имя`, `ТипЗначения`, `Варианты`, `ДоступныеПоля`; отсутствующие `ВидПараметра` и `Обязательный` заполняются нейтральными значениями `Неопределено` и `Ложь`.
- Фаза UI и изменения form modules в этот план не входят.

---

### Task 1: EDT baseline и исполняемый RED-контур

**Files:**
- Create via EDT-MCP: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО.mdo`
- Create via EDT-MCP: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`
- Create via EDT-MCP: `yaxunit/src/DataProcessors/КОНС_ПоставщикМетаданныхТаблицШпион/КОНС_ПоставщикМетаданныхТаблицШпион.mdo`
- Create via EDT-MCP: `yaxunit/src/DataProcessors/КОНС_ПоставщикМетаданныхТаблицШпион/ObjectModule.bsl`

**Interfaces:**
- Consumes: `ЮТТесты.ДобавитьТестовыйНабор`, `ЮТест.ОжидаетЧто`, dynamic `Вычислить()` для доступа из YAxUnit-extension к production-extension.
- Produces: test tag `ПоставщикиМетаданныхТаблиц`; spy contract `Инициализировать`, `ИмяПоставщика`, `Сегменты`, `ТаблицаСуществует`, `ОписаниеТаблицы`, `КоличествоПроверокСуществования`, `КоличествоПолученийОписания`.

- [ ] **Step 1: Зафиксировать EDT baseline**

  Дождаться `ready` для `QueryConsoleZUP_Semantics` и `QueryConsoleZUP_YAxUnit`, сохранить `get_problem_summary` и подробные `get_project_errors` обоих проектов. Проверить через `list_modules`, что EDT читает `ОбработкаМоделиЗапроса` и существующие `КОНС_Обр_*_МО` из semantic-worktree.

- [ ] **Step 2: Создать test-only metadata через EDT-MCP**

  Создать server common module `КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО` и data processor `КОНС_ПоставщикМетаданныхТаблицШпион`. Production metadata на этом шаге не создавать.

- [ ] **Step 3: Записать test spy**

```bsl
Перем СегментыПоставщика;
Перем СуществующиеТаблицы;
Перем ИмяПоставщикаШпиона;
Перем СчетчикПроверокСуществования;
Перем СчетчикПолученийОписания;

Функция Инициализировать() Экспорт
	СчетчикПроверокСуществования = 0;
	СчетчикПолученийОписания = 0;
	Возврат ЭтотОбъект;
КонецФункции

Функция Настроить(ИмяПоставщика, Сегменты, Таблицы) Экспорт
	ИмяПоставщикаШпиона = ИмяПоставщика;
	СегментыПоставщика = Сегменты;
	СуществующиеТаблицы = Таблицы;
	Возврат ЭтотОбъект;
КонецФункции

Функция ИмяПоставщика() Экспорт
	Возврат ИмяПоставщикаШпиона;
КонецФункции

Функция Сегменты() Экспорт
	Возврат СегментыПоставщика;
КонецФункции

Функция ТаблицаСуществует(ИмяТаблицы) Экспорт
	СчетчикПроверокСуществования = СчетчикПроверокСуществования + 1;
	Возврат СуществующиеТаблицы.Получить(ВРег(ИмяТаблицы)) <> Неопределено;
КонецФункции

Функция ОписаниеТаблицы(ИмяТаблицы) Экспорт
	СчетчикПолученийОписания = СчетчикПолученийОписания + 1;
	Возврат СуществующиеТаблицы.Получить(ВРег(ИмяТаблицы));
КонецФункции
```

- [ ] **Step 4: Записать первые registry tests до production metadata**

  В `ИсполняемыеСценарии()` зарегистрировать серверные тесты `РеестрДелегируетОписаниеБезПредварительнойПроверки`, `РеестрВозвращаетНеопределеноДляНеизвестногоСегмента`, `РеестрОтклоняетКоллизиюСегментов`. Тесты создают production registry через `Вычислить("Обработки.РеестрПоставщиковМетаданныхТаблиц.Создать()")`; первый прогон обязан завершиться ошибкой отсутствующего объекта.

- [ ] **Step 5: Запустить RED**

  Run: EDT-MCP `run_yaxunit_tests` с tag `ПоставщикиМетаданныхТаблиц`.

  Expected: FAIL из-за отсутствия `РеестрПоставщиковМетаданныхТаблиц`; test project при этом компилируется, потому что обращение динамическое.

- [ ] **Step 6: Commit test harness**

```powershell
git add yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО yaxunit/src/DataProcessors/КОНС_ПоставщикМетаданныхТаблицШпион
git commit -m "test: define metadata provider semantics contract"
```

### Task 2: Neutral descriptors и immutable registry

**Files:**
- Create via EDT-MCP: `QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/МетаданныеТаблицЗапроса.mdo`
- Create via EDT-MCP: `QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl`
- Create via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/РеестрПоставщиковМетаданныхТаблиц.mdo`
- Create via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/ManagerModule.bsl`
- Create via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/ObjectModule.bsl`
- Modify via EDT-MCP: test module from Task 1.

**Interfaces:**
- Produces factories `НовыйОписаниеТаблицы`, `НовыйОписаниеПоля`, `НовыйОписаниеПараметра`, `НайтиПоле`, `ВидПоляОбычное`, `ВидПоляВложеннаяТаблица`.
- Produces manager factory `СоздатьРеестр(Поставщики = Неопределено)`.
- Produces registry methods `Инициализировать(Поставщики)`, `ТаблицаСуществует(ИмяТаблицы)`, `ОписаниеТаблицы(ИмяТаблицы)`.

- [ ] **Step 1: Расширить RED тестами neutral factories**

  Добавить проверки всех полей структур из spec и независимости массивов `Поля`, `Параметры`, `Варианты`. Mutation caught: повторное использование одного mutable массива между двумя descriptors.

- [ ] **Step 2: Запустить RED**

  Expected: FAIL из-за отсутствия common module и registry metadata.

- [ ] **Step 3: Создать два production metadata skeleton через EDT-MCP**

  На этом task создать common module `МетаданныеТаблицЗапроса` с server-context flags и data processor `РеестрПоставщиковМетаданныхТаблиц`. Два concrete provider-а создаются в Tasks 3–4.

- [ ] **Step 4: Реализовать neutral factories минимально**

```bsl
Функция НовыйОписаниеТаблицы(ИмяТаблицы = "", ИмяПоставщика = "", ВидИсточника = "", Представление = "") Экспорт
	Описание = Новый Структура;
	Описание.Вставить("ИмяТаблицы", ИмяТаблицы);
	Описание.Вставить("ИмяПоставщика", ИмяПоставщика);
	Описание.Вставить("ВидИсточника", ВидИсточника);
	Описание.Вставить("Представление", Представление);
	Описание.Вставить("Поля", Новый Массив);
	Описание.Вставить("Параметры", Новый Массив);
	Описание.Вставить("ДанныеПоставщика", Неопределено);
	Возврат Описание;
КонецФункции
```

  Аналогично создать exact field/parameter shapes из spec. `НайтиПоле()` сравнивает `ВРег(Поле.Имя)` с `ВРег(ИмяПоля)`.

- [ ] **Step 5: Реализовать registry**

  `Инициализировать()` сначала инициализирует все providers во временном массиве, строит новое private `Соответствие`, проверяет коллизии нормализованных сегментов, и только после успешного полного прохода присваивает private индекс. Публичной регистрации после инициализации нет.

- [ ] **Step 6: Проверить прямую делегацию**

  Registry test обязан получить `КоличествоПолученийОписания() = 1` и `КоличествоПроверокСуществования() = 0`. Unknown segment возвращает `Неопределено`. Два spy provider-а с одинаковым сегментом должны дать исключение, содержащее сегмент и оба имени provider-а.

- [ ] **Step 7: Запустить GREEN и revalidate**

  Run: tag `ПоставщикиМетаданныхТаблиц`; затем EDT-MCP `revalidate_objects` для двух production metadata objects и двух test objects.

- [ ] **Step 8: Commit**

```powershell
git add QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц yaxunit/src
git commit -m "feat: add immutable metadata provider registry"
```

### Task 3: Standard table provider

**Files:**
- Create via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц/ПоставщикМетаданныхСтандартныхТаблиц.mdo`
- Create via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц/ObjectModule.bsl`
- Modify via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/ManagerModule.bsl`
- Modify via EDT-MCP: provider test module.

**Interfaces:**
- Produces provider contract with name `СтандартныеТаблицы`, platform segments, source kind `СтандартнаяТаблица`.
- Owns exactly one `СхемаЗапроса`, its `ДоступныеТаблицы`, and positive `ОписанияТаблицПоИменам` per provider instance.

- [ ] **Step 1: Write RED tests**

  Tests use literals verified by runtime:

```bsl
Описание = Поставщик.ОписаниеТаблицы("Документ.НачислениеЗарплаты");
Поле = МетаданныеТаблицЗапроса.НайтиПоле(Описание.Поля, "Начисления");
ЮТест.ОжидаетЧто(Поле.ВидПоля).Равно("ВложеннаяТаблица");
ЮТест.ОжидаетЧто(Поле.Поля.Количество()).Равно(40);

ОписаниеВиртуальнойТаблицы = Поставщик.ОписаниеТаблицы(
	"РегистрСведений.КадроваяИсторияСотрудников.СрезПоследних");
ЮТест.ОжидаетЧто(ОписаниеВиртуальнойТаблицы.Параметры.Количество()).Равно(2);
```

  Проверить параметры `Период` (`ТипЗначения = ОписаниеТипов("Дата")`, `Варианты = 0`, `Поля = 0`) и `Условие` (`Поля = 24`). Проверить unknown table и case-insensitive cache key. Проверить, что два независимых provider instances не разделяют descriptor cache.

- [ ] **Step 2: Run RED**

  Expected: FAIL из-за отсутствия provider metadata.

- [ ] **Step 3: Создать metadata и реализовать provider**

  Рекурсивная conversion различает `ДоступнаяВложеннаяТаблицаСхемыЗапроса` и обычное поле. Для параметров читать только подтверждённые platform properties: `Имя`, `ТипЗначения`, `Варианты`, `ДоступныеПоля`; `ВидПараметра = Неопределено`, `Обязательный = Ложь`. Raw table/field/parameter помещается только в `ДанныеПоставщика`.

- [ ] **Step 4: Добавить provider в default composition root**

  Manager registry создаёт `Обработки.ПоставщикМетаданныхСтандартныхТаблиц.Создать()` и передаёт объект в registry до инициализации.

- [ ] **Step 5: Run GREEN, EDT revalidate, commit**

```powershell
git add QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц yaxunit/src
git commit -m "feat: provide neutral standard table metadata"
```

### Task 4: Executable-view provider adapter

**Files:**
- Create via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ПоставщикМетаданныхИсполняемыхПредставлений.mdo`
- Create via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl`
- Modify via EDT-MCP: registry manager.
- Modify via EDT-MCP: provider test module.

**Interfaces:**
- Produces provider name `ИсполняемыеПредставления`, segment `ИсполняемоеПредставление`, source kind `ИсполняемоеПредставление`.
- Consumes raw `ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмениТаблицы()` and never changes its public API.

- [ ] **Step 1: Write RED test for one real executable view**

  Use existing literal `ИсполняемоеПредставление.РегистрНакопления.СведенияОДоходахНДФЛ.НарастающиеИтоги`. Assert non-empty fields, parameter names, `ВидИсточника`, and exact identity `Описание.ДанныеПоставщика = raw description`. Unknown view returns `Неопределено`.

- [ ] **Step 2: Run RED**

- [ ] **Step 3: Implement adapter and positive converted cache**

  Convert `ПолеПредставления` to ordinary neutral fields. Convert parameter structures by their `Тип`: constant parameter maps `ТипКонстанты`, `ДоступныеЗначения`, `Обязательный`; ВТ-filter maps `ПоляФильтра`; selection maps `ДоступныеПоля`. Missing optional structure properties get neutral values through `Свойство()`.

- [ ] **Step 4: Add to composition root, run GREEN and commit**

```powershell
git add QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц yaxunit/src
git commit -m "feat: adapt executable view metadata provider"
```

### Task 5: One registry per semantic context lifecycle

**Files:**
- Modify via EDT-MCP: `QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl`
- Modify via EDT-MCP: `QueryConsoleZUP/src/CommonModules/МодельЗапросаУтилиты/Module.bsl`
- Modify via EDT-MCP: provider test module.

**Interfaces:**
- `КонтекстОбработкиВыражения(РеестрПоставщиков = Неопределено)` stores `РеестрПоставщиковМетаданныхТаблиц`.
- `КонтекстОбработкиЗапроса(РеестрПоставщиков = Неопределено)` passes through the optional registry.
- Derived context factories reuse the exact same registry object.
- `МодельЗапросаУтилиты.КонтекстОбработкиВыражения(..., РеестрПоставщиков = Неопределено)` forwards it.

- [ ] **Step 1: Write RED identity and isolation tests**

  Assert same registry identity for nested-query and virtual-parameter contexts; assert two top-level contexts have different registry objects. Assert temporary-table descriptions remain shared only where current context contract already shares them.

- [ ] **Step 2: Run RED**

- [ ] **Step 3: Replace duplicate catalog ownership**

  Remove `ДоступныеТаблицыИБ` and helper `СхемаЗапроса` from new contexts. Derived contexts call the factory with the current registry, so they do not create then discard a second registry.

- [ ] **Step 4: Run GREEN plus existing semantic tests and commit**

```powershell
git add QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl QueryConsoleZUP/src/CommonModules/МодельЗапросаУтилиты/Module.bsl yaxunit/src
git commit -m "refactor: share metadata registry across semantic contexts"
```

### Task 6: Neutral field resolution and nested dereference

**Files:**
- Modify via EDT-MCP: `QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl`
- Modify via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl`
- Modify via EDT-MCP: `yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl`

**Interfaces:**
- `НайтиПолеВИсточнике()` returns a neutral field descriptor for provider-backed sources and compatible neutral ordinary descriptors for local sources.
- `ТипЭлементаРазыменованияИзОписанияТипов(..., Контекст)` resolves reference metadata through registry; legacy `ДоступныеТаблицы` is created only when context has no registry property.
- Visitor branches on `ВидПоля`, recursively resolves `Поля`, and pushes `ОписаниеТипов("ТаблицаЗначений")` for a selected nested table.

- [ ] **Step 1: Write RED semantic tests**

  Add real query tests for `Документ.НачислениеЗарплаты.Начисления.Сотрудник`, a normal standard field, an unknown field, and an executable-view field. Expected types are hand-derived from the platform descriptor, not produced by code under test.

- [ ] **Step 2: Run RED**

- [ ] **Step 3: Implement registry-backed resolution**

  Preserve source precedence: nested query, temporary table and table-value parameter branches return before provider resolution. For named standard/executable sources call registry once. If registry exists and returns `Неопределено`, do not create a platform schema or call the legacy provider.

- [ ] **Step 4: Refactor visitor without raw platform type checks**

  Remove branches on `Тип("ДоступнаяВложеннаяТаблицаСхемыЗапроса")`; use only `ОписаниеПоля.ВидПоля`. Ordinary field dereference continues through `ОписаниеТипов.Типы()`; nested field recursion uses `МетаданныеТаблицЗапроса.НайтиПоле()`.

- [ ] **Step 5: Run GREEN, full expression-model tag and commit**

```powershell
git add QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl
git commit -m "refactor: resolve semantic fields through neutral metadata"
```

### Task 7: Source validation and executable-view conversion

**Files:**
- Modify via EDT-MCP: `QueryConsoleZUP/src/CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl`
- Modify via EDT-MCP: `yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/Module.bsl`
- Modify via EDT-MCP: provider test module.

**Interfaces:**
- `ОбработатьИсточникЗапроса()` validates every `ИсточникДанныхТаблица` through registry when registry is present.
- For `ВидИсточника = "ИсполняемоеПредставление"`, raw description comes from neutral descriptor `ДанныеПоставщика`.
- Legacy direct lookup remains only when context has no registry property.

- [ ] **Step 1: Write RED tests**

  Add unknown standard and unknown executable named sources with no referenced fields; full semantic processing must throw `Таблица <имя> не найдена`. Add context-with-registry spy returning `Неопределено` and assert legacy executable provider is not used. Preserve existing executable conversion test.

- [ ] **Step 2: Run RED**

- [ ] **Step 3: Implement strict registry path and compatibility fallback**

```bsl
Если Контекст.Свойство("РеестрПоставщиковМетаданныхТаблиц", Реестр) Тогда
	ОписаниеТаблицы = Реестр.ОписаниеТаблицы(Источник.Источник.ИмяТаблицы);
	Если ОписаниеТаблицы = Неопределено Тогда
		ВызватьИсключение "Таблица " + Источник.Источник.ИмяТаблицы + " не найдена";
	КонецЕсли;
	Если ОписаниеТаблицы.ВидИсточника <> "ИсполняемоеПредставление" Тогда
		Возврат;
	КонецЕсли;
	ОписаниеПредставления = ОписаниеТаблицы.ДанныеПоставщика;
Иначе
	// Существующий direct lookup только для legacy context.
КонецЕсли;
```

- [ ] **Step 4: Run GREEN, executable-view regression tag and commit**

```powershell
git add QueryConsoleZUP/src/CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl yaxunit/src
git commit -m "feat: validate named query sources through registry"
```

### Task 8: Builder lifecycle, local-source regressions and join topology

**Files:**
- Modify via EDT-MCP: `QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl`
- Modify via EDT-MCP: `yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/Module.bsl`
- Modify via EDT-MCP: provider test module.

**Interfaces:**
- Builder private `РеестрПоставщиковМетаданныхТаблиц` is created once in `Инициализировать()`.
- `ДобавитьИсточник()` resolves only multi-segment named sources through registry and keeps exact user error.
- Builder expression contexts receive the same registry.

- [ ] **Step 1: Write RED builder tests**

  Verify standard source, executable source, unknown source, table-value parameter, temporary table, nested query and joined source. The join test asserts both sides remain present through `МодельЗапросаУтилиты.ВсеИсточникиОператора()` and their fields resolve.

- [ ] **Step 2: Run RED**

- [ ] **Step 3: Implement one-time builder composition**

  Add private variable, initialize it once, use neutral `ВидИсточника` to select standard vs executable source construction, and use `ДанныеПоставщика` only on server for `ИсполняемоеПредставлениеПоОписанию()` and parameter setup.

- [ ] **Step 4: Run GREEN and all relevant server suites**

  Run tags `ПоставщикиМетаданныхТаблиц`, `МодельВыражений`, existing executable-view suite and applied-consumer suite. Confirm the previously skipped `ДеревоЗначений` tests remain the same known UI gap rather than a new semantic failure.

- [ ] **Step 5: Commit**

```powershell
git add QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl yaxunit/src
git commit -m "refactor: reuse metadata registry in query builder"
```

### Task 9: Diagnostic delta, runtime smoke, report and independent review

**Files:**
- Create: `docs/research/2026-08-30-metadata-provider-runtime-mcp-report.md`
- Modify only if review finds defects: files from Tasks 2–8.

**Interfaces:**
- Produces semantic acceptance evidence and MCP utility/harm report required by the spec.

- [ ] **Step 1: Re-read all changed BSL through EDT-MCP**

  Confirm current `contentHash`, exact module source, references and method structures. Run `revalidate_objects` for four production objects plus five changed consumers and two test objects.

- [ ] **Step 2: Compare diagnostic delta**

  Capture new `get_problem_summary` and `get_project_errors`; classify only new diagnostics relative to Task 1 baseline. Existing workspace errors are reported separately and do not count as introduced regressions.

- [ ] **Step 3: Run final YAxUnit gate**

  Run all affected suites through EDT-MCP. Record exact test totals, failures, skipped tests and launch configuration used.

- [ ] **Step 4: Run runtime smoke only after loaded extension is confirmed**

  Reuse `runtime.ensure(mode="experiment")`; do not call `runtime.close`. Probe one standard table, one executable view, one repeated lookup and one unknown table. If the current infobase has not received the semantic extension revision, record `stale extension` and do not interpret probe failure as a code regression.

- [ ] **Step 5: Write MCP report**

  Include the already observed frontend-contract defect: BSL `code.run_inline` advertises `outputs`, but the service rejects BSL outputs with `invalid_request`; messages work when `outputs` is omitted. Include the earlier 10-second control timeout, benefit of platform-property probes, absence of public object-module hot reload, and comparison with EDT/YAxUnit. Exclude credentials, PIDs and business data.

- [ ] **Step 6: Independent review**

  Request review of the complete diff against the spec, with special attention to cache ownership, no negative cache, fallback boundary, local-source precedence, nested fields, join traversal and accidental `КОНС_` production names. Apply only verified findings and rerun affected tests.

- [ ] **Step 7: Final repository verification**

```powershell
git diff --check master...HEAD
git status --short --branch
rg -n "КОНС_(РеестрПоставщиков|ПоставщикМетаданных|МетаданныеТаблицЗапроса)|ПоставщикМетаданныхВременныхТаблиц" QueryConsoleZUP/src
```

  Expected: diff check clean; no production objects with forbidden prefix; no temporary-table provider; only documented files changed.

- [ ] **Step 8: Commit verification/report fixes**

```powershell
git add docs/research QueryConsoleZUP/src yaxunit/src
git commit -m "test: verify metadata provider semantics"
```
