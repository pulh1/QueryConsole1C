# Матрица покрытия миграции grammar/query model

## Состояние доказательств

- Python: команда `python -m pytest --collect-only -q -p no:cacheprovider`,
  запущенная из `tools/parsergen` с `PYTHONDONTWRITEBYTECODE=1`, собрала **234**
  теста. Число 227 из первоначального brief устарело. Оно также не противоречит
  актуальному результату полного suite, ранее зафиксированному как 233 passed +
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

| Consumer | Affected | Current automated evidence | Gap | Phase 2.5 test | Gate type |
|---|---|---|---|---|---|
| AST factories | Да: 91 `Новый*` factory из `ЭлементыМоделиЗапроса/Module.bsl` создают структуры query model. | Косвенно: parser/semantic YAxUnit. | Нет contract factory→свойства/коллекции. | Factory contracts по семействам AST; factory-dispatcher-template completeness. | new-headless-test |
| Lexer | Да: `ЛексическийАнализатор/ObjectModule.bsl` производит токены для parser. | Static `КОНС_Обр_ЛексическийАнализатор_МО`: 18 процедур, включая `ИсполняемыеСценарии`; fresh run отсутствует. | Нет отдельного нового semantic corpus. | Сохранить и прогнать token/EOF/error characterization как существующий регрессионный gate. | existing-automated |
| Expression parser | Да: `Парсер/ObjectModule.bsl.РазобратьВыражение` строит expression AST. | Static `КОНС_Обр_Парсер_МО`: 30 процедур, 1 функция; fresh run отсутствует. | Binding properties и semantic contracts не выделены. | Добавить expression AST semantic cases и включить существующий YAxUnit module. | new-headless-test |
| Full-query parser | Да: `Парсер/ObjectModule.bsl.Разобрать` строит package/query/source/field/filter model. | Static `КОНС_Обр_ПарсерЗапросов_МО`: 31 процедура, 3 функции; 42 QueryExamples. | Нет закреплённого property corpus. | Semantic sources/aliases/joins/fields/nested/union на curated QueryExamples; full-query parser regression. | new-headless-test |
| Semantic analyzer | Да: `ОбработкаМоделиЗапроса/Module.bsl.ОбработатьМодельЗапроса`, `ОбработатьВыражение`, `ОбработатьУсловие`. | Static `КОНС_ОМ_ОбработкаМоделиЗапроса`: 12 процедур, 6 функций. | Источники/metadata/parser lanes не характеризованы end-to-end. | Semantic sources/aliases/joins/fields/nested/union с явными model assertions. | new-headless-test |
| Expression dispatcher/template | Да: `ОбходМоделиЯзыкаВыражений/Module.bsl.ОбойтиДерево`, 59 template callbacks. | Direct automated test не найден. | Не проверены все node kinds и порядок callbacks. | Factory-dispatcher-template completeness: 59 callback order/coverage contract. | new-headless-test |
| Semantic visitor | Да: `СемантическийАнализВыраженийПосетитель/ObjectModule.bsl.УстановитьКонтекст`. | Косвенно через static semantic YAxUnit. | Public object contract не изолирован. | Concrete visitor behavior contract №1: semantic types/aggregate flags. | new-headless-test |
| Filter applicability visitor | Да: `ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl.ВыделитьИМодифицироватьОтбор`. | Console/constructor Vanessa scenarios существуют, свежий запуск отсутствует. | Headless delegatable/mixed/prohibited contract отсутствует. | Concrete visitor behavior contract №2: executable-view filter transformation/delegation. | new-headless-test |
| SKD dereference visitor | Да: `ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl.УстановитьКонтекст`. | Direct automated test не найден. | Нет output-shape contract. | Concrete visitor behavior contract №3: dereference/type conversion cases. | new-headless-test |
| Model builder | Да: `ПостроительМоделиЗапроса/ObjectModule.bsl.ДобавитьИсточник`, `ДобавитьОтбор`, `ПолучитьМодель`. | Direct automated test не найден. | Мутации object module не зафиксированы. | Headless builder mutations: source/filter/order/totals mutation sequence. | new-headless-test |
| Query/expression text generation | Да: `ГенерацияТекстовЗапросов/Module.bsl.ТекстПакетаЗапросов`, `ВыражениеВСтроку`. | Feature output evidence; fresh Vanessa отсутствует. | Нет headless golden/unknown-node error. | Model → text → model semantic round-trip; unknown expression node error in text generation. | new-headless-test |
| Executable-view processing | Да: `ОбработкаПредставлениеЗапросов/Module.bsl.ОбработатьИсточникЗапроса`, `ИсполняемоеПредставлениеПоОписанию`. | Console execution features существуют, свежий запуск отсутствует. | Нет transform/delegation contract. | Executable-view filter transformation/delegation in headless fixture. | new-headless-test |
| Executor/code/SKD generation | Да: `ИсполнительПредставлений/Module.bsl.ВыполнитьПакетЗапросов`, `ПолучитьИсполняемыйКод`, `ПолучитьТекстЗапросаДляСКД`. | Console execution/code feature suites существуют. | Нет focused headless snapshots/integration. | Executor/code-generation focused integration for representative model. | new-headless-test |
| Query console underlying logic | Да: `КонсольЗапросов/ObjectModule.bsl.ВыполнитьЗапрос`, `ПреобразоватьВМетаданные`. | 42 execution/code features; fresh Vanessa отсутствует. | Object-module contract не изолирован от form workflow. | Direct headless object characterization; interactive console flow only after headless gate. | new-headless-test |
| Query Constructor underlying logic | Да: `КонструкторЗапросов/ObjectModule.bsl.AvailableTablesBeforeExpandAtServer`, `SourcesBeforeExpandAtServer`, `GetSchemaQuery`. | 42 constructor features; fresh Vanessa отсутствует. | Stable non-form chain ещё не доказана, но это не manual-only. | Query Constructor non-form dependencies: characterize public object calls and stable chain before final UI gate. | new-headless-test |
| Universal report | Да: `УниверсальныйОтчетРасширенный/Module.bsl.ЗаменитьИсполняемыеПредставленияВременнымиТаблицами`. | Direct automated test не найден. | Common/object transformation contract отсутствует. | Universal-report non-form transformations. | new-headless-test |
| Feature-generation helpers | Да: `ГенераторFeatureФайлов/ObjectModule.bsl.СценарийСозданияПакетаЗапросаВТекДок`. | Сгенерированные suites — downstream evidence. | Нет direct helper golden. | Model-to-feature golden with generated oracle content. | new-headless-test |
| 15 `Представление*` manager consumers | Да: каждый direct consumer вызывает `МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель)`; перечень путей — в impact matrix. | Соответствующие Vanessa workflows существуют. | Provider dispatch и infobase dependencies требуют runtime trace. | Пер-manager exported-function characterization после доступного runtime fixture; representative Vanessa после headless gates. | external-blocker |

## Точный backlog Phase 2.5

1. semantic sources/aliases/joins/fields/nested/union.
2. factory-dispatcher-template completeness.
3. unknown expression node error in text generation.
4. three concrete visitor behavior contracts.
5. headless builder mutations.
6. model → text → model semantic round-trip.
7. executable-view filter transformation/delegation.
8. executor/code-generation focused integration.
9. universal-report non-form transformations.
10. Query Constructor non-form dependencies.
11. runtime parser benchmark harness — отдельный cross-cutting headless gate ниже;
    Python analysis timing is insufficient.

## Cross-cutting gate: runtime parser benchmark harness

| Owner/runtime target | Current automated evidence | Observable artifact and required metrics | Corpus classes from approved design | Phase 2.5 test | Gate type |
|---|---|---|---|---|---|
| New test/benchmark harness owned by the production parser entrypoints `DataProcessors/Парсер/ObjectModule.bsl.Разобрать` and `РазобратьВыражение` | Нет runtime harness; baseline matrix records only static/analysis metrics. | Machine-readable benchmark result for every corpus class: warm-up parse wall-clock median/p95, production nonterminal calls, dispatch calls, maximum recursion depth, constructor/semantic-action executions and AST node/container allocation count; generated BSL function count and LOC. Test instrumentation only; no production counters. | 42 `QueryExamples`; большой пакетный запрос; synthetic long field list; synthetic JOIN chain; synthetic UNION/package chain; long arithmetic, logical and dereference chains. | runtime parser benchmark harness records the listed metrics before the first production grammar/model change; no launch command is specified until the harness exists. | new-headless-test |

После выполнения headless backlog выполняется интерактивный/form Vanessa gate.
Он не заменяет headless contracts и не переводит Query Constructor в manual-only:
его non-form dependencies остаются обязательной ранней проверкой.

## Проверка соответствия строкам Task 3

- [x] AST factories → AST factories
- [x] Lexer → Lexer
- [x] Expression parser → Expression parser
- [x] Full-query parser → Full-query parser
- [x] Semantic analyzer → Semantic analyzer
- [x] Expression dispatcher/template → Expression dispatcher/template
- [x] Semantic visitor → Semantic visitor
- [x] Filter applicability visitor → Filter applicability visitor
- [x] SKD dereference visitor → SKD dereference visitor
- [x] Model builder → Model builder
- [x] Query/expression text generation → Query/expression text generation
- [x] Executable-view processing → Executable-view processing
- [x] Executor/code/SKD generation → Executor/code/SKD generation
- [x] Query console underlying logic → Query console underlying logic
- [x] Query Constructor underlying logic → Query Constructor underlying logic
- [x] Universal report → Universal report
- [x] Feature-generation helpers → Feature-generation helpers
- [x] 15 `Представление*` manager consumers → 15 `Представление*` manager consumers

Связанные evidence: [impact matrix](2026-08-07-query-model-consumer-impact.md),
[foundation plan](../plans/2026-08-07-grammar-query-model-foundation.md).
