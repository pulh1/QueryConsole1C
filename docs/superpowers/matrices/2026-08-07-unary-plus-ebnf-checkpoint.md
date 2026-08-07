# Production checkpoint: EBNF-цепочка унарных знаков

`УнарнаяОперация` переведена в canonical ownership. Query model и её
properties не изменялись: `Знаки` остаётся упорядоченным массивом лексем,
`Выражение` — единственным operand.

## Result

- Source helper-production `УнарнаяОперацияПродолжение` и отдельная
  production `ЗнакУнарнойОперации` удалены.
- Grammar использует declarative binding
  `Знаки += ('-' | '+')+ Выражение = <Операнд>`.
- Parser IR поддерживает literal/token как значение явно bound group branch,
  не меняя прежний приоритет semantic child над separator.
- Generated BSL сначала разбирает обязательный знак, затем выполняет один
  loop для остальных знаков; runtime recursion и legacy dispatch отсутствуют.
- Production `lookahead` остался `k=2`; canonical SELECT conflicts: `0`.
- Full legacy matcher artifact остался `9 078` rows и используется только
  compatibility-аудитом.
- Characterization `+-1` перенесён из opt-in future grammar suite в основной
  expression regression: проверяются порядок знаков и operand.

## Structural delta

| Metric | Before unary slice | After unary slice |
| --- | ---: | ---: |
| Source productions | 118 | 116 |
| Source alternatives | 273 | 269 |
| Lowered CFG productions / alternatives / epsilon | 124 / 281 / 63 | 124 / 282 / 63 |
| Semantic action blocks / statements | 354 / 380 | 347 / 373 |
| Constructor statements | 93 | 92 |
| Collection statements | 33 | 31 |
| Constant statements | 26 | 26 |
| Structural statements | 223 | 219 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions | 130 | 128 |
| Generated BSL LOC | 3 275 | 3 246 |
| Production select rows | 7 312 | 7 223 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Identifier rows | 276 | 276 |

Рост lowered alternatives на одну строку является внутренним результатом
canonical lowering двух literal alternatives внутри `+`; source grammar и
generated runtime при этом стали меньше, а повторение генерируется как loop.

## Verification

- Focused Parser IR/codegen/repository/audit/reference tests:
  `62 passed, 57 subtests passed`.
- Full Python: `411 passed, 1 skipped, 4090 subtests passed`.
- `parsergen validate`: exit `0`, две известных `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Canonical/runtime conflicts: `0` / `0`.
- EDT revalidation: production Parser `10`, два затронутых YAxUnit-модуля
  суммарно `35`; новых syntax diagnostics нет.
- Interactive YAxUnit/Vanessa run оставлен на финальный integration gate.

## Remaining

Остальные list/optional helper families, specialized logical operators и
query-model normalization остаются следующими coherent vertical slices.
