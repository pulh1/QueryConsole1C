# Checkpoint: список параметров таблицы с пустыми slots

Дата: 2026-08-08.

## Результат

Связная family параметров параметризованной таблицы переведена на
declarative root collection и EBNF loop:

```text
<СписокПараметров> ::=
    @НовыйСписокПараметров
    += <ПараметрТаблицы>
    (',' += <ПараметрТаблицы>)*

<ПараметрТаблицы> ::=
      <ВыражениеМоделиЗапроса>
    | := Неопределено
```

Удалена technical production `ПродолжениеСпискаПараметров`. Generated BSL
использует один `Пока`, вызывает constructor один раз и добавляет один элемент
массива для каждой позиции параметра.

Сохранены прежние contracts:

- `Таблица()` создает один пустой slot;
- leading, intermediate и trailing empty slots не теряются;
- каждый пустой slot представлен `Неопределено`;
- непустой slot содержит прежний expression AST;
- порядок и количество элементов массива не меняются.

Query model и downstream property `ИсточникДанныхТаблица.Параметры` не
изменялись.

## Transparent constant result

В DSL добавлена минимальная property-less форма `:=`:

```text
:= Неопределено
```

Она возвращает whitelist-константу как semantic result alternative. Форма не
требует constructor, но validator запрещает смешивать ее на одном execution
path с constructor, другим transparent result или semantic child. Arbitrary
BSL и вычисляемые expressions не поддерживаются.

В Parser IR этот contract представлен отдельной операцией `ReturnConstant`.
Codegen использует ее как value выбранной alternative; отдельный AST node или
runtime helper не создается.

## Structural metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 92 / 215 | 91 / 213 |
| Lowered CFG productions / alternatives / epsilon | 136 / 298 / 67 | 136 / 298 / 67 |
| Semantic action blocks / statements | 110 / 125 | 105 / 118 |
| Constructor / collection / constant / structural statements | 19 / 12 / 14 / 77 | 18 / 10 / 14 / 73 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 104 / 2 509 | 103 / 2 488 |
| SELECT rows | 2 583 | 2 090 |
| Legacy matcher rows | 9 572 | 9 572 |

Lowered CFG counts не изменились: удаленная source continuation заменена
analysis-only synthetic repeat production, которая не становится runtime
function.

Canonical analysis остается `k=2`; порядок generated `Если` не используется
для разрешения конфликтов:

- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- validation diagnostics: `0`;
- generated artifact drift: `0`.

## Tests

Property-less constant result покрыт отдельными Python tests:

- DSL parsing и malformed value;
- whitelist validation;
- запрет constructor/semantic-result mixing;
- explicit `ReturnConstant` в Parser IR;
- root-list codegen с empty slots и loop.

Repository shape-test проверяет:

- один `НовыйСписокПараметров`;
- два append sites (первый slot и loop iteration);
- один `Пока`;
- отсутствие `ПродолжениеСпискаПараметров`;
- отсутствие `ТекущийЭлемент` и `НомерВариантаПродукции` в обеих migrated
  functions.

Существующий headless full-parser corpus содержит parameterized table calls;
фактический platform/YAxUnit прогон остается общим финальным integration gate,
как согласовано для migration.

## Verification

- focused infrastructure/repository suite: `125 passed`, `139 subtests`;
- полный `tools/parsergen/tests`: `457 passed`, `1 skipped`, `4508 subtests`;
- skip: недоступно создание symlink без Windows privilege;
- `parsergen validate`: exit `0`, diagnostics отсутствуют;
- canonical/legacy conflicts: `0 / 0`;
- `parsergen generate --check`: artifacts current;
- targeted EDT revalidation `DataProcessor.Парсер`: success.

EDT показывает прежние пять parser markers: metadata prefix, `НСтр` language
code и три unused `ТекущийЭлемент`; новых diagnostics нет.
