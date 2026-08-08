# Checkpoint: canonical DCS boundary shell

Дата: 2026-08-08.

## Результат

Одним compatibility-boundary package переведены на canonical codegen две
связанные actionless productions:

- `РасширениеСКД`;
- `ТипБлокаСКД`.

Source grammar и query model в этом package не менялись. Цель шага — убрать
legacy matcher dispatch с внешней оболочки СКД до более крупной migration
самого `ТелоБлокаСКД`.

Generated `РасширениеСКД` теперь:

- принимает решение по canonical SELECT(2);
- потребляет `{` и `}` без matcher table lookup;
- вызывает оставшийся legacy island `ТелоБлокаСКД` через явно проверенный
  compatibility ABI;
- не содержит `НомерВариантаПродукции` и `ТекущийЭлемент`.

`ТипБлокаСКД` также использует canonical disjoint alternatives для
`ВЫБРАТЬ`, `УПОРЯДОЧИТЬ ПО` и `ИТОГИ ПО`.

## Boundary constraint

Parameterized canonical call к `ТелоБлокаСКД(Оператор)` генерируется как:

```bsl
НеТерминалТелоБлокаСКД(Неопределено, Неопределено, Оператор)
```

То есть legacy ABI slots `Родитель`/`ЛевыйЭлемент` не получают canonical AST
accumulator; через boundary передается только явный source formal argument.
Canonical analysis не использует legacy matcher semantics.

## Coverage

Существующие headless YAxUnit cases защищают observable behavior:

- `K04`: расширение `{ГДЕ ...}` после обычного `ГДЕ`;
- `K05`: расширение `{ГДЕ ...}` после SELECT fields;
- error case `K06`: незакрытый блок СКД.

Repository shape-test проверяет canonical code shape, delimiters, три типа
блока, точный boundary call и отсутствие legacy dispatch plumbing.
Фактический platform run YAxUnit остается финальным integration gate.

## Metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 90 / 210 | 90 / 210 |
| Lowered CFG productions / alternatives / epsilon | 139 / 303 / 69 | 139 / 303 / 69 |
| Semantic action blocks / statements | 98 / 111 | 98 / 111 |
| Generated BSL functions / LOC | 102 / 2 486 | 102 / 2 476 |
| SELECT artifact rows | 1 596 | 1 588 |
| Legacy analysis matcher rows | 9 908 | 9 908 |

- production lookahead: `k=2`;
- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- validation diagnostics: `0`.

Focused repository/config/audit/reference suite: `74 passed`,
`129 subtests`.

Полный `tools/parsergen/tests`: `467 passed`, `1 skipped`,
`4512 subtests`; skip — прежнее ограничение Windows на создание symlink.

Точечная ревалидация EDT объекта `DataProcessor.Парсер` завершилась успешно.
После регенерации осталось четыре прежних marker-а: требование префикса
расширения, один `НСтр` и две неиспользуемые локальные переменные. Новых
диагностик нет; по сравнению с предыдущим checkpoint исчез ещё один marker
неиспользуемого `ТекущийЭлемент`.

## Remaining DCS legacy island

Пока не мигрированы:

- `ТелоБлокаСКД` с mutation `Оператор.ОтборыСКД`;
- `СписокПолейОпционально`, остающийся для DCS-body field lists.

Их нужно переводить одним coherent model/binding slice, а не сохранять
`Родитель` или side-effect mutation в новом DSL.
