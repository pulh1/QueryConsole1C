# Clean runtime benchmark: lazy batch-regex lexer

Дата измерения: 2026-08-10.

## Итог

Production-ready lazy batch-regex lexer быстрее historical lexer на всех девяти
corpus. На двух основных реальных сценариях:

| Сценарий | Токены | Historical lexer, median | Lazy lexer, median | Ускорение | Parser + lazy lexer, median |
| --- | ---: | ---: | ---: | ---: | ---: |
| `large_package` | 843 | 70,5 мс | 20,0 мс | 3,52x | 65,5 мс |
| `time_accounting_large` | 19 617 | 1 370 мс | 579,5 мс | 2,36x | 1 584 мс |

Значения в таблице — медианы трёх независимо выполненных run medians. Каждый
run содержит 3 warm-up и 20 timed samples. Для этих двух corpus batch size равен
одной corpus iteration во всех девяти запусках.

## Условия и матрица

- Runtime: 1С:Предприятие 8.3.27.2170, Windows x86-64.
- Execution context: YAxUnit server test.
- Clock: `ТекущаяУниверсальнаяДатаВМиллисекундах`, resolution 1 мс.
- Calibration target: 25 мс; warm-ups: 3; samples: 20.
- Launch configuration: `QueryConsoleZUP Benchmark Тонкий клиент`.
- `ATTR_SHOW_PERFORMANCE=false`; debug и profiler не использовались.
- Series 1: historical lexer, lazy lexer, parser + lazy lexer.
- Series 2: lazy lexer, historical lexer, parser + lazy lexer.
- Series 3: historical lexer, lazy lexer, parser + lazy lexer.
- Historical parser и полный semantic frontend намеренно не измерялись.

Измеряемый lexer path включает установку исходного текста, batch regex scan,
последовательное чтение и materialization всех содержательных токенов и EOF.
Parser path включает `Разобрать`/`РазобратьВыражение` и внутреннюю токенизацию;
создание parser object находится вне timed sample.

## Provenance

- Historical lexer: `old-lexer-59d538f`, commit
  `59d538fd974c723c6b1cf336c61b0fea1aec8453`, normalized SHA-256
  `434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20`.
- Lazy lexer: `current-lazy-lexer-f6abfbe`, implementation commit
  `f6abfbecc1156bbd12eaedf36cc5ac6765d1eee6`, normalized SHA-256
  `f954b1bb7b619052c553bf42699ed5fbbc3d5a7b64cd6ef4386b1970ca5e967d`.
- Parser: `current-parser-lazy-lexer-f6abfbe`, normalized SHA-256
  `f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf`.
- Benchmark provenance preparation: commit
  `18df5672df137cabd632b1d9ffacbef1b779e0e8`.

## Результаты по всем corpus

`median/p95` — median трёх run medians и median трёх run p95. Время относится к
одной corpus iteration; `query_examples_all_42` выполняет 42 операции за одну
iteration. CV — median коэффициента вариации raw samples по трём runs.

| Corpus | Токены | Old median/p95, мс | Lazy median/p95, мс | Ускорение | Parser+lazy median/p95, мс | CV old/lazy/parser | Batch old/lazy/parser |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `query_examples_all_42` | 7 309 | 514,5 / 607 | 214 / 271 | 2,40x | 568 / 660 | 10,2% / 15,4% / 9,1% | 1 / 1 / 1 |
| `large_package` | 843 | 70,5 / 100 | 20 / 34,5 | 3,52x | 65,5 / 82 | 21,8% / 29,2% / 21,1% | 1 / 1 / 1 |
| `long_field_list` | 800 | 42 / 71 | 23,25 / 38 | 1,81x | 67 / 91 | 29,5% / 25,5% / 16,8% | 1 / 2 / 1 |
| `join_chain` | 612 | 30,5 / 54,5 | 20,5 / 27 | 1,49x | 41,5 / 58 | 28,8% / 28,3% / 23,9% | 1 / 2 / 1 |
| `union_package_chain` | 477 | 24,5 / 39,5 | 17,25 / 25 | 1,42x | 39,5 / 58 | 30,6% / 23,4% / 23,7% | 2 / 2 / 1 |
| `arithmetic_chain` | 399 | 23 / 35 | 11,5 / 19 | 2,00x | 25,75 / 41,5 | 30,7% / 27,4% / 24,5% | 1 / 4 / 2 |
| `logical_chain` | 479 | 25,5 / 42,5 | 13,75 / 19,25 | 1,85x | 37,5 / 56 | 26,6% / 29,3% / 22,7% | 2 / 4 / 1 |
| `dereference_chain` | 239 | 11,5 / 19 | 5,3125 / 8,875 | 2,16x | 12 / 17,5 | 26,3% / 31,3% / 23,8% | 2 / 8 / 4 |
| `time_accounting_large` | 19 617 | 1 370 / 1 729 | 579,5 / 642 | 2,36x | 1 584 / 1 724 | 8,0% / 10,5% / 6,6% | 1 / 1 / 1 |

Высокий CV коротких synthetic corpus ожидаем при миллисекундном clock и малом
абсолютном времени. Основные крупные сценарии имеют заметно меньшую
вариативность, а направление выигрыша одинаково во всех трёх runs.

Run medians основных сценариев:

| Сценарий | Historical lexer, мс | Lazy lexer, мс | Parser + lazy lexer, мс |
| --- | --- | --- | --- |
| `query_examples_all_42` | 514,5; 512; 530,5 | 214; 219,5; 193,5 | 568; 623,5; 529,5 |
| `large_package` | 70,5; 51,5; 77 | 20; 19; 20,5 | 70; 65,5; 64 |
| `time_accounting_large` | 1 503,5; 1 370; 1 305 | 588,5; 579,5; 506 | 1 584; 1 644,5; 1 520 |

## Validation

Все девять timed registrations завершились с `Total=1`, `Passed=1`,
`Failed=0`, `Errors=0`, `Skipped=0`.

Проверка 9/9 raw JSON подтвердила:

- schema version, implementation id, source ref/commit и artifact hashes;
- одинаковые runtime и methodology;
- девять corpus в одинаковом порядке;
- точное совпадение input ids, lengths, provenance и generator parameters;
- совпадение token counts historical и lazy lexer для каждого input;
- 20 положительных samples, положительные batch sizes, median и p95;
- уникальные capture timestamps для трёх runs каждой реализации.

Raw sidecar не содержит `raw_match_count`; поэтому ранее исследованные 1 297 и
29 717 regex matches не смешиваются с этой production timing evidence. Полный
semantic frontend также не входил в измеряемую матрицу.

## Raw evidence

| Файл | SHA-256 |
| --- | --- |
| `2026-08-10-runtime-old-lexer-clean-1.json` | `ee1fd5afa46389aebdc2d0f62339796deb20227c8f9f8aea69e9faabaf1a5943` |
| `2026-08-10-runtime-old-lexer-clean-2.json` | `6a85dd49355af25f74cc24fd43472782b51d3a9ec51d75509a0d4152df094423` |
| `2026-08-10-runtime-old-lexer-clean-3.json` | `8ba6d21b7511dd9f784c13811a057998ea836f402fd92127ce8decc7484a08ae` |
| `2026-08-10-runtime-lazy-lexer-clean-1.json` | `0368eaffc45166ff3bfa426da243a51a0f5adfa756835dccf0364083a5a1698e` |
| `2026-08-10-runtime-lazy-lexer-clean-2.json` | `a19f9c89482e0aae563a488af5da597deab267f63855d59ba8244bd9a146a3a4` |
| `2026-08-10-runtime-lazy-lexer-clean-3.json` | `1702bacf8f2fda8a1ff94f5d1bfc22596684dad5a2dc4feacb7463f5b6510fcc` |
| `2026-08-10-runtime-parser-lazy-lexer-clean-1.json` | `9c816e65c83eb5c470128baba3394bab1b602ffd7474a7010078714917541380` |
| `2026-08-10-runtime-parser-lazy-lexer-clean-2.json` | `4362a8aa3a6a7424f8b740585ed64da74c779ea2cf3d7374e9087d380fb7eb96` |
| `2026-08-10-runtime-parser-lazy-lexer-clean-3.json` | `d31e9834310406e8ce9b9aa0eaa366d63ac110e620fcfe873fea37aeb8c35ef2` |
