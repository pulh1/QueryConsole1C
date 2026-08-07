# Production checkpoint: declarative constant alternatives

`Константа` переведена в canonical ownership без изменения query model.
String/number values связываются как parsed tokens, а keyword alternatives
задают semantic value через declarative constant binding.

## Result

- Six source alternatives now use `@НовыйКонстанта`.
- `&СтроковаяКонстанта` and `&ЧисловаяКонстанта` bind directly to `Значение`.
- `ИСТИНА`, `ЛОЖЬ`, `NULL`, `НЕОПРЕДЕЛЕНО` consume their keyword and assign
  `Истина`, `Ложь`, `Null`, `Неопределено` respectively.
- The DSL/validator explicitly supports BSL `Null`; arbitrary names remain
  rejected by `BIND204`.
- Generated dispatch uses canonical disjoint SELECT at production `k=2`;
  canonical/runtime conflicts: `0` / `0`.
- Legacy matcher artifact remains isolated and unchanged: `9 078` rows.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 112 / 262 | 112 / 262 |
| Lowered CFG productions / alternatives / epsilon | 124 / 282 / 63 | 124 / 282 / 63 |
| Semantic action blocks / statements | 332 / 358 | 320 / 346 |
| Constructor statements | 88 | 82 |
| Collection / constant statements | 29 / 26 | 29 / 22 |
| Structural statements | 210 | 208 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 124 / 3 183 | 124 / 3 162 |
| Production SELECT rows | 6 725 | 6 719 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

The audit counts only legacy source action statements; therefore four keyword
assignments disappear from `constant_statements` after becoming declarative
`AssignConstant` operations.

## Coverage

- Existing YAxUnit parameterized characterization checks integer, decimal,
  string, boolean true/false, platform `Null` and `Неопределено` values.
- Focused validator/codegen tests prove that `Null` is accepted and rendered
  exactly, while the existing invalid-name test still protects `BIND204`.
- Focused production shape test checks six constructors/bindings, direct
  keyword consumption and absence of legacy variables/dispatch.
- Interactive YAxUnit/Vanessa remains the final integration gate by agreement.

## Verification

- Focused repository/audit/reference/codegen/binding/config/codec: `104 passed`,
  `95 subtests`.
- Full Python: `416 passed`, `1 skipped`, `4094 subtests passed`; skip is the
  known Windows symlink-privilege case.
- `parsergen validate`: exit `0`, two known `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Read-only audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  artifact changes `0`.
- EDT revalidation of `DataProcessor.Парсер`: the same `10` baseline
  diagnostics; no new syntax or unused-local diagnostics.

## Remaining

Enum/dotted symbolic constants are supported synthetically but not yet used by
a production slice. Remaining list/optional families and query-model
normalization continue separately.
