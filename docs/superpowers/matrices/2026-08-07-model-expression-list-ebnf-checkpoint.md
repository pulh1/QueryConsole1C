# Production checkpoint: EBNF-список model expressions

`СписокВыраженийМодели` переведён в canonical ownership после
`СписокВыражений`. Query model и её properties не изменялись:
container `СписокВыражений` сохранён как предметное значение
`Группировка`.

## Result

- Source helper-production
  `ОпциональноеПродолжениеСпискаВыраженийМодели` удалёна.
- Grammar использует
  `Элементы += <ВыражениеМоделиЗапроса> (',' ...)*`.
- Generated BSL содержит один loop, без recursive helper и
  без legacy dispatch.
- Separator не попадает в AST и потребляется без ненужной
  temporary variable. Это правило закреплено focused codegen test.
- Production `lookahead` остался `k=2`; canonical SELECT conflicts: `0`.
- Full legacy matcher artifact остался `9 078` rows.

## Structural delta

| Metric | Before model-list slice | After model-list slice |
| --- | ---: | ---: |
| Source productions | 119 | 118 |
| Source alternatives | 275 | 273 |
| Lowered CFG productions / alternatives / epsilon | 124 / 281 / 63 | 124 / 281 / 63 |
| Semantic action blocks / statements | 358 / 384 | 354 / 380 |
| Constructor statements | 94 | 93 |
| Collection statements | 35 | 33 |
| Constant statements | 26 | 26 |
| Structural statements | 224 | 223 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions | 131 | 130 |
| Generated BSL LOC | 3 291 | 3 275 |
| Production select rows | 7 600 | 7 312 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Identifier rows | 276 | 276 |

## Verification

- Focused generator/repository tests: `25 passed, 8 subtests passed`.
- Focused production/reference tests: `61 passed, 1 skipped, 70 subtests passed`.
- Full Python: `409 passed, 1 skipped, 4090 subtests passed`.
- `parsergen validate`: exit `0`, две известных `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Canonical/runtime conflicts: `0` / `0`.
- EDT revalidation: production Parser `10`, full-query YAxUnit module `37`;
  новых syntax diagnostics нет.
- Full-query YAxUnit characterization добавляет группировку из
  пяти expressions и проверяет количество; interactive run оставлен
  на финальный Vanessa/YAxUnit gate.

## Remaining

Остальные list/optional helper families, comparison/specialized logical
operators и query-model normalization остаются следующими vertical slices.
