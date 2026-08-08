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
  `C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________f49cea393_39767d76ab1d38f5fadfa5c32807961daa03e544\runtime-parser-benchmark-after.json`.
- JUnit report в том же каталоге: `report.md`.

## Wall-clock before/after

| Corpus | Median before, ms | Median after, ms | Median change | p95 before, ms | p95 after, ms | p95 change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `query_examples_all_42` | 1679.5 | 862.5 | -48.6% | 2030 | 918 | -54.8% |
| `large_package` | 161.5 | 95 | -41.2% | 195 | 97 | -50.3% |
| `long_field_list` | 161.5 | 83 | -48.6% | 192 | 92 | -52.1% |
| `join_chain` | 68.5 | 55.5 | -19.0% | 80 | 88 | +10.0% |
| `union_package_chain` | 96.5 | 41.5 | -57.0% | 125 | 49 | -60.8% |
| `arithmetic_chain` | 65.5 | 48.5 | -26.0% | 96 | 64 | -33.3% |
| `logical_chain` | 77 | 55 | -28.6% | 109 | 64 | -41.3% |
| `dereference_chain` | 20 | 13 | -35.0% | 32 | 20 | -37.5% |

Во всех восьми классах уменьшилась median. p95 уменьшился в семи классах из
восьми; на коротком JOIN corpus p95 одного повторного прогона вырос с 80 до
88 мс при неизменном улучшении median на 19.0%. Наибольший выигрыш median
получен на UNION/package chain, полном наборе QueryExamples и длинном списке
полей. Заранее заданного обязательного процента ускорения не было.

## Structural before/after

| Metric | Before | After |
| --- | ---: | ---: |
| Source productions | 124 | 66 |
| Source alternatives | 281 | 144 |
| Explicit source epsilon alternatives | 63 | 1 |
| Action blocks / statements | 398 / 431 | 0 / 0 |
| Formal parameters / actual arguments | 8 / 26 | 0 / 0 |
| Generated BSL LOC | 3394 | 1954 |
| Generated functions | 135 | 77 |
| Generated procedures | 6 | 5 |
| Generated routines | 141 | 82 |
| Generated `НеТерминал*` functions | 124 | 66 |
| Runtime legacy dispatch calls | available in old path | 0 |

After parser artifact SHA256:
`537939b79bc29d77d581b8148973595481f444c1415b082d032e461133736b45`.

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
