# Runtime benchmark текущего Decision DAG parser

## Результат

Измерен только production parser `DataProcessor.Парсер`. Старый parser и оба
lexer benchmark не запускались.

- implementation: `current-parser-5a054c2`;
- parser source commit: `5a054c2d69d46ee261553c3c9ea696f89e65bb23`;
- normalized parser SHA-256: `f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf`;
- platform/runtime: `8.3.27.2170`, Windows x86-64, YAxUnit server test;
- методика: 3 прогрева, 20 samples, target калибровки batch 25 ms;
- YAxUnit: 1 test, 1 passed, 0 failed/errors/skipped;
- durable JSON SHA-256: `483bba2d336097d19c47f769934aae61c75d5d7ef63245456c7a1c135eb477bd`.

| Corpus | Median, ms | p95, ms | Batch | CV samples | Median к pre-DAG |
|---|---:|---:|---:|---:|---:|
| `query_examples_all_42` | 525.50 | 535.00 | 1 | 1.2% | -39.5% |
| `large_package` | 60.00 | 61.00 | 1 | 2.4% | -35.1% |
| `long_field_list` | 52.50 | 56.00 | 1 | 4.0% | -35.2% |
| `join_chain` | 36.00 | 39.00 | 1 | 6.5% | -34.5% |
| `union_package_chain` | 32.00 | 33.00 | 1 | 3.8% | -22.9% |
| `arithmetic_chain` | 26.00 | 28.00 | 1 | 4.4% | -33.3% |
| `logical_chain` | 32.00 | 36.00 | 1 | 6.2% | -40.2% |
| `dereference_chain` | 12.75 | 13.50 | 2 | 3.3% | +2.0% |
| `time_accounting_large` | 1451.50 | 1509.00 | 1 | 1.9% | -58.8% |

Столбец сравнения использует сохранённый single-run pre-DAG baseline
`2026-08-08-runtime-current-parser-baseline.json` (`current-parser-17c105d`) с
теми же девятью corpus. Это направляющее сравнение, а не окончательный
counterbalanced verdict: реализации запускались не в чередующемся порядке.

Для corpus из 42 реальных запросов median всего пакета равна 525.5 ms, то есть
примерно 12.51 ms на один parse. Огромный запрос учёта времени длиной 160135
символов разбирается за median 1451.5 ms.

## Evidence

- Durable sidecar: `2026-08-09-runtime-parser-decision-dag.json`.
- Temporary YAxUnit report:
  `C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________b685c402a_2035629e9d2197b86aae3a64b2c4271ae41a74a0\report.md`.
- Temporary sidecar был скопирован без преобразования; SHA-256 исходного и
  durable файла совпал.
