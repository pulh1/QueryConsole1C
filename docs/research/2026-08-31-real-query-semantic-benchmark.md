# Полный semantic benchmark на реальных запросах

Дата измерения: 2026-08-31.

## Итог

Feature-реализация проходит performance gate на всех четырёх корпусах, но
ускорением результат считать нельзя. На полном наборе из 42 реальных запросов
feature медленнее baseline по медиане на 5,5%, при этом p95 лучше на 4,0%.
На крупнейшем реальном пакете медиана хуже на 12,1%, p95 — на 9,9%.

Gate: `feature median <= baseline median * 1.25` и
`feature p95 <= baseline p95 * 1.50`. Все восемь сравнений проходят.

## Сравниваемые реализации

- baseline: `0f0b17d3325216fd8af16f05ced9bc2c17021475`,
  `metadata-provider-semantics-real-baseline-0f0b17d`;
- feature: `60e610164c01e52198015d9d88ae53c2b9599863`,
  `metadata-provider-semantics-real-lazy-60e6101`;
- платформа и runtime: `8.3.27.2170`, Windows x86-64;
- entrypoint: полный публичный путь
  `ОбработкаМоделиЗапроса.РазобратьЗапрос`, включая lexer, parser и semantic
  analysis.

До измерений aggregate preflight прошёл все 42 QueryExamples на обеих
реализациях без исключений. Корпус имеет одинаковые id, порядок, длины и
provenance входов во всех sidecar.

## Методика

- две зеркальные серии: A-B-B-A и B-A-A-B;
- перед каждой загрузкой реализации — отдельный нетаймируемый preflight;
- 3 внутренних warmup, 20 samples на запуск, target калибровки batch 25 ms;
- четыре запуска на реализацию, итого 80 raw samples на корпус и реализацию;
- перед каждым timed run подтверждены: runtime-client `running=false`, ноль
  debug launches/targets, ноль breakpoints, отсутствие `dbgs`/`rdbg` и listener
  на порту 1550;
- harness уже записывает каждый raw sample как длительность batch, делённую на
  `iterations_per_sample`, то есть как время одной полной итерации корпуса;
  итоговые median и p95 рассчитаны по 80 таким значениям каждой реализации.
  В `repeated_standard_source` калибратор в двух запусках выбрал batch 8, в
  остальных — 16, но эта разница уже устранена самим harness до записи
  `samples_ms`. p95 использует тот же nearest-rank алгоритм, что harness.

Первая серия показала сильный order effect: второй baseline был быстрее первого
на 19–33% на реальных корпусах. Поэтому одиночная A-B-B-A серия не использована
для финального вывода; выполнена зеркальная серия и объединён сбалансированный
набор.

## Сбалансированный результат

| Корпус | Входы / длина | Baseline median корпуса, ms | Feature median корпуса, ms | Median ratio | Baseline p95 корпуса, ms | Feature p95 корпуса, ms | P95 ratio | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `semantic_contract` | 7 / 1 087 | 14,0 | 17,0 | 1,2143 | 23,0 | 28,0 | 1,2174 | PASS |
| `repeated_standard_source` | 1 / 178 | 2,8125 | 3,125 | 1,1111 | 4,75 | 4,8125 | 1,0132 | PASS |
| `semantic_query_examples_all_42` | 42 / 67 253 | 646,0 | 681,5 | 1,0550 | 826,0 | 793,0 | 0,9600 | PASS |
| `semantic_large_package` | 1 / 8 170 | 62,0 | 69,5 | 1,1210 | 91,0 | 100,0 | 1,0989 | PASS |

Для корпуса 42 QueryExamples нормализованная стоимость одного запроса равна
15,381 ms на baseline и 16,226 ms на feature по медиане; это медиана полного
прохода корпуса, делённая на 42, а не распределение индивидуальных задержек
каждого запроса. Для крупнейшего пакета индивидуальная медиана — 62,0 против
69,5 ms.

Объединённый CV raw samples:

| Корпус | Baseline CV | Feature CV |
| --- | ---: | ---: |
| `semantic_contract` | 23,77% | 20,42% |
| `repeated_standard_source` | 23,72% | 21,00% |
| `semantic_query_examples_all_42` | 18,43% | 8,72% |
| `semantic_large_package` | 21,37% | 16,32% |

Короткий repeated-корпус остаётся шумным; его небольшую разницу нельзя
интерпретировать как доказательство ускорения или замедления. Он пригоден для
проверки установленного регрессионного порога.

## Raw evidence

Файлы скопированы из каталога JUnit report без изменения байтов; SHA-256
источника и durable copy совпал при каждом копировании.

| Файл | SHA-256 |
| --- | --- |
| `2026-08-31-full-semantic-pipeline-real-baseline-1.json` | `01B5C7C46AC4A0B233AE22203AFE3486E9CD6C3DE1E277FD32FACCF05F9C2657` |
| `2026-08-31-full-semantic-pipeline-real-feature-1.json` | `47C444ABFCADA508AB75C97CE2C8B1ACA98276CBC861DB48176B8F3F1E0206E9` |
| `2026-08-31-full-semantic-pipeline-real-feature-2.json` | `641087B039C207E85D988868EF42671F03E22C0923BF1C18CA290DB6899A1547` |
| `2026-08-31-full-semantic-pipeline-real-baseline-2.json` | `52F95F25F2B857CC040300C314EEC571FBB4B947DF9F8988F0FE8BEE10D33238` |
| `2026-08-31-full-semantic-pipeline-real-repeat-feature-1.json` | `765C146C34595539C567895B01D11985D346C047159BB116983EBB193321815C` |
| `2026-08-31-full-semantic-pipeline-real-repeat-baseline-1.json` | `E823634E48763488F7C497C55721ABC2FC9D715F8CEDC7A55DAC4472D36E6753` |
| `2026-08-31-full-semantic-pipeline-real-repeat-baseline-2.json` | `41BBDF936970ADB621F365C29489344E14ABD923ABC8FA176E569EF94A59D577` |
| `2026-08-31-full-semantic-pipeline-real-repeat-feature-2.json` | `C8B5FE82F8BE7ED729D89B2CDE66D02AF9CB7D131D751A752DEA511C359CD5EA` |

Четыре ранее существовавших untracked JSON без `real-` не изменялись и в этот
вывод не включены. Runtime MCP в этих измерениях не использовался.
