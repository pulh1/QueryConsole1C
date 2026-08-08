# Checkpoint: declarative SELECT operator

Дата: 2026-08-08.

## Результат

`ОбъединяемыйЗапрос` переведён на canonical codegen целиком: constructor,
модификаторы SELECT, поля и optional clauses теперь описаны EBNF и
declarative bindings в одной предметной production.

Удалены 12 technical helper-productions:

- `БлокВыбрать`;
- `МодификаторыВыборки`;
- `РазличныеРазрешенныеОпционально`;
- `РазрешенныеОпционально`;
- `ПервыеРазрешенныеОпционально`;
- `ПервыеОпционально`;
- `ПервыеРазличныеОпционально`;
- `РазличныеОпционально`;
- `БлокПоместить`;
- `БлокГде`;
- `БлокСгруппировать`;
- `БлокИмеющие`.

`ПЕРВЫЕ`, `РАЗЛИЧНЫЕ` и `РАЗРЕШЕННЫЕ` допускаются в прежних предметно
значимых перестановках, но каждое слово — не более одного раза. Все nested
decisions имеют disjoint canonical SELECT(2); порядок generated `Если` не
используется для разрешения конфликтов.

Optional clauses `ПОМЕСТИТЬ`, `ИЗ`, `ГДЕ`, `СГРУППИРОВАТЬ ПО` и `ИМЕЮЩИЕ`
оставляют factory defaults, если отсутствуют. При наличии значение сразу
попадает в свойство operator-а; intermediate `ПУСТО` и structural propagation
не создаются.

`БлокИз` пока остаётся legacy island source-family. Теперь он разбирает только
тело списка sources; ключевое слово `ИЗ`, optional boundary и СКД-extension
принадлежат canonical operator-production. В canonical/legacy boundary не
передаются `Родитель` или `ЛевыйЭлемент`.

## Coverage

Repository test проверяет generated behavior/shape:

- один constructor `НовыйОператорЗапроса`;
- bindings всех modifier и clause properties;
- отсутствие 12 runtime helper-functions;
- отсутствие `ТекущийЭлемент` и `НомерВариантаПродукции`;
- явный вызов оставшегося `БлокИз` без AST accumulator.

В основной headless YAxUnit parameterized test `МодификаторCase` добавлены
ранее документированные RED cases `M06`, `M07`, `M10`, `M14` для всех трёх
модификаторов в разных порядках. EDT syntax check прошёл. Фактический
platform run остаётся финальным integration gate.

## Metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 90 / 210 | 78 / 181 |
| Lowered CFG productions / alternatives / epsilon | 139 / 303 / 69 | 142 / 309 / 72 |
| Semantic action blocks / statements | 98 / 111 | 64 / 77 |
| Structural action statements | 71 | 45 |
| Formal parameters / actual arguments | 9 / 25 | 9 / 26 |
| `Родитель` / `ЛевыйЭлемент` usages in source grammar | 29 / 6 | 10 / 6 |
| Generated BSL functions / LOC | 102 / 2 476 | 90 / 2 328 |
| SELECT artifact rows | 1 588 | 1 487 |
| Legacy analysis matcher rows | 9 908 | 10 010 |

Lowered CFG немного вырос из-за nested EBNF choices. Эти synthetic productions
используются только canonical analysis: generated runtime функций для них не
создаёт, а production BSL уменьшился на 12 functions и 148 LOC.

- production lookahead: `k=2`;
- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- validation diagnostics: `0`.

Focused config/audit/repository/reference suite: `75 passed`,
`150 subtests`.

Полный Python-контур: `468 passed`, `1 skipped`, `4 533 subtests`.
Единственный skip — системное ограничение Windows на создание symlink
(`WinError 1314`).

EDT подтвердил двухфазный контракт `Отбор` и `ОтборСгруппированных`:
до semantic processing это одно выражение, после обработки — массив выражений.
Документация constructor-а уточнена как `Произвольный`; две возникшие при
прямом declarative binding ошибки `Структура` → `Массив` устранены. У generated
parser остались только четыре ранее известные фоновые диагностики.

## Remaining boundary

Следующий source/JOIN slice должен убрать внутренние accumulators из
`БлокИз`, `СписокТаблиц`, `ИсточникДанныхЗапроса`, `Соединение`,
`ПраваяЧастьСоединения` и `ИсточникДанныхСоединения`. До этого `БлокИз`
остаётся изолированным legacy island и не определяет canonical dispatch.
