# Production checkpoint: declarative destroy-query binding

`ЗапросУничтожения` переведён в canonical ownership без изменения query model.
Top-level query node still exposes `ИмяТаблицы`; parser now fills it directly
from `#ID_ИмяТаблицы`.

## Result

- Source grammar:
  `@НовыйЗапросУничтожения УНИЧТОЖИТЬ ИмяТаблицы = #ID_ИмяТаблицы`.
- Generated BSL consumes `УНИЧТОЖИТЬ`, captures one identifier and performs one
  scalar assignment, without `ТекущийЭлемент`, guards or legacy dispatch.
- Production lookahead remains `k=2`; canonical/runtime conflicts: `0` / `0`.
- Legacy matcher artifact remains isolated and unchanged: `9 078` rows.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 112 / 262 | 112 / 262 |
| Lowered CFG productions / alternatives / epsilon | 124 / 282 / 63 | 124 / 282 / 63 |
| Semantic action blocks / statements | 317 / 342 | 315 / 340 |
| Constructor statements | 81 | 80 |
| Collection / constant statements | 29 / 22 | 29 / 22 |
| Structural / other statements | 206 / 4 | 205 / 4 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 124 / 3 155 | 124 / 3 151 |
| Production SELECT rows | 6 718 | 6 700 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

## Coverage and consumers

- Existing full-parser case `Q03: УНИЧТОЖИТЬ ВТ` checks exact node type and
  `ИмяТаблицы = "ВТ"`; mixed package cases check ordering with SELECT queries.
- `ГенерацияТекстовЗапросов` reads `ИмяТаблицы` when recreating destroy-query
  text; `ИсполнительПредставлений` dispatches the same node type.
- Focused Python shape test checks exact identifier class/binding and absence
  of legacy plumbing.
- Interactive YAxUnit/Vanessa remains the final integration gate by agreement.

## Verification

- Focused Python: `52 passed`, `61 subtests passed`.
- Full `tools/parsergen/tests`: `418 passed`, `1 skipped`,
  `4 094 subtests passed`; the skip is the known Windows symlink privilege case.
- `parsergen validate`: exit `0`, with the two existing `VAL102` unreachable
  production warnings.
- `parsergen generate --check`: exit `0`, artifacts are current.
- Migration audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  changed artifacts `0`.
- EDT revalidation of `DataProcessor.Парсер`: the same 10 baseline diagnostics
  (object prefix, `НСтр`, seven unused `ТекущийЭлемент` variables and one
  unused helper method); no new parser syntax diagnostics.
- `git diff --check`: exit `0`; only line-ending conversion warnings.

## Remaining

`ПакетЗапросов` and `ЗапросПакета` still use recursive/structural plumbing and
will be handled as a coherent package-list EBNF slice.
