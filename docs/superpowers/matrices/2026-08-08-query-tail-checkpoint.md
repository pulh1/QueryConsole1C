# Checkpoint: canonical query tail

> Follow-up: temporary UNION action described below was removed by the
> required returned-child decorator migration documented in
> `2026-08-08-union-returned-child-checkpoint.md`.

Дата: 2026-08-08.

## Результат

Вся хвостовая часть `ЗапросВыбора` переведена в одну canonical EBNF
production:

- список `ОБЪЕДИНИТЬ [ВСЕ]` генерирует BSL loop;
- `УПОРЯДОЧИТЬ ПО` генерирует optional branch и scalar binding `Порядок`;
- `ИНДЕКСИРОВАТЬ ПО` генерирует optional branch и scalar binding `Индекс`;
- `ИТОГИ ... ПО` декларативно заполняет `ВыраженияИтогов` и
  `КонтрольныеТочкиИтогов`;
- `АВТОУПОРЯДОЧИВАНИЕ` декларативно задаёт `Автопорядок = Истина`.

Удалены шесть technical helper-productions:

- `БлокОбъединить`;
- `ВсеОпционально`;
- `БлокУпорядочить`;
- `БлокИндексировать`;
- `БлокИтоги`;
- `АвтоупорядочиваниеОпционально`.

Добавлены две предметные productions: одноальтернативный
`ОператорОбъединения` и canonical `ТипОбъединенияЗапроса`. Последняя имеет
ровно две alternatives — `ВСЕ` и epsilon/default — с disjoint canonical
SELECT(2). Generated `Если` не разрешает конфликты порядком веток.

## Canonical/legacy boundary

UNION loop и выбор `ВСЕ`/default полностью используют canonical analysis.
`ОператорОбъединения` имеет только одну alternative, поэтому не выполняет
runtime dispatch и не зависит от legacy matcher selection. В нём временно
остаётся одно structural действие: присвоение `ТипОбъединения` уже разобранному
`ОбъединяемыйЗапрос` и возврат этого operator node.

Это узкий adapter существующей domain model `ЗапросВыбора.Операторы`, где тип
UNION хранится на следующем operator node. Его удаление потребует либо
минимального declarative returned-child decorator binding, либо согласованной
model migration; произвольная BSL action system ради этого не добавлялась.

## Coverage

Repository code-shape test проверяет:

- отсутствие шести runtime helper-functions;
- один constructor `НовыйЗапросВыбора`;
- iterative loop для UNION members;
- collection/scalar/constant bindings всех хвостовых свойств;
- отсутствие `ТекущийЭлемент` и `НомерВариантаПродукции` в canonical
  `ЗапросВыбора`;
- отсутствие dispatch в `ТипОбъединенияЗапроса` и
  `ОператорОбъединения`;
- сохранение обоих domain constructors типа UNION.

Существующий headless YAxUnit full-parser contour уже покрывает обычный UNION,
`ОБЪЕДИНИТЬ ВСЕ`, цепочку из трёх members, ORDER variants, INDEX, TOTALS,
AUTOORDER и syntax errors. Дополнительно добавлен case `C16`, объединяющий в
одном запросе UNION + ORDER + INDEX + TOTALS + AUTOORDER и проверяющий все
значимые AST properties. EDT syntax check для тестового модуля прошёл.

Полный Python-контур: `474 passed`, `1 skipped`, `4 548 subtests`.
Единственный skip — системное ограничение Windows на создание symlink
(`WinError 1314`).

Targeted EDT revalidation прошла для generated `DataProcessor.Парсер` и
YAxUnit `CommonModule.КОНС_Обр_ПарсерЗапросов_МО`; новых diagnostics уровня
`ERRORS` нет. Интерактивный platform run остаётся согласованным финальным
integration gate.

## Metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 77 / 178 | 73 / 169 |
| Lowered CFG productions / alternatives / epsilon | 143 / 310 / 72 | 144 / 311 / 72 |
| Semantic action blocks / statements | 64 / 74 | 51 / 61 |
| Constructor / collection / constant statements | 14 / 6 / 7 | 11 / 4 / 6 |
| Structural action statements | 47 | 40 |
| `Родитель` / `ЛевыйЭлемент` usages | 7 / 6 | 1 / 6 |
| Generated BSL functions / LOC | 89 / 2 330 | 85 / 2 277 |
| SELECT artifact rows | 1 364 | 1 261 |
| Legacy analysis matcher rows | 10 023 | 10 025 |

Lowered CFG вырос на одну synthetic production, используемую только canonical
analysis optional/repeat lowering. Runtime parser уменьшился на четыре
functions и 53 LOC; UNION chain больше не увеличивает parser recursion depth.

- production lookahead: `k=2`;
- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- validation diagnostics: `0`;
- generated artifacts current: да.

## Remaining boundary

Последнее использование `Родитель` находится в legacy СКД field-list helper
`СписокПолейОпционально`. Шесть использований `ЛевыйЭлемент` сосредоточены в
logical/comparison expression family и должны уйти отдельным coherent
direct-LR/left-fold package.
