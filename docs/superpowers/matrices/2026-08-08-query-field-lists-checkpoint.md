# Checkpoint: query field list loops

Дата: 2026-08-08.

## Результат

Одним migration package переведены две связанные production families:

```text
<ПоляВыборки>(Оператор) ::=
    @НовыйВыбираемыеПоля
    += <ПолеВыборки>
    <РасширениеСКД>(Оператор)
    (',' += <ПолеВыборки> <РасширениеСКД>(Оператор))*

<ПоляИтогов> ::=
    @НовыйВыраженияИтогов
    (+= <ПолеВыборки>
        (',' += <ПолеВыборки> <РасширениеСКД>)*)?
```

Оба списка теперь строятся declarative root-collection bindings и generated
BSL loops. Recursive `СписокПолейОпционально` больше не вызывается из main
SELECT fields и totals. Production пока остается в legacy island только для
тел СКД; ее окончательное удаление относится к migration самого СКД package.

Query model и downstream properties не менялись:

- `Оператор.ВыбираемыеПоля` остается упорядоченным массивом полей;
- `Запрос.ВыраженияИтогов` остается упорядоченным массивом выражений итогов;
- пустой список выражений итогов представлен естественным пустым массивом,
  созданным существующим factory `НовыйВыраженияИтогов`.

## Canonical/legacy boundary

Встроенное после поля `<РасширениеСКД>` пока является legacy island. Для
этого boundary закреплены два узких правила:

- branch с явным collection binding не выводит semantic result из следующего
  unbound compatibility call;
- hybrid adapter добавляет `Неопределено, Неопределено` в ABI slots
  `Родитель`, `ЛевыйЭлемент` и передает только явный formal argument
  `Оператор`.

Canonical Parser IR не получает legacy matcher semantics и не передает новый
AST accumulator в legacy island. Standalone canonical codegen по-прежнему
генерирует только объявленные source arguments.

## Characterization coverage

До migration уже существовали headless YAxUnit contracts:

- `F01`, `F07`: два поля, порядок и псевдонимы;
- большой curated query corpus: длинные реальные field lists;
- `T03`, `T04`, `T05`: один и несколько итоговых expressions и control
  points;
- `K04`, `K05`: выполняемые контракты расширения СКД.

Repository shape-test дополнительно проверяет по одной generated function на
family: один constructor, один loop, два append sites, отсутствие
`ТекущийЭлемент` и `НомерВариантаПродукции`, а также точный compatibility call.
Фактический platform run YAxUnit остается финальным integration gate.

## Structural metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 90 / 211 | 90 / 210 |
| Lowered CFG productions / alternatives / epsilon | 136 / 298 / 67 | 139 / 303 / 69 |
| Semantic action blocks / statements | 102 / 115 | 98 / 111 |
| Constructor / collection / constant / structural statements | 17 / 10 / 14 / 71 | 15 / 8 / 14 / 71 |
| Formal parameters / actual arguments | 7 / 22 | 9 / 25 |
| Generated BSL functions / LOC | 102 / 2 477 | 102 / 2 486 |
| SELECT artifact rows | 2 087 | 1 596 |
| Legacy analysis matcher rows | 9 572 | 9 908 |

Рост lowered CFG является analysis-only ценой двух EBNF constructs; synthetic
productions не превращаются в runtime functions. Количество generated
functions не выросло, а SELECT artifact уменьшился на 491 строку.

Canonical analysis остается `k=2`, SELECT alternatives disjoint:

- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- validation diagnostics: `0`.

## Verification

- focused IR/hybrid/repository/config/audit/codec suite: `90 passed`,
  `126 subtests`;
- полный `tools/parsergen/tests`: `466 passed`, `1 skipped`,
  `4509 subtests`;
- skip: недоступно создание symlink без Windows privilege;
- production artifacts regenerated and reference fixtures synchronized;
- `parsergen generate --check`: artifacts current;
- targeted EDT revalidation `DataProcessor.Парсер`: success, прежние пять
  markers (prefix, `НСтр`, три unused `ТекущийЭлемент`) без новых diagnostics.
