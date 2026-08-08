# Production checkpoint: transparent alias alternatives

`Псевдоним` переведён с imperative token propagation на transparent canonical
choice:

```text
<Псевдоним> ::= КАК #ID_ПсевдонимРасширенный | #ID_Псевдоним
```

В каждой alternative identifier является единственным value-bearing symbol и
автоматически становится результатом production.

## Result

- Exact identifier classes сохранены: после `КАК` используется расширенный
  alias class, без `КАК` — более узкий `ID_Псевдоним`.
- Generated BSL возвращает identifier value из обеих alternatives без
  `ТекущийЭлемент` и legacy matcher dispatch.
- Canonical SELECT alternatives disjoint при production `k=2`; конфликт не
  разрешается порядком generated branches.
- Query model и downstream alias properties не изменены.
- Full legacy matcher artifact остаётся `9 079` rows.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 111 / 259 | 111 / 259 |
| Lowered CFG productions / alternatives / epsilon | 125 / 283 / 64 | 125 / 283 / 64 |
| Semantic action blocks / statements | 308 / 333 | 306 / 331 |
| Constructor statements | 79 | 79 |
| Collection / constant statements | 27 / 22 | 27 / 22 |
| Structural / other statements | 201 / 4 | 199 / 4 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 123 / 3 125 | 123 / 3 114 |
| Production SELECT rows | 6 564 | 6 479 |
| Full legacy matcher rows | 9 079 | 9 079 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

## Coverage

- Focused Python test checks both exact identifier classes, transparent results
  and absence of legacy plumbing.
- Existing full-parser alias cases F02/F03 and source aliases S01/S09/S10 cover
  `КАК` and bare aliases through observable AST properties.
- Existing invalid keyword/alias characterization protects the narrower bare
  alias class.
- Interactive YAxUnit/Vanessa execution remains the final integration gate by
  agreement.

## Verification

- Focused repository/config/audit/codec/reference: `55 passed`,
  `61 subtests passed`.
- Full `tools/parsergen/tests`: `421 passed`, `1 skipped`,
  `4 094 subtests passed`; the skip is the known Windows symlink privilege case.
- `parsergen validate`: exit `0`, with the two existing `VAL102` unreachable
  production warnings.
- `parsergen generate --check`: exit `0`, artifacts are current.
- Migration audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  changed artifacts `0`.
- EDT revalidation of `DataProcessor.Парсер`: the same 10 baseline diagnostics
  (object prefix, `НСтр`, seven unused `ТекущийЭлемент` variables and one
  unused helper method); no new parser syntax diagnostics.
- Post-gate process check found no Python process with working set above 1 GB.
- `git diff --check`: exit `0`; only line-ending conversion warnings.

## Remaining

`ПсевдонимОпционально` remains a helper production. It can be removed only in
the coherent `ПолеВыборки` migration, where optional alias binding and the
special `*` field alternative must preserve the existing expression wrapper.
