# Матрица покрытия миграции grammar/query model

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
| C10 | Model builder | Да: `ПостроительМоделиЗапроса/ObjectModule.bsl.ДобавитьИсточник`, `ДобавитьОтбор`, `ПолучитьМодель`. | Direct automated test не найден. | Мутации object module не зафиксированы. | Headless builder mutations: source/filter/order/totals mutation sequence. | new-headless-test |
| C11 | Query/expression text generation | Да: `ГенерацияТекстовЗапросов/Module.bsl.ТекстПакетаЗапросов`, `ВыражениеВСтроку`. | Task 3 fresh run closes the real two-argument unknown-node error path. | Частично: Task 4 still must add model → text → model semantic round-trip before GREEN. | `НеизвестныйУзелВыраженияВызываетИсключениеГенератораТекста`; round-trip remains Task 4. | new-headless-test |
| C12 | Executable-view processing | Да: `ОбработкаПредставлениеЗапросов/Module.bsl.ОбработатьИсточникЗапроса`, `ИсполняемоеПредставлениеПоОписанию`. | Console execution features существуют, свежий запуск отсутствует. | Нет transform/delegation contract. | Executable-view filter transformation/delegation in headless fixture. | new-headless-test |
| C13 | Executor/code/SKD generation | Да: `ИсполнительПредставлений/Module.bsl.ВыполнитьПакетЗапросов`, `ПолучитьИсполняемыйКод`, `ПолучитьТекстЗапросаДляСКД`. | Console execution/code feature suites существуют. | Нет focused headless snapshots/integration. | Executor/code-generation focused integration for representative model. | new-headless-test |
| C14 | Query console underlying logic | Да: `КонсольЗапросов/ObjectModule.bsl.ВыполнитьЗапрос`, `ПреобразоватьВМетаданные`. | 42 execution/code features; fresh Vanessa отсутствует. | Object-module contract не изолирован от form workflow. | Direct headless object characterization of `ВыполнитьЗапрос` and `ПреобразоватьВМетаданные`; interactive flow only after headless gate. | new-headless-test |
| C15 | Query Constructor underlying logic | Да: `КонструкторЗапросов/ObjectModule.bsl.AvailableTablesBeforeExpandAtServer`, `SourcesBeforeExpandAtServer`, `GetSchemaQuery`. | 42 constructor features; fresh Vanessa отсутствует. | Stable non-form chain ещё не доказана, но это не manual-only. | Query Constructor non-form dependencies: characterize public object calls and stable chain before final UI gate. | new-headless-test |
| C16 | Universal report | Да: `УниверсальныйОтчетРасширенный/Module.bsl.ЗаменитьИсполняемыеПредставленияВременнымиТаблицами`. | Direct automated test не найден. | Common/object transformation contract отсутствует. | Universal-report non-form transformations. | new-headless-test |
| C17 | Feature-generation helpers | Да: `ГенераторFeatureФайлов/ObjectModule.bsl.СценарийСозданияПакетаЗапросаВТекДок`. | Сгенерированные suites — downstream evidence. | Нет direct helper golden. | Model-to-feature golden with generated oracle content. | new-headless-test |
| C18 | 15 `Представление*` manager consumers | Да: каждый direct consumer вызывает `МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель)`; перечень путей — в impact matrix. | Соответствующие Vanessa workflows существуют. | Provider dispatch и infobase dependencies ещё не проверены фактическим runtime trace. | Для каждого из 15 managers проверить exports `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД`; каждый незапускаемый contract получает exact failing call/prerequisite blocker. | new-headless-test |

## Точный backlog Phase 2.5

Backlog состоит из всех строк `C01`–`C18`, а не из сокращённого списка
типов тестов. Cross-cutting runtime gate имеет отдельный ID `X01`. Один
vertical slice может закрыть несколько IDs, но evidence фиксируется отдельно
для каждого ID: executable test/tag и actual run либо exact runtime blocker.

## Cross-cutting gate: runtime parser benchmark harness

| Contract ID | Owner/runtime target | Current automated evidence | Observable artifact and required metrics | Corpus classes from approved design | Phase 2.5 test | Gate type |
|---|---|---|---|---|---|---|
| X01 | New test/benchmark harness owned by the production parser entrypoints `DataProcessors/Парсер/ObjectModule.bsl.Разобрать` and `РазобратьВыражение` | Нет runtime harness; baseline matrix records only static/analysis metrics. | Machine-readable actual benchmark result for every corpus class: warm-up parse wall-clock median/p95 are mandatory; nonterminal calls, dispatch calls, maximum recursion depth, constructor/semantic-action executions and AST node/container allocation count are values or `null` plus a non-empty reason; generated BSL function count and LOC are mandatory. Test instrumentation only; no production counters. | 42 `QueryExamples`; большой пакетный запрос; synthetic long field list; synthetic JOIN chain; synthetic UNION/package chain; long arithmetic, logical and dereference chains. | Runtime parser benchmark records a before-baseline before the first production grammar/model change. Missing verified runner/path blocks migration handoff; it cannot close X01 as a passed blocker. | new-headless-test |

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
