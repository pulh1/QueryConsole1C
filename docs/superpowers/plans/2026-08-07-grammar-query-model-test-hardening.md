# Phase 2.5: Headless Test Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** До первого изменения EBNF, bindings, Parser IR, production grammar или query model создать и выполнить воспроизводимые headless characterization/contract gates для всех обязательных consumer contracts и runtime parser baseline.

**Architecture:** Phase 2.5 расширяет существующие серверные YAxUnit common modules и добавляет только test/benchmark modules в проект `yaxunit`; production extension и generated parser остаются неизменными. Каждый вертикальный срез проверяет наблюдаемую semantic projection (типы, свойства, порядок, aliases, generated text), а не continuation/container topology. Runtime benchmark живёт в test-only контуре, формирует machine-readable результат и не добавляет счётчиков или progress guards в production BSL.

**Tech Stack:** 1С:Предприятие 8.3.24, BSL, EDT project `yaxunit`, existing YAxUnit API (`ЮТТесты`, `ЮТест`, `ЮТМетоды`), QueryExamples corpus, Python 3.12/pytest, PowerShell, Git.

## Global Constraints

- Не менять `tools/parsergen/grammar/query-language.grammar`, EBNF syntax, bindings, lowering, Parser IR, nullable/FIRST/FOLLOW/SELECT, production query-model factories/properties или `QueryConsoleZUP/src/DataProcessors/Парсер`.
- До GREEN всех headless tasks не начинать EBNF/bindings/LR/model migration.
- Form modules не являются unit-test targets; Query Constructor non-form dependencies обязательны и не считаются manual-only.
- Не создавать EDT launch configuration и не придумывать 1С/YAxUnit/Vanessa command: на начало Phase 2.5 она отсутствует. Сначала обнаружить реальный launch path; при его отсутствии сохранить конкретный blocker и выполнить доступные static/Python checks.
- Vanessa interactive/form gate выполняется только после всей миграции, вне этого Phase 2.5 плана.
- Каждое новое BSL-тестовое действие регистрировать в `ИсполняемыеСценарии()` существующего или созданного common module; assertions проверяют business semantics, не topology legacy continuation nodes.
- Для новой common module создавать парные `.mdo` и `Module.bsl`; `.mdo` задаёт `<server>true</server>`, UUID генерируется EDT при создании metadata object, а не вручную.
- Каждый vertical slice: RED в зарегистрированном YAxUnit test → минимальная test-only fixture/contract code → GREEN в доступном runner → targeted static check → commit → push → independent review. Команда запуска YAxUnit будет вписана только после её фактического обнаружения.

## File Map

- Modify: `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl` — expression parser semantic observations and unknown-node text-generation error.
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl` — full-query sources/aliases/joins/fields/nested/union parser projection.
- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl` — parser-to-semantic source lanes.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/КОНС_Обр_МодельВыражений_МО.mdo`, `.../Module.bsl` — factory/dispatcher/template and three concrete-visitor contracts.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО.mdo`, `.../Module.bsl` — builder mutation and model-text-model contracts.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/КОНС_Обр_ИсполняемыеПредставления_МО.mdo`, `.../Module.bsl` — executable-view, executor/code and universal-report contracts.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_КонструкторЗапросов_МО/КОНС_Обр_КонструкторЗапросов_МО.mdo`, `.../Module.bsl` — Query Constructor public non-form contracts.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/КОНС_Обр_БенчмаркПарсера_МО.mdo`, `.../Module.bsl` — test-only runtime harness and JSON result.
- Create: `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md` — measured result, corpus identity, runner/version and metric definitions after an actual run.
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md` — change each completed headless row from gap to dated evidence; leave external blockers explicit.

## Known runnable commands and launch gap

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_migration_audit.py -v -p no:cacheprovider

Set-Location tools/parsergen
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q -p no:cacheprovider
Set-Location ../..
```

The repository currently provides no verified command for loading `yaxunit` into an incremental 1С infobase or executing an individual YAxUnit tag. Therefore every task below has two explicit paths: use the discovered command verbatim after recording its executable, infobase, extension/update state and tag/filter syntax; otherwise do not claim YAxUnit GREEN and record `external-blocker` with those missing values. The commands above remain the only mandatory executable suite commands until that discovery succeeds.

---

### Task 1: Establish the executable headless-test boundary

**Files:**
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md`
- Verify: existing `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl`, `.../КОНС_Обр_ПарсерЗапросов_МО/Module.bsl`, `.../КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`

**Interfaces:**
- Consumes: `ИсполняемыеСценарии() Экспорт` and existing server-test registration pattern.
- Produces: recorded real runner contract or a concrete external blocker; no production interface.

- [ ] **Step 1: Inspect registered test sets and available launch metadata**

Run:

```powershell
rg -n "ДобавитьТестовыйНабор|\.Тег\(|ДобавитьСерверныйТест" yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl
rg -n -i "yaxunit|launch|infobase|1cv8|vanessa" . -g '!*.log' -g '!*.json' -g '!*.pyc'
```

Expected: identify only repository evidence; do not infer a runner from a feature file or historical result.

- [ ] **Step 2: Record the red/green command only if it was discovered**

Add a short dated evidence row to the coverage matrix containing the exact command, executable/version, infobase identity, update state, selected tag and exit/output contract. If none is discovered, add `external-blocker: executable, infobase and incremental-update launch configuration absent`; do not add a shell command.

- [ ] **Step 3: Run available Python regression baseline**

Run the two commands in **Known runnable commands and launch gap**. Expected: focused audit passes; full suite passes with only the documented WinError 1314 skip.

- [ ] **Step 4: Commit and publish the runner-boundary evidence**

```powershell
git add -- docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md
git commit -m "Зафиксировать границу headless запуска тестов"
git push
```

### Task 2: Full-query parser and semantic source projection

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`
- Test data: selected existing `QueryExamples/*.q1c` with sources, aliases, joins, fields, nested query and union.

**Interfaces:**
- Consumes: `Парсер.Разобрать(ИсходныйТекст)`, `КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер()` and `ОбработкаМоделиЗапроса.ОбработатьМодельЗапроса(ПакетЗапросов)`.
- Produces: parser and semantic projection assertions for `ПакетЗапросов`, `ЗапросВыбора`, `ОператорЗапроса`, sources, aliases, joins, fields, nested query and union.

- [ ] **Step 1: Select and name six existing corpus inputs before editing tests**

Run:

```powershell
rg --files QueryExamples -g '*.q1c'
rg -n -i "соедин|объедин|выбрать|из " QueryExamples -g '*.q1c'
```

Record in the test module comments the exact six chosen relative paths and the contract each demonstrates; do not synthesize a replacement corpus if an existing file covers the case.

- [ ] **Step 2: Add RED registered server tests in the existing modules**

Register a parameterized `ПроверяетсяСемантическаяПроекцияПолногоЗапроса` in `КОНС_Обр_ПарсерЗапросов_МО.ИсполняемыеСценарии()` and `СемантикаИсточниковПакетаСогласованаСПарсером` in `КОНС_ОМ_ОбработкаМоделиЗапроса.ИсполняемыеСценарии()`. The semantic test parses a `ПакетЗапросов`, calls `ОбработкаМоделиЗапроса.ОбработатьМодельЗапроса(ПакетЗапросов)` with its single real argument, then asserts element count/order, source identity, alias, join kind/condition, field expression/alias, nested-query boundary or union member count.

- [ ] **Step 3: Run the discovered YAxUnit tags and confirm RED**

Run the command recorded by Task 1 with the two actual tags. Expected: assertion failure only for the new semantic projection; if no command exists, preserve the RED test source and record that execution is blocked.

- [ ] **Step 4: Complete only reusable test helpers and explicit assertions**

Add private helpers equivalent in scope to existing `РазобратьЗапросДляТеста`, `ЕдинственныйЗапросВыбора` and `ЕдинственныйОператор`; helpers may read model properties but must not transform production objects. Re-run the selected tags and expect GREEN when a runner exists.

- [ ] **Step 5: Run static and Python checks, then commit/push**

```powershell
rg -n "ПроверяетсяСемантическаяПроекцияПолногоЗапроса|СемантикаИсточниковПакетаСогласованаСПарсером" yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_migration_audit.py -v -p no:cacheprovider
git add -- yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl
git commit -m "Усилить headless контракт полного разбора запроса"
git push
```

### Task 3: Complete factory inventory, expression dispatcher, visitors and text error

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl`
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/КОНС_Обр_МодельВыражений_МО.mdo`, `.../Module.bsl`

**Interfaces:**
- Consumes: all 91 exports of `ЭлементыМоделиЗапроса`: helper `НовыйЭлементМоделиЗапроса(Тип, ТекущийТокен = Неопределено)` plus 90 concrete `Новый*` factories; `ОбходМоделиЯзыкаВыражений.ОбойтиДерево(Узел, Посетитель)`; 59 callback template methods; `ГенерацияТекстовЗапросов.СоздатьГенераторТекстовВыражений()` and `ВыражениеВСтроку(Выражение, ГенераторТекстовВыражений)`; visitor lifecycle methods and `ВыделитьИМодифицироватьОтбор`.
- Produces: a classified 91-export inventory; complete factory property/collection contracts split into expression, query/package/source, and remaining type/executable-view families; dispatcher callback order; three concrete visitor contracts; and the unknown-expression-node generator error.

- [ ] **Step 1: Read exact public signatures and callback names**

```powershell
$factory = 'QueryConsoleZUP/src/CommonModules/ЭлементыМоделиЗапроса/Module.bsl'
$exports = Select-String -Path $factory -Pattern '^Функция\s+(Новый\S+)\(' | ForEach-Object { $_.Matches[0].Groups[1].Value }
"factory_exports=$($exports.Count)"; $exports
$template = 'QueryConsoleZUP/src/DataProcessors/Шаблон_ПосетительМоделиВыражений/ObjectModule.bsl'
$templateCallbacks = Select-String -Path $template -Pattern '^Процедура\s+(\S+)\(.*\)\s+Экспорт' | ForEach-Object { $_.Matches[0].Groups[1].Value }
function Assert-ExactSet([string]$Name, [string[]]$Expected, [string[]]$Actual) {
  $delta = Compare-Object ($Expected | Sort-Object -Unique) ($Actual | Sort-Object -Unique)
  if ($null -ne $delta) {
    $delta | Format-Table -AutoSize | Out-String | Write-Error
    throw "set mismatch: $Name"
  }
  "set_contract=clean $Name"
}
$expectedVisitorExtras = @{
  'QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl' = @('ЗавершитьОбходВыражения','УстановитьКонтекст','УстановитьРассчитываемыеСвойства')
  'QueryConsoleZUP/src/DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl' = @('ВыделитьИМодифицироватьОтбор','ЗавершитьОбходВыражения','МожноДелегироватьВесьОтбор','УстановитьИдентификаторИсточникаПредставления','УстановитьИмяПредставления','УстановитьОписаниеОтбора','УстановитьРежимВалидации')
  'QueryConsoleZUP/src/DataProcessors/ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl' = @('УстановитьКонтекст')
}
foreach ($visitor in $expectedVisitorExtras.Keys) {
  $exports = Select-String -Path $visitor -Pattern '^(Процедура|Функция)\s+(\S+)\(.*\)\s+Экспорт' | ForEach-Object { $_.Matches[0].Groups[2].Value } | Sort-Object -Unique
  $callbacks = $exports | Where-Object { $_ -in $templateCallbacks }
  $extras = $exports | Where-Object { $_ -notin $templateCallbacks }
  Assert-ExactSet "visitor callbacks: $visitor" $templateCallbacks $callbacks
  Assert-ExactSet "visitor lifecycle/helper exports: $visitor" $expectedVisitorExtras[$visitor] $extras
}
$dispatcherCalls = Select-String -Path 'QueryConsoleZUP/src/CommonModules/ОбходМоделиЯзыкаВыражений/Module.bsl' -Pattern 'Посетитель\.(\S+)\(' | ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
Assert-ExactSet 'dispatcher callback targets' $templateCallbacks $dispatcherCalls
rg -n "СоздатьГенераторТекстовВыражений|ВыражениеВСтроку|УстановитьКонтекст|ВыделитьИМодифицироватьОтбор" QueryConsoleZUP/src/CommonModules/ГенерацияТекстовЗапросов/Module.bsl QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl QueryConsoleZUP/src/DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl QueryConsoleZUP/src/DataProcessors/ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl
```

Expected: exactly 91 factory exports; the first is the documented base helper and the remaining 90 are concrete factories. For every visitor, comparison 1 fails on a missing or unexpected callback in its callback subset; comparison 2 fails on a missing or unexpected lifecycle/helper export in its explicitly enumerated allowed extras. The plan deliberately does not compare the complete visitor export set directly with the template. The dispatcher is compared by its `Посетитель.<callback>` targets because it exports only `ОбойтиДерево`.

- [ ] **Step 2: Add RED contracts as one expression vertical slice**

Create the common module through EDT and register seven server tests: `ФабрикиВыраженийСоздаютОжидаемыеСвойства`, `ФабрикиПакетаЗапросаИИсточниковСоздаютОжидаемыеСвойства`, `ОстальныеФабрикиТиповИИсполняемыхПредставленийСоздаютОжидаемыеСвойства`, `ДиспетчерВызываетВсе59КолбэковВПорядкеОбхода`, `СемантическийПосетительСохраняетТипыИАгрегаты`, `ПосетительОтбораРазделяетДелегируемыеСмешанныеИНедопустимыеУсловия`, `ПосетительСКДПреобразуетРазыменованиеИТип`.

The three factory tests must consume an explicit 91-row inventory maintained beside the tests: (1) `НовыйЭлементМоделиЗапроса` is tested as a base helper for `Тип`; (2) expression factories cover expression nodes, functions, type descriptions and their collections; (3) query/package/source factories cover package, selection/destruction query, operator, columns, source, joins, ordering and totals; (4) the remaining concrete factories cover executable-view/filter/parameter structures. Every row declares export name, test family, expected `Тип`, scalar property names and collection/map property names. A missing export, duplicate inventory row, unexpected export, absent property or wrong empty collection/map fails the test. This is deliberately not a claim that all 91 exports are expression factories.

Add `НеизвестныйУзелВыраженияВызываетИсключениеГенератораТекста` to the existing parser module. It creates `ГенераторТекстовВыражений = ГенерацияТекстовЗапросов.СоздатьГенераторТекстовВыражений()` and calls `ГенерацияТекстовЗапросов.ВыражениеВСтроку(НеизвестныйУзел, ГенераторТекстовВыражений)`, asserting the real generator's exception; no one-argument call is permitted. The callback recorder must emit callback name plus enter/exit order and compare it to the explicit expected array derived from the template, not merely count calls.

- [ ] **Step 3: Execute RED, then implement only test fixtures**

Run the discovered tags. Expected RED: unregistered/new test or missing assertion helper. Add only test fixtures: the full factory inventory, real nodes from the four stated families, and a test visitor object. Do not add production dispatch, model fields or fallback text generation.

- [ ] **Step 4: Execute GREEN and verify contract completeness**

```powershell
rg -n "ФабрикиВыраженийСоздаютОжидаемыеСвойства|ФабрикиПакетаЗапросаИИсточниковСоздаютОжидаемыеСвойства|ОстальныеФабрикиТиповИИсполняемыхПредставленийСоздаютОжидаемыеСвойства|ДиспетчерВызываетВсе59КолбэковВПорядкеОбхода|НеизвестныйУзелВыраженияВызываетИсключениеГенератораТекста" yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl
```

Expected: the full extraction/set-comparison command from Step 1 is clean, the registered inventory covers 91 exports exactly once, and all seven behavior contracts are present. Execute the real YAxUnit tags if Task 1 found a command; otherwise retain explicit blocked status.

- [ ] **Step 5: Commit and publish**

```powershell
git add -- yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО
git commit -m "Добавить headless контракты модели выражений"
git push
```

### Task 4: Builder and model-to-text-to-model contract

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО.mdo`, `.../Module.bsl`

**Interfaces:**
- Consumes: `ПостроительМоделиЗапроса.Инициализировать`, `ПолучитьМодель`, `ДобавитьИсточник`, `ДобавитьОтбор`, `ДобавитьУпорядочивание`, `ДобавитьКонтрольнуюТочкуИтогов`, `УстановитьПолучениеОбщихИтогов`; `ГенерацияТекстовЗапросов.ТекстПакетаЗапросов`, `ТекстЗапросаВыбора`, `ВыражениеВСтроку`; parser `Разобрать`.
- Produces: source/filter/order/totals mutation sequence and semantic equality projection for `model → text → model`.

- [ ] **Step 1: Read live signatures before creating fixtures**

```powershell
rg -n "^(Процедура|Функция) (Инициализировать|ПолучитьМодель|ДобавитьИсточник|ДобавитьОтбор|ДобавитьУпорядочивание|ДобавитьКонтрольнуюТочкуИтогов|УстановитьПолучениеОбщихИтогов|ТекстПакетаЗапросов|ТекстЗапросаВыбора|ВыражениеВСтроку)" QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl QueryConsoleZUP/src/CommonModules/ГенерацияТекстовЗапросов/Module.bsl
```

- [ ] **Step 2: Register RED tests**

Register `ПостроительМеняетИсточникиОтборСортировкуИИтогиПоШагам` and `ТекстПакетаПослеПовторногоРазбораСохраняетСемантику`. The first calls, in order, `ДобавитьИсточник(ИмяИсточника, Псевдоним)`, `ДобавитьОтбор(ТекстВыражения)`, `ДобавитьУпорядочивание(ТекстВыражения)`, `ДобавитьКонтрольнуюТочкуИтогов(ТекстВыражения)` and `УстановитьПолучениеОбщихИтогов(ОбщиеИтоги)`, asserting model state after each returned operation. The second compares a projection containing package/operator order, source identity/alias, selected-field expression/alias, filter, ordering, totals point and general-totals flag; it explicitly excludes continuation/container topology.

- [ ] **Step 3: Run RED and add minimal private projection helpers**

Run the discovered YAxUnit tag. Implement only private test helpers that construct the fixture, call the listed public methods and produce a deterministic `Структура`/`Массив` projection for assertion; do not change production model or generator.

- [ ] **Step 4: Run GREEN, static checks and commit/push**

```powershell
rg -n "ПостроительМеняетИсточникиОтборСортировкуИИтогиПоШагам|ТекстПакетаПослеПовторногоРазбораСохраняетСемантику" yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/Module.bsl
git add -- yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО
git commit -m "Покрыть построитель и семантический round-trip запроса"
git push
```

### Task 5: Executable-view, executor/code and universal-report non-form contracts

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/КОНС_Обр_ИсполняемыеПредставления_МО.mdo`, `.../Module.bsl`

**Interfaces:**
- Consumes: `ОбработкаПредставлениеЗапросов.ОбработатьИсточникЗапроса`, `ИсполняемоеПредставлениеПоОписанию`, `ИсполнительПредставлений.ПолучитьИсполняемыйКод`, `ПолучитьТекстЗапросаДляСКД`, `УниверсальныйОтчетРасширенный.ЗаменитьИсполняемыеПредставленияВременнымиТаблицами`.
- Produces: transformation/delegation projection, focused code/SKD text snapshots and universal-report temporary-table adaptation.

- [ ] **Step 1: Read exact signatures and required context shapes**

```powershell
rg -n "^(Процедура|Функция) (ОбработатьИсточникЗапроса|ИсполняемоеПредставлениеПоОписанию|ПолучитьИсполняемыйКод|ПолучитьТекстЗапросаДляСКД|ЗаменитьИсполняемыеПредставленияВременнымиТаблицами)" QueryConsoleZUP/src/CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl QueryConsoleZUP/src/CommonModules/ИсполнительПредставлений/Module.bsl QueryConsoleZUP/src/CommonModules/УниверсальныйОтчетРасширенный/Module.bsl
```

- [ ] **Step 2: Register RED cases as one downstream vertical slice**

Register `ИсполняемоеПредставлениеПреобразуетИДелегируетОтбор`, `ИсполнительФормируетКодИТекстСКДДляПредставительнойМодели`, `УниверсальныйОтчетЗаменяетИсполняемыеПредставленияВременнымиТаблицами`. Use one representative parser-built model; assert delegated/residual filters, stable meaningful fragments of code/SKD text and adapted source/table identities. Do not assert formatting-only whitespace.

- [ ] **Step 3: Run RED, build only headless fixtures, then GREEN**

Call only the public interfaces listed above from server tests. If a fixture reaches metadata/provider dispatch or an infobase dependency, split that exact case to `external-blocker` in the coverage matrix; do not substitute a form/Vanessa scenario.

- [ ] **Step 4: Commit and publish**

```powershell
rg -n "ИсполняемоеПредставлениеПреобразуетИДелегируетОтбор|ИсполнительФормируетКодИТекстСКДДляПредставительнойМодели|УниверсальныйОтчетЗаменяетИсполняемыеПредставленияВременнымиТаблицами" yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/Module.bsl
git add -- yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md
git commit -m "Добавить headless контракты исполняемых представлений"
git push
```

### Task 6: Query Constructor non-form dependency characterization

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_КонструкторЗапросов_МО/КОНС_Обр_КонструкторЗапросов_МО.mdo`, `.../Module.bsl`

**Interfaces:**
- Consumes: `КонструкторЗапросов.ObjectModule.AvailableTablesBeforeExpandAtServer`, `SourcesBeforeExpandAtServer`, `GetSchemaQuery` and their exact live parameter lists.
- Produces: verified non-form public-call contract or explicit runtime blocker for each call.

- [ ] **Step 1: Read complete signatures and all non-form callees**

```powershell
Get-Content -Raw 'QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/ObjectModule.bsl'
rg -n "AvailableTablesBeforeExpandAtServer|SourcesBeforeExpandAtServer|GetSchemaQuery" QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов -g '*.bsl'
```

- [ ] **Step 2: Register RED public-object tests without a form**

Register `СхемаЗапросаВозвращаетсяДляВложеннойПозиции`, `ДоступныеТаблицыРаскрываютсяБезФормы`, `ИсточникиРаскрываютсяБезФормы`, using the exact inputs established in Step 1. Assert schema query, source ordering and table identities; do not call a form module.

- [ ] **Step 3: Run RED and classify each dependency**

Run the discovered tag. A server-call success becomes a headless contract. A dependency on unavailable address, provider or infobase is recorded with the exact failing call and prerequisite in the coverage matrix; it remains `external-blocker`, not `form-only-vanessa/manual`.

- [ ] **Step 4: Run GREEN where possible; commit/push the evidence**

```powershell
rg -n "СхемаЗапросаВозвращаетсяДляВложеннойПозиции|ДоступныеТаблицыРаскрываютсяБезФормы|ИсточникиРаскрываютсяБезФормы" yaxunit/src/CommonModules/КОНС_Обр_КонструкторЗапросов_МО/Module.bsl
git add -- yaxunit/src/CommonModules/КОНС_Обр_КонструкторЗапросов_МО docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md
git commit -m "Охарактеризовать non-form зависимости конструктора запросов"
git push
```

### Task 7: Runtime parser benchmark harness and baseline

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/КОНС_Обр_БенчмаркПарсера_МО.mdo`, `.../Module.bsl`
- Create: `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md`

**Interfaces:**
- Consumes: `Парсер.Разобрать(Текст)` and `РазобратьВыражение(Текст)`, 42 `QueryExamples`, and test-only timing/instrumentation facilities actually available in the discovered runtime.
- Produces: UTF-8 JSON result per corpus class with warm-up count, median/p95 wall-clock, nonterminal calls, dispatch calls, maximum recursion depth, constructor/action executions, AST node/container allocations, generated BSL function count and LOC.

- [ ] **Step 1: Prove available instrumentation before writing benchmark assertions**

Read parser entrypoint and generated module boundaries; record which counters can be collected without production edits. If no test-only interception mechanism exists, record the exact missing hook and stop this task as `external-blocker`; do not insert counters into `QueryConsoleZUP/src/DataProcessors/Парсер`.

- [ ] **Step 2: Add RED benchmark registration and corpus manifest**

Register one server benchmark test with explicit corpus classes: all 42 `QueryExamples`, large package, long field list, JOIN chain, UNION/package chain, arithmetic chain, logical chain, dereference chain. Store each class identifier and input provenance in the JSON result; synthetic inputs are built by private test helpers with their exact length recorded in that result.

- [ ] **Step 3: Implement test-only measurement and run baseline**

Warm up before measurements, collect multiple samples, compute median and p95 from the sorted sample array, and write JSON only through an approved test-result/output facility discovered in Task 1. The result must identify platform, 1С runtime version, parser artifact identity and every unavailable metric as `null` with an explanation; it must not silently report zero.

- [ ] **Step 4: Review the baseline and freeze no performance threshold**

Create the baseline matrix only from an actual JSON run. State that Phase 2.5 has no predeclared speedup percentage; later migration must explain wall-clock/generated-size regressions and prove repeat/direct-LR stack depth does not grow with chain length. Never use Python analysis timings as BSL runtime values.

- [ ] **Step 5: Commit and publish**

```powershell
git add -- yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md
git commit -m "Добавить baseline runtime benchmark парсера"
git push
```

### Task 8: Phase 2.5 closure and migration handoff

**Files:**
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md`
- Verify: all Phase 2.5 test modules and `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md`

**Interfaces:**
- Consumes: all task evidence.
- Produces: a gate decision authorizing the next planning/execution phase, or an evidence-backed list of unresolved external blockers.

- [ ] **Step 1: Reconcile all mandatory backlog items**

Update a checklist with exactly these eleven items: semantic sources/aliases/joins/fields/nested/union; factory-dispatcher-template completeness; unknown expression node error; three concrete visitor behavior contracts; builder mutations; model-text-model round-trip; executable-view filter transformation/delegation; executor/code-generation integration; universal-report transformations; Query Constructor non-form dependencies; runtime benchmark harness.

- [ ] **Step 2: Run all commands that actually exist**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_migration_audit.py -v -p no:cacheprovider
Set-Location tools/parsergen
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q -p no:cacheprovider
Set-Location ../..
git diff --check
git status --short --branch
```

Run the discovered YAxUnit command for every new tag only if Task 1 recorded it. Expected: no unreported failures; the known Python symlink skip remains limited to WinError 1314.

- [ ] **Step 3: Enforce the gate**

Do not begin EBNF/bindings/LR/model production work unless every headless-contract row is GREEN or has the precisely documented external blocker permitted by the approved design. Do not run Vanessa here: its interactive/form checklist follows the entire migration, after headless contracts and production slices.

- [ ] **Step 4: Commit/push closure evidence and request review**

```powershell
git add -- docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md
git commit -m "Закрыть gate Phase 2.5 headless тестов"
git push
```

Request two reviews: first verifies each matrix backlog item maps to an executable test or an exact external blocker; second verifies no production grammar/model/parser or form-module diff entered the Phase 2.5 commits.

## Self-review

- Mandatory backlog coverage: Task 2 covers semantic sources/aliases/joins/fields/nested/union; Task 3 covers factory-dispatcher-template completeness, unknown node and all three visitors; Task 4 covers builder plus round-trip; Task 5 covers executable-view, executor/code and universal-report; Task 6 covers Query Constructor non-form dependencies; Task 7 covers the runtime benchmark harness.
- Scope: the plan contains no EBNF, bindings, lowering, Parser IR, LR, production grammar, production model or generated-parser implementation task.
- UI: Query Constructor is explicitly headless first; Vanessa is deferred until after the whole migration.
- Runner integrity: no 1С/YAxUnit/Vanessa invocation was fabricated; its absence is an explicit blocker that must be resolved with actual environment evidence.
