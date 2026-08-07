# Production checkpoint: declarative reference-type bindings

`ТипСсылочногоПоля` переведён в canonical ownership без изменения query model.
Точные identifier classes, ранее введённые для устранения ложного LL(2)
конфликта, сохранены в source grammar.

## Result

- Source grammar:
  `@НовыйТипСсылочногоПоля Группа = #ID_ГруппаТипаСсылки '.' Таблица = #ID_ИмяТипа`.
- Generated BSL сохраняет два identifier values в `Группа` и `Таблица` в
  исходном порядке; separator `.` потребляется без AST binding.
- В функции отсутствуют `ТекущийЭлемент`, action guards, случайный пустой BSL
  statement из старого constructor action и legacy dispatch.
- Canonical SELECT remains disjoint at production `k=2`; конфликтов `0`.
- Invalid broad group such as `АВТОУПОРЯДОЧИВАНИЕ.Имя` остаётся rejected.
- Legacy matcher artifact remains isolated and unchanged: `9 078` rows,
  runtime conflicts `0`.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 112 / 262 | 112 / 262 |
| Lowered CFG productions / alternatives / epsilon | 124 / 282 / 63 | 124 / 282 / 63 |
| Semantic action blocks / statements | 320 / 346 | 317 / 342 |
| Constructor statements | 82 | 81 |
| Collection / constant statements | 29 / 22 | 29 / 22 |
| Structural / other statements | 208 / 5 | 206 / 4 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 124 / 3 162 | 124 / 3 155 |
| Production SELECT rows | 6 719 | 6 718 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

## Coverage

- Existing YAxUnit function-type case checks exact `Группа = "Справочник"`
  and `Таблица = "Номенклатура"` values.
- Existing reference-check expression covers the same node in the `ССЫЛКА`
  operator path.
- Existing syntax-error case protects rejection of
  `ССЫЛКА АВТОУПОРЯДОЧИВАНИЕ.Имя`.
- Focused Python shape test verifies both identifier classes/bindings,
  separator consumption and absence of legacy plumbing.
- Interactive YAxUnit/Vanessa remains the final integration gate by agreement.

## Verification

- Focused repository/audit/reference/config/codec: `51 passed`, `61 subtests`.
- Full Python: `417 passed`, `1 skipped`, `4094 subtests passed`; skip is the
  known Windows symlink-privilege case.
- `parsergen validate`: exit `0`, two known `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Read-only audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  artifact changes `0`.
- EDT revalidation of `DataProcessor.Парсер`: the same `10` baseline
  diagnostics; no new syntax or unused-local diagnostics.

## Remaining

The parent `ЛогическийОператор` still uses legacy actions and left-element
plumbing; it requires a separate coherent left-fold/operator slice.
