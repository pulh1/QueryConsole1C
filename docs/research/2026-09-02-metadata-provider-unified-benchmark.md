# Свежий old/new benchmark metadata provider

Дата измерения: 2026-09-02.

## Итог

На полном корпусе из 42 реальных `QueryExamples` объединённая реализация не
показала регрессии: median полного прохода уменьшилась с 687,5 до 682,5 ms
(`0,9927×`, −0,7%), p95 — с 836 до 786 ms (`0,9402×`, −6,0%). Median на один
запрос, полученная делением времени прохода корпуса на 42, равна 16,37 ms для
baseline и 16,25 ms для feature.

На controlled contract из семи коротких запросов feature медленнее на 17,2%
по median и 18,2% по p95. Абсолютно это 17,0 против 14,5 ms на семь запросов;
оба распределения шумные (`CV 20,78%` и `21,87%`). На одном большом пакете
median хуже на 2,8%, а p95 лучше на 2,9%.

## Реализации и порядок

- baseline production:
  `0f0b17d3325216fd8af16f05ced9bc2c17021475`;
- feature production:
  `62c21c440cec1a14586c4ab0389a320f40fea6c7`;
- платформа/runtime: `8.3.27.2170`, Windows x86-64;
- entrypoint: `ОбработкаМоделиЗапроса.РазобратьЗапрос`, то есть полный путь
  lexer → parser → построение и семантическая обработка модели;
- порядок: feature → baseline → baseline → feature (`F–B–B–F`).

Каждый запуск выполнял только exact-тест
`КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineСемантическогоКонвейераФормируется`.
Parser/lexer benchmark-регистрации в эту серию не входили. Перед timed-run
EDT показывал 0 debug launches/targets; `dbgs`/`rdbg` отсутствовали, порт 1550
был свободен. Runtime MCP и test client Vanessa не работали против целевой ИБ.

## Методика и валидация

- 3 warmup и 20 timed samples в каждом из четырёх запусков;
- одинаковые schema 2, benchmark id, entrypoint, четыре corpus id, порядок,
  точные input length и SHA-256 всех входов;
- одинаковый runtime, clock и calibration target;
- все 160 sample положительные;
- все artifact hash обеих реализаций пересчитаны из заявленных source commit
  как normalized UTF-8 LF без BOM и совпали;
- raw sidecar скопированы без изменения байтов; SHA-256 источника и durable
  copy совпал.

Калибратор выбрал `iterations_per_sample=8` для baseline и 16 для feature на
коротком `repeated_standard_source`. `samples_ms` уже делятся harness-ом на
число итераций, но из-за различного batch этот micro-результат не используется
для сильного вывода. На `semantic_contract` batch одинаков и равен 2, на двух
реальных корпусах — 1.

## Результаты отдельных запусков

| Порядок | Реализация | Contract median / p95, ms | Repeated median / p95, ms | 42 queries median / p95, ms | Large median / p95, ms |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | feature | 16,50 / 26,50 | 3,09375 / 4,6875 | 708 / 870 | 69 / 84 |
| 2 | baseline | 15 / 22 | 3,3125 / 5,375 | 690 / 836 | 70 / 91 |
| 3 | baseline | 14 / 21,50 | 2,8125 / 3,625 | 686,50 / 818 | 82 / 103 |
| 4 | feature | 18 / 23 | 3 / 4,375 | 680 / 712 | 79,50 / 104 |

## Объединённый контрбалансированный результат

Для каждой реализации объединены 40 raw samples двух внешних или двух
внутренних запусков соответственно.

| Корпус | Baseline median | Feature median | Ratio median | Baseline p95 | Feature p95 | Ratio p95 | CV baseline / feature |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `semantic_contract` | 14,50 | 17,00 | 1,1724 | 22,00 | 26,00 | 1,1818 | 21,87% / 20,78% |
| `repeated_standard_source` | 3,125 | 3,0625 | 0,9800 | 5,25 | 4,5625 | 0,8690 | 24,81% / 20,17% |
| `semantic_query_examples_all_42` | 687,50 | 682,50 | 0,9927 | 836,00 | 786,00 | 0,9402 | 10,93% / 8,97% |
| `semantic_large_package` | 72,00 | 74,00 | 1,0278 | 103,00 | 100,00 | 0,9709 | 16,84% / 18,46% |

## Raw evidence

| Порядок | Файл | SHA-256 |
| ---: | --- | --- |
| 1 | `2026-09-02-full-semantic-pipeline-unified-62c21c4.json` | `C0CF9F50D1E5D9024E24BAF6058AAA38EED345C113A2AEFDEE25D963AAC78C9C` |
| 2 | `2026-09-02-full-semantic-pipeline-baseline-fresh-0f0b17d-1.json` | `93C89114086F93B9FB140924DBAB2E14C2B8A3F1CC0FF9741F0073BD84FC4249` |
| 3 | `2026-09-02-full-semantic-pipeline-baseline-fresh-0f0b17d-2.json` | `38E9B90B26D0B986057FD7EE906CDAA758C43ECF6163084E3C956655E3CA5C27` |
| 4 | `2026-09-02-full-semantic-pipeline-unified-62c21c4-2.json` | `9136D9F07E1F2D392561E17A4ED000E45EF6A305ECC18ADAE0A329E6F9A7DF51` |

Все файлы находятся в `docs/superpowers/matrices/`.

## Вывод

Для реального корпуса из 42 запросов и большого пакета регрессии полного
конвейера не обнаружено. Накладные расходы видны на маленьком controlled
contract, но не масштабируются на реальные запросы. Результат
`repeated_standard_source` подтверждает отсутствие крупной повторной стоимости,
однако из-за разного calibrated batch и высокого CV трактуется только как
вспомогательный micro-signal.
