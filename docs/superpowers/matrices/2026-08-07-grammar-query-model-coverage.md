# Матрица покрытия миграции grammar/query model

## Post-migration evidence — 2026-08-08

Production grammar и query model после systematic migration проверены свежими
прогонами:

- полный Python suite `tools/parsergen/tests`: **508 passed, 1 skipped,
  4 558 subtests passed**; единственный skip — системное ограничение Windows на
  создание symlink (`WinError 1314`);
- expression/full-query parser YAxUnit:
  `КОНС_Обр_Парсер_МО` + `КОНС_Обр_ПарсерЗапросов_МО` — **223/223 GREEN**;
- lexer/model/semantic/executor/codegen/report/other downstream YAxUnit —
  **265 total / 262 passed / 0 failed / 0 errors / 3 documented skips**;
- runtime parser after-benchmark — **1/1 GREEN**;
- суммарный свежий headless integration gate — **489 total / 486 passed /
  0 failed / 0 errors / 3 documented skips**.

Три skip не скрывают parser/model regressions:

1. `ПредставлениеРабочиеМестаСотрудников.ТекстЗапросаДляСКД` блокируется
   существующим production-дефектом `.ОписаниеФильтра` при фактическом
   `.ОписаниеВТФильтр`.
2. Два exact-call контракта Query Constructor требуют form-only
   `ДанныеФормыДерево.FindByID`; headless `ДеревоЗначений` этот API не имеет.

Отчёт parser YAxUnit:
`C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________5c25e5c01_442e96e48351dc418ba0d9c35affb20b53c54ed5\report.md`.
Отчёт downstream YAxUnit:
`C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________ebf4b34ca_763285d8beaa1e61d69ea862760439d79207470a\report.md`.
Отчёт benchmark YAxUnit:
`C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________8acc9b7ac_cb9a94032232579ef15977ae91f60977c6bea36c\report.md`.

`X01` после миграции повторён на том же runtime/corpus: все восемь median и
p95 улучшились. Durable evidence:
[after JSON](2026-08-08-runtime-parser-benchmark-after.json) и
[before/after report](2026-08-08-runtime-parser-benchmark-after.md).
Интерактивный Vanessa/form gate остаётся финальной ручной проверкой и не
заменяет перечисленные headless-контракты.

## Состояние доказательств

- Python: команда `python -m pytest --collect-only -q -p no:cacheprovider`,
  запущенная из `tools/parsergen` с `PYTHONDONTWRITEBYTECODE=1`, собрала **235**
  теста. Число 227 из первоначального brief устарело. Оно также не противоречит
  актуальному результату полного suite, зафиксированному как 234 passed +
  1 skipped: collect-only включает skipped test в инвентарь.
- YAxUnit: после добавления контрактов выполнен свежий совместный runtime-прогон
  модулей lexer, expression parser, full-query parser и semantic analyzer:
  **347 total / 347 passed / 0 failed / 0 errors / 0 skipped**. Отдельный полный
  прогон lexer дал **141/141**. Точные команды и пути отчётов находятся в
  `2026-08-07-grammar-query-model-phase25-evidence.json`.
- Корпус: `QueryExamples` — 42 `.q1c`; в каждом из наборов `ВыполнениеЗапросовВКонсоли`,
  `ГенерацияКодаВКонсоли` и `СозданиеЗапросовВКонструкторе` — по 42 `.feature`.
  Всего прикладных Vanessa-сценариев в этих трёх наборах — 126. До Phase 2.5
  Task 1 Vanessa и YAxUnit в этой задаче не запускались.

## Граница headless-запуска — 2026-08-07

- EDT-MCP обнаружил runtime-client launch configuration `QueryConsoleZUP Тонкий
  клиент` (не запущена), связанный с проектом
  `База_разработки_исполняемых_представлений_демо_ЗУП`. Его infobase:
  `База разработки исполняемых представлений (демо ЗУП)`, исходное состояние
  обновления — `INCREMENTAL_UPDATE_REQUIRED`.
- Фактический runner: `mcp__edt_mcp__run_yaxunit_tests` с
  `launchConfigurationName="QueryConsoleZUP Тонкий клиент"`,
  `extensions=["YAXUNIT"]`, `modules=["КОНС_Обр_Парсер_МО"]`,
  `timeout=60`, `updateBeforeLaunch=true`,
  `updateScope="extension:yaxunit"`. В модуле зарегистрирован тег `Парсер`;
  runner поддерживает module filter, поэтому точечный запуск выбран по модулю.
- После завершения incremental pre-launch запуск дал JUnit-отчёт: **84 total /
  84 passed / 0 failed / 0 errors / 0 skipped**. Полный отчёт сохранён EDT-MCP
  во временном каталоге; контракт успешного вывода — JUnit Markdown report.
- Исполняемый путь/точная версия thin client не раскрываются EDT launch metadata;
  это не подменяется предположением. EDT-MCP: `2026.1.2.2`; compatibility mode
  целевой конфигурации: `8.3.24`.

## Headless-контракты parser → semantic — 2026-08-07

- `C02`: полный существующий lexer module — **141/141 GREEN**.
- `C03`: пять semantic projection cases для выражений: ассоциативность,
  приоритет, порядок разыменования, аргументов функции и ветвей условного
  выражения.
- `C04`: шесть focused full-query cases и фактический
  `QueryExamples/ТестПакетЗапрсов.q1c`; проверены порядок пакета/UNION,
  источники, псевдонимы, поля, LEFT JOIN и граница вложенного запроса.
- `C05`: parser-to-semantic handshake вызывает реальный
  `ОбработкаМоделиЗапроса.ОбработатьМодельЗапроса(ПакетЗапросов)` с одним
  аргументом и проверяет разрешённый источник поля.
- Совместный финальный прогон четырёх модулей — **347/347 GREEN**. Diagnostic
  delta трёх изменённых модулей равна нулю: 92 сообщения до и после.
- Текущая правая ассоциативность `1 - 2 - 3` зафиксирована только как временный,
  ненормативный baseline известного дефекта. Direct-LR migration обязана
  заменить его левым сворачиванием `((1 - 2) - 3)`.

## Headless-контракты исполняемых представлений — 2026-08-07

- Новый серверный модуль `КОНС_Обр_ИсполняемыеПредставления_МО` прошёл
  focused-прогон **3/3 GREEN** и совместный прогон с ранее добавленными
  Phase 2.5 модулями **219/219 GREEN**.
- `C12`: сырой parser-source преобразуется через public API в исполняемое
  представление; явный параметр `Отбор` делегируется в source, а остаточная
  секция `ГДЕ` сохраняется.
- `C13`: на модели `ИсполняемоеПредставление.Периоды` проверены предметные
  фрагменты generated BSL и текста СКД, исходные query parameters и отсутствие
  технического executable source в результате для СКД.
- `C16`: универсальный отчёт добавляет декларацию временной таблицы, заменяет
  executable source на `ИсточникДанныхВременнаяТаблица` и сохраняет имена
  таблицы, псевдонима и выбранного поля.
- Все три проверки выполнены через серверные public interfaces без форм и без
  Vanessa; external blockers не обнаружены.
- После object revalidation у нового модуля нет BSL-проблем; остаётся один
  известный metadata marker `extension-md-object-prefix`, обусловленный
  утверждённым проектным именем тестового модуля.

## Headless-контракты прикладных потребителей — 2026-08-07

- Новый серверный модуль `КОНС_Обр_ПрикладныеПотребителиЗапроса_МО` прошёл
  focused/combined gate: **6 total / 4 passed / 0 failed / 0 errors / 2 skipped**;
  совместный прогон семи Phase 2.5 модулей — **225 total / 223 passed /
  0 failed / 0 errors / 2 skipped**.
- `C14`: прямые вызовы `КонсольЗапросов.ВыполнитьЗапрос` и
  `ПреобразоватьВМетаданные` прошли focused-прогон **2/2 GREEN**; проверены
  колонка/строка результата и литеральные identity/cost поля плана.
- `C15`: `GetSchemaQuery` прошёл **1/1 GREEN** для двух различимых вложенных
  источников: позиция `[0, 1]` выбрала второй запрос с одним источником, тогда
  как первый имеет ноль источников; пара индексов сохранилась. Контрольная
  мутация `[0, 1] → [0, 0]` дала **0 passed / 1 failed** на сравнении `0 != 1`,
  после восстановления focused-тест снова GREEN. `AvailableTablesBeforeExpandAtServer`
  и `SourcesBeforeExpandAtServer` отдельно дошли до production object module
  и завершились точной ошибкой `Метод объекта не обнаружен (FindByID)`:
  headless `ДеревоЗначений` не заменяет требуемое `ДанныеФормыДерево`. После
  фиксации failing-run evidence оба зарегистрированных теста используют
  штатный `ЮТест.Пропустить` с этой причиной; формы и production не менялись.
- `C17`: реальный `ГенераторFeatureФайлов` с реальным expression generator и
  `ТекстовыйДокумент` прошёл **1/1 GREEN**; две ожидаемые строки feature-текста
  заданы независимыми литералами в тестовом модуле.
- EDT object revalidation не выявила BSL-проблем; остаётся только известный
  marker `extension-md-object-prefix` из-за утверждённого имени модуля.

## Решения о покрытии

| Contract ID | Consumer | Affected | Current automated evidence | Gap | Phase 2.5 test | Gate type |
|---|---|---|---|---|---|---|
| C01 | AST factories | Да: 91 `Новый*` factory из `ЭлементыМоделиЗапроса/Module.bsl` создают структуры query model. | Fresh Task 3 run: 97/97; explicit 91-row inventory, 91 unique rows, три семейства 51/35/5. | Закрыт: defaults и пустые collection/map contracts проверены для каждого export. | `ФабрикиВыраженийСоздаютОжидаемыеСвойства`; `ФабрикиПакетаЗапросаИИсточниковСоздаютОжидаемыеСвойства`; `ОстальныеФабрикиТиповИИсполняемыхПредставленийСоздаютОжидаемыеСвойства`. | new-headless-test |
| C02 | Lexer | Да: `ЛексическийАнализатор/ObjectModule.bsl` производит токены для parser. | Fresh full-module runtime run 2026-08-07: 141/141 passed. | Закрыт для текущего token/EOF/error baseline. | Полный существующий lexer module; evidence manifest содержит command/result/report. | existing-automated |
| C03 | Expression parser | Да: `Парсер/ObjectModule.bsl.РазобратьВыражение` строит expression AST. | Fresh combined run 2026-08-07: 347/347; пять semantic projection cases. | Закрыт для выбранной проекции; правая ассоциативность вычитания помечена ненормативным defect baseline. | Exact operand/operator, precedence, dereference, arguments and conditional ordering. | new-headless-test |
| C04 | Full-query parser | Да: `Парсер/ObjectModule.bsl.Разобрать` строит package/query/source/field/filter model. | Fresh combined run 2026-08-07: 347/347; шесть focused cases + фактический `ТестПакетЗапрсов.q1c`. | Закрыт для package/source/alias/field/join/nested/union projection. | Семантическая проекция и corpus assertion порядка трёх UNION-members. | new-headless-test |
| C05 | Semantic analyzer | Да: `ОбработкаМоделиЗапроса/Module.bsl.ОбработатьМодельЗапроса`, `ОбработатьВыражение`, `ОбработатьУсловие`. | Fresh combined run 2026-08-07: 347/347; parser-to-semantic handshake. | Закрыт для source/alias/inferred field alias/resolved field source contract. | Реальный одноаргументный semantic entrypoint и explicit model assertions. | new-headless-test |
| C06 | Expression dispatcher/template | Да: `ОбходМоделиЯзыкаВыражений/Module.bsl.ОбойтиДерево`, 59 template callbacks. | Fresh Task 3 run: explicit expected traversal invokes all 59 callbacks in enter/exit order. | Закрыт; static set comparison template↔dispatcher также clean. | `ДиспетчерВызываетВсе59КолбэковВПорядкеОбхода`. | new-headless-test |
| C07 | Semantic visitor | Да: `СемантическийАнализВыраженийПосетитель/ObjectModule.bsl.УстановитьКонтекст`. | Fresh Task 3 run: real visitor lifecycle preserves numeric type and aggregate flag. | Закрыт для isolated aggregate/type contract. | `СемантическийПосетительСохраняетТипыИАгрегаты`. | new-headless-test |
| C08 | Filter applicability visitor | Да: `ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl.ВыделитьИМодифицироватьОтбор`. | Fresh Task 3 run: delegatable, mixed `И` and prohibited `ИЛИ` paths executed headlessly. | Закрыт для delegation/split/residual contract. | `ПосетительОтбораРазделяетДелегируемыеСмешанныеИНедопустимыеУсловия`. | new-headless-test |
| C09 | SKD dereference visitor | Да: `ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl.УстановитьКонтекст`. | Fresh Task 3 run: `Справочник.Организации.Ссылка.Наименование` conversion checked on real metadata. | Закрыт для reference type/dereference output shape. | `ПосетительСКДПреобразуетРазыменованиеИТип`. | new-headless-test |
| C10 | Model builder | Да: `ПостроительМоделиЗапроса/ObjectModule.bsl.ДобавитьИсточник`, `ДобавитьОтбор`, `ДобавитьУпорядочивание`, `ДобавитьКонтрольнуюТочкуИтогов`, `УстановитьПолучениеОбщихИтогов`. | Fresh Task 4 module run: 2/2 passed; mutation test checks state after every public operation. | Закрыт: source identity/alias, filter, ordering, totals point and general-totals flag protected headlessly. | `ПостроительМеняетИсточникиОтборСортировкуИИтогиПоШагам`. | new-headless-test |
| C11 | Query/expression text generation | Да: `ГенерацияТекстовЗапросов/Module.bsl.ТекстПакетаЗапросов`, `ВыражениеВСтроку`. | Task 3 covers the real unknown-node error; fresh Task 4 module run 2/2 covers semantic model → text → model. | Закрыт: package/operator order, source, field, filter, order and totals projection survives generation and reparsing. | `НеизвестныйУзелВыраженияВызываетИсключениеГенератораТекста`; `ТекстПакетаПослеПовторногоРазбораСохраняетСемантику`. | new-headless-test |
| C12 | Executable-view processing | Да: `ОбработкаПредставлениеЗапросов/Module.bsl.ОбработатьИсточникЗапроса`, `ИсполняемоеПредставлениеПоОписанию`. | Fresh Task 5 module run: 3/3 passed; combined Phase 2.5 run: 219/219 passed. | Закрыт: transform/delegation projection проверяет provider-built identity, explicit `Отбор` и сохранение residual `ГДЕ`. | `ИсполняемоеПредставлениеПреобразуетИДелегируетОтбор`. | new-headless-test |
| C13 | Executor/code/SKD generation | Да: `ИсполнительПредставлений/Module.bsl.ВыполнитьПакетЗапросов`, `ПолучитьИсполняемыйКод`, `ПолучитьТекстЗапросаДляСКД`. | Fresh Task 5 module run: 3/3 passed; generated BSL и СКД проходят общий executor traversal на parser-built модели. | Закрыт для code/SKD generation: проверены предметный generator call, ВТ identity, period parameters и удаление executable source из СКД-текста. | `ИсполнительФормируетКодИТекстСКДДляПредставительнойМодели`. | new-headless-test |
| C14 | Query console underlying logic | Да: `КонсольЗапросов/ObjectModule.bsl.ВыполнитьЗапрос`, `ПреобразоватьВМетаданные`. | Fresh Task 6 focused run: 2/2 passed; combined Phase 2.5 run: 225 total / 223 passed / 2 documented C15 skips. | Закрыт для прямых headless object-call contracts; интерактивный form flow остаётся последующим gate. | `КонсольВыполняетМинимальныйЗапросБезФормы`; `КонсольПреобразуетПланВМетаданныеБезФормы`. | new-headless-test |
| C15 | Query Constructor underlying logic | Да: `КонструкторЗапросов/ObjectModule.bsl.AvailableTablesBeforeExpandAtServer`, `SourcesBeforeExpandAtServer`, `GetSchemaQuery`. | `GetSchemaQuery` GREEN 1/1 на двух различимых nested sources и позиции `[0, 1]`; mutation `[0, 0]` RED 0/1; combined module gate 6 total / 4 passed / 2 skipped. Оба tree-expansion calls воспроизведены отдельно и сохранены как exact runtime blockers. | `AvailableTablesBeforeExpandAtServer` и `SourcesBeforeExpandAtServer` требуют `ДанныеФормыДерево.FindByID`; headless `ДеревоЗначений` не предоставляет этот API. Это external blocker, не manual-only классификация. | `СхемаЗапросаВозвращаетсяДляВложеннойПозиции` GREEN и различает source index по 0/1 source count; два экспортных exact-call characterization зарегистрированы и штатно skipped после фиксации failing-run evidence. | external-blocker |
| C16 | Universal report | Да: `УниверсальныйОтчетРасширенный/Module.bsl.ЗаменитьИсполняемыеПредставленияВременнымиТаблицами`. | Fresh Task 5 module run: 3/3 passed; combined Phase 2.5 run: 219/219 passed. | Закрыт: проверены декларация ВТ, замена source и сохранение table/alias/column identities. | `УниверсальныйОтчетЗаменяетИсполняемыеПредставленияВременнымиТаблицами`. | new-headless-test |
| C17 | Feature-generation helpers | Да: `ГенераторFeatureФайлов/ObjectModule.bsl.СценарийСозданияПакетаЗапросаВТекДок`. | Fresh Task 6 focused run: 1/1 passed; independent two-line literal golden matched. | Закрыт: expected строки хранятся литерально в тесте и не выводятся production generator-ом. | `ГенераторFeatureФайловФормируетЭталонПакетаЗапроса`. | new-headless-test |
| C18 | 15 `Представление*` manager consumers | Да: каждый direct consumer вызывает `МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель)`; перечень путей — в impact matrix. | Fresh Task 7 module run: 90 total / 89 passed / 1 documented skip; final combined 10-module Phase 2.5 gate including X01: 457 total / 454 passed / 3 skips. Покрыты 15 managers × exports `Описание`, `Справка`, `ИмяПредставления`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД`, `Исполнить`. | Один exact external blocker: `Обработки.ПредставлениеРабочиеМестаСотрудников.ТекстЗапросаДляСКД(ПараметрыВыполнения)` падает на production `ManagerModule.bsl:275` с `Поле объекта не обнаружено (ОписаниеФильтра)`; live factory предоставляет `ОписаниеВТФильтр`. Требуется production fix `.ОписаниеФильтра` → `.ОписаниеВТФильтр`. Остальные 89 cells GREEN; `ОстаткиОтпусков` direct SKD export GREEN, central capability нормативно остаётся `Ложь`. | Шесть static adapters содержат все 15 литеральных `Обработки.<Manager>.<Export>` calls; generation проверяет parseable SKD, ВТ/source identity и отсутствие executable source, execution — создаваемую ВТ и колонку результата. Blocked cell зарегистрирован и штатно skipped только после сохранения failing-run evidence 15 total / 14 passed / 1 error. | external-blocker |

## Точный backlog Phase 2.5

Backlog состоит из всех строк `C01`–`C18`, а не из сокращённого списка
типов тестов. Cross-cutting runtime gate имеет отдельный ID `X01`. Один
vertical slice может закрыть несколько IDs, но evidence фиксируется отдельно
для каждого ID: executable test/tag и actual run либо exact runtime blocker.

## Cross-cutting gate: runtime parser benchmark harness

| Contract ID | Owner/runtime target | Current automated evidence | Observable artifact and required metrics | Corpus classes from approved design | Phase 2.5 test | Gate type |
|---|---|---|---|---|---|---|
| X01 | New test/benchmark harness owned by the production parser entrypoints `DataProcessors/Парсер/ObjectModule.bsl.Разобрать` and `РазобратьВыражение` | GREEN 1/1: `КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineПарсераФормируется`, tag `БенчмаркПарсера`. Actual result: `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-before.json`; readable report: `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-baseline.md`; runner sidecar: `C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________f49cea393_39767d76ab1d38f5fadfa5c32807961daa03e544\runtime-parser-benchmark-before.json`. | Three warm-ups and 20 samples per corpus. Median/p95, ms: `query_examples_all_42` 1679.5/2030; `large_package` 161.5/195; `long_field_list` 161.5/192; `join_chain` 68.5/80; `union_package_chain` 96.5/125; `arithmetic_chain` 65.5/96; `logical_chain` 77/109; `dereference_chain` 20/32. Parser artifact SHA256 `0c365e1e521322554b63e400379be47c0dc5ecaa7f60dd6951dc84bc7cccd084`, 3394 LOC, 135 functions (141 routines including 6 procedures; 124 nonterminal functions). `nonterminal_calls`, `dispatch_calls`, `maximum_recursion_depth`, `constructor_action_executions` and `ast_node_container_allocations` are each `null` with a non-empty reason: production instrumentation is intentionally absent and was not added for the benchmark. | 42 exact XML `/querylist/query/text` inputs from `QueryExamples` with provenance; large package; synthetic long field list; JOIN chain; UNION/package chain; long arithmetic, logical and dereference chains. | Actual before-baseline recorded before the first production grammar/model change; all eight corpora have positive median/p95. No production counters or production parser changes were introduced. | new-headless-test |

После выполнения headless backlog выполняется интерактивный/form Vanessa gate.
Он не заменяет headless contracts и не переводит Query Constructor в manual-only:
его non-form dependencies остаются обязательной ранней проверкой.

## Проверка соответствия строкам Task 3

- [x] `C01` AST factories → AST factories
- [x] `C02` Lexer → Lexer
- [x] `C03` Expression parser → Expression parser
- [x] `C04` Full-query parser → Full-query parser
- [x] `C05` Semantic analyzer → Semantic analyzer
- [x] `C06` Expression dispatcher/template → Expression dispatcher/template
- [x] `C07` Semantic visitor → Semantic visitor
- [x] `C08` Filter applicability visitor → Filter applicability visitor
- [x] `C09` SKD dereference visitor → SKD dereference visitor
- [x] `C10` Model builder → Model builder
- [x] `C11` Query/expression text generation → Query/expression text generation
- [x] `C12` Executable-view processing → Executable-view processing
- [x] `C13` Executor/code/SKD generation → Executor/code/SKD generation
- [x] `C14` Query console underlying logic → Query console underlying logic
- [x] `C15` Query Constructor underlying logic → Query Constructor underlying logic
- [x] `C16` Universal report → Universal report
- [x] `C17` Feature-generation helpers → Feature-generation helpers
- [x] `C18` 15 `Представление*` manager consumers → 15 `Представление*` manager consumers
- [x] `X01` cross-cutting runtime parser benchmark → benchmark gate

Связанные evidence: [impact matrix](2026-08-07-query-model-consumer-impact.md),
[foundation plan](../plans/2026-08-07-grammar-query-model-foundation.md).
