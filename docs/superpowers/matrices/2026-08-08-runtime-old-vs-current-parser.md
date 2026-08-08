# Runtime: старый и текущий parser

## Provenance

- Старый parser: `old-parser-59d538f`, commit
  `59d538fd974c723c6b1cf336c61b0fea1aec8453`.
- Текущий parser: `current-parser-17c105d`, commit
  `17c105dcc864ea475353c350088e3cdbe97a3761`.
- Старый JSON SHA-256:
  `709cae8deda9df266d19675508f9ad364729d34cb86589012574bdf5fe166d6c`.
- Текущий JSON SHA-256:
  `2e0b7587ac474fe781db11d325d0c846e4c188465278a786c1fb6fa6042fdc24`.
- Оба запуска выполнены через один YAxUnit harness: девять corpus,
  три прогрева, двадцать samples, batch calibration target 25 ms.
- Значение `ускорение` вычислено как `старый / текущий`; больше единицы
  означает преимущество текущего parser.

## Результаты

| corpus | median старый, ms | median текущий, ms | ускорение median | p95 старый, ms | p95 текущий, ms | ускорение p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| query_examples_all_42 | 1276 | 869 | 1.468× | 1456 | 944 | 1.542× |
| large_package | 118 | 92.5 | 1.276× | 181 | 102 | 1.775× |
| long_field_list | 115.5 | 81 | 1.426× | 145 | 106 | 1.368× |
| join_chain | 82 | 55 | 1.491× | 111 | 71 | 1.563× |
| union_package_chain | 82.5 | 41.5 | 1.988× | 103 | 50 | 2.060× |
| arithmetic_chain | 53 | 39 | 1.359× | 83 | 43 | 1.930× |
| logical_chain | 82 | 53.5 | 1.533× | 105 | 63 | 1.667× |
| dereference_chain | 22.25 | 12.5 | 1.780× | 34.5 | 14.75 | 2.339× |
| time_accounting_large | 3333 | 3519 | 0.947× | 3759 | 3895 | 0.965× |

## Наблюдение

Текущий parser быстрее старого на восьми из девяти corpus. На большом запросе
учёта времени текущий parser медленнее: median на 5.6%, p95 на 3.6%. Это
измерительный факт, а не performance verdict; следующий Decision DAG этап
следует отдельно сравнить с обоими сохранёнными результатами.
