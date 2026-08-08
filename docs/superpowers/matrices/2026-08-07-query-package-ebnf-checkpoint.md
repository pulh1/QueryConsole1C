# Production checkpoint: query-package EBNF

`ПакетЗапросов` переведён с recursive continuation-production на canonical
EBNF без изменения query model. Корневой узел по-прежнему содержит
`Элементы` в исходном порядке.

## Result

- Source grammar:
  `@НовыйПакетЗапросов Элементы += <ЗапросПакета> (';' Элементы += <ЗапросПакета>)* ';'?`.
- `ПродолжениеПакетаЗапросов` удалена из source grammar и generated BSL.
- Generated BSL разбирает дополнительные запросы одним `Пока` и отдельно
  допускает завершающую `;`; separator в AST не сохраняется.
- Repeat/exit и optional consume/exit SELECT disjoint при production `k=2`;
  canonical conflicts: `0`.
- `ЗапросПакета` пока остаётся legacy island. Canonical package code calls it
  through the stable nonterminal boundary and не использует matcher dispatch
  для собственных EBNF decisions.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 112 / 262 | 111 / 259 |
| Lowered CFG productions / alternatives / epsilon | 124 / 282 / 63 | 125 / 283 / 64 |
| Semantic action blocks / statements | 315 / 340 | 310 / 335 |
| Constructor statements | 80 | 79 |
| Collection / constant statements | 29 / 22 | 27 / 22 |
| Structural / other statements | 205 / 4 | 203 / 4 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 124 / 3 151 | 123 / 3 136 |
| Production SELECT rows | 6 700 | 6 630 |
| Full legacy matcher rows | 9 078 | 9 079 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

Lowered CFG grows by one production and one alternative because repeat and
optional each retain a synthetic analysis node. These nodes do not become BSL
functions. The one-row legacy matcher delta belongs only to the compatibility
artifact built from the lowered CFG; canonical package decisions do not read it.

## Coverage

- Focused Python test checks one generated loop, optional separator handling,
  two ordered collection append sites and absence of both continuation function
  and legacy dispatch in `НеТерминалПакетЗапросов`.
- Existing full-parser contracts Q00-Q05 cover a single SELECT, two SELECTs,
  trailing `;`, one destroy query and both SELECT/destroy orderings. They assert
  package type, element count, order, node types and destroy-table name.
- Existing text generation consumes `ПакетЗапросов.Элементы` in order; query
  model and downstream property names are unchanged.
- Interactive YAxUnit/Vanessa execution remains the final migration gate by
  agreement.

## Verification

- Focused repository/config/audit/codec/reference: `53 passed`,
  `61 subtests passed`.
- Full `tools/parsergen/tests`: `419 passed`, `1 skipped`,
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

`ЗапросПакета` still contains two structural passthrough actions. Its migration
needs an explicit declarative passthrough/choice decision and is not folded into
this EBNF slice mechanically.
