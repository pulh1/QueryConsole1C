# Runtime parser benchmark baseline — before EBNF/LR migration

Дата фактического прогона: 2026-08-07.

Baseline получен серверным YAxUnit-тестом
`КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineПарсераФормируется`.
Прогон завершён **1/1 GREEN**. Это измерения runtime BSL parser, а не
Python-анализ и не оценочные значения.

## Артефакты

- Durable UTF-8 JSON без BOM:
  `docs/superpowers/matrices/2026-08-07-runtime-parser-benchmark-before.json`.
- Raw sidecar, записанный самим серверным тестом рядом с JUnit:
  `C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________f49cea393_39767d76ab1d38f5fadfa5c32807961daa03e544\runtime-parser-benchmark-before.json`.
- JUnit/report:
  `C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________f49cea393_39767d76ab1d38f5fadfa5c32807961daa03e544\report.md`.

## Runtime и parser artifact

| Metric | Actual value |
| --- | ---: |
| 1C platform/runtime | 8.3.27.2170 |
| Platform type | Windows x86-64 |
| Execution context | YAxUnit server test |
| Parser path | `QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl` |
| SHA256 | `0c365e1e521322554b63e400379be47c0dc5ecaa7f60dd6951dc84bc7cccd084` |
| Generated BSL LOC | 3394 |
| Functions | 135 |
| Procedures | 6 |
| Total routines | 141 |
| `НеТерминал*` functions | 124 |

## Measurement method

- Clock: `ТекущаяУниверсальнаяДатаВМиллисекундах`, nominal resolution 1 ms.
- Three warm-up batches and twenty measured batches for every corpus.
- Batch size is calibrated until at least 25 ms to avoid zero/quantized
  measurements; per-iteration time is batch duration divided by its iteration
  count.
- One initialized parser object is reused inside a corpus. Parser object
  creation is outside samples.
- `query_examples_all_42` parses every embedded XML
  `/querylist/query/text` once per iteration. The other corpora parse one
  input per iteration.
- Median uses the middle pair of 20 sorted samples; p95 uses nearest-rank.

## Actual wall-clock baseline

| Corpus | Entrypoint | Inputs | Total input length | Iterations/sample | Median, ms | p95, ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `query_examples_all_42` | `Разобрать` | 42 | 67253 | 1 | 1679.5 | 2030 |
| `large_package` | `Разобрать` | 1 | 8170 | 1 | 161.5 | 195 |
| `long_field_list` | `Разобрать` | 1 | 3190 | 1 | 161.5 | 192 |
| `join_chain` | `Разобрать` | 1 | 2962 | 1 | 68.5 | 80 |
| `union_package_chain` | `Разобрать` | 1 | 3081 | 1 | 96.5 | 125 |
| `arithmetic_chain` | `РазобратьВыражение` | 1 | 1089 | 1 | 65.5 | 96 |
| `logical_chain` | `РазобратьВыражение` | 1 | 1221 | 1 | 77 | 109 |
| `dereference_chain` | `РазобратьВыражение` | 1 | 854 | 2 | 20 | 32 |

Полный массив двадцати samples, точная provenance каждого входа и параметры
synthetic generators находятся в durable JSON. Для
`query_examples_all_42` там зафиксированы все 42 repository-relative path,
`/querylist/query/text`, query name, UTF-8 SHA256 и точная длина embedded
текста. Статический gate посимвольно сравнил каждый embedded BSL input с
соответствующим XML text.

## Недоступные internal counters

Production parser не изменялся и test-only interception hooks в нём нет.
Поэтому следующие значения нормативно записаны как JSON `null`, каждое с
непустым `unavailable_reason`:

| Counter | Reason |
| --- | --- |
| `nonterminal_calls` | Generated `НеТерминал*` functions не публикуют test-only call counter. |
| `dispatch_calls` | Private `НомерВариантаПродукции` не имеет exported counter/interception hook. |
| `maximum_recursion_depth` | Generated parser не предоставляет test-only stack-depth hook. |
| `constructor_action_executions` | Inline semantic constructors не предоставляют execution counter. |
| `ast_node_container_allocations` | Runtime не предоставляет этому server test scoped allocation counter для parser AST/container objects. |

## Interpretation rule

Phase 2.5 не задаёт обязательного процента ускорения. После migration нужно
повторить тот же corpus и объяснить wall-clock или generated-size regression.
Для repetition и direct-LR отдельно требуется доказать, что parser stack depth
не растёт пропорционально длине chain; текущий baseline не подменяет это
ограничение нулевым или выдуманным counter.
