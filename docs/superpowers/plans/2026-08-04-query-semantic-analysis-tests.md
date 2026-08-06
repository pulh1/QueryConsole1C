# Query Semantic Analysis Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить 122–156 устойчивых YAxUnit matrix cases публичного семантического контракта выражений QueryConsoleZUP и отдельный opt-in RED-набор будущей семантики без изменения production-кода.

**Architecture:** Зелёные тесты вызывают `ОбработкаМоделиЗапроса.ОбработатьВыражение`, строят входной AST через `ЭлементыМоделиЗапроса.Новый*` и проверяют только type sets, parameter/source bindings, flags и смысловые ошибки. Pure, synthetic-source, metadata-backed и parser-to-semantic lanes находятся в четырёх отдельных project-local common modules с именованными YAxUnit-наборами и запускаются независимо точным параметром `modules=[...]`; доказанные будущие контракты находятся в пятом модуле, который регистрируется только по точному module filter.

**Tech Stack:** 1C:Enterprise 8.3.24, EDT 2026.1, BSL, YAxUnit 25.12, EDT-MCP, расширения `QueryConsoleZUP` и `yaxunit`.

## Global Constraints

- Production-проект `QueryConsoleZUP` не изменять: этот план добавляет только тесты и документацию.
- Production parser и visitor не исправлять даже при подтверждении дефекта.
- Все изменения metadata и BSL в EDT-проектах выполнять через EDT-MCP; обычные Markdown-файлы изменять точечно.
- Каждый запуск YAxUnit обязан задавать `updateBeforeLaunch=true` и `updateScope="extension:yaxunit"`.
- Не вызывать `clean_project`, full rebuild, update scope `all` или обновление всей конфигурации.
- Тесты добавлять пакетами: один точечный preflight run, затем один module-level run на задачу.
- Все четыре green semantic modules всегда должны быть зелёными и независимо
  запускаемыми точным `modules=[...]` фильтром.
- Opt-in future-semantic module не регистрирует тесты без точного module filter.
- Metadata-backed cases используют только metadata `Справочник.Организации` и не читают и не записывают прикладные данные.
- Не фиксировать parser topology, callback order, visitor stack, порядок типов в `ОписаниеТипов` или строковое представление типа.
- Если зелёный case обнаруживает новый production defect, сохранить RED evidence, остановить задачу и запросить отдельное решение; не ослаблять assertion.
- Политики совместимости операндов и конфликтующих ограничений параметра являются decision gates и не выбираются исполнителем.
- Канонизация регистра `ИмяПоля` является отдельным decision gate: зелёные
  source cases используют только канонический вход `ИНН`, фиксируют
  идентификатор источника и ключ `<идентификатор>.ИНН`, но ничего не
  утверждают о mixed-case вариантах.
- Перед итоговым утверждением покрытия привлечь независимого reviewer, не участвовавшего в реализации пакетов.
- Task 1 имеет ровно три независимо проверенных sibling-extension EDT false
  positives `undefined-variable` на строках 25, 34 и 36 нового pure module.
  Узкое исключение действует только при exact marker identity/count, изолированном
  delta без иных новых `ERROR/CRITICAL/MAJOR`, smoke 1/1 и точной metadata
  registration; любое изменение снова закрывает diagnostic gate. Это не общий
  allowlist и не переносится на следующие пакеты автоматически.
- Task 2 после отдельного review заменяет Task 1 line set ровно 11 markers для
  source hash `a637fd98c0974bfc`: `МодельЗапросаТипы` line 35;
  `ЭлементыМоделиЗапроса` lines 76/78/87/88/125/131/137/145/155;
  `ОбработкаМоделиЗапроса` line 157. Разрешение требует exact 12/12 run и
  isolated delta `556→572` без изменения BLOCKER/CRITICAL/MAJOR. Оно не
  наследуется Task 3 и автоматически закрывается при любом drift.
- После создания каждого common module сверять EDT metadata discovery с
  `Configuration.mdo`: новый reference должен присутствовать ровно один раз,
  а набор существовавших registrations не должен сокращаться или получать
  дубликаты.

---

## File Map

**Create via EDT-MCP:**

- `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/КОНС_ОМ_ОбработкаМоделиЗапроса.mdo` — metadata зелёного server common module.
- `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl` — pure lane и именованный набор `СемантикаЧистыеВыражения`.
- `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИсточники/` — synthetic-source lane и набор `СемантикаСинтетическиеИсточники`.
- `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные/` — metadata-backed lane и набор `СемантикаМетаданные`.
- `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция/` — parser-to-semantic lane и набор `СемантикаИнтеграцияПарсер`.
- `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика/КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика.mdo` — metadata opt-in RED common module.
- `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика/Module.bsl` — только явно выбранные future contracts.

**Modify:**

- `yaxunit/src/Configuration/Configuration.mdo` — регистрации пяти project-local common modules, создаваемые EDT metadata operation.
- `yaxunit/UPSTREAM.md` — перечисление новых project-local additions.

**Create:**

- `docs/superpowers/matrices/2026-08-04-query-semantic-analysis-tests.md` — связь callback/branch → case → статус → evidence.

**Read-only production interfaces:**

- `QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl:772` — `ОбработатьВыражение(Выражение, Контекст, РассчитываемыеСвойства, Посетитель = Неопределено)`.
- `QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl:5` — `КонтекстОбработкиВыражения()`.
- `QueryConsoleZUP/src/CommonModules/ЭлементыМоделиЗапроса/Module.bsl` — `Новый*` model factories.
- `QueryConsoleZUP/src/CommonModules/МодельЗапросаТипы/Module.bsl:31` — `СодержитПроизвольныйТип(ТипЗначения)`.

## Independent lane commands

Каждая зелёная дорожка выполняется отдельным точным вызовом:

```text
run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  extensions=["YAXUNIT"],
  modules=["КОНС_ОМ_ОбработкаМоделиЗапроса"],
  updateBeforeLaunch=true, updateScope="extension:yaxunit", timeout=60)

run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  extensions=["YAXUNIT"],
  modules=["КОНС_ОМ_ОбработкаМоделиЗапросаИсточники"],
  updateBeforeLaunch=true, updateScope="extension:yaxunit", timeout=60)

run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  extensions=["YAXUNIT"],
  modules=["КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные"],
  updateBeforeLaunch=true, updateScope="extension:yaxunit", timeout=60)

run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  extensions=["YAXUNIT"],
  modules=["КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция"],
  updateBeforeLaunch=true, updateScope="extension:yaxunit", timeout=60)
```

Нельзя заменять их одним общим запуском: в evidence должны остаться отдельные
total/passed/failed/errors для pure, synthetic-source, metadata-backed и
parser-to-semantic lanes.

---

### Task 1: Runtime preflight, metadata scaffold and one smoke case

**Files:**

- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/КОНС_ОМ_ОбработкаМоделиЗапроса.mdo`
- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`
- Modify: `yaxunit/src/Configuration/Configuration.mdo`
- Modify: `yaxunit/UPSTREAM.md`

**Interfaces:**

- Consumes: `ЭлементыМоделиЗапроса.НовыйКонстанта()`, `ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса()`, `ОбработкаМоделиЗапроса.ОбработатьВыражение(...)`.
- Produces: private helpers `НовыйУзелКонстанты(Значение)`,
  `ОбработатьУзел(Узел, Контекст = Неопределено)`,
  `ПроверитьТипы(ОписаниеТипов, ОжидаемыеТипы, ОписаниеПроверки)` used by
  Tasks 2–5. Other lanes keep equivalent helpers private in their own modules
  so they remain independently runnable.

- [ ] **Step 1: Verify the live EDT projects and baseline diagnostics without modifying them**

Use EDT-MCP `list_projects` and require both `QueryConsoleZUP` and `yaxunit` to
be `ready`. Capture both diagnostic views before any change:

```text
get_problem_summary(projectName="yaxunit")
get_project_errors(projectName="yaxunit", limit=1000,
                   responseFormat="detailed")
```

Save severity totals and the complete marker set with check id, object/file and
line. Read `yaxunit/src/Configuration/Configuration.mdo`, obtain the current
common-module list through EDT-MCP and reconcile the existing project-local
module registrations before creating anything. Do not run build, clean or
tests.

- [ ] **Step 2: Verify exact production symbols through EDT-MCP**

Read the signatures of:

```bsl
ЭлементыМоделиЗапроса.НовыйКонстанта()
ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса()
ОбработкаМоделиЗапроса.ОбработатьВыражение(
    Выражение,
    Контекст,
    РассчитываемыеСвойства,
    Посетитель = Неопределено)
```

If any signature differs, stop and update the design/plan before creating metadata.

- [ ] **Step 3: Create the green server common module through EDT-MCP**

Create `CommonModule.КОНС_ОМ_ОбработкаМоделиЗапроса` in project `yaxunit` with the same execution properties as `КОНС_Обр_Парсер_МО`: non-global, server enabled, non-privileged, no server-call export. Confirm the exact metadata name using `get_metadata_details`; this check prevents the previously observed class of invalid-module-name errors.

- [ ] **Step 4: Write the smoke registration and helpers through EDT-MCP**

Use this initial module body:

```bsl
#Область ТестовыйИнтерфейс

Процедура ИсполняемыеСценарии() Экспорт

    ЮТТесты
        .ДобавитьТестовыйНабор("СемантикаЧистыеВыражения")
            .Тег("СемантикаЧистая")
            .ДобавитьСерверныйТест("ВыводТипаЧисловойКонстанты");

КонецПроцедуры

Процедура ВыводТипаЧисловойКонстанты() Экспорт

    Результат = ОбработатьУзел(НовыйУзелКонстанты(1));
    ПроверитьТипы(Результат.ТипЗначения, МассивТипов(Тип("Число")),
        "Числовая константа должна иметь тип Число");

КонецПроцедуры

#КонецОбласти

#Область СлужебныеПроцедурыИФункции

Функция НовыйУзелКонстанты(Значение)
    Узел = ЭлементыМоделиЗапроса.НовыйКонстанта();
    Узел.Значение = Значение;
    Возврат Узел;
КонецФункции

Функция ОбработатьУзел(Узел, Контекст = Неопределено)
    Если Контекст = Неопределено Тогда
        Контекст = Новый Структура;
    КонецЕсли;
    Результат = ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса();
    Результат.Значение = Узел;
    ОбработкаМоделиЗапроса.ОбработатьВыражение(Узел, Контекст, Результат);
    Возврат Результат;
КонецФункции

Функция МассивТипов(
    Тип1,
    Тип2 = Неопределено,
    Тип3 = Неопределено,
    Тип4 = Неопределено)

    Результат = Новый Массив;
    Результат.Добавить(Тип1);
    Если Тип2 <> Неопределено Тогда
        Результат.Добавить(Тип2);
    КонецЕсли;
    Если Тип3 <> Неопределено Тогда
        Результат.Добавить(Тип3);
    КонецЕсли;
    Если Тип4 <> Неопределено Тогда
        Результат.Добавить(Тип4);
    КонецЕсли;
    Возврат Результат;
КонецФункции

Процедура ПроверитьТипы(ОписаниеТипов, ОжидаемыеТипы, ОписаниеПроверки)
    ЮТест.ОжидаетЧто(ОписаниеТипов.Типы().Количество())
        .Равно(ОжидаемыеТипы.Количество(), ОписаниеПроверки);
    Для Каждого ОжидаемыйТип Из ОжидаемыеТипы Цикл
        ЮТест.ОжидаетЧто(ОписаниеТипов.СодержитТип(ОжидаемыйТип))
            .ЭтоИстина(ОписаниеПроверки);
    КонецЦикла;
КонецПроцедуры

#КонецОбласти
```

- [ ] **Step 5: Confirm metadata registration and update the vendoring manifest**

Verify through EDT-MCP `get_metadata_details`, `list_modules` and
`get_module_structure` that
`CommonModule.КОНС_ОМ_ОбработкаМоделиЗапроса` exists and its BSL module is
discoverable. Re-read `Configuration.mdo` and prove that the new common-module
reference is present exactly once, while every preflight registration remains
present exactly once. A missing or duplicate registration blocks the smoke
run. Add the name to the project-local additions list in `yaxunit/UPSTREAM.md`.
Do not reformat the rest of either file.

- [ ] **Step 6: Run only the smoke test with incremental extension update**

Run:

```text
run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  extensions=["YAXUNIT"],
  tests=["КОНС_ОМ_ОбработкаМоделиЗапроса.ВыводТипаЧисловойКонстанты"],
  updateBeforeLaunch=true,
  updateScope="extension:yaxunit",
  timeout=60
)
```

Expected: exactly one test discovered and passed. Zero discovered tests is a failure. Any invalid-module-name error blocks the task and must be diagnosed in metadata registration; do not work around it in production.

- [ ] **Step 7: Compare diagnostics incrementally**

Repeat both
`get_problem_summary(projectName="yaxunit")` and
`get_project_errors(projectName="yaxunit", limit=1000,
responseFormat="detailed")`. Compare the complete marker identities, not only
totals. New errors in the added module are not acceptable except the exact three
Task 1 sibling-extension markers fixed by the global constraint above: lines 25
and 34 for `ЭлементыМоделиЗапроса`, line 36 for
`ОбработкаМоделиЗапроса`, all check `undefined-variable`. Accept them only when
their exact messages/count/positions match, the isolated delta contains no other
new `ERROR/CRITICAL/MAJOR`, and the 1/1 smoke executes the references. Existing
unrelated diagnostics are recorded, not attributed to this task. Recheck the
exact-once `Configuration.mdo` registration after the incremental update.

- [ ] **Step 8: Commit the independently usable smoke slice**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса yaxunit/src/Configuration/Configuration.mdo yaxunit/UPSTREAM.md
git commit -m "test: add semantic analysis smoke coverage"
```

---

### Task 2: Complete the 12-case vertical slice

**Files:**

- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`

**Interfaces:**

- Consumes: Task 1 helpers.
- Produces: `НовыйУзелПараметра`, `НовыйБинарныйУзел`, `ПроверитьПараметр` and the first 12-row coverage slice.

- [ ] **Step 1: Add reusable AST builders**

```bsl
Функция НовыйУзелПараметра(Имя)
    Узел = ЭлементыМоделиЗапроса.НовыйПараметрЗапроса();
    Узел.Имя = Имя;
    Возврат Узел;
КонецФункции

Функция НовыйБинарныйУзел(Операция, ЛеваяЧасть, ПраваяЧасть)
    Узел = ЭлементыМоделиЗапроса.НовыйБинарнаяОперация();
    Узел.Операция = Операция;
    Узел.ЛеваяЧасть = ЛеваяЧасть;
    Узел.ПраваяЧасть = ПраваяЧасть;
    Возврат Узел;
КонецФункции

Процедура ПроверитьПараметр(Результат, Имя, ОжидаемыеТипы, ЭтоСписокЗначений = Ложь)
    ОписаниеПараметра = Результат.ПараметрыЗапроса.Получить(ВРег(Имя));
    ЮТест.ОжидаетЧто(ОписаниеПараметра).НеРавно(Неопределено,
        "Параметр должен быть собран семантическим анализом");
    ЮТест.ОжидаетЧто(ОписаниеПараметра.Имя).Равно(Имя);
    ЮТест.ОжидаетЧто(ОписаниеПараметра.ЭтоСписокЗначений).Равно(ЭтоСписокЗначений);
    Если ОжидаемыеТипы <> Неопределено Тогда
        ПроверитьТипы(ОписаниеПараметра.ТипЗначения, ОжидаемыеТипы,
            "Параметр должен получить ожидаемые ограничения типа");
    КонецЕсли;
КонецПроцедуры
```

- [ ] **Step 2: Register the remaining vertical-slice cases as one batch**

Add parameterized primitive constants for `Строка`, `Булево` and `Дата`, then tests for:

```text
ПараметрБезОграниченияИмеетПроизвольныйТип
АрифметикаВыводитТипПараметра
СравнениеВозвращаетБулево
ЛогическаяОперацияВыводитБулевоДляПараметра
ПриведениеВозвращаетЗаданныйТип
ВыборОбъединяетТипыВетвей
МинимумСохраняетТипАргумента
СуммаВозвращаетЧислоИОтмечаетАгрегат
```

For arbitrary type use:

```bsl
ЮТест.ОжидаетЧто(МодельЗапросаТипы.СодержитПроизвольныйТип(Результат.ТипЗначения))
    .ЭтоИстина("Свободный параметр должен сохранять произвольный тип");
```

Do not assert `Тип("Массив")` directly. Вместе с четырьмя строками primitive
constants перечисленные восемь cases дают ровно 12 строк vertical slice.

- [ ] **Step 3: Run the whole green semantic module once**

Run the same incremental call as Task 1 with:

```text
modules=["КОНС_ОМ_ОбработкаМоделиЗапроса"]
```

Expected: all registered cases pass; the future-semantic module is not yet present.

- [ ] **Step 3a: Reconcile the Task 2 diagnostic boundary**

For live source hash `a637fd98c0974bfc`, require exactly 11
`undefined-variable [Сервер]` markers: `МодельЗапросаТипы` line 35;
`ЭлементыМоделиЗапроса` lines 76, 78, 87, 88, 125, 131, 137, 145, 155;
`ОбработкаМоделиЗапроса` line 157. The saved module run must be 12/12 and every
flagged reference must be exercised. Diagnostic delta must be exactly
`556→572`: `ERRORS 4→12`, `MINOR 427→435`, with unchanged BLOCKER 86,
CRITICAL 6 and MAJOR 27 and unchanged CRITICAL/MAJOR identity sets. This narrow
set replaces Task 1 positions for Task 2 only; it is not inherited by Task 3.
Any mismatch blocks commit and requires a new independent review.

- [ ] **Step 4: Commit the vertical slice**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl
git commit -m "test: cover semantic analysis vertical slice"
```

---

### Task 3: Expand pure constants, operations and parameter inference to 34–40 cases

**Files:**

- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`

**Interfaces:**

- Consumes: `НовыйУзелКонстанты`, `НовыйУзелПараметра`, `НовыйБинарныйУзел`, `ОбработатьУзел`, `ПроверитьТипы`, `ПроверитьПараметр`.
- Produces: green coverage for binary, unary, logical and parameter branches of the visitor.

- [ ] **Step 1: Add the pure-operation matrix as parameterized cases**

Cover exactly the supported green contract:

```text
constants: Число, Строка, Булево, Дата, Null, Неопределено
arithmetic: +, -, *, /
comparisons: =, <>, >, <, >=, <=
logical: И, ИЛИ, НЕ
unary: + and -
parameter inference: binary left, binary right, МЕЖДУ bounds, В scalar list,
                     В single-parameter list, НЕ, unary, ПОДОБНО
repeatability: success after success, success after caught semantic error
```

Use only valid operand combinations. `%` is excluded from green coverage and belongs to Task 10.

- [ ] **Step 2: Assert side effects in the same cases**

For every parameter case verify uppercase-insensitive lookup through `Получить(ВРег(Имя))`, original `Имя`, inferred type set and `ЭтоСписокЗначений`. Verify that pure cases leave `ПоляИсточников` empty and both flags false unless the case is an aggregate.

For the caught-error repeatability case use `Попытка/Исключение`, assert that
the first call contains `Не корректный тип условия`, then process a numeric
constant in a fresh wrapper and assert `{Число}`.

- [ ] **Step 3: Run the full green semantic module incrementally**

Use `modules=["КОНС_ОМ_ОбработкаМоделиЗапроса"]` and
`updateScope="extension:yaxunit"`.

Expected: 34–40 cumulative pure matrix cases pass. Record the exact YAxUnit total because parameter rows, not procedure count, define coverage.

- [ ] **Step 4: Commit the pure matrix**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl
git commit -m "test: cover semantic operations and parameters"
```

---

### Task 4: Add operators, lists, casts and CASE (18–22 cases)

**Files:**

- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`

**Interfaces:**

- Consumes: existing pure builders and public factories `НовыйОператорМежду`, `НовыйОператорПроверкиТипа`, `НовыйОператорПроверкиНаNULL`, `НовыйСписокВыражений`, `НовыйОператорВ`, `НовыйОператорПодобно`, `НовыйПриведениеТипа`, `НовыйВыбор`, `НовыйАльтернативаВыбора`.
- Produces: green result-type and parameter-side-effect coverage for these node kinds.

- [ ] **Step 1: Add operator and list cases**

Cover:

```text
МЕЖДУ; ЕСТЬ NULL; ЕСТЬ НЕ NULL; type check;
single-element list preserves its element type;
multi-element list returns СписокЗначений;
В with list; В with one list parameter and ЭтоСписокЗначений=Истина;
ПОДОБНО with constants and with two parameters.
```

- [ ] **Step 2: Add cast cases**

Parameterize primitive casts to `Булево`, `Дата`, `Число` and `Строка`. Do not include reference casts here; they belong to metadata-backed coverage.

- [ ] **Step 3: Add CASE union cases**

Cover one alternative, multiple alternatives, with and without `Иначе`, equal action types and different action types. Assert type sets only; do not assert branch traversal order. Do not add a non-Boolean condition case until the operand compatibility decision gate is resolved.

- [ ] **Step 4: Run one module-level incremental batch and commit**

Expected: all green tests pass.

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl
git commit -m "test: cover semantic operators casts and case"
```

---

### Task 5: Add aggregates and built-ins (26–32 cases)

**Files:**

- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`

**Interfaces:**

- Consumes: public aggregate and function factories in `ЭлементыМоделиЗапроса`.
- Produces: type and flag coverage for every function node supported by `ОбходМоделиЯзыкаВыражений`.

- [ ] **Step 1: Cover aggregate branches**

Parameterize:

```text
МИНИМУМ and МАКСИМУМ preserve argument type;
СУММА and СРЕДНЕЕ return Число;
КОЛИЧЕСТВО(*) and КОЛИЧЕСТВО(argument) return Число;
every aggregate sets ИспользуетсяАгрегатнаяФункция=Истина.
```

- [ ] **Step 2: Cover date-part result types**

For `ГОД`, `КВАРТАЛ`, `МЕСЯЦ`, `ДЕНЬГОДА`, `ДЕНЬ`, `ДЕНЬМЕСЯЦА`, `ДЕНЬНЕДЕЛИ`, `ЧАС`, `МИНУТА`, `СЕКУНДА`, pass a Date constant and assert only the numeric result. Parameter inference for these functions is a known RED gap and is not asserted green.

- [ ] **Step 3: Cover the remaining supported functions**

Cover:

```text
НАЧАЛОПЕРИОДА and КОНЕЦПЕРИОДА -> Дата;
ДОБАВИТЬКДАТЕ -> Дата and parameter constraints Date/Number;
ДАТАВРЕМЯ -> Дата;
ЕСТЬNULL equal and mixed argument types -> union type set;
ПРЕДСТАВЛЕНИЕ and ПРЕДСТАВЛЕНИЕССЫЛКИ -> Строка;
ТИПЗНАЧЕНИЯ and ТИП -> Тип;
РАЗНОСТЬДАТ -> Число and two Date parameter constraints.
```

Do not add `ПОДСТРОКА`: its AST node is not dispatched and belongs to Task 10. Keep `ЗНАЧЕНИЕ` reference cases in Task 7 because they depend on metadata.

- [ ] **Step 4: Run one module-level incremental batch and commit**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl
git commit -m "test: cover semantic aggregates and builtins"
```

---

### Task 6: Add synthetic source and dereference coverage (18–24 cases)

**Files:**

- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИсточники/КОНС_ОМ_ОбработкаМоделиЗапросаИсточники.mdo`
- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИсточники/Module.bsl`
- Modify: `yaxunit/src/Configuration/Configuration.mdo`
- Modify: `yaxunit/UPSTREAM.md`

**Interfaces:**

- Consumes: source, query-column, temporary-table and dereference factories from `ЭлементыМоделиЗапроса`.
- Produces: named suite `СемантикаСинтетическиеИсточники`,
  `НовыйSyntheticКонтекст`, `ДобавитьSyntheticИсточник`,
  `НовыйУзелРазыменования` and assertions for stable source binding.

- [ ] **Step 1: Add explicit synthetic context builders**

Create the module through EDT-MCP and register a named suite
`СемантикаСинтетическиеИсточники`. The context builder must start from the
public production context so nested-query traversal receives every required
property, then reset the mutable maps to a controlled state:

```bsl
Функция НовыйSyntheticКонтекст()
    Контекст = ОбработкаМоделиЗапроса.КонтекстОбработкиВыражения();
    Контекст.ИндексЗапросаПакета = 0;
    Контекст.ИспользуемыеТаблицы.Очистить();
    Контекст.ИсточникиПоИдентификаторам.Очистить();
    Контекст.ИдентификаторыИсточниковВнешнегоЗапроса.Очистить();
    Контекст.ОписанияВременныхТаблиц.Очистить();
    Контекст.ДоступныПсевдонимыИсточников = Истина;
    Контекст.ДоступныИсточникиВнешнегоЗапроса = Истина;
    Контекст.ЗаполнятьОписаниеВременныхТаблиц = Ложь;
    Возврат Контекст;
КонецФункции
```

Do not replace `ДоступныеТаблицыИБ` or `__СхемаЗапрос`: they are initialized by
`КонтекстОбработкиВыражения()` and read by
`КонтекстОбработкиВложенногоЗапроса`. Before registering the first case, assert
in the fixture smoke that `ИндексЗапросаПакета`, `ОписанияВременныхТаблиц`,
`ДоступныеТаблицыИБ` and `__СхемаЗапрос` are available. If production adds
another required property, document the exact read site and initialize it
without invoking the parser.

- [ ] **Step 2: Cover nested-query and temporary-table sources**

Create query columns and VT column mappings in memory. Cover explicit alias,
unqualified unique field, missing field, ambiguous field across two sources,
field type and `ПоляИсточников` binding. The green explicit-alias case must use
only canonical input field name `ИНН` and assert all three independently:

```text
ПолеИсточника.ИдентификаторИсточника = <идентификатор fixture source>
ПолеИсточника.ИмяПоля = "ИНН"
ПоляИсточников contains "<идентификатор>.ИНН" -> "ИНН"
```

Do not add any mixed-case green case. Preservation/canonicalization remains
only a decision-gated matrix row.

- [ ] **Step 3: Cover external-source behavior and nested query in `В`**

Mark one source identifier in `ИдентификаторыИсточниковВнешнегоЗапроса` and
assert `ИспользуютсяИсточникиВнешнегоЗапроса=Истина`. Cover unavailable
external source as an error.

Register a separate case named
`ВложенныйЗапросВОператореВОбрабатываетсяПосетителем`: create
`ВложенныйЗапрос = ЭлементыМоделиЗапроса.НовыйЗапросВыбора()`, add at least
one valid `ЭлементыМоделиЗапроса.НовыйОператорЗапроса()` with a selected
in-memory expression to `ВложенныйЗапрос.Операторы`, and assign that
`ЗапросВыбора` directly to `ОператорВ.Список`. Run it with
`НовыйSyntheticКонтекст()`, assert the Boolean outer result and the nested
query's public enriched column effects. Do not wrap this node in
`НовыйИсточникДанныхВложенныйЗапрос`: that factory is valid only for a source
inside `ИЗ`. This case is the direct evidence for the 59th callback
`ПосетитьВложенныйЗапрос`; it must be a distinct matrix row, not merely part of
generic `В` coverage.

- [ ] **Step 4: Run one module-level incremental batch and commit**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИсточники yaxunit/src/Configuration/Configuration.mdo yaxunit/UPSTREAM.md
git commit -m "test: cover semantic synthetic source resolution"
```

Run the lane with
`modules=["КОНС_ОМ_ОбработкаМоделиЗапросаИсточники"]` and the mandatory
incremental parameters from **Independent lane commands**.

---

### Task 7: Add minimal metadata-backed coverage (10–14 cases)

**Files:**

- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные/КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные.mdo`
- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные/Module.bsl`
- Modify: `yaxunit/src/Configuration/Configuration.mdo`
- Modify: `yaxunit/UPSTREAM.md`

**Interfaces:**

- Consumes: `ОбработкаМоделиЗапроса.КонтекстОбработкиВыражения()`, real metadata table `Справочник.Организации` and its verified fields.
- Produces: named suite `СемантикаМетаданные` and metadata-backed evidence
  without any data access.

- [ ] **Step 1: Reconfirm the metadata fixture through EDT-MCP**

Before writing tests, require `Catalog.Организации` and fields `ИНН`, `ЕстьОбособленныеПодразделения`, `ГоловнаяОрганизация` to exist with types String, Boolean and `CatalogRef.Организации`. If the base configuration changed, stop and revise the fixture in the design rather than silently choosing another business object.

- [ ] **Step 2: Add a context helper that registers one real table source**

Create the module through EDT-MCP, register the named suite
`СемантикаМетаданные`, then use `КонтекстОбработкиВыражения()`, create
`Источник` plus `ИсточникДанныхТаблица` with
`ИмяТаблицы="Справочник.Организации"` and alias `Организации`, and insert it
into both source maps by alias and identifier.

- [ ] **Step 3: Add metadata-backed cases**

Cover:

```text
Организации.Ссылка -> СправочникСсылка.Организации;
Организации.ИНН -> Строка;
Организации.ЕстьОбособленныеПодразделения -> Булево;
Организации.ГоловнаяОрганизация -> СправочникСсылка.Организации;
Организации.ГоловнаяОрганизация.ИНН -> Строка;
unqualified unique ИНН;
missing field;
unknown table alias;
reference cast to Справочник.Организации;
ЗНАЧЕНИЕ(Справочник.Организации.ПустаяСсылка).
```

Add up to four rows only when required to cover a distinct metadata utility branch. Do not broaden the fixture to another configuration object merely to increase the count.

For every resolved field use the canonical fixture spelling (`ИНН`,
`ГоловнаяОрганизация`) and assert the fixture source identifier, the matching
uppercase `ПоляИсточников` key and the same canonical spelling in
`ПолеИсточника.ИмяПоля`/map value. Do not add a mixed-case green assertion;
both preservation and conversion scenarios belong only to the canonicalization
decision gate.

- [ ] **Step 4: Run one module-level incremental batch and confirm no data writes**

Run with `modules=["КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные"]` and all
mandatory incremental parameters from **Independent lane commands**. Do not
add `.ВТранзакции()` because these tests perform no data operations.

- [ ] **Step 5: Commit the metadata-backed slice**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные yaxunit/src/Configuration/Configuration.mdo yaxunit/UPSTREAM.md
git commit -m "test: cover semantic metadata resolution"
```

---

### Task 8: Add stable semantic error coverage (8–12 cases)

**Files:**

- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИсточники/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные/Module.bsl`

**Interfaces:**

- Consumes: pure, synthetic and metadata fixtures from earlier tasks.
- Produces: lane-local `ПроверитьСемантическуюОшибку(Узел, Контекст,
  ФрагментСообщения)` without introducing dependencies between test modules.

- [ ] **Step 1: Add an exception helper based on BSL `Попытка/Исключение`**

```bsl
Процедура ПроверитьСемантическуюОшибку(Узел, Контекст, ФрагментСообщения)
    ИсключениеПолучено = Ложь;
    Попытка
        ОбработатьУзел(Узел, Контекст);
    Исключение
        ИсключениеПолучено = Истина;
        ЮТест.ОжидаетЧто(СтрНайти(ОписаниеОшибки(), ФрагментСообщения) > 0)
            .ЭтоИстина("Семантическая ошибка должна содержать ожидаемый смысловой фрагмент");
    КонецПопытки;
    ЮТест.ОжидаетЧто(ИсключениеПолучено)
        .ЭтоИстина("Ожидалось исключение семантического анализа");
КонецПроцедуры
```

- [ ] **Step 2: Register only stable error contracts**

Cover non-Boolean logical operands, non-Boolean query condition through `ОбработатьВыражениеУсловие`, missing and ambiguous synthetic fields, unknown alias, impossible dereference, unknown reference type, unsupported AST node and list-valued selected field through `ОбработатьВыражениеВыбираемогоПоля`.

Place every error in the lane owning its fixture: pure contract errors in
`КОНС_ОМ_ОбработкаМоделиЗапроса`, source-resolution errors in
`...Источники`, metadata-only errors in `...Метаданные`. Do not add operand
compatibility, conflicting-parameter or field-canonicalization cases here;
they remain decision gates.

- [ ] **Step 3: Run the three affected lanes independently and commit**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИсточники/Module.bsl yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные/Module.bsl
git commit -m "test: cover stable semantic errors"
```

Run the three affected module filters separately and preserve three reports;
do not merge them into one broad filter.

---

### Task 9: Add the parser-to-semantic handshake (8–12 cases)

**Files:**

- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция/КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция.mdo`
- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция/Module.bsl`
- Modify: `yaxunit/src/Configuration/Configuration.mdo`
- Modify: `yaxunit/UPSTREAM.md`

**Interfaces:**

- Consumes: `ОбработкаМоделиЗапроса.РазобратьЗапрос(ТекстЗапроса)`.
- Produces: named suite `СемантикаИнтеграцияПарсер` and minimal integration
  evidence that parser output is accepted by semantic processing.

- [ ] **Step 1: Add short whole-query cases**

Create the module through EDT-MCP, register the named suite
`СемантикаИнтеграцияПарсер`, then use only compact queries whose semantic
expectation is independent of parser recursion topology:

```text
ВЫБРАТЬ 1 КАК Значение
ВЫБРАТЬ 1 + 2 КАК Значение
ВЫБРАТЬ ВЫБОР КОГДА ИСТИНА ТОГДА 1 ИНАЧЕ 2 КОНЕЦ КАК Значение
ВЫБРАТЬ СУММА(1) КАК Значение
ВЫБРАТЬ Организации.ИНН ИЗ Справочник.Организации КАК Организации
ВЫБРАТЬ Организации.ГоловнаяОрганизация.ИНН ИЗ Справочник.Организации КАК Организации
ВЫБРАТЬ 1 КАК Значение ПОМЕСТИТЬ ВТ; ВЫБРАТЬ ВТ.Значение ИЗ ВТ КАК ВТ
ВЫБРАТЬ 1 КАК Значение ОБЪЕДИНИТЬ ВСЕ ВЫБРАТЬ 2 КАК Значение
```

Additional rows may cover a parameter or nested query, but total handshake count must remain at most 12.

- [ ] **Step 2: Assert only enriched public properties**

Assert package/operator/column counts needed to locate the output, then type sets, aggregate flag, parameter descriptor or resolved field identity. Do not assert the shape of intermediate binary nodes.

- [ ] **Step 3: Run one module-level incremental batch and commit**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция yaxunit/src/Configuration/Configuration.mdo yaxunit/UPSTREAM.md
git commit -m "test: add parser semantic handshake coverage"
```

Run only
`modules=["КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция"]` with the mandatory
incremental parameters from **Independent lane commands**.

---

### Task 10: Add the opt-in future-semantic RED suite

**Files:**

- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика/КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика.mdo`
- Create: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика/Module.bsl`
- Modify: `yaxunit/src/Configuration/Configuration.mdo`
- Modify: `yaxunit/UPSTREAM.md`

**Interfaces:**

- Consumes: the same public semantic entry points and model factories as the green suite.
- Produces: five unambiguous opt-in RED cases plus documented decision-gated rows.

- [ ] **Step 1: Create and verify the exact common-module metadata name through EDT-MCP**

Create server common module `КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика`. Confirm it is discoverable before writing BSL. Add it to `yaxunit/UPSTREAM.md`.

- [ ] **Step 2: Guard registration by exact module filter**

Use the established parser acceptance pattern:

```bsl
Процедура ИсполняемыеСценарии() Экспорт
    Фильтр = ЮТКонтекстСлужебный.КонтекстЧитателя().Фильтр;
    Если НЕ Фильтр.ЕстьФильтрМодулей
        ИЛИ НЕ Фильтр.Модули.Свойство("КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика") Тогда
        Возврат;
    КонецЕсли;
    ЮТТесты
        .ДобавитьТестовыйНабор("БудущаяСемантика")
            .Тег("БудущаяСемантика")
            .ДобавитьСерверныйТест("ОстатокОтДеленияВозвращаетЧисло")
            .ДобавитьСерверныйТест("ПодстрокаВозвращаетСтроку")
            .ДобавитьСерверныйТест("ЧастьПериодаВыводитТипПараметраДата")
            .ДобавитьСерверныйТест("ВсеПоляЗапросаОбрабатываютсяБезОшибки")
            .ДобавитьСерверныйТест("ВсеПоляИсточникаОбрабатываютсяБезОшибки");
КонецПроцедуры
```

- [ ] **Step 3: Implement the five unambiguous future assertions**

Expected contracts:

```text
5 % 2 -> type set {Число};
ПОДСТРОКА("abc", 1, 2) -> type set {Строка};
ГОД(&Дата) -> result {Число}, parameter Дата -> {Дата};
ВЫБРАТЬ * ИЗ Справочник.Организации -> semantic processing completes without exception.
ВЫБРАТЬ Организации.* ИЗ Справочник.Организации КАК Организации -> semantic processing completes without exception.
```

The fourth and fifth cases independently assert successful whole-query semantic
processing, not a guessed scalar `ТипЗначения` for `*` or `Источник.*`.

- [ ] **Step 4: Record, but do not execute, the three policy gates**

In the coverage matrix add:

```text
operand_compatibility: decision_required
parameter_constraint_conflict: decision_required
field_name_canonicalization: decision_required
```

For operand compatibility present exact alternatives: strict semantic error
versus current permissive behavior. For parameter conflict present exact
alternatives: semantic error, union type set, or arbitrary type. Add
`field_name_canonicalization: decision_required` with alternatives preserve
input spelling versus replace with source/metadata name. Do not register a
YAxUnit case until the user selects one alternative.

- [ ] **Step 5: Prove the normal green run excludes RED**

Run all four green lane commands separately:

```text
modules=["КОНС_ОМ_ОбработкаМоделиЗапроса"]
modules=["КОНС_ОМ_ОбработкаМоделиЗапросаИсточники"]
modules=["КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные"]
modules=["КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция"]
```

Each is a separate `run_yaxunit_tests` call with the mandatory incremental
parameters. Expected: all green tests pass and none of the five future test
names appears.

- [ ] **Step 6: Run the exact opt-in module and preserve expected RED evidence**

Run:

```text
modules=["КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика"]
updateScope="extension:yaxunit"
```

Expected current result: the five acceptance cases fail for their documented
production gaps. Record the exact total and failure summaries. Do not change
production and do not commit a weakened expectation.

- [ ] **Step 7: Commit the isolated RED suite**

```bash
git add yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика yaxunit/src/Configuration/Configuration.mdo yaxunit/UPSTREAM.md
git commit -m "test: document future semantic contracts"
```

---

### Task 11: Coverage matrix, verification and independent review

**Files:**

- Create: `docs/superpowers/matrices/2026-08-04-query-semantic-analysis-tests.md`
- Modify if review finds omissions: only the affected one of four green
  semantic modules or the opt-in RED module

**Interfaces:**

- Consumes: EDT module structure for the 59 callbacks, all implemented YAxUnit cases and their last run evidence.
- Produces: auditable coverage verdict and independent review report.

- [ ] **Step 1: Build the callback/branch matrix from the live EDT project**

Create columns:

```text
Production module | Method/branch | Expected public effect | Test method |
Matrix rows | Lane | Status | Last evidence
```

Allowed statuses are exactly:

```text
green
opt_in_red
decision_required
out_of_scope_with_reason
```

Every callback from `БинарнаяОперацияПриВходе` through
`ВыражениеВсеПоляПриВыходе` must have at least one row. Add distinct rows for
branches inside binary operations, dereference, casts, CASE, aggregates,
parameter inference and utilities.

Treat `ПосетитьВложенныйЗапрос` as the 59th callback and give it its own row
linked to `ВложенныйЗапросВОператореВОбрабатываетсяПосетителем`. Also retain a
separate branch/case row for the outer `В` operator with a nested query; neither
row may be inferred from generic source or generic `В` coverage. The fixture
column must state that `ОператорВ.Список` contains a direct `ЗапросВыбора`
created by `НовыйЗапросВыбора()` with a non-empty `Операторы`, not an
`ИсточникДанныхВложенныйЗапрос` wrapper.

- [ ] **Step 2: Reconcile the case count**

Count parameter rows as matrix cases. Require 122–156 green cases. The five
opt-in RED cases and decision-gated rows are reported separately and do not
inflate the green total. The first vertical slice remains exactly 12 cases.

- [ ] **Step 3: Run final green verification incrementally**

Run the four green module filters from **Independent lane commands** as four
separate calls with `updateScope="extension:yaxunit"`.

Expected: all green cases pass. Capture total, passed, failed and errors per
lane, then reconcile their matrix-case sum to 122–156.

- [ ] **Step 4: Re-run the opt-in RED module separately**

Expected: only the documented future contracts fail. An infrastructure error, invalid module name or zero discovered tests is not acceptable RED evidence.

- [ ] **Step 5: Compare final EDT diagnostics to the preflight baseline**

Repeat both baseline calls exactly:

```text
get_problem_summary(projectName="yaxunit")
get_project_errors(projectName="yaxunit", limit=1000,
                   responseFormat="detailed")
```

Compare the full marker identities and additionally filter/inspect every added
common module. Through `get_metadata_details`, `list_modules`,
`get_module_structure` and targeted reading of `Configuration.mdo`, verify
that all five semantic common modules are discoverable and registered exactly
once, with no pre-existing registration removed or duplicated. Report all new
errors; do not claim success based only on an unchanged total if errors moved
between files.

- [ ] **Step 6: Ask an independent reviewer for a coverage audit**

The reviewer must not have implemented any package. Give them:

- the design and this plan;
- all four green semantic test modules and the opt-in RED module;
- the coverage matrix;
- the production walker, visitor, semantic utilities and `МодельЗапросаТипы`;
- final green and opt-in RED evidence.

Require explicit answers:

```text
1. Are all 59 callbacks and meaningful branches represented?
2. Do any assertions freeze parser topology, callback order or type order?
3. Are pure, synthetic, metadata and handshake lanes correctly separated?
4. Can any metadata case read or write application data?
5. Are known gaps isolated from the green suite?
6. Are decision gates still undecided rather than silently assumed?
```

- [ ] **Step 7: Apply only test/documentation review findings and rerun affected batches**

Any proposed production fix is out of scope and requires a separate task. After test-only corrections, rerun the green semantic module and, if affected, the exact opt-in module, always with `updateScope="extension:yaxunit"`.

- [ ] **Step 8: Commit the matrix and reviewed final state**

```bash
git add docs/superpowers/matrices/2026-08-04-query-semantic-analysis-tests.md yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИсточники yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаМетаданные yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаИнтеграция yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапросаБудущаяСемантика
git commit -m "test: complete semantic analysis coverage matrix"
```

- [ ] **Step 9: Report completion accurately**

The final handoff must list changed files, green totals, opt-in RED totals, EDT diagnostic delta, independent reviewer verdict, unresolved decision gates and confirmation that no production file or full update was used.
