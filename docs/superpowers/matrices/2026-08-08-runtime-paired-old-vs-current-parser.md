# Counterbalanced runtime: old → current → old → current → current → old

## Методика

- Порядок запусков: old #1, current #1, old #2, current #2, current #3,
  old #3. Последняя пара обращает порядок и проверяет order effect.
- Каждый запуск: один и тот же YAxUnit harness, девять corpus, три прогрева,
  двадцать samples и batch calibration target 25 ms.
- Итоговые median и nearest-rank p95 рассчитаны по объединённым 60 samples
  каждой реализации. Samples уже нормализованы harness на одну итерацию.
- Отрицательное изменение означает преимущество current parser.

## Raw evidence

| Запуск | SHA-256 |
| --- | --- |
| old #1 | `fbb717f0f8146ff49f266f6c6af7deae727fddb72075275349d083e760efa0f2` |
| current #1 | `79fd646d2258d759f9a5b7ea48d05d550a1fe72b057408030334c342ec728b4e` |
| old #2 | `7ffc2b9d8bd23488b5806a0ba218943c8e8941410c467c288f5e6fa76fa39678` |
| current #2 | `7e2a9065356a4ae784403827346f560b83ffe190b03dff97abbb0404d93d8ebf` |
| current #3 | `9efe47f5084a274c7ce2c378df85b10f0398efb62a611dfc5adc7f4abb2f1fa6` |
| old #3 | `b020a55f207f6369deaae665f3e36c14460411c2c49675bebdaf098609cb9f68` |

## Объединённые результаты

| corpus | old median, ms | current median, ms | median change | old p95, ms | current p95, ms | p95 change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| query_examples_all_42 | 1272 | 1200 | −5.7% | 1447 | 1392 | −3.8% |
| large_package | 122 | 129 | +5.7% | 168 | 179 | +6.5% |
| long_field_list | 119.5 | 110.5 | −7.5% | 160 | 149 | −6.9% |
| join_chain | 70.5 | 79.5 | +12.8% | 93 | 112 | +20.4% |
| union_package_chain | 77.5 | 55 | −29.0% | 135 | 83 | −38.5% |
| arithmetic_chain | 53 | 52 | −1.9% | 76 | 83 | +9.2% |
| logical_chain | 91 | 74 | −18.7% | 131 | 106 | −19.1% |
| dereference_chain | 20.75 | 17.75 | −14.5% | 35.5 | 32 | −9.9% |
| time_accounting_large | 3285 | 3592 | **+9.3%** | 3616 | 3848 | **+6.4%** |

## Проверка большого запроса по парам

| Пара | old median, ms | current median, ms | current change |
| --- | ---: | ---: | ---: |
| #1 | 3396 | 3574 | +5.2% |
| #2 | 3304.5 | 3656.5 | +10.7% |
| обратная #3 (`current → old`) | 3216 | 3567.5 | +10.9% |
| объединённые 60 samples | 3285 | 3592 | +9.3% |

Для `time_accounting_large` направление повторилось в обеих прямых парах и
в обратной паре. В объединённой серии коэффициент вариации равен 9.31% у old
и 3.57% у current. Поэтому локальное замедление current parser на этом запросе
нельзя объяснить единичным выбросом или тем, что current всегда запускался
вторым.

Результаты остальных малых corpus более чувствительны к шуму millisecond
clock и состоянию runtime. Наиболее устойчивые крупные эффекты этой серии:
ускорение `union_package_chain` и `logical_chain`, а также замедление
`join_chain` и `time_accounting_large`. `dereference_chain` быстрее в
aggregate, но направление его разницы менялось между отдельными парами.
