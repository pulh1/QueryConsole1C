# Metadata Provider UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести деревья конструктора запросов на ленивые transport-safe каталоги поставщиков метаданных без изменения существующей визуальной иерархии.

**Architecture:** Оба поставщика получают метод `ДочерниеЭлементы()`, возвращающий только простые структуры каталога. `КонструкторЗапросовФормы` создаёт серверный UI-контекст с реестром и двумя поставщиками, отображает узлы каталога и нейтральные описания полей в существующие `ДанныеФормыДерево`; формы больше не создают собственную `СхемаЗапроса`.

**Tech Stack:** 1С:Предприятие 8.3.24+, русский BSL, EDT, YAxUnit, Vanessa Automation 1.2.043.28, Vanessa MCP/client_mcp 0.6.5.

**Spec:** `docs/superpowers/specs/2026-08-30-metadata-provider-semantics-ui-design.md`

## Global Constraints

- Новая корневая группа поставщика не добавляется.
- Порядок корня: стандартные группы, `Представления`, затем условная `Временные таблицы`.
- `ДанныеПоставщика`, platform objects и stateful providers не попадают в данные формы.
- Поля таблиц и вложенные поля раскрываются лениво.
- Временные таблицы, вложенные запросы и таблицы значений остаются model-local.
- `Form.form` не изменяется без отдельного доказательства EDT inspection.
- Все BSL-записи выполняются через EDT-MCP с revision/hash guard.

---

### Task 1: Transport-safe catalog node contract

**Files:**
- Modify: `QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Produces: `МетаданныеТаблицЗапроса.НовыйЭлементКаталога(Идентификатор, ИдентификаторРодителя, ИмяТаблицы, Представление, ЭтоГруппа, ЕстьДочерние, ВидИсточника)`.
- Returns: structure with exactly `Идентификатор, ИдентификаторРодителя, ИмяТаблицы, Представление, ЭтоГруппа, ЕстьДочерние, ВидИсточника`.

- [x] **Step 1: Write the failing contract test**

Add server test `ЭлементКаталогаСодержитТолькоТранспортныеПоля`. It calls the wished-for factory, asserts the seven literal values, `Количество() = 7`, and absence of `ДанныеПоставщика`.

- [x] **Step 2: Run RED**

Run:

```text
EDT-MCP run_yaxunit_tests
tests = КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО.ЭлементКаталогаСодержитТолькоТранспортныеПоля
debug = false
updateScope = extension:QueryConsoleZUP_Semantics,extension:QueryConsoleZUP_YAxUnit
```

Expected: FAIL because `НовыйЭлементКаталога` is not defined.

- [x] **Step 3: Implement the factory**

```bsl
Функция НовыйЭлементКаталога(
    Идентификатор,
    ИдентификаторРодителя = Неопределено,
    ИмяТаблицы = Неопределено,
    Представление = "",
    ЭтоГруппа = Ложь,
    ЕстьДочерние = Ложь,
    ВидИсточника = "") Экспорт

    Возврат Новый Структура(
        "Идентификатор,ИдентификаторРодителя,ИмяТаблицы,Представление,ЭтоГруппа,ЕстьДочерние,ВидИсточника",
        Идентификатор,
        ИдентификаторРодителя,
        ИмяТаблицы,
        Представление,
        ЭтоГруппа,
        ЕстьДочерние,
        ВидИсточника);

КонецФункции
```

- [x] **Step 4: Run GREEN and re-read diagnostics**

Expected: 1 passed, 0 failed; no new EDT errors for the two modules.

- [x] **Step 5: Commit**

```powershell
git commit -am "feat: add transport-safe metadata catalog node"
```

### Task 2: Lazy standard-provider catalog

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц/ObjectModule.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Produces: `ДочерниеЭлементы(ИдентификаторРодителя = Неопределено)`.
- Root call returns the existing `СтатическиеСегменты()` in order without traversing `ДоступныеТаблицыПоставщика`.
- Segment call returns table nodes only for that segment; names ending in `.Изменения` are excluded.
- Table fields are not returned by this method.

- [x] **Step 1: Write two failing tests**

Add:

- `СтандартныйКаталогВозвращаетСтатическиеКорневыеГруппы`: root nodes equal the literal static segment list, are groups, and contain no provider data.
- `СтандартныйКаталогЛенивоВозвращаетТаблицыСегмента`: expanding `Справочник` includes leaf `Справочник.ФизическиеЛица`, while the root call contains no table leaf.

- [x] **Step 2: Run RED**

Expected: FAIL because `ДочерниеЭлементы` is absent.

- [x] **Step 3: Implement root and segment expansion**

Create catalog nodes with `МетаданныеТаблицЗапроса.НовыйЭлементКаталога`. Root identifiers are segment names. On segment expansion traverse only the selected platform group/subtree and return table identifiers/full names; do not call `ОписаниеТаблицы()`.

- [x] **Step 4: Run GREEN plus existing provider module**

Run the two new tests, then module `КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО`.

- [x] **Step 5: Commit**

```powershell
git commit -am "feat: expose lazy standard table catalog"
```

### Task 3: Lazy executable-view catalog

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Produces: `ДочерниеЭлементы(ИдентификаторРодителя = Неопределено)`.
- Root returns current executable-view groups.
- Group expansion returns child groups followed by leaf table nodes.
- Leaf nodes contain full `ИмяТаблицы`; the method never builds full table descriptions.

- [x] **Step 1: Write failing tests**

Add `КаталогИсполняемыхПредставленийСохраняетГруппыИТаблицы` and `КаталогИсполняемыхПредставленийНеРаскрываетПоляЗаранее`. Use the real provider and literal known view `ИсполняемоеПредставление.РегистрНакопления.СведенияОДоходахНДФЛ.НарастающиеИтоги`.

- [x] **Step 2: Run RED**

Expected: FAIL because `ДочерниеЭлементы` is absent.

- [x] **Step 3: Implement catalog mapping**

Map `ГруппыИсполняемыхПредставлений()`, `ИменаДочернихГрупп()`, and `ИменаТаблицПредставленийВходящихВГруппу()` to the shared seven-field node contract. Use the last identifier segment only for display.

- [x] **Step 4: Run GREEN and provider regression module**

- [x] **Step 5: Commit**

```powershell
git commit -am "feat: expose executable view catalog"
```

### Task 4: Provider-backed form facade

**Files:**
- Modify: `QueryConsoleZUP/src/CommonModules/КонструкторЗапросовФормы/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/Module.bsl`

**Interfaces:**
- Produces: server-only `НовыйКонтекстМетаданныхUI()` with `Реестр`, `СтандартныйПоставщик`, and `ПоставщикПредставлений`.
- `ДобавитьТаблицыЗапроса`, `ДобавитьТаблицу`, `ЗаполнитьДочерниеЭлементыДереваДоступныхТаблиц`, and tree mapping helpers consume this context rather than raw `ДоступныеТаблицыИБ`.
- Provider nodes are mapped to existing columns/flags; neutral fields are mapped without `ДанныеПоставщика`.

- [ ] **Step 1: Add failing server tests for pure facade boundaries**

Add tests for mapping catalog nodes and neutral fields into an intermediate row-description structure: standard group, standard table, executable group/table, nested field, and absence of raw properties. Keep actual `ДанныеФормыДерево` behavior for Vanessa because `ДеревоЗначений` does not implement `НайтиПоИдентификатору`.

- [ ] **Step 2: Run RED**

- [ ] **Step 3: Implement UI context and mapping helpers**

The context is created per server form operation and never stored in a form attribute. `ЗаполнитьДочерние...` chooses:

- standard group → standard provider catalog;
- table leaf → registry `ОписаниеТаблицы()`, then neutral fields;
- executable group → executable provider catalog;
- temporary/local source → existing local helpers;
- nested query → existing model traversal.

- [ ] **Step 4: Preserve lazy placeholders and root order**

Only add an empty child row when `ЕстьДочерние = Истина`. Add `Представления` after all standard roots. Leave temporary-table insertion to the form so it remains last and conditional.

- [ ] **Step 5: Run focused provider/facade tests and EDT diagnostics**

- [ ] **Step 6: Commit**

```powershell
git commit -am "refactor: route query constructor trees through providers"
```

### Task 5: Migrate both managed-form modules

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/КонструкторЗапросов/Module.bsl`
- Modify: `QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/РедакторВыражений/Module.bsl`
- Inspect only: corresponding `Form.form`

**Interfaces:**
- All calls to `КонструкторЗапросовФормы` use `НовыйКонтекстМетаданныхUI()`.
- Deletes private `ДоступныеТаблицыИБ()` and `_схема` ownership after the final caller is migrated.

- [ ] **Step 1: Capture EDT form/module baseline**

Read both form modules, inspect form metadata/layout and record diagnostics. Confirm existing columns and flags are sufficient; do not modify `Form.form` when confirmed.

- [ ] **Step 2: Migrate initial available-table tree**

Populate static standard roots from the standard provider, append existing `Представления`, and append `Временные таблицы` only when local descriptions exist.

- [ ] **Step 3: Migrate the six expansion call sites**

Update available tables, sources, expression editor, grouping, order/conditions, and totals secondary trees. Remove every raw `ДоступныеТаблицыИБ` argument.

- [ ] **Step 4: Migrate current-source rendering**

Use the registry-backed facade for standard tables, executable views, joins, temporary tables, table-valued parameters, and nested queries.

- [ ] **Step 5: Remove obsolete schema factory and re-search callers**

Expected: no form-owned `Новый СхемаЗапроса`, `ДоступныеТаблицыИБ()`, or `Перем _схема`.

- [ ] **Step 6: Run YAxUnit provider, consumer, and builder modules**

Run without debugger:

- `КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО`;
- `КОНС_Обр_ПрикладныеПотребителиЗапроса_МО`;
- `КОНС_Обр_ПостроениеИГенерацияЗапросов_МО`.

- [ ] **Step 7: Commit**

```powershell
git commit -am "feat: use metadata providers in query constructor UI"
```

### Task 6: Vanessa MCP UI acceptance

**Files:**
- Create: `features/СозданиеЗапросовВКонструкторе/КаталогПоставщиковМетаданных.feature`
- Reuse: `features/lib/ДобавлениеИсточникаВКонструкторе.feature`
- Reuse: `features/lib/ДобавитьПолеИсточника.feature`

**Interfaces:**
- Scenario verifies root order, lazy standard group, executable-view hierarchy, one standard source, one executable source, one nested field, and conditional last temporary-table group.

- [ ] **Step 1: Repoint EDT junctions to the UI worktree and update the test database**

Verify exact junction targets before removal. Recreate only the two `src` junctions for `QueryConsoleZUP_Semantics` and `QueryConsoleZUP_YAxUnit`; do not touch EDT processes.

- [ ] **Step 2: Configure Vanessa target**

Install official `VAExtension.1.29.cfe` into the ZUP test infobase, create a Vanessa test-client profile, stop only conflicting 1C child processes, update the database, and restart runtime after the real infobase change.

- [ ] **Step 3: Diagnose the MCP file-constructor failure**

Reproduce `open_feature_file` and `load_features`; trace the received JSON path into Vanessa. Test one hypothesis at a time. Do not patch the Vanessa repository; prefer launch/configuration correction or a documented direct UI fallback.

- [ ] **Step 4: Write the feature using recorded/reused steps**

Preserve Russian Gherkin and existing encoding. First run must fail before the UI implementation or against a deliberately reverted catalog commit; then restore and run GREEN.

- [ ] **Step 5: Execute acceptance through Vanessa MCP**

Use `get_VanessaAutomation_state`, `connect_test_client`, `get_form_analysis`, `get_table_data`, `run_scenario`, `get_test_results`, and screenshot tools on failure.

- [ ] **Step 6: Run existing regression scenarios**

Run `ТестСотрудникиОрганизацииБезВТФизлица.feature` and `ТестПараметрыСрезаПоследних.feature`.

### Task 7: Portable Vanessa MCP documentation and project report

**Files:**
- Create: `documentation/VanessaMCP.md`
- Create: `docs/research/2026-08-31-vanessa-mcp-ui-report.md`

**Interfaces:**
- The portable guide contains no repository-specific credentials, usernames, tokens, PIDs, or fixed infobase data.
- The project report records exact tools, errors, usefulness, harmful effects, workarounds, and comparison with EDT/YAxUnit.

- [ ] **Step 1: Write portable setup**

Cover official artifacts, dedicated manager base, extension installation, one-time WebTransport restart, Streamable HTTP endpoint, Codex `mcp add`, required protocol headers, client profile, target `VAExtension`, process isolation, and update/restart rules.

- [ ] **Step 2: Write operating workflow**

Document state → connect → inspect → record/search steps → load/check → run/wait → results/screenshot → close client. Explicitly separate manager base, target test base, runtime, and EDT debugger.

- [ ] **Step 3: Add troubleshooting decision table**

Include `Session not found`, `Ошибка при вызове конструктора (Файл)`, empty-editor `lineNumber`, unavailable native tools before Codex restart, stale extension, blocked test client, and debugger interference.

- [ ] **Step 4: Record project-specific evidence**

List versions, commands/tools actually used, successful operations, failed operations, time costs, and which acceptance criteria MCP did and did not prove.

- [ ] **Step 5: Commit**

```powershell
git add documentation/VanessaMCP.md docs/research/2026-08-31-vanessa-mcp-ui-report.md features
git commit -m "docs: add portable Vanessa MCP workflow"
```

### Task 8: Final verification, review, and ready PR

**Files:**
- Review all changes against the spec and this plan.

- [ ] **Step 1: Run fresh verification**

Run focused YAxUnit modules without debugger, EDT diagnostic delta for every modified module/form, `git diff --check`, and Vanessa acceptance/regressions.

- [ ] **Step 2: Verify repository invariants**

Search for remaining form-owned `ДоступныеТаблицыИБ`, raw `ДанныеПоставщика` flow into forms, new provider-root UI, and unintended `Form.form` changes.

- [ ] **Step 3: Perform read-only independent review**

Review the full `feature/metadata-provider-semantics..feature/metadata-provider-ui` diff. Resolve every Critical/High finding and repeat affected tests.

- [ ] **Step 4: Push and create a ready PR**

Use base `feature/metadata-provider-semantics` while PR #76 is unmerged; retarget to `master` after semantics merges. Include verification evidence and remaining manual gaps.
