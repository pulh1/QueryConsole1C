# Production checkpoint: totals checkpoint type

`ТипКонтрольнойТочки` переведён на two constructor-only alternatives and an
explicit empty alternative:

```text
@НовыйТипКонтрольнойТочкиТолькоИерархия ТОЛЬКО ИЕРАРХИЯ
| @НовыйТипКонтрольнойТочкиИерархия ИЕРАРХИЯ
| ПУСТО
```

## Result

- The two present forms construct the same string enum values; the empty form
  returns `Неопределено` as before.
- Alternatives are disjoint under production `k=2`; generated branch order is
  not conflict resolution.
- `КонтрольнаяТочкаИтогов.ТипКонтрольнойТочки` and downstream consumers remain
  unchanged.
- Full legacy matcher artifact remains isolated at `9 079` rows.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 111 / 259 | 111 / 259 |
| Lowered CFG productions / alternatives / epsilon | 125 / 283 / 64 | 125 / 283 / 64 |
| Semantic action blocks / statements | 302 / 327 | 300 / 325 |
| Constructor statements | 75 | 73 |
| Collection / constant statements | 27 / 22 | 27 / 22 |
| Structural / other statements | 199 / 4 | 199 / 4 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 123 / 3 107 | 123 / 3 105 |
| Production SELECT rows | 6 475 | 6 472 |
| Full legacy matcher rows | 9 079 | 9 079 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

The audit constructor count includes only legacy action statements; both
constructors remain explicit canonical Parser IR operations.

## Coverage

- Focused Python test checks the exact terminal sequence, both constructors,
  the empty result and absence of legacy dispatch.
- Existing full-parser T07/T08/T03 cases cover hierarchy, only-hierarchy and
  empty forms through the observable totals checkpoint property.
- Interactive YAxUnit/Vanessa execution remains the final integration gate by
  agreement.

## Verification

- Focused repository/config/audit/codec/reference: `57 passed`,
  `65 subtests passed`.
- Full `tools/parsergen/tests`: `423 passed`, `1 skipped`,
  `4 098 subtests passed`; the skip is the known Windows symlink privilege case.
- `parsergen validate`: exit `0`, with the two existing `VAL102` unreachable
  production warnings.
- `parsergen generate --check`: exit `0`, artifacts are current.
- Migration audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  changed artifacts `0`.
- EDT revalidation of `DataProcessor.Парсер`: diagnostics improved from 9 to 8
  because one more unused `ТекущийЭлемент` disappeared. Remaining baseline is
  the object prefix, `НСтр`, five unused `ТекущийЭлемент` variables and one
  unused helper method; no new parser syntax diagnostics.
- Post-gate process check found no Python process with working set above 1 GB.
- `git diff --check`: exit `0`; only line-ending conversion warnings.

## Remaining

The surrounding totals/checkpoint productions still use parent propagation,
optional helpers and structural property assignments; they require a coherent
totals vertical slice.
