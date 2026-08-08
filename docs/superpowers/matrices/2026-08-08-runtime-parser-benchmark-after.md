# Runtime parser benchmark — after grammar optimization

Дата фактического прогона: 2026-08-08.

After-замер выполнен тем же серверным YAxUnit-тестом и на том же corpus,
что baseline до миграции. Прогон
`КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineПарсераФормируется`
завершён **1/1 GREEN** на 1C 8.3.27.2170, Windows x86-64.

## Артефакты

- Durable JSON: `2026-08-08-runtime-parser-benchmark-after.json`.
- Before JSON: `2026-08-07-runtime-parser-benchmark-before.json`.
- Raw after sidecar:
  `C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________8acc9b7ac_cb9a94032232579ef15977ae91f60977c6bea36c\runtime-parser-benchmark-after.json`.
- JUnit report в том же каталоге: `report.md`.

## Wall-clock before/after

| Corpus | Median before, ms | Median after, ms | Median change | p95 before, ms | p95 after, ms | p95 change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `query_examples_all_42` | 1679.5 | 860 | -48.8% | 2030 | 903 | -55.5% |
| `large_package` | 161.5 | 99 | -38.7% | 195 | 107 | -45.1% |
| `long_field_list` | 161.5 | 85.5 | -47.1% | 192 | 95 | -50.5% |
| `join_chain` | 68.5 | 55.5 | -19.0% | 80 | 77 | -3.7% |
| `union_package_chain` | 96.5 | 44.5 | -53.9% | 125 | 67 | -46.4% |
| `arithmetic_chain` | 65.5 | 40 | -38.9% | 96 | 49 | -49.0% |
| `logical_chain` | 77 | 54.5 | -29.2% | 109 | 70 | -35.8% |
| `dereference_chain` | 20 | 12.5 | -37.5% | 32 | 13 | -59.4% |

Во всех восьми классах уменьшились и median, и p95. Наибольший выигрыш
median получен на UNION/package chain, полном наборе QueryExamples и длинном
списке полей. Заранее заданного обязательного процента ускорения не было.

## Structural before/after

| Metric | Before | After |
| --- | ---: | ---: |
| Source productions | 124 | 66 |
| Source alternatives | 281 | 144 |
| Explicit source epsilon alternatives | 63 | 1 |
| Action blocks / statements | 398 / 431 | 0 / 0 |
| Formal parameters / actual arguments | 8 / 26 | 0 / 0 |
| Generated BSL LOC | 3394 | 1949 |
| Generated functions | 135 | 77 |
| Generated procedures | 6 | 5 |
| Generated routines | 141 | 82 |
| Generated `НеТерминал*` functions | 124 | 66 |
| Runtime legacy dispatch calls | available in old path | 0 |

After parser artifact SHA256:
`bee278fd4eaa17ff559164ee5dd3ec460b6586d244bb9ef78e3b36928ad4c71a`.

Canonical analysis CFG после EBNF lowering содержит 156 productions, 334
alternatives и 80 epsilon alternatives. Эти synthetic analysis nodes не
генерируют recursive runtime functions; codegen сохраняет high-level EBNF/LR
knowledge и выпускает loops/left folds.

## Internal counters

`dispatch_calls.value = 0`: canonical generated parser не содержит
`НомерВариантаПродукции`. Остальные internal counters остаются `null` с
непустым `unavailable_reason`, поскольку production runtime намеренно не
получал дорогостоящую test-only instrumentation:

- `nonterminal_calls`;
- `maximum_recursion_depth`;
- `constructor_action_executions`;
- `ast_node_container_allocations`.

Итеративная форма repetition и direct LR отдельно защищена generated-code
shape tests и long-chain runtime tests; недоступный stack counter не заменён
выдуманным числом.

## Interpretation

Это один before/after прогон на одном runtime и машине, поэтому проценты не
следует трактовать как универсальную аппаратно-независимую оценку. Сравнение
валидно как migration evidence: одинаковы platform/runtime, corpus,
entrypoints, warm-up count, sample count и метод калибровки.
