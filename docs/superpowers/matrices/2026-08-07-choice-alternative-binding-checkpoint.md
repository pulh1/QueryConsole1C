# Production checkpoint: declarative CASE alternative

`КогдаТогда` переведён в canonical ownership без изменения query model.
Предметный узел `АльтернативаВыбора` по-прежнему содержит scalar properties
`Условие` и `Действие`, но source grammar больше не присваивает их через
imperative BSL actions.

## Result

- Source grammar использует constructor `@НовыйАльтернативаВыбора` и bindings
  `Условие = <Выражение>`, `Действие = <Выражение>`.
- Generated function напрямую потребляет `КОГДА`/`ТОГДА`, сохраняет два
  semantic results и выполняет ровно по одному присваиванию каждого property.
- В функции отсутствуют `ТекущийЭлемент`, action guards и legacy dispatch.
- Production lookahead остался `k=2`; canonical/runtime conflicts: `0` / `0`.
- Legacy matcher artifact не изменился: `9 078` rows.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 112 / 262 | 112 / 262 |
| Lowered CFG productions / alternatives / epsilon | 124 / 282 / 63 | 124 / 282 / 63 |
| Semantic action blocks / statements | 337 / 363 | 334 / 360 |
| Constructor statements | 90 | 89 |
| Collection / constant statements | 29 / 26 | 29 / 26 |
| Structural statements | 213 | 211 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 124 / 3 193 | 124 / 3 187 |
| Production SELECT rows | 6 846 | 6 803 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

## Coverage

- Focused Python test first demonstrated legacy token plumbing (RED), then
  verifies constructor cardinality, both scalar bindings, direct terminal
  consumption and absence of legacy variables/dispatch (GREEN).
- Existing YAxUnit CASE characterization checks selector, two ordered
  condition/action pairs and `ИНАЧЕ` value, so this slice needs no new model
  assertion.
- Interactive YAxUnit/Vanessa remains the final integration gate by agreement.

## Verification

- Focused repository/audit/reference/codegen: `55 passed`, `37 subtests`.
- Full Python: `414 passed`, `1 skipped`, `4090 subtests passed`; skip is the
  known Windows symlink-privilege case.
- `parsergen validate`: exit `0`, two known `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Read-only audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  artifact changes `0`.
- EDT revalidation of `DataProcessor.Парсер`: the same `10` baseline
  diagnostics; no new syntax or unused-local diagnostics.

## Remaining

CASE/`ВЫБОР` no longer contains structural semantic actions. Other scalar,
list and optional production families remain separate vertical slices.
