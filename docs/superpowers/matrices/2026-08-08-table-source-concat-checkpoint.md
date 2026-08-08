# Checkpoint: scalar concat binding и источник обычной таблицы

Дата: 2026-08-08.

## Результат

Добавлен минимальный declarative binding `~=` для накопления строкового
scalar-свойства:

```text
ИмяТаблицы ~= #ID_ИмяТаблицы
(ИмяТаблицы ~= '.' ИмяТаблицы ~= #ID_Полный)+
```

Binding генерирует присоединение разобранного terminal/token к начальному
значению свойства, заданному constructor factory. Он применим только к
terminal-like значениям, требует active constructor и не может смешиваться с
`=` или `+=` для того же свойства.

На canonical path одним package переведен `ИсточникДанныхТаблица`:

- составное имя таблицы собирается без structural actions;
- разыменование генерируется одним BSL loop;
- параметры и псевдоним разбираются conditional branches из `?`;
- обязательная первая точка сохранена через `+`, поэтому обычная таблица не
  пересекается с временной таблицей;
- query model и downstream property names не менялись.

Удалены technical productions:

- `РазыменованиеТаблицы`;
- `ПродолжениеРазыменованияТаблицы`;
- `ПараметрыТаблицыОпционально`;
- `ПсевдонимОпционально`.

`СписокПараметров` пока оставлен legacy production: его поддержка пустых
позиций требует отдельной декларативной semantics, а не механической замены.

## Model contract

`ИсточникДанныхТаблица.Параметры` фактически имеет тип
`Неопределено | Массив` и сохраняет прежнее runtime-представление. Комментарий
factory ошибочно ссылался на `НовыйСписокВыражений` (`Структура`); после того
как canonical code сделал присваивание типизированным и EDT обнаружил ошибку,
документирующий контракт исправлен на `Неопределено, Массив`.

## Structural metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 96 / 222 | 92 / 215 |
| Lowered CFG productions / alternatives / epsilon | 136 / 298 / 67 | 136 / 298 / 67 |
| Semantic action blocks / statements | 120 / 135 | 110 / 125 |
| Constructor / collection / constant / structural statements | 20 / 12 / 14 / 86 | 19 / 12 / 14 / 77 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 108 / 2 561 | 104 / 2 509 |
| SELECT rows | 2 890 | 2 583 |
| Legacy matcher rows | 9 572 | 9 572 |

Canonical analysis остается `k=2`; SELECT alternatives disjoint:

- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- validation diagnostics: `0`;
- generated artifact drift: `0`.

## Tests

`~=` покрыт отдельными Python tests на уровнях DSL parser, validation,
lowering/Parser IR и BSL codegen. Проверены:

- concat внутри repeat;
- malformed binding;
- запрет nonterminal concat;
- запрет смешения binding modes;
- explicit `ConcatScalar` в Parser IR;
- накопление значения и loop shape в generated BSL.

Repository shape-test проверяет один constructor, один `Пока`, пять concat
assignments, прямые bindings параметров и псевдонима, отсутствие удаленных
functions, `ТекущийЭлемент` и `НомерВариантаПродукции`.

## Verification

- focused infrastructure: `46 passed`, `12 subtests`;
- repository/config/audit/reference/codec suite: `118 passed`, `137 subtests`;
- полный `tools/parsergen/tests`: `451 passed`, `1 skipped`, `4503 subtests`;
- skip: недоступно создание symlink без Windows privilege;
- `parsergen generate --check`: artifacts current;
- `parsergen validate`: exit `0`, diagnostics отсутствуют;
- targeted EDT revalidation для parser и model factory: success.

После исправления документирующего контракта у `DataProcessor.Парсер` остались
только прежние пять markers: metadata prefix, `НСтр` language code и три
unused `ТекущийЭлемент`. Новый type mismatch `Структура` / `Массив` исчез.
