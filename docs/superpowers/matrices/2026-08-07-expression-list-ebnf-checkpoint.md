# Production checkpoint: EBNF-список выражений

`СписокВыражений` переведён в canonical ownership как первый
production EBNF-срез. Query model и её properties не изменялись:
`СписокВыражений` остаётся предметным container node для оператора
`В`.

## Result

- Source helper-production `ОпциональноеПродолжениеСпискаВыражений` удалёна.
- Естественная grammar использует
  `Элементы += <Выражение> (',' Элементы += <Выражение>)*`.
- Generated BSL содержит один `Пока` loop, без recursive helper
  и без `НомерВариантаПродукции`.
- Separator `,` потребляется внутри loop и не попадает в AST.
- Production `lookahead` остался `k=2`; canonical SELECT conflicts: `0`.
- Legacy matcher artifact не изменился и не участвует в loop decision.

## Structural delta

| Metric | Before list slice | After list slice |
| --- | ---: | ---: |
| Source productions | 120 | 119 |
| Source alternatives | 277 | 275 |
| Lowered CFG productions / alternatives / epsilon | 124 / 281 / 63 | 124 / 281 / 63 |
| Semantic action blocks / statements | 362 / 388 | 358 / 384 |
| Constructor statements | 95 | 94 |
| Collection statements | 37 | 35 |
| Constant statements | 26 | 26 |
| Structural statements | 225 | 224 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions | 132 | 131 |
| Generated BSL LOC | 3 307 | 3 291 |
| Production select rows | 7 888 | 7 600 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Identifier rows | 276 | 276 |

## Verification

- Focused Python: `60 passed, 1 skipped, 70 subtests passed`.
- Full Python: `408 passed, 1 skipped, 4090 subtests passed`.
- `parsergen validate`: exit `0`, две известных `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Canonical/runtime conflicts: `0` / `0`.
- EDT revalidation: production Parser `11`, expression YAxUnit module `31`.
  Новых syntax errors нет; production list включает давно
  documented unreachable `НеТерминалКакОпционально` как unused-method
  warning.
- Generated-shape test проверяет loop, две collection bindings,
  separator и отсутствие helper/legacy dispatch.
- YAxUnit characterization проверяет порядок пяти элементов
  в `В (1, 2, 3, 4, 5)`; interactive run оставлен на финальный
  Vanessa/YAxUnit gate.

## Remaining

Остальные list/optional helper families, comparison/specialized logical
operators и query-model normalization остаются следующими vertical slices.
Legacy compatibility остаётся isolated для ещё не migrated
productions.
