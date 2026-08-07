# Production checkpoint: join-type constructors

`ТипСоединения` переведён с legacy constructor actions на четыре canonical
constructor declarations:

```text
@НовыйТипСоединенияЛевое ЛЕВОЕ
| @НовыйТипСоединенияПравое ПРАВОЕ
| @НовыйТипСоединенияВнутреннее ВНУТРЕННЕЕ
| @НовыйТипСоединенияПолное ПОЛНОЕ
```

## Result

- Generated BSL invokes each existing domain constructor exactly once in its
  keyword alternative and returns the same string enum value.
- Four SELECT alternatives are pairwise disjoint at production `k=2`; branch
  order is not used as conflict resolution.
- `ПраваяЧастьСоединения.ТипСоединения` and all downstream consumers remain
  unchanged.
- Full legacy matcher artifact remains isolated and unchanged at `9 079` rows.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 111 / 259 | 111 / 259 |
| Lowered CFG productions / alternatives / epsilon | 125 / 283 / 64 | 125 / 283 / 64 |
| Semantic action blocks / statements | 306 / 331 | 302 / 327 |
| Constructor statements | 79 | 75 |
| Collection / constant statements | 27 / 22 | 27 / 22 |
| Structural / other statements | 199 / 4 | 199 / 4 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 123 / 3 114 | 123 / 3 107 |
| Production SELECT rows | 6 479 | 6 475 |
| Full legacy matcher rows | 9 079 | 9 079 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

The audit constructor count covers only legacy action statements. The four
constructors remain present as declarative `ConstructNode` operations in the
canonical Parser IR and generated BSL.

## Coverage

- Focused Python test checks all four exact keyword/constructor pairs and
  absence of legacy dispatch/temporary propagation.
- Existing full-parser J01-J04 cases assert all four resulting
  `Соединения[0].ТипСоединения` values; J05-J07 cover optional and chained joins.
- Interactive YAxUnit/Vanessa execution remains the final integration gate by
  agreement.

## Verification

- Focused repository/config/audit/codec/reference: `56 passed`,
  `65 subtests passed`.
- Full `tools/parsergen/tests`: `422 passed`, `1 skipped`,
  `4 098 subtests passed`; the skip is the known Windows symlink privilege case.
- `parsergen validate`: exit `0`, with the two existing `VAL102` unreachable
  production warnings.
- `parsergen generate --check`: exit `0`, artifacts are current.
- Migration audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  changed artifacts `0`.
- EDT revalidation of `DataProcessor.Парсер`: diagnostics improved from 10 to
  9 because one unused `ТекущийЭлемент` disappeared. Remaining baseline is the
  object prefix, `НСтр`, six unused `ТекущийЭлемент` variables and one unused
  helper method; no new parser syntax diagnostics.
- Post-gate process check found no Python process with working set above 1 GB.
- `git diff --check`: exit `0`; only line-ending conversion warnings.

## Remaining

`ПраваяЧастьСоединения`, source/join collection recursion and optional join
braces still contain structural actions and require a coherent source-list
vertical slice.
