# Матрица покрытия миграции grammar/query model

## Состояние доказательств

- Python: команда `python -m pytest --collect-only -q -p no:cacheprovider`,
  запущенная из `tools/parsergen` с `PYTHONDONTWRITEBYTECODE=1`, собрала **235**
  теста. Число 227 из первоначального brief устарело. Оно также не противоречит
  актуальному результату полного suite, зафиксированному как 234 passed +
  1 skipped: collect-only включает skipped test в инвентарь.
- YAxUnit: EDT-MCP прочитал статические структуры в проекте `yaxunit`:
  лексер — 18 процедур; parser expression — 30 процедур и 1 функция; parser
  query — 31 процедура и 3 функции; parser future grammar — 5 процедур;
  обработка модели — 12 процедур и 6 функций. Это регистрация исходных
  тестовых процедур, а не результат свежего запуска.
- Корпус: `QueryExamples` — 42 `.q1c`; в каждом из наборов `ВыполнениеЗапросовВКонсоли`,
  `ГенерацияКодаВКонсоли` и `СозданиеЗапросовВКонструкторе` — по 42 `.feature`.
  Всего прикладных Vanessa-сценариев в этих трёх наборах — 126. Vanessa и
  YAxUnit в этой задаче не запускались.

## Решения о покрытии

| Contract ID | Consumer | Affected | Current automated evidence | Gap | Phase 2.5 test | Gate type |
|---|---|---|---|---|---|---|
| C01 | AST factories | Да: 91 `Новый*` factory из `ЭлементыМоделиЗапроса/Module.bsl` создают структуры query model. | Косвенно: parser/semantic YAxUnit. | Нет contract factory→свойства/коллекции. | Factory contracts по семействам AST; factory-dispatcher-template completeness. | new-headless-test |
| C02 | Lexer | Да: `ЛексическийАнализатор/ObjectModule.bsl` производит токены для parser. | Static `КОНС_Обр_ЛексическийАнализатор_МО`: 18 процедур, включая `ИсполняемыеСценарии`; fresh run отсутствует. | Исходный token/EOF/error regression не прогонялся в актуальной incremental базе. | Выполнить полный существующий тег `Лексер` свежим runtime run и сохранить command/exit/result evidence. | existing-automated |
| C03 | Expression parser | Да: `Парсер/ObjectModule.bsl.РазобратьВыражение` строит expression AST. | Static `КОНС_Обр_Парсер_МО`: 30 процедур, 1 функция; fresh run отсутствует. | Binding properties и semantic contracts не выделены. | Добавить expression AST semantic cases и включить существующий YAxUnit module. | new-headless-test |
| C04 | Full-query parser | Да: `Парсер/ObjectModule.bsl.Разобрать` строит package/query/source/field/filter model. | Static `КОНС_Обр_ПарсерЗапросов_МО`: 31 процедура, 3 функции; 42 QueryExamples. | Нет закреплённого property corpus. | Semantic sources/aliases/joins/fields/nested/union на curated QueryExamples; full-query parser regression. | new-headless-test |
| C05 | Semantic analyzer | Да: `ОбработкаМоделиЗапроса/Module.bsl.ОбработатьМодельЗапроса`, `ОбработатьВыражение`, `ОбработатьУсловие`. | Static `КОНС_ОМ_ОбработкаМоделиЗапроса`: 12 процедур, 6 функций. | Источники/metadata/parser lanes не характеризованы end-to-end. | Semantic sources/aliases/joins/fields/nested/union с явными model assertions. | new-headless-test |
| C06 | Expression dispatcher/template | Да: `ОбходМоделиЯзыкаВыражений/Module.bsl.ОбойтиДерево`, 59 template callbacks. | Direct automated test не найден. | Не проверены все node kinds и порядок callbacks. | Factory-dispatcher-template completeness: 59 callback order/coverage contract. | new-headless-test |
| C07 | Semantic visitor | Да: `СемантическийАнализВыраженийПосетитель/ObjectModule.bsl.УстановитьКонтекст`. | Косвенно через static semantic YAxUnit. | Public object contract не изолирован. | Concrete visitor behavior contract №1: semantic types/aggregate flags. | new-headless-test |
| C08 | Filter applicability visitor | Да: `ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl.ВыделитьИМодифицироватьОтбор`. | Console/constructor Vanessa scenarios существуют, свежий запуск отсутствует. | Headless delegatable/mixed/prohibited contract отсутствует. | Concrete visitor behavior contract №2: executable-view filter transformation/delegation. | new-headless-test |
| C09 | SKD dereference visitor | Да: `ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl.УстановитьКонтекст`. | Direct automated test не найден. | Нет output-shape contract. | Concrete visitor behavior contract №3: dereference/type conversion cases. | new-headless-test |
| C10 | Model builder | Да: `ПостроительМоделиЗапроса/ObjectModule.bsl.ДобавитьИсточник`, `ДобавитьОтбор`, `ПолучитьМодель`. | Direct automated test не найден. | Мутации object module не зафиксированы. | Headless builder mutations: source/filter/order/totals mutation sequence. | new-headless-test |
| C11 | Query/expression text generation | Да: `ГенерацияТекстовЗапросов/Module.bsl.ТекстПакетаЗапросов`, `ВыражениеВСтроку`. | Feature output evidence; fresh Vanessa отсутствует. | Нет headless golden/unknown-node error. | Model → text → model semantic round-trip; unknown expression node error in text generation. | new-headless-test |
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
