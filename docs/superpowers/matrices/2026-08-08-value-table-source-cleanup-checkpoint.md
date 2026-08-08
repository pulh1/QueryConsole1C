# Checkpoint: источник таблицы значений и unreachable grammar cleanup

Дата: 2026-08-08.

## Результат

Связный leaf-пакет источников данных переведен без изменения query model:

- `ИсточникДанныхТаблицаЗначений` теперь использует constructor и scalar bindings;
- имя параметра связывается непосредственно из `& #ID_Полный` с `ИмяТаблицы`;
- обязательный `Псевдоним` связывается с одноименным свойством;
- runtime-вызов `НеТерминалПараметр` из этой production удален;
- удалены недостижимые `КакОпционально` и `ВыражениеСКДПараметр`;
- repository grammar теперь валидируется без `VAL102` warnings.

Удаление двух productions безопасно подтверждено прежним impact analysis: первая не имела callers, вторая имела только self-call и обе были недостижимы из `Разобрать`.

Query model и downstream contracts не менялись. Существующий full-parser case `S05` характеризует наблюдаемый результат: тип источника, имя таблицы значений и псевдоним.

## Generated shape

`НеТерминалИсточникДанныхТаблицаЗначений`:

- создает AST-узел ровно один раз;
- потребляет `&` и `#ID_Полный` напрямую;
- присваивает `ИмяТаблицы` и `Псевдоним` declarative bindings;
- не содержит `ТекущийЭлемент` и `НомерВариантаПродукции`.

Generated BSL больше не содержит функций удаленных unreachable productions.

## Structural metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 98 / 226 | 96 / 222 |
| Lowered CFG productions / alternatives / epsilon | 138 / 302 / 69 | 136 / 298 / 67 |
| Semantic action blocks / statements | 123 / 138 | 120 / 135 |
| Constructor / collection / constant / structural statements | 21 / 12 / 14 / 88 | 20 / 12 / 14 / 86 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 110 / 2 595 | 108 / 2 561 |
| SELECT rows | 3 014 | 2 890 |
| Legacy matcher rows | 9 618 | 9 572 |

Canonical analysis остается `k=2`, `SELECT` alternatives disjoint:

- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- diagnostics: `0`;
- generated artifacts drift: `0`.

## Проверки

- focused repository/config tests: `3 passed`, `7 subtests`;
- repository/config/audit/reference/codec: `72 passed`, `121 subtests`;
- полный `tools/parsergen/tests`: `445 passed`, `1 skipped`, `4498 subtests`;
- skip: недоступно создание symlink без Windows privilege;
- `parsergen generate --check`: artifacts current;
- `parsergen validate`: exit `0`, diagnostics отсутствуют;
- EDT targeted revalidation `DataProcessor.Парсер`: success.

После revalidation EDT показывает пять существующих markers: prefix metadata, `НСтр` language code и три unused `ТекущийЭлемент`. Удаленные unused method и связанный с этим package лишний marker исчезли; новых syntax diagnostics нет.
