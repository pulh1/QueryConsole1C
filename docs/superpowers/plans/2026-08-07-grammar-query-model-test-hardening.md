# Phase 2.5: Headless Test Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** До первого изменения EBNF, bindings, Parser IR, production grammar или query model создать и выполнить воспроизводимые headless characterization/contract gates для всех обязательных consumer contracts и runtime parser baseline.

**Architecture:** Phase 2.5 расширяет существующие серверные YAxUnit common modules и добавляет только test/benchmark modules в проект `yaxunit`; production extension и generated parser остаются неизменными. Каждый вертикальный срез проверяет наблюдаемую semantic projection (типы, свойства, порядок, aliases, generated text), а не continuation/container topology. Runtime benchmark живёт в test-only контуре, формирует machine-readable результат и не добавляет счётчиков или progress guards в production BSL.

**Tech Stack:** 1С:Предприятие 8.3.24, BSL, EDT project `yaxunit`, existing YAxUnit API (`ЮТТесты`, `ЮТест`, `ЮТМетоды`), QueryExamples corpus, Python 3.12/pytest, PowerShell, Git.

## Global Constraints

- Не менять `tools/parsergen/grammar/query-language.grammar`, EBNF syntax, bindings, lowering, Parser IR, nullable/FIRST/FOLLOW/SELECT, production query-model factories/properties или `QueryConsoleZUP/src/DataProcessors/Парсер`.
- До GREEN всех headless tasks не начинать EBNF/bindings/LR/model migration.
- Form modules не являются unit-test targets; Query Constructor non-form dependencies обязательны и не считаются manual-only.
- Не создавать EDT launch configuration и не придумывать 1С/YAxUnit/Vanessa command: на начало Phase 2.5 она отсутствует. Сначала обнаружить реальный launch path; при его отсутствии сохранить конкретный blocker и выполнить доступные static/Python checks. Отсутствие verified runner/path блокирует handoff к production migration: оно не считается пройденным gate.
- Vanessa interactive/form gate выполняется только после всей миграции, вне этого Phase 2.5 плана.
- Каждое новое BSL-тестовое действие регистрировать в `ИсполняемыеСценарии()` существующего или созданного common module; assertions проверяют business semantics, не topology legacy continuation nodes.
- Для новой common module создавать парные `.mdo` и `Module.bsl`; `.mdo` задаёт `<server>true</server>`, UUID генерируется EDT при создании metadata object, а не вручную.
- Каждый vertical slice: RED в зарегистрированном YAxUnit test → минимальная test-only fixture/contract code → GREEN в доступном runner → targeted static check → commit → push → independent review. Команда запуска YAxUnit будет вписана только после её фактического обнаружения.

## File Map

- Verify/run: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl` — fresh token/EOF/error regression evidence.
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl` — expression-parser AST semantic observations and unknown-node text-generation error.
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl` — full-query sources/aliases/joins/fields/nested/union parser projection.
- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl` — parser-to-semantic source lanes.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/КОНС_Обр_МодельВыражений_МО.mdo`, `.../Module.bsl` — factory/dispatcher/template and three concrete-visitor contracts.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО.mdo`, `.../Module.bsl` — builder mutation and model-text-model contracts.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/КОНС_Обр_ИсполняемыеПредставления_МО.mdo`, `.../Module.bsl` — executable-view, executor/code and universal-report contracts.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО.mdo`, `.../Module.bsl` — Query Console, Query Constructor and feature-generator non-form contracts.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ПотребителиПредставлений_МО/КОНС_Обр_ПотребителиПредставлений_МО.mdo`, `.../Module.bsl` — per-contract characterization for all 15 direct `Представление*` manager consumers.
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/КОНС_Обр_БенчмаркПарсера_МО.mdo`, `.../Module.bsl` — test-only runtime harness and JSON result.
- Create: `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md` — measured result, corpus identity, runner/version and metric definitions after an actual run.
- Create: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json` — machine-checkable evidence for `C01`–`C18` and `X01`.
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

The repository currently provides no verified command for loading `yaxunit` into an incremental 1С infobase or executing an individual YAxUnit tag. Therefore every task below has two explicit paths: use the discovered command verbatim after recording its executable, infobase, extension/update state and tag/filter syntax; otherwise do not claim YAxUnit GREEN and record `external-blocker` with those missing values. Such a blocker permits static preparation but does **not** authorize handoff to production migration, because the fresh runtime suite and actual wall-clock before-baseline are mandatory. The commands above remain the only mandatory executable suite commands until discovery succeeds.

## Machine-checkable contract-to-task map

| Contract ID | Phase 2.5 task | Required executable evidence |
|---|---:|---|
| C01 | 3 | 91-factory inventory/property contracts |
| C02 | 2 | fresh complete `Лексер` tag run |
| C03 | 2 | expression-parser AST semantic projections |
| C04 | 2 | full-query parser corpus projections |
| C05 | 2 | parser-to-semantic source projections |
| C06 | 3 | dispatcher/template callback order and completeness |
| C07 | 3 | semantic visitor behavior contract |
| C08 | 3 | filter visitor delegation contract |
| C09 | 3 | SKD dereference visitor contract |
| C10 | 4 | builder mutation sequence |
| C11 | 3, 4 | unknown-node error and model/text/model round-trip |
| C12 | 5 | executable-view transformation/delegation |
| C13 | 5 | executor code/SKD integration |
| C14 | 6 | direct Query Console object characterization |
| C15 | 6 | Query Constructor non-form calls |
| C16 | 5 | universal-report transformation |
| C17 | 6 | feature-generator literal golden |
| C18 | 7 | 15×6 manager/export test-or-blocker manifest |
| X01 | 8 | actual runtime before-baseline with positive wall-clock median/p95 |

Task 9 checks this complete ID set against both durable matrices and the
evidence JSON; task grouping does not collapse evidence rows.

---

### Task 1: Establish the executable headless-test boundary

**Files:**
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md`
- Create: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json`
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

Add a short dated evidence row to the coverage matrix containing the exact command, executable/version, infobase identity, update state, selected tag and exit/output contract. Initialize the evidence JSON with `schema_version: 1`, the same `runner` fields and an empty `contracts` array that later tasks fill. If none is discovered, store a `runner_blocker` with the exact missing executable, infobase and incremental-update launch configuration and leave runner identity fields `null`; do not add a shell command and do not permit closure.

- [ ] **Step 3: Run available Python regression baseline**

Run the two commands in **Known runnable commands and launch gap**. Expected: focused audit passes; full suite passes with only the documented WinError 1314 skip.

- [ ] **Step 4: Commit and publish the runner-boundary evidence**

```powershell
git add -- docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Зафиксировать границу headless запуска тестов"
git push
```

### Task 2: Fresh lexer and parser-to-semantic handshake

**Files:**
- Verify/run: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json`
- Test data: selected existing `QueryExamples/*.q1c` with sources, aliases, joins, fields, nested query and union.

**Interfaces:**
- Consumes: existing tag `Лексер`; `Парсер.РазобратьВыражение(ИсходныйТекст)`, `Парсер.Разобрать(ИсходныйТекст)`, `КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер()` and `ОбработкаМоделиЗапроса.ОбработатьМодельЗапроса(ПакетЗапросов)`.
- Produces: fresh token/EOF/error regression evidence; semantic AST projections for expression precedence, associativity, dereference, function arguments and conditional expressions; parser and semantic projections for package, query, sources, aliases, joins, fields, nested query and union. Closes `C02`–`C05` independently in the evidence manifest.

- [ ] **Step 1: Inventory lexer/expression contracts and select six query corpus inputs before editing tests**

Run:

```powershell
rg -n "ДобавитьСерверныйТест|\.Тег\(" yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl
rg --files QueryExamples -g '*.q1c'
rg -n -i "соедин|объедин|выбрать|из " QueryExamples -g '*.q1c'
```

Record in the test module comments the exact six chosen relative paths and the contract each demonstrates; do not synthesize a replacement corpus if an existing file covers the case. Keep the complete existing `Лексер` tag as the fresh `C02` gate; do not replace it with a single smoke test.

- [ ] **Step 2: Add RED expression/full-query/semantic server tests in the existing modules**

Register parameterized `ПроверяетсяСемантическаяПроекцияВыражения` in `КОНС_Обр_Парсер_МО.ИсполняемыеСценарии()`, `ПроверяетсяСемантическаяПроекцияПолногоЗапроса` in `КОНС_Обр_ПарсерЗапросов_МО.ИсполняемыеСценарии()` and `СемантикаИсточниковПакетаСогласованаСПарсером` in `КОНС_ОМ_ОбработкаМоделиЗапроса.ИсполняемыеСценарии()`. Expression rows must cover left/right operand identity and operation for an arithmetic chain, precedence nesting, dereference element order, function argument order and conditional-expression alternatives/result. The full-query semantic test parses a `ПакетЗапросов`, calls `ОбработкаМоделиЗапроса.ОбработатьМодельЗапроса(ПакетЗапросов)` with its single real argument, then asserts element count/order, source identity, alias, join kind/condition, field expression/alias, nested-query boundary or union member count.

- [ ] **Step 3: Run the complete lexer tag, then new parser tags and confirm RED**

Run the command recorded by Task 1 first with the complete existing `Лексер` tag and record its fresh result, then with the expression/full-query/semantic tags. Expected: lexer GREEN and assertion failure only for the new semantic projections. If no command exists, preserve the RED test source and record `C02`–`C05` as blocked by the missing runner; none is GREEN.

- [ ] **Step 4: Complete only reusable test helpers and explicit assertions**

Add private helpers equivalent in scope to existing `РазобратьВыражениеДляТеста`, `РазобратьЗапросДляТеста`, `ЕдинственныйЗапросВыбора` and `ЕдинственныйОператор`; helpers may read model properties but must not transform production objects. Re-run the complete lexer and selected parser/semantic tags and expect GREEN when a runner exists.

- [ ] **Step 5: Run static and Python checks, then commit/push**

```powershell
rg -n "ПроверяетсяСемантическаяПроекцияВыражения|ПроверяетсяСемантическаяПроекцияПолногоЗапроса|СемантикаИсточниковПакетаСогласованаСПарсером" yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_migration_audit.py -v -p no:cacheprovider
git add -- yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Усилить headless контракт разбора запроса"
git push
```

### Task 3: Complete factory inventory, expression dispatcher, visitors and text error

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl`
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/КОНС_Обр_МодельВыражений_МО.mdo`, `.../Module.bsl`
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json`

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
git add -- yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Добавить headless контракты модели выражений"
git push
```

### Task 4: Builder and model-to-text-to-model contract

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО.mdo`, `.../Module.bsl`
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json`

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
git add -- yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Покрыть построитель и семантический round-trip запроса"
git push
```

### Task 5: Executable-view, executor/code and universal-report non-form contracts

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/КОНС_Обр_ИсполняемыеПредставления_МО.mdo`, `.../Module.bsl`
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json`

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
git add -- yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Добавить headless контракты исполняемых представлений"
git push
```

### Task 6: Application object-layer consumers and feature golden

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО.mdo`, `.../Module.bsl`

**Interfaces:**
- Consumes: `КонсольЗапросов.ObjectModule.ВыполнитьЗапрос`, `ПреобразоватьВМетаданные`; `КонструкторЗапросов.ObjectModule.AvailableTablesBeforeExpandAtServer`, `SourcesBeforeExpandAtServer`, `GetSchemaQuery`; `ГенераторFeatureФайлов.ObjectModule.УстановитьГенераторТекстовВыражений`, `УстановитьТекстовыйДокумент`, `СценарийСозданияПакетаЗапросаВТекДок` and their exact live parameter lists.
- Produces: direct Query Console result/plan-metadata characterization (`C14`), verified Query Constructor non-form public-call contracts (`C15`) and a literal model-to-feature golden (`C17`), or an exact runtime blocker for each individual call that cannot execute.

- [ ] **Step 1: Read complete signatures and all non-form callees for the three objects**

```powershell
Get-Content -Raw 'QueryConsoleZUP/src/DataProcessors/КонсольЗапросов/ObjectModule.bsl'
Get-Content -Raw 'QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/ObjectModule.bsl'
Get-Content -Raw 'QueryConsoleZUP/src/DataProcessors/ГенераторFeatureФайлов/ObjectModule.bsl'
rg -n "ВыполнитьЗапрос|ПреобразоватьВМетаданные|AvailableTablesBeforeExpandAtServer|SourcesBeforeExpandAtServer|GetSchemaQuery|СценарийСозданияПакетаЗапросаВТекДок" QueryConsoleZUP/src/DataProcessors/КонсольЗапросов QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов QueryConsoleZUP/src/DataProcessors/ГенераторFeatureФайлов -g '*.bsl'
```

- [ ] **Step 2: Register RED public-object and golden tests without a form**

Register `КонсольВыполняетМинимальныйЗапросБезФормы` and `КонсольПреобразуетПланВМетаданныеБезФормы` with complete argument fixtures for the exact signatures read in Step 1; assert result-table columns/row values and stable plan node identity/cost fields, not a non-empty result. Register `СхемаЗапросаВозвращаетсяДляВложеннойПозиции`, `ДоступныеТаблицыРаскрываютсяБезФормы`, `ИсточникиРаскрываютсяБезФормы`, asserting schema query, source ordering and table identities. Register `ГенераторFeatureФайловФормируетЭталонПакетаЗапроса`: parse one fixed package, inject the real expression-text generator and a `ТекстовыйДокумент`, invoke `СценарийСозданияПакетаЗапросаВТекДок`, and compare the resulting lines with an explicit literal golden stored in the test module. Do not call a form module and do not derive the expected golden with the production generator.

- [ ] **Step 3: Run RED and classify each individual dependency**

Run the discovered tag. A server-call success becomes a headless contract. A dependency on unavailable address, provider, DBMS plan format or infobase is recorded with the exact public call, complete error and missing prerequisite in the evidence manifest; one blocked call does not erase GREEN evidence for neighboring calls. `C14`, `C15` or `C17` remains `external-blocker`, not `form-only-vanessa/manual`, until every required observable has a test or per-call blocker.

- [ ] **Step 4: Run GREEN where possible; verify the literal golden and commit/push evidence**

```powershell
rg -n "КонсольВыполняетМинимальныйЗапросБезФормы|КонсольПреобразуетПланВМетаданныеБезФормы|СхемаЗапросаВозвращаетсяДляВложеннойПозиции|ДоступныеТаблицыРаскрываютсяБезФормы|ИсточникиРаскрываютсяБезФормы|ГенераторFeatureФайловФормируетЭталонПакетаЗапроса" yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/Module.bsl
git add -- yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Охарактеризовать прикладные потребители модели запроса"
git push
```

### Task 7: Fifteen direct `Представление*` manager consumers

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_ПотребителиПредставлений_МО/КОНС_Обр_ПотребителиПредставлений_МО.mdo`, `.../Module.bsl`
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json`

**Interfaces:**
- Consumes: the 15 concrete manager modules listed in the impact matrix; each exports `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД`, with live signatures read before test creation. `ПредставлениеРегистрСведенийЗаписи` and `ПредставлениеРегистрСведенийСрезПоследних` receive `ИмяРегистра` where their live signature requires it.
- Produces: a 15×6 contract manifest for `C18`; every cell contains a GREEN test reference and actual run evidence or the exact failing public call, error text and runtime prerequisite. A family-level statement such as “infobase required” is insufficient.

- [ ] **Step 1: Freeze the exact 15-manager/signature manifest**

```powershell
$central = 'МодельЗапросаУтилиты\.СоздатьПостроительМодели\(Модель\)'
$managerPaths = Get-ChildItem 'QueryConsoleZUP/src/DataProcessors' -Directory -Filter 'Представление*' |
  ForEach-Object { Join-Path $_.FullName 'ManagerModule.bsl' } |
  Where-Object { Test-Path $_ } |
  Where-Object { Select-String -Path $_ -Pattern $central -Quiet } |
  Sort-Object
if ($managerPaths.Count -ne 15) { throw "expected 15 direct managers, got $($managerPaths.Count)" }
$managerPaths | ForEach-Object {
  Select-String -Path $_ -Pattern '^(Процедура|Функция) (Описание|Справка|ИмяПредставления|Исполнить|ИсполняемыйКод|ТекстЗапросаДляСКД)\(.*\).*Экспорт'
}
```

Copy the exact names/signatures into an explicit 15-row test manifest. Each row has six operation slots and an adapter that invokes the concrete `Обработки.<Имя>.<Export>` call; do not use reflection that can silently skip an export.

- [ ] **Step 2: Register RED table-driven contracts in three behavior groups**

Register `Все15МенеджеровПубликуютОписаниеСправкуИИмя`, `Все15МенеджеровФормируютКодИТекстСКДДляМодели` and `Все15МенеджеровИсполняютПредставительнуюМодель`. The first test asserts stable non-empty identity/help semantics for all 15. The second parses one representative model per required manager family and asserts meaningful query/code fragments and source identities for both generation exports. The third invokes `Исполнить` and asserts returned table/column semantics. Parameterized register managers use an existing harmless register fixture established from live metadata; no metadata name is invented.

- [ ] **Step 3: Execute each manifest row and record granular evidence**

Run the discovered YAxUnit tag with a parameter filter per manager if supported; otherwise run the complete tag and emit a result row per manager/export. For each failure, record `manager`, `export`, exact arguments, exception/error text and missing provider/metadata/infobase prerequisite in `C18.evidence.contracts`. Do not convert all 90 cells to one blocker because one provider-dependent call failed.

- [ ] **Step 4: Verify completeness and commit/push**

Run a script over the evidence JSON that asserts exactly 15 unique managers, exactly the six required exports per manager, and status `green` or `external-blocker` with the required fields. Then:

```powershell
rg -n "Все15МенеджеровПубликуютОписаниеСправкуИИмя|Все15МенеджеровФормируютКодИТекстСКДДляМодели|Все15МенеджеровИсполняютПредставительнуюМодель" yaxunit/src/CommonModules/КОНС_Обр_ПотребителиПредставлений_МО/Module.bsl
git add -- yaxunit/src/CommonModules/КОНС_Обр_ПотребителиПредставлений_МО docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Охарактеризовать менеджеры представлений"
git push
```

### Task 8: Runtime parser benchmark harness and baseline

**Files:**
- Create through EDT: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/КОНС_Обр_БенчмаркПарсера_МО.mdo`, `.../Module.bsl`
- Create: `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md`
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json`

**Interfaces:**
- Consumes: `Парсер.Разобрать(Текст)` and `РазобратьВыражение(Текст)`, 42 `QueryExamples`, and test-only timing/instrumentation facilities actually available in the discovered runtime.
- Produces: actual UTF-8 JSON result per corpus class with warm-up count, mandatory median/p95 wall-clock, optional internal counters represented as values or `null` plus reason, and mandatory generated BSL function count and LOC. Closes `X01` only after an actual runtime run.

- [ ] **Step 1: Prove available instrumentation before writing benchmark assertions**

Read parser entrypoint and generated module boundaries; record which counters can be collected without production edits. Lack of a test-only interception hook permits only the affected internal counters (`nonterminal_calls`, `dispatch_calls`, `maximum_recursion_depth`, `constructor_action_executions`, `ast_node_container_allocations`) to be `null` with a non-empty per-metric reason. It does not stop wall-clock measurement and does not close `X01` as a blocker. Do not insert counters into `QueryConsoleZUP/src/DataProcessors/Парсер`.

- [ ] **Step 2: Add RED benchmark registration and corpus manifest**

Register one server benchmark test with explicit corpus classes: all 42 `QueryExamples`, large package, long field list, JOIN chain, UNION/package chain, arithmetic chain, logical chain, dereference chain. Store each class identifier and input provenance in the JSON result; synthetic inputs are built by private test helpers with their exact length recorded in that result.

- [ ] **Step 3: Implement test-only measurement and run baseline**

Warm up before measurements, collect multiple samples, compute median and p95 from the sorted sample array, and write JSON only through an approved test-result/output facility discovered in Task 1. The result must identify platform, 1С runtime version, parser artifact identity and every unavailable internal metric as `null` with an explanation; it must not silently report zero. `wall_clock_median_ms` and `wall_clock_p95_ms` must be finite positive numbers for every corpus class. If no verified runner/path exists, no actual baseline is created and handoff remains blocked.

- [ ] **Step 4: Review the baseline and freeze no performance threshold**

Create the baseline matrix only from an actual JSON run. State that Phase 2.5 has no predeclared speedup percentage; later migration must explain wall-clock/generated-size regressions and prove repeat/direct-LR stack depth does not grow with chain length. Never use Python analysis timings as BSL runtime values.

- [ ] **Step 5: Commit and publish**

```powershell
git add -- yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Добавить baseline runtime benchmark парсера"
git push
```

### Task 9: Phase 2.5 closure and migration handoff

**Files:**
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md`
- Create/finalize: `docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json`
- Verify: all Phase 2.5 test modules and `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md`

**Interfaces:**
- Consumes: all task evidence.
- Produces: a machine-checked gate decision for all 18 impact/coverage rows plus the cross-cutting benchmark, or an evidence-backed list of unresolved external blockers. Production handoff additionally requires a verified runner and GREEN `X01` actual before-baseline.

- [ ] **Step 1: Reconcile all mandatory backlog items**

Create the evidence JSON with `schema_version: 1`, a `runner` object and exactly 19 rows keyed by `contract_id`: `C01`–`C18` and `X01`. Each row repeats the exact component label from the impact/coverage matrices, has status `green` or `external-blocker`, and has a non-empty `evidence` array. A GREEN evidence item contains `kind: "test-run"`, the exact module path and module filter, registered test/tag, exact factual command and result reference. Success is represented either by an actual process `exit_code: 0` or by observed JUnit counts with `total > 0`, `failed = 0` and `errors = 0`. When the runner does not expose a process exit code, store `exit_code: null` and a non-empty `exit_code_unavailable_reason`; do not manufacture `0`. A blocker item contains `kind: "external-blocker"`, exact public call, error text and missing prerequisite. `X01` may only be `green` and must reference the actual runtime benchmark JSON/baseline; internal counter gaps belong inside that baseline as `null` plus reason.

Run this mapping/schema gate from repository root:

```powershell
@'
import json
import re
from pathlib import Path

root = Path('.')
impact = (root / 'docs/superpowers/matrices/2026-08-07-query-model-consumer-impact.md').read_text(encoding='utf-8')
coverage = (root / 'docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md').read_text(encoding='utf-8')
evidence_path = root / 'docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json'
payload = json.loads(evidence_path.read_text(encoding='utf-8'))
expected = {f'C{number:02d}' for number in range(1, 19)} | {'X01'}
impact_map = dict(re.findall(r'^\| (C\d{2}) \| ([^|]+?) \|', impact, re.MULTILINE))
coverage_map = dict(re.findall(r'^\| ([CX]\d{2}) \| ([^|]+?) \|', coverage, re.MULTILINE))
rows = payload['contracts']
actual = {row['contract_id'] for row in rows}
normalize = lambda value: value.replace('`', '').strip()
assert payload['schema_version'] == 1
assert set(impact_map) == expected - {'X01'}
assert set(coverage_map) == expected
assert all(normalize(impact_map[key]) == normalize(coverage_map[key]) for key in impact_map)
assert actual == expected and len(rows) == 19
runner = payload['runner']
for key in ('command', 'executable', 'version', 'infobase', 'update_state'):
    assert runner[key]
for row in rows:
    assert normalize(row['component']) == normalize(coverage_map[row['contract_id']])
    assert row['status'] in {'green', 'external-blocker'}
    assert row['evidence']
    if row['status'] == 'green':
        for item in row['evidence']:
            assert item['kind'] == 'test-run'
            assert item['module'] and item['module_filter']
            assert item['test_or_tag'] and item['command'] and item['result_ref']
            exit_code = item.get('exit_code')
            junit = item.get('junit')
            junit_success = (
                isinstance(junit, dict)
                and junit.get('total', 0) > 0
                and junit.get('failed') == 0
                and junit.get('errors') == 0
            )
            assert exit_code == 0 or junit_success
            if exit_code is None:
                assert item.get('exit_code_unavailable_reason')
    else:
        for item in row['evidence']:
            assert item['kind'] == 'external-blocker'
            assert item['call'] and item['error'] and item['prerequisite']
x01 = next(row for row in rows if row['contract_id'] == 'X01')
assert x01['status'] == 'green'
baseline = json.loads(Path(x01['benchmark_result']).read_text(encoding='utf-8'))
assert baseline['corpora']
for corpus in baseline['corpora']:
    assert corpus['wall_clock_median_ms'] > 0
    assert corpus['wall_clock_p95_ms'] > 0
print('phase25_mapping=clean contracts=19 runtime_baseline=actual')
'@ | python -
```

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

Run the discovered YAxUnit command for the complete fresh lexer tag and every new tag. If Task 1 did not discover a verified command, this step cannot complete and handoff is blocked. Expected: no unreported failures; the known Python symlink skip remains limited to WinError 1314.

- [ ] **Step 3: Enforce the gate**

Do not begin EBNF/bindings/LR/model production work unless the 19-row mapping command passes, every `C01`–`C18` row is GREEN or has the precisely documented external blocker permitted by the approved design, the runner identity is complete, and `X01` is GREEN with actual positive median/p95 measurements for every corpus class. Missing runner/path or a wholly unexecuted benchmark is a hard handoff blocker even when test sources and static checks are complete. Do not run Vanessa here: its interactive/form checklist follows the entire migration, after headless contracts and production slices.

- [ ] **Step 4: Commit/push closure evidence and request review**

```powershell
git add -- docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md docs/superpowers/matrices/2026-08-07-grammar-query-model-phase25-evidence.json
git commit -m "Закрыть gate Phase 2.5 headless тестов"
git push
```

Request two reviews: first verifies each matrix backlog item maps to an executable test or an exact external blocker; second verifies no production grammar/model/parser or form-module diff entered the Phase 2.5 commits.

## Self-review

- Mandatory backlog coverage: Task 2 covers fresh lexer plus expression/full-query/parser-semantic handshake (`C02`–`C05`); Task 3 covers factories, dispatcher/template, unknown node and all three visitors (`C01`, `C06`–`C09`, part of `C11`); Task 4 covers builder plus round-trip (`C10`, remainder of `C11`); Task 5 covers executable-view, executor/code and universal-report (`C12`, `C13`, `C16`); Task 6 covers Query Console, Query Constructor and feature-generator golden (`C14`, `C15`, `C17`); Task 7 covers all 15 manager consumers (`C18`); Task 8 records the actual runtime benchmark (`X01`). Task 9 machine-checks all 19 IDs.
- Scope: the plan contains no EBNF, bindings, lowering, Parser IR, LR, production grammar, production model or generated-parser implementation task.
- UI: Query Constructor is explicitly headless first; Vanessa is deferred until after the whole migration.
- Runner integrity: no 1С/YAxUnit/Vanessa invocation was fabricated; its absence is an explicit hard blocker to production-migration handoff that must be resolved with actual environment evidence.
