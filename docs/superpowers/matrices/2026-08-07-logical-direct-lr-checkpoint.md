# Production checkpoint: direct LR логических цепочек

`Выражение` и `ЛогическоеСлагаемое` переведены на canonical
Parser IR вслед за arithmetic families. Query model и её properties не
изменялись.

## Result

- Source helper-productions `ЛогическоеИли` и `ЛогическоеИ` удалены.
- `Выражение` описывает left-recursive `ИЛИ`,
  `ЛогическоеСлагаемое` — left-recursive `И`.
- Generated BSL содержит по одному loop на precedence level, ноль
  self-calls и ноль `НомерВариантаПродукции` calls.
- Left associativity: `A И B И C` строит `((A И B) И C)`,
  `A ИЛИ B ИЛИ C` строит `((A ИЛИ B) ИЛИ C)`.
- Precedence остаётся структурным: `И` разбирается в base
  production для `ИЛИ` и поэтому имеет более высокий приоритет.
- Production `lookahead` остался `k=2`; canonical SELECT conflicts: `0`.

## Structural delta

| Metric | Before logical slice | After logical slice |
| --- | ---: | ---: |
| Source productions | 122 | 120 |
| Source alternatives | 279 | 277 |
| Lowered CFG productions / alternatives / epsilon | 124 / 281 / 63 | 124 / 281 / 63 |
| Semantic action blocks / statements | 374 / 402 | 362 / 388 |
| Constructor statements | 97 | 95 |
| Constant statements | 28 | 26 |
| Structural statements | 235 | 225 |
| Collection statements | 37 | 37 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions | 134 | 132 |
| Generated BSL LOC | 3 351 | 3 307 |
| Production select rows | 8 464 | 7 888 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Identifier rows | 276 | 276 |

## Verification

- Full Python: `407 passed, 1 skipped, 4090 subtests passed`.
- `parsergen validate`: exit `0`, две известных `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Canonical/runtime conflicts: `0` / `0`.
- EDT diagnostic totals не изменились: production Parser `10`, expression
  YAxUnit module `31`; нового syntax delta нет.
- Repository generated-shape tests проверяют `LeftFold`, loops, отсутствие
  helper-functions, self-recursion и legacy dispatch calls.
- YAxUnit scenarios добавлены для левой ассоциативности `И`/`ИЛИ`;
  interactive run оставлен на финальный Vanessa/YAxUnit gate.

## Remaining

Comparison, specialized logical operators, repetition/optional families и query-model
normalization остаются в следующих vertical slices. Legacy compatibility
остаётся isolated для ещё не migrated productions.
