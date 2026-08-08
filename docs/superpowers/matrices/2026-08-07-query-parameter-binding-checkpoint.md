# Production checkpoint: declarative query parameter token binding

`Параметр` переведён в canonical ownership без изменения query model.
Production теперь декларативно связывает значение identifier token с
`ПараметрЗапроса.Имя`.

## Result

- Source grammar: `@НовыйПараметрЗапроса '&' Имя = #ID_Полный`.
- Generated BSL напрямую потребляет `&`, материализует ровно один semantic
  identifier result и присваивает его в `ЭтотУзел.Имя`.
- В функции отсутствуют `ТекущийЭлемент`, action guard и legacy dispatch.
- Production lookahead остался `k=2`; canonical/runtime conflicts: `0` / `0`.
- Legacy matcher artifact не изменился: `9 078` rows.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 112 / 262 | 112 / 262 |
| Lowered CFG productions / alternatives / epsilon | 124 / 282 / 63 | 124 / 282 / 63 |
| Semantic action blocks / statements | 334 / 360 | 332 / 358 |
| Constructor statements | 89 | 88 |
| Collection / constant statements | 29 / 26 | 29 / 26 |
| Structural statements | 211 | 210 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 124 / 3 187 | 124 / 3 183 |
| Production SELECT rows | 6 803 | 6 725 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

## Coverage

- Existing YAxUnit `ПараметрЗапросаРазбирается` checks the node type and exact
  value `Имя = "Параметр"` for input `&Параметр`.
- Existing parser-reuse characterization repeats parameter parsing after a
  previous expression and checks the same semantic value.
- Focused Python shape test was RED on legacy token plumbing and now verifies
  the direct identifier call/binding and absence of legacy variables/dispatch.
- Interactive YAxUnit/Vanessa remains the final integration gate by agreement.

## Verification

- Focused repository/audit/reference/codegen/config/codec: `84 passed`,
  `86 subtests`.
- Full Python: `415 passed`, `1 skipped`, `4090 subtests passed`; skip is the
  known Windows symlink-privilege case.
- `parsergen validate`: exit `0`, two known `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Read-only audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  artifact changes `0`.
- EDT revalidation of `DataProcessor.Парсер`: the same `10` baseline
  diagnostics; no new syntax or unused-local diagnostics.

## Remaining

Token binding is proven on a production identifier. Constant/enum bindings,
remaining list/optional families and query-model normalization continue as
separate vertical slices.
