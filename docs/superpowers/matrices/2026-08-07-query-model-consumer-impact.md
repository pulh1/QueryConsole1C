# Матрица влияния потребителей модели запроса

Состояние: ветка `feature/grammar-optimization`; `d4ca830` — baseline/source snapshot, а не текущий HEAD. Обозначения: **[Факт]** — подтверждено живым проектом; **[Вывод]** — требование будущего test; **[Динамика]** — путь требует runtime trace.

## Реестр доказательств

- [Факт] EDT-MCP видит ready extension `QueryConsoleZUP` и 103 BSL-модуля. Central API: `CommonModules/ЭлементыМоделиЗапроса/Module.bsl`, `ОбработкаМоделиЗапроса/Module.bsl`, `МодельЗапросаУтилиты/Module.bsl`, `ОбходМоделиЯзыкаВыражений/Module.bsl`, `МодельЗапросаТипы/Module.bsl`.
- [Факт] `ЭлементыМоделиЗапроса` экспортирует 91 factory. `rg` по production `src/**/*.bsl` пяти API: 43 файла, 752 совпадения (509/23, 53/15, 152/30, 9/7, 29/12). В baseline записано 751; `git diff d4ca830..533d387 --` для пяти API пуст, поэтому source diff, объясняющий число 752, отсутствует.
- [Факт] Template содержит 59 callbacks; три concrete visitors имеют callback parity 59/59, без missing/extra callback. Методика extra counts: из export methods каждого concrete module исключены 59 callback, включая `ПосетитьВложенныйЗапрос`; остаётся 3 semantic, 7 filter, 1 SKD export.
- [Факт] Existing YAxUnit source: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`, `КОНС_Обр_Парсер_МО/Module.bsl`, `КОНС_Обр_ПарсерЗапросов_МО/Module.bsl`, `КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl`; это не fresh run.

## 15 direct Представление* consumers

[Факт] `rg` пяти central API в 19 обнаруженных manager modules нашёл ровно 15 direct consumers: в каждом строка вызывает `МодельЗапросаУтилиты.СоздатьПостроительМодели(Модель)`.

| Concrete manager path | Public entrypoints |
|---|---|
| `DataProcessors/ПредставлениеДанныеПозицийШтатногоРасписания/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеДанныеСотрудников/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеДанныеУчетаВремениСотрудников/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеДанныеФизическихЛиц/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеНачисленияУдержанияВыплаты/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеНачисленияУдержанияВыплатыАвансом/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеОстаткиОтпусков/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеПериоды/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеПлановоеВремяСотрудников/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеРабочиеМестаСотрудников/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеРегистрСведенийЗаписи/ManagerModule.bsl` | `Описание(ИмяРегистра)`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеРегистрСведенийСрезПоследних/ManagerModule.bsl` | `Описание(ИмяРегистра)`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеСотрудникиОрганизации/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеСтажиФизическихЛиц/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |
| `DataProcessors/ПредставлениеФактическиеОтпускаСотрудников/ManagerModule.bsl` | `Описание`, `Справка`, `ИмяПредставления`, `Исполнить`, `ИсполняемыйКод`, `ТекстЗапросаДляСКД` |

[Факт] Direct non-consumer exclusions (в их manager modules `rg` пяти API не нашёл): `DataProcessors/ПредставлениеОплаченноеВремя/ManagerModule.bsl`, `ПредставлениеРегистрНакопленияНарастающийИтог/ManagerModule.bsl`, `ПредставлениеРегистрРасчетаБаза/ManagerModule.bsl`, `ПредставлениеРегистрСведенийПериоды/ManagerModule.bsl`. Это не утверждает отсутствие косвенной динамики.

| Component | Model types/properties | Model ingress | Observable output | Existing automated test | Coverage gap | Required Phase 2.5 test |
|---|---|---|---|---|---|---|
| AST factories | [Факт] package/query/operator/source/expression/executable-view structures | [Факт] `ЭлементыМоделиЗапроса/Module.bsl`: `Новый*` | [Факт] BSL structures/properties/collections | [Факт] indirect parser/semantic YAxUnit | [Факт] no factory-property contract | [Вывод] factory-per-family contract |
| Lexer | [Факт] token type/lexeme/value/position | [Факт] `ЛексическийАнализатор/ObjectModule.bsl`: `Инициализировать`, `УстановитьОбрабатываемыйТекст`, `СледующийТокен` | [Факт] tokens/error | [Факт] `КОНС_Обр_ЛексическийАнализатор_МО.ИсполняемыеСценарии` | [Факт] no fresh baseline | [Вывод] token/EOF/error characterization |
| Expression parser | [Факт] expression AST | [Факт] `Парсер/ObjectModule.bsl`: `РазобратьВыражение` | [Факт] tree/error | [Факт] `КОНС_Обр_Парсер_МО.ИсполняемыеСценарии` | [Факт] binding properties uncovered | [Вывод] parser-to-AST cases |
| Full-query parser | [Факт] package/query/operator/source/field/filter/order/totals/SKD | [Факт] `Парсер/ObjectModule.bsl`: `Разобрать` | [Факт] package/error | [Факт] `КОНС_Обр_ПарсерЗапросов_МО.ИсполняемыеСценарии` | [Факт] no property corpus | [Вывод] curated + QueryExamples contracts |
| Semantic analyzer | [Факт] `ТипЗначения`, sources, aliases, flags | [Факт] `ОбработкаМоделиЗапроса/Module.bsl`: `ОбработатьМодельЗапроса`, `ОбработатьВыражение`, `ОбработатьУсловие` | [Факт] enriched model/error | [Факт] `КОНС_ОМ_ОбработкаМоделиЗапроса` | [Факт] source/metadata/parser lanes absent | [Вывод] four headless lanes |
| Expression dispatcher/template | [Факт] 29 kinds, 59 callbacks | [Факт] `ОбходМоделиЯзыкаВыражений/Module.bsl`: `ОбойтиДерево`; template object module | [Факт] enter/exit traversal | [Факт] direct test not found | [Факт] full set unexercised | [Вывод] 59-callback order contract |
| Semantic visitor | [Факт] nodes/context/`ТипЗначения` | [Факт] `СемантическийАнализВыраженийПосетитель/ObjectModule.bsl`: `УстановитьКонтекст` | [Факт] semantic expression | [Факт] indirect semantic module | [Факт] direct characterization absent | [Вывод] public-object node contract |
| Filter applicability visitor | [Факт] filter/source id/description | [Факт] `ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl`: `УстановитьОписаниеОтбора`, `ВыделитьИМодифицироватьОтбор` | [Факт] delegated/residual filter | [Факт] console/constructor Vanessa workflows | [Факт] direct contract absent | [Вывод] delegatable/mixed/prohibited cases |
| SKD dereference visitor | [Факт] dereference/type conversion | [Факт] `ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl`: `УстановитьКонтекст` | [Факт] transformed expression | [Факт] direct test not found | [Факт] output-shape contract absent | [Вывод] dereference/type cases |
| Model builder | [Факт] package/operator/source/filter/order/totals | [Факт] `ПостроительМоделиЗапроса/ObjectModule.bsl`: `Инициализировать`, `ПолучитьМодель`, `ДобавитьИсточник`, `ДобавитьОтбор` | [Факт] edited model | [Факт] direct test not found | [Факт] object module uncharacterized | [Вывод] mutation sequence |
| Query/expression text generation | [Факт] operator/source/expression/filter | [Факт] `ГенерацияТекстовЗапросов/Module.bsl`: `ТекстПакетаЗапросов`, `ТекстЗапросаВыбора`, `ВыражениеВСтроку` | [Факт] query/expression text | [Факт] feature output evidence | [Факт] headless goldens absent | [Вывод] AST-to-text goldens |
| Executable-view processing | [Факт] executable view/parameters/filters/VT | [Факт] `ОбработкаПредставлениеЗапросов/Module.bsl`: `ОбработатьИсточникЗапроса`, `ИсполняемоеПредставлениеПоОписанию` | [Факт] execution model | [Факт] console execution features | [Факт] transform contract absent | [Вывод] description-to-model cases |
| Executor/code/SKD generation | [Факт] package/source/field/filter/view | [Факт] `ИсполнительПредставлений/Module.bsl`: `ВыполнитьПакетЗапросов`, `ПолучитьИсполняемыйКод`, `ПолучитьТекстЗапросаДляСКД`; code generator: `ИсполняемыйКод` | [Факт] query result/BSL/SKD | [Факт] console execution/code features | [Факт] headless snapshots absent | [Вывод] representative snapshots |
| Query console underlying logic | [Факт] text/package/result | [Факт] `КонсольЗапросов/ObjectModule.bsl`: `ВыполнитьЗапрос`, `ПреобразоватьВМетаданные` | [Факт] result/plan metadata | [Факт] execution/code features | [Факт] object contract absent | [Вывод] direct object characterization + Vanessa workflow |
| Query Constructor underlying logic | [Факт] available table/source tree/schema query | [Факт] `КонструкторЗапросов/ObjectModule.bsl`: `AvailableTablesBeforeExpandAtServer`, `SourcesBeforeExpandAtServer`, `GetSchemaQuery` | [Факт] sources/DCS query | [Факт] constructor features | [Динамика] stable non-form chain unproven; not manual-only | [Вывод] characterize public object calls and stable chain; UI gate last |
| Universal report | [Факт] package/source/filter/SKD adaptation | [Факт] report object `ПриСозданииНаСервере`; `УниверсальныйОтчетРасширенный/Module.bsl`: `ЗаменитьИсполняемыеПредставленияВременнымиТаблицами` | [Факт] adapted query/SKD | [Факт] direct test not found | [Факт] report contract absent | [Вывод] common/object characterization |
| Feature-generation helpers | [Факт] model/text/feature document | [Факт] `ГенераторFeatureФайлов/ObjectModule.bsl`: `УстановитьГенераторТекстовВыражений`, `УстановитьТекстовыйДокумент`, `СценарийСозданияПакетаЗапросаВТекДок` | [Факт] feature/oracle content | [Факт] generated suites downstream only | [Факт] helper contract absent | [Вывод] model-to-feature golden |
| 15 Представление* manager consumers | [Факт] model via `СоздатьПостроительМодели(Модель)` | [Факт] 15 concrete paths/exports above | [Факт] query result/BSL/SKD through listed exports | [Факт] corresponding Vanessa workflows | [Динамика] provider dispatch/infobase dependencies not traced | [Вывод] per-manager exported-function characterization + representative Vanessa |

## Факты

[Факт] Form modules are not unit-test targets; callable common/object-module dependencies remain headless scope. [Факт] Query Constructor имеет Vanessa workflow coverage, но это не доказывает manual-only status.

## Гипотезы

Нет.

## Пробелы

- [Динамика] `Обработки.*.Создать()` и provider dispatch требуют runtime trace.
- [Факт] Fresh YAxUnit/Vanessa run требует launch configuration и здесь не запускался.

## Change protocol

producer/reference discovery → GREEN headless characterization → new semantic contract → factory/parser/consumer migration in one slice → zero stale references → old property removal

Связанные правила: [approved design](../specs/2026-08-07-grammar-query-model-optimization-design.md) и [foundation plan](../plans/2026-08-07-grammar-query-model-foundation.md).

## UI boundary

Form modules are not unit-test targets. Their callable common/object-module
dependencies remain in headless scope. A workflow is manual/Vanessa-only only
after its entrypoint analysis proves that no stable non-form contract can be
invoked.

Для Query Constructor такого доказательства нет: Vanessa scenarios — workflow
coverage, не доказательство manual-only. Интерактивный UI gate — в конце миграции.
