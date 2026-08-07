# Матрица влияния потребителей модели запроса

Состояние: `feature/grammar-optimization`, HEAD `d4ca830`.
Обозначения: **[Факт]** — подтверждено EDT-MCP/Serena/поиском; **[Вывод]** — будущий test requirement; **[Динамика]** — вызов обработки требует runtime trace.

## Реестр доказательств

- EDT-MCP: extension `QueryConsoleZUP` готов, содержит 103 BSL-модуля. API: `CommonModules/ЭлементыМоделиЗапроса/Module.bsl`, `ОбработкаМоделиЗапроса/Module.bsl`, `МодельЗапросаУтилиты/Module.bsl`, `ОбходМоделиЯзыкаВыражений/Module.bsl`, `МодельЗапросаТипы/Module.bsl`.
- `ЭлементыМоделиЗапроса` экспортирует 91 factory, включая `НовыйЭлементМоделиЗапроса`, `НовыйПакетЗапросов`, `НовыйВыражениеМоделиЗапроса`, `НовыйИсполняемоеПредставление`.
- `rg` по production `src/**/*.bsl` пяти API: 43 файла, 752 совпадения (509/23, 53/15, 152/30, 9/7, 29/12 соответственно). Baseline содержит 751; `git diff d4ca830..HEAD --` для этих API пуст: source commit/diff не найден, значит расходится зафиксированная методика подсчёта, не текущий код.
- Template visitor содержит 59 callbacks. Сравнение с semantic/filter/SKD concrete visitors: 0 missing и 0 extra; lifecycle/helper: 5, 12 и 4.
- Existing YAxUnit code: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`, `КОНС_Обр_Парсер_МО/Module.bsl`, `КОНС_Обр_ПарсерЗапросов_МО/Module.bsl`, `КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`. Это source evidence, не свежий run.

| Component | Model types/properties | Model ingress | Observable output | Existing automated test | Coverage gap | Required Phase 2.5 test |
|---|---|---|---|---|---|---|
| AST factories | [Факт] пакет, запрос, оператор, источник, выражение, исполняемое представление | `CommonModules/ЭлементыМоделиЗапроса/Module.bsl`: `Новый*` | BSL structures, properties, collections | Косвенно parser/semantic YAxUnit | Нет factory-property contract | Headless representative factory-per-family contract |
| Lexer | Токен: тип, лексема, значение, координаты | `DataProcessors/ЛексическийАнализатор/ObjectModule.bsl`: `Инициализировать`, `УстановитьОбрабатываемыйТекст`, `СледующийТокен` | Tokens/error | `КОНС_Обр_ЛексическийАнализатор_МО.ИсполняемыеСценарии` | Нет fresh runtime baseline | Headless token/EOF/error characterization |
| Expression parser | Expression AST: value, operation, arguments, flags | `DataProcessors/Парсер/ObjectModule.bsl`: `РазобратьВыражение` | Tree/error | `КОНС_Обр_Парсер_МО.ИсполняемыеСценарии` | Нет contract каждого изменяемого binding | Parser-to-AST cases per migrated property |
| Full-query parser | Package/query/operator/sources/fields/filters/order/totals/SKD | `DataProcessors/Парсер/ObjectModule.bsl`: `Разобрать` | Package/error | `КОНС_Обр_ПарсерЗапросов_МО.ИсполняемыеСценарии` | Нет full property-level corpus | 12 curated + representative QueryExamples AST contracts |
| Semantic analyzer | `ТипЗначения`, sources, aliases, aggregate/condition flags | `CommonModules/ОбработкаМоделиЗапроса/Module.bsl`: `ОбработатьМодельЗапроса`, `ОбработатьВыражение`, `ОбработатьУсловие` | Enriched model/error | `КОНС_ОМ_ОбработкаМоделиЗапроса` semantic cases | Нет source/metadata/parser lanes | Headless pure, synthetic, metadata, parser-to-semantic lanes |
| Expression dispatcher/template | 29 expression kinds; 59 callbacks | `CommonModules/ОбходМоделиЯзыкаВыражений/Module.bsl`: `ОбойтиДерево`; `DataProcessors/Шаблон_ПосетительМоделиВыражений/ObjectModule.bsl` | Enter/exit traversal | Direct test not found | Callbacks not exercised as full set | One 59-callback order contract |
| Semantic visitor | Nodes, semantic context, `ТипЗначения` | `DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl`: `УстановитьКонтекст` | Semantic expression | Indirect semantic module | No direct visitor characterization | Public-object representative-node contract |
| Filter applicability visitor | Filter tree, source id, filter description | `DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl`: `УстановитьИдентификаторИсточникаПредставления`, `УстановитьОписаниеОтбора`, `ВыделитьИМодифицироватьОтбор` | Delegated/residual filter | Console/constructor Vanessa workflows | No headless public contract | Delegatable, mixed, prohibited filter cases |
| SKD dereference visitor | Dereference, type conversion, expression types | `DataProcessors/ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl`: `УстановитьКонтекст` | Transformed SKD expression | Direct test not found | No output-shape contract | Dereference/type-reference headless contract |
| Model builder | Package/operator/sources/fields/filter/group/order/totals | `DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl`: `Инициализировать`, `ПолучитьМодель`, `ДобавитьИсточник`, `ДобавитьОтбор` | Edited valid model | Direct test not found | Object module uncharacterized outside form | Create/mutate/remove source and filter/order/totals sequence |
| Query/expression text generation | Operator/source/expression, alias/filter/source properties | `CommonModules/ГенерацияТекстовЗапросов/Module.bsl`: `ТекстПакетаЗапросов`, `ТекстЗапросаВыбора`, `ВыражениеВСтроку` | Query/expression text | Feature output evidence | No headless goldens | AST-to-text golden corpus, nested source/filter/SKD |
| Executable-view processing | Executable view, parameters, filters, temporary tables | `CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl`: `ОбработатьИсточникЗапроса`, `ИсполняемоеПредставлениеПоОписанию` | Execution model | `features/ВыполнениеЗапросовВКонсоли/*.feature` | Transformations not isolated | Description-to-executable-view model contract |
| Executor/code/SKD generation | Package/source/field/filter/executable views | `CommonModules/ИсполнительПредставлений/Module.bsl`: `ВыполнитьПакетЗапросов`, `ПолучитьИсполняемыйКод`, `ПолучитьТекстЗапросаДляСКД`; `DataProcessors/ГенераторКодаИсполняемыхПредставлений/ObjectModule.bsl`: `ИсполняемыйКод` | Query result, BSL code, SKD | Console execution/code-generation features | No headless snapshots | Representative execution/code/SKD snapshots |
| Query console underlying logic | Text, parsed package, execution result | `DataProcessors/КонсольЗапросов/ObjectModule.bsl`: `ВыполнитьЗапрос`, `ПреобразоватьВМетаданные` | Result/plan metadata | `features/ВыполнениеЗапросовВКонсоли/*.feature`, `features/ГенерацияКодаВКонсоли/*.feature` | Object contract not characterized | Direct object-module test; retain end-of-migration Vanessa workflow |
| Query Constructor underlying logic | Available table/source tree and schema query | `DataProcessors/КонструкторЗапросов/ObjectModule.bsl`: `AvailableTablesBeforeExpandAtServer`, `SourcesBeforeExpandAtServer`, `GetSchemaQuery` | Available sources and DCS query | `features/СозданиеЗапросовВКонструкторе/*.feature` | Stable non-form chain needs proof; not manual-only | Characterize these public object calls and any stable common-module path; end UI gate |
| Universal report | Package/source/filter/SKD adaptation | `Reports/УниверсальныйОтчетРасширенный/ObjectModule.bsl`: `ПриСозданииНаСервере`; `CommonModules/УниверсальныйОтчетРасширенный/Module.bsl`: `ЗаменитьИсполняемыеПредставленияВременнымиТаблицами` | Adapted report query/SKD | Direct test not found | No headless report contract | Common/object-module adaptation characterization |
| Feature-generation helpers | Query model/text/expected files | `DataProcessors/ГенераторFeatureФайлов/ObjectModule.bsl`: `УстановитьГенераторТекстовВыражений`, `УстановитьТекстовыйДокумент`, `СценарийСозданияПакетаЗапросаВТекДок` | Feature and oracle content | Generated feature suites are downstream only | No helper contract | Model-to-feature fixture golden test |
| Представление* manager consumers (19 live; brief says 15) | Description/query/code/execution parameters | [Факт] `DataProcessors/Представление*/ManagerModule.bsl`: `Описание`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` where exported | Query result/BSL/SKD | Corresponding console/constructor/code-generation Vanessa scenarios | [Динамика] provider dispatch and infobase dependencies; live count 19 | Per-manager stable exported-function characterization plus representative Vanessa workflows |

### Факты

EDT-MCP подтвердил paths и public entrypoints из матрицы. Serena подтвердил active BSL EDT project. Form modules не являются unit-test target, но их callable common/object dependencies входят в headless scope. Vanessa suites есть для console execution/code generation и Query Constructor, но не заменяют headless characterization.

### Гипотезы

Отсутствуют: **[Вывод]** в таблице ограничен будущим test requirement и не утверждает текущее runtime-поведение.

### Пробелы

1. Fresh YAxUnit/Vanessa run требует launch configuration и не выполнялся.
2. [Динамика] `Обработки.*.Создать()` и provider dispatch требуют runtime trace.
3. Live EDT modules дают 19 `Представление*` managers; значение 15 из brief нельзя переносить в migration backlog без отдельной сверки.

## Change protocol

producer/reference discovery → GREEN headless characterization → new semantic contract → factory/parser/consumer migration in one slice → zero stale references → old property removal

Связанные правила: [approved design](../specs/2026-08-07-grammar-query-model-optimization-design.md) и [foundation plan](../plans/2026-08-07-grammar-query-model-foundation.md).

## UI boundary

Form modules are not unit-test targets. Their callable common/object-module
dependencies remain in headless scope. A workflow is manual/Vanessa-only only
after its entrypoint analysis proves that no stable non-form contract can be
invoked.

Для Query Constructor такого доказательства нет: Vanessa scenarios — workflow coverage, не доказательство manual-only. Интерактивный UI gate — в конце миграции.
