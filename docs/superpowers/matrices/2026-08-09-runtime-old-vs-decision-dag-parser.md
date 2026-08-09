# Runtime: old parser vs Decision DAG parser

## Результат

Оба parser измерены отдельными YAxUnit server tests на одинаковых девяти
corpus. В каждом запуске использованы 3 прогрева, 20 samples и target
калибровки batch 25 ms. Lexer benchmark не запускался.

| Corpus | Old median, ms | DAG median, ms | Median | Ускорение | Old p95, ms | DAG p95, ms | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `query_examples_all_42` | 1461.50 | 525.50 | -64.0% | 2.78x | 1583.00 | 535.00 | -66.2% |
| `large_package` | 135.00 | 60.00 | -55.6% | 2.25x | 180.00 | 61.00 | -66.1% |
| `long_field_list` | 131.50 | 52.50 | -60.1% | 2.50x | 156.00 | 56.00 | -64.1% |
| `join_chain` | 81.00 | 36.00 | -55.6% | 2.25x | 101.00 | 39.00 | -61.4% |
| `union_package_chain` | 101.00 | 32.00 | -68.3% | 3.16x | 120.00 | 33.00 | -72.5% |
| `arithmetic_chain` | 60.00 | 26.00 | -56.7% | 2.31x | 93.00 | 28.00 | -69.9% |
| `logical_chain` | 88.50 | 32.00 | -63.8% | 2.77x | 148.00 | 36.00 | -75.7% |
| `dereference_chain` | 26.00 | 12.75 | -51.0% | 2.04x | 34.00 | 13.50 | -60.3% |
| `time_accounting_large` | 3499.50 | 1451.50 | -58.5% | 2.41x | 3880.00 | 1509.00 | -61.1% |

Decision DAG parser быстрее старого на всех девяти corpus. Диапазон выигрыша
median составляет 51.0–68.3%, или 2.04–3.16 раза. На запросе учёта времени
длиной 160135 символов median уменьшилась с 3499.5 до 1451.5 ms.

Это последовательная серия `Decision DAG → old`, а не counterbalanced запуск.
Поэтому она не отделяет полностью order/environment effect. Однако минимальная
наблюдаемая разница median (51.0%) существенно больше внутрисерийной
вариативности; CV старого parser составляет 5.5–26.0%, Decision DAG parser —
1.2–6.5%.

## Evidence

- Old parser: `2026-08-09-runtime-old-parser-baseline-rerun.json`, SHA-256
  `4edc89750e1159d3f5f237bba84c703f6b89642f1397862cf17c657b773b16b1`.
- Decision DAG parser: `2026-08-09-runtime-parser-decision-dag.json`, SHA-256
  `483bba2d336097d19c47f769934aae61c75d5d7ef63245456c7a1c135eb477bd`.
- Old parser implementation: `old-parser-59d538f`, commit
  `59d538fd974c723c6b1cf336c61b0fea1aec8453`.
- Decision DAG implementation: `current-parser-5a054c2`, commit
  `5a054c2d69d46ee261553c3c9ea696f89e65bb23`.
- YAxUnit old-parser result: 1 passed, 0 failed/errors/skipped.
