# Production checkpoint: declarative CASE/ВЫБОР

`Выбор` переведён в canonical ownership целиком. Query model сохранила
предметные properties `ВыражениеВыбора`, `АльтернативыВыбора` и `Иначе`;
технический промежуточный массив между parser и model удалён.

## Result

- Source helper-productions `ВыражениеВыбора`, `АльтернативыВыбора`,
  `ПродолжениеАльтернативВыбора` и `Иначе` удалены.
- Grammar использует `<Выражение>?`, `<КогдаТогда>+` и
  `(ИНАЧЕ <Выражение>)?` с declarative bindings непосредственно в `Выбор`.
- Generated BSL содержит один alternatives loop и два optional branches,
  без helper recursion, legacy dispatch и unused token temporaries.
- `НовыйАльтернативыВыбора`, возвращавший сырой parser-container `Массив`,
  удалён после фактической проверки references; `НовыйВыбор` по-прежнему
  создаёт предметный массив `АльтернативыВыбора`.
- Canonical BSL validation различает generated identifiers и member names:
  keyword запрещён как имя функции/параметра, но допустим после точки,
  поэтому существующее property `ЭтотУзел.Иначе` поддерживается явно.
- Production `lookahead` остался `k=2`; canonical/runtime conflicts: `0` / `0`.
- Full legacy matcher artifact остался `9 078` rows и не участвует в
  canonical CASE decisions.

## Structural delta

| Metric | Before choice slice | After choice slice |
| --- | ---: | ---: |
| Source productions | 116 | 112 |
| Source alternatives | 269 | 262 |
| Lowered CFG productions / alternatives / epsilon | 124 / 282 / 63 | 124 / 282 / 63 |
| Semantic action blocks / statements | 347 / 373 | 337 / 363 |
| Constructor statements | 92 | 90 |
| Collection statements | 31 | 29 |
| Constant statements | 26 | 26 |
| Structural statements | 219 | 213 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions | 128 | 124 |
| Generated BSL LOC | 3 246 | 3 193 |
| Production select rows | 7 223 | 6 846 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Constructor names in generated artifact | 79 | 78 |
| Identifier rows | 276 | 276 |

## Coverage

- Existing searched CASE scenarios retain one and multiple alternatives.
- New simple CASE characterization checks selector, two ordered conditions,
  two ordered actions and `ИНАЧЕ` value.
- Focused codegen test checks optional absent assignment, exactly one loop,
  direct collection binding and absence of four helper functions.
- Interactive YAxUnit/Vanessa run remains the final integration gate.

## Verification

- Focused generator/repository/audit/reference tests:
  `59 passed, 68 subtests passed` до финального liveness regression.
- Focused codegen liveness regression: `33 passed, 8 subtests passed`.
- Full Python: `413 passed, 1 skipped, 4090 subtests passed`.
- `parsergen validate`: exit `0`, две известных `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Canonical/runtime conflicts: `0` / `0`.
- EDT revalidation: production Parser вернулся к baseline `10`; expression
  model factory module имеет `82` фоновых diagnostics; YAxUnit module `33`.
  Новых syntax diagnostics нет.
- EDT code search после regeneration/removal:
  `НовыйАльтернативыВыбора` — `0` references/definitions.

## Remaining

`КогдаТогда` was migrated in the next
[choice-alternative checkpoint](2026-08-07-choice-alternative-binding-checkpoint.md).
Remaining list/optional families and query-model normalization continue as
separate vertical slices.
