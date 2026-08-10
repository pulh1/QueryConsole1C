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

> **Correction 2026-08-11:** standalone lexer speedup подтверждён только для
> lexer registration. Опубликованная ниже historical parser+lexer → current
> parser+lazy lexer разница не изолирует влияние lexer, потому что одновременно
> меняется parser implementation. Поэтому она не является доказательством
> ускорения полного пути за счёт lexer. Full-path lexer performance verdict по
> этой серии: **не установлен**.

Отдельная interleaved order-varied серия полного пути `lexer + parser` с
порядком ABA измерила общую historical → current эволюцию:

| Сценарий | Historical parser + lexer | Current parser + lazy lexer | Ускорение |
| --- | ---: | ---: | ---: |
| `query_examples_all_42` | 1 019 мс | 600 мс | 1,70x |
| `large_package` | 92 мс | 61,5 мс | 1,50x |
| `time_accounting_large` | 2 671,5 мс | 1 738 мс | 1,54x |

Это медианы трёх run medians из отдельной шестизапусковой серии. Current path
оказался быстрее в каждой из трёх пар запусков на каждом corpus. Порядок ABA не
является полностью сбалансированным, поэтому величина ускорения ниже считается
descriptive и order-sensitive. Кроме того, сравнение смешивает две независимые
переменные — parser и lexer — и не позволяет приписать эффект lexer.

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
- Full-path series 1: historical parser + lexer, current parser + lazy lexer.
- Full-path series 2: current parser + lazy lexer, historical parser + lexer.
- Full-path series 3: historical parser + lexer, current parser + lazy lexer.
- Полный semantic frontend намеренно не измерялся.

Измеряемый lexer path включает установку исходного текста, batch regex scan,
последовательное чтение и materialization всех содержательных токенов и EOF.
Parser path включает `Разобрать`/`РазобратьВыражение` и внутреннюю токенизацию;
создание parser object находится вне timed sample.

## Provenance

- Historical lexer: `old-lexer-59d538f`, commit
  `59d538fd974c723c6b1cf336c61b0fea1aec8453`, normalized SHA-256
  `434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20`.
- Historical parser: `old-parser-59d538f`, materialized normalized SHA-256
  `dc401e271105eb34b4b2234c75b13fcdfd0341bb3b6766507d9f8cb1eb62e8b7`;
  historical source SHA-256
  `0c365e1e521322554b63e400379be47c0dc5ecaa7f60dd6951dc84bc7cccd084`.
- Lazy lexer: `current-lazy-lexer-f6abfbe`, implementation commit
  `f6abfbecc1156bbd12eaedf36cc5ac6765d1eee6`, normalized SHA-256
  `f954b1bb7b619052c553bf42699ed5fbbc3d5a7b64cd6ef4386b1970ca5e967d`.
- Parser: `current-parser-lazy-lexer-f6abfbe`, normalized SHA-256
  `f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf`.
- Benchmark provenance preparation: commit
  `18df5672df137cabd632b1d9ffacbef1b779e0e8`.

Для двух current parser templates sidecar `original_bytes` SHA относится к
CRLF-байтам Windows checkout. Git blobs implementation commit имеют LF и другие
raw SHA, но их содержимое побайтно совпадает после нормализации CRLF/CR в LF.
Следовательно, commit provenance для templates является normalized-content
provenance, а не равенством raw bytes.

## Результаты по всем corpus

`median/p95` — median трёх run medians и median трёх run p95. Время относится к
одной corpus iteration; `query_examples_all_42` выполняет 42 операции за одну
iteration. p95 внутри run вычисляется nearest-rank методом. CV — median
коэффициента вариации raw samples по трём runs с sample standard deviation
(`n-1`). Batch — median трёх значений `iterations_per_sample`.

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

## Полный путь lexer + parser

Эта таблица использует только отдельную interleaved order-varied серию
old/current parser с порядком ABA, а не contextual parser values из lexer-серии
выше. Ускорения являются descriptive/order-sensitive оценками; current path
быстрее во всех 27 парных сравнениях (3 runs x 9 corpus). Таблица характеризует
общую замену historical parser+lexer на current parser+lazy lexer, но не эффект
lexer при фиксированном parser.

| Corpus | Old parser+lexer median/p95, мс | Current parser+lazy median/p95, мс | Ускорение | CV old/current | Batch old/current |
| --- | ---: | ---: | ---: | ---: | ---: |
| `query_examples_all_42` | 1 019 / 1 083 | 600 / 662 | 1,70x | 6,0% / 6,8% | 1 / 1 |
| `large_package` | 92 / 122 | 61,5 / 83 | 1,50x | 13,7% / 16,7% | 1 / 1 |
| `long_field_list` | 96 / 126 | 75 / 94 | 1,28x | 13,4% / 14,6% | 1 / 1 |
| `join_chain` | 52,5 / 88 | 50 / 60 | 1,05x | 23,6% / 25,1% | 1 / 1 |
| `union_package_chain` | 57,5 / 85 | 48 / 63 | 1,20x | 17,9% / 19,6% | 1 / 1 |
| `arithmetic_chain` | 38 / 44 | 33 / 40 | 1,15x | 22,0% / 24,0% | 1 / 1 |
| `logical_chain` | 59 / 84 | 48 / 55 | 1,23x | 18,9% / 22,6% | 1 / 1 |
| `dereference_chain` | 15 / 17 | 14,625 / 17,25 | 1,03x | 7,0% / 25,6% | 2 / 4 |
| `time_accounting_large` | 2 671,5 / 2 869 | 1 738 / 1 856 | 1,54x | 4,8% / 8,1% | 1 / 1 |

Run medians основных full-path сценариев:

| Сценарий | Historical parser + lexer, мс | Current parser + lazy lexer, мс |
| --- | --- | --- |
| `query_examples_all_42` | 1 019; 1 480,5; 858 | 652,5; 600; 495 |
| `large_package` | 92; 158,5; 86 | 75; 61,5; 61,5 |
| `time_accounting_large` | 2 671,5; 3 725,5; 2 223,5 | 1 738; 1 771; 1 494,5 |

Во второй паре заметен общий всплеск historical timings. Он не скрыт и не
отфильтрован: итог использует median трёх runs, а raw medians приведены выше.
Направление результата не зависит от этой пары — current path быстрее во всех
трёх парных сериях.

## Контроль с фиксированным Decision DAG parser

После сопоставления с ранее сохранёнными measurements обнаружено, что parser
SHA-256 во всех трёх группах одинаков:
`f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf`.
Меняется только lexer artifact:

- before batch: `434c0230...`;
- eager batch: `292fba5e...`;
- lazy batch: `f954b1bb...`.

| Corpus | Decision DAG + old lexer | Decision DAG + eager batch | Decision DAG + lazy batch |
| --- | ---: | ---: | ---: |
| `query_examples_all_42` | 557,5 мс | 559,5 мс | 600 мс |
| `large_package` | 62 мс | 63,5 мс | 61,5 мс |
| `time_accounting_large` | 1 551 мс | 1 486,5 мс | 1 738 мс |

Это median трёх run medians из сохранённых групп:

- old lexer: `2026-08-09-runtime-parser-before-batch-{1,2,3}.json`;
- eager batch: локальные
  `2026-08-10-runtime-parser-after-batch-{1,2,3}.json`;
- lazy batch: `2026-08-10-runtime-parser-lazy-lexer-comparison-{1,2,3}.json`.

Относительно fixed-parser old-lexer группы lazy результат составляет примерно
`+7,6%` для 42 запросов, `-0,8%` для 843 токенов и `+12,1%` для большого
запроса, где плюс означает замедление. Эти группы запускались не в одной
counterbalanced серии и имели разные launch conditions, поэтому числа являются
только диагностическим cross-series наблюдением. Они не доказывают регрессию,
и не подтверждают дополнительный full-path speedup. Ранее заявленный verdict
отозван из-за confounding parser+lexer в historical→current baseline.

Для окончательного verdict нужен новый clean benchmark, в котором один и тот же
Decision DAG parser чередуется только между old и lazy lexer, без изменения
parser artifact, corpus, runtime и launch configuration.

## Validation

Во время выполнения `run_yaxunit_tests` сообщил для каждой из пятнадцати timed
registrations `Total=1`, `Passed=1`, `Failed=0`, `Errors=0`, `Skipped=0`.
Runner reports были transient и не включены в durable evidence; raw sidecar
самостоятельно доказывает завершённое измерение и данные, но не YAxUnit outcome.

Проверка 15/15 raw JSON подтвердила:

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
| `2026-08-10-runtime-old-parser-clean-1.json` | `5090e61dd02d76a867ca6346e75742a4322b7ea52303e40ac3427e6ee64b0a11` |
| `2026-08-10-runtime-old-parser-clean-2.json` | `8ccecfe8d33e09f1f2e89fc584ecbeb6f0f2646345413a494d0cebfc47933926` |
| `2026-08-10-runtime-old-parser-clean-3.json` | `77ed06f762fd994de75ce4604d70f6ba9bb2f668d1a24024fe5d58768711f5ac` |
| `2026-08-10-runtime-parser-lazy-lexer-comparison-1.json` | `27487e8d7fd3fd6dd9277e22cb29fcd335125e5dc27f59c1bc5652186d424a4f` |
| `2026-08-10-runtime-parser-lazy-lexer-comparison-2.json` | `937dbe2893a5a0cfb9aa2f1473ca13da4ca115e810a47b672b2af8bcc1fdd8b6` |
| `2026-08-10-runtime-parser-lazy-lexer-comparison-3.json` | `16717fd04e08a0f9cccd7cc023556e78708120e45ef4b8ac21dbfdf8368ab1c5` |
