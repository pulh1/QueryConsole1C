# Production checkpoint: direct LR арифметики

Первый production vertical slice переводит
`АрифметическоеВыражение` и `Слагаемое` на canonical Parser IR. Query
model и её properties на этом шаге не изменялись.

## Grammar и semantics

- Удалены source helper-productions
  `АрифметическаяОперация` и `ОперацияУмножения`.
- `+`, `-`, `*`, `/` и `%` описаны естественной direct left recursion.
- Constructor и `ЛеваяЧасть`/`Операция`/`ПраваяЧасть`
  задаются declarative binding, без `ЛевыйЭлемент` и structural
  actions в migrated families.
- Generated parser выполняет left fold. `1 - 2 - 3` даёт
  `((1 - 2) - 3)`, `8 / 4 / 2` даёт `((8 / 4) / 2)`.
- Precedence сохранена разделением
  `АрифметическоеВыражение -> Слагаемое -> Множитель`.

Lowered CFG по-прежнему имеет synthetic tail productions только для
canonical analysis. Codegen не создаёт для них runtime functions.

## Canonical/legacy boundary

- Production config явно передаёт две migrated productions hybrid
  generator.
- CLI, migration audit и reference generation используют один
  `generate_from_compilation` entrypoint, поэтому не могут
  незаметно разойтись в выборе backend.
- Canonical SELECT по-прежнему disjoint при `k=2`; conflicts: `0`.
- Full legacy matcher artifact сохранил `9 078` normalized rows и
  нуль runtime conflicts.
- Production hybrid select table содержит `8 464` rows: migrated
  productions и их synthetic analysis tails из legacy matcher исключены.
- Canonical arithmetic functions не вызывают
  `НомерВариантаПродукции` и не зависят от порядка `Если` для
  разрешения conflicts.

## Structural before/after

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions | 124 | 122 |
| Source alternatives | 281 | 279 |
| Lowered CFG productions | 124 | 124 |
| Lowered CFG alternatives | 281 | 281 |
| Lowered epsilon alternatives | 63 | 63 |
| Semantic action blocks | 398 | 374 |
| Semantic action statements | 431 | 402 |
| Constructor statements | 102 | 97 |
| Constant statements | 33 | 28 |
| Structural statements | 254 | 235 |
| Collection statements | 37 | 37 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions | 135 | 134 |
| Generated BSL LOC | 3 394 | 3 351 |
| Production select rows | 9 078 | 8 464 |
| Full legacy matcher rows | 9 078 | 9 078 |
| Identifier rows | 276 | 276 |

Generated function count уменьшился на одну, потому что две
continuation-functions удалены, а hybrid runtime добавил одну neutral
lookahead function. Generated arithmetic code содержит по одному `Пока`
на precedence level и не содержит self-calls.

## Verification evidence

- Full Python: `406 passed, 1 skipped, 4086 subtests passed`.
- Current-source `parsergen validate`: exit `0`, только две известных
  `VAL102` warnings.
- Current-source `parsergen generate --check`: exit `0`, artifacts current.
- EDT revalidation: production `DataProcessor.Парсер` нашёл те же
  `10` background issues; `CommonModule.КОНС_Обр_Парсер_МО` — те же
  `31` background issues. Новой syntax diagnostic delta нет.
- Added repository tests проверяют Parser IR `LeftFold`, один loop,
  отсутствие self-recursion, legacy dispatch calls и helper-functions.
- YAxUnit acceptance проверяет левую ассоциативность
  вычитания и деления, а также приоритет умножения. Его
  interactive platform run намеренно оставлен на финальный Vanessa/YAxUnit
  gate.

## Remaining slice limitations

- Runtime before/after benchmark не переснят; он входит в финальный
  performance gate.
- Остальные expression/list/optional families остаются в legacy island.
- Общий счётчик structural actions ещё не нулевой; в двух migrated
  arithmetic families он равен нулю.
