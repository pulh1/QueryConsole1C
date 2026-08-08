# SKD field-list migration checkpoint

> Superseded: the remaining compatibility island and context parameters were
> removed by `2026-08-08-dcs-declarative-merge-checkpoint.md`.

## Scope

The SKD grammar family was migrated as one coherent package instead of
refactoring one continuation alternative at a time.

- `СписокПолейОпционально` and `ТелоБлокаСКД` were removed.
- `ТипБлокаСКД` was inlined because it had no observable
  semantic result.
- `СписокПолейСКД` is a canonical root collection with an EBNF
  separator repeat and generates an iterative BSL loop.
- The source grammar no longer uses `Родитель`.

The public model contract remains `Оператор.ОтборыСКД`, a flat ordered
collection of select-field nodes. Existing semantic analysis, builder, query
generation and Query Constructor consumers therefore require no compatibility
property.

## Remaining legacy island

`ОтборСКД(ОтборыСКД)` remains a legacy compatibility production. Its
single action appends the already parsed canonical list to the contextual
operator collection. This cross-context mutation cannot currently be expressed
by the minimal binding DSL without either:

- adding an external-target/attribute-grammar mechanism; or
- changing the public SKD model to retain block containers.

Neither expansion is justified for this slice. The island contains no manual
list recursion and is the only remaining SKD action. Removal condition: a
separately designed declarative collection-merge/context binding or an approved
SKD block model migration.

## Characterization coverage

The full-parser YAxUnit contract now includes `K07`, which places two `{ ГДЕ
... }` blocks at different grammar boundaries and asserts that all three fields
are accumulated in source order. This catches an implementation that replaces
the collection with the last parsed block.

Interactive YAxUnit execution remains deferred to the final integration stage.
Python code-shape coverage verifies that the generated SKD list contains one
`Пока` loop, two collection appends (first and repeated item), and no recursive
self-call.

## Structural delta

| Metric | Before | After |
| --- | ---: | ---: |
| Source productions | 70 | 69 |
| Source alternatives | 162 | 158 |
| Lowered productions | 149 | 150 |
| Lowered alternatives | 319 | 320 |
| Action blocks | 7 | 3 |
| Action statements | 8 | 4 |
| Constructor action statements | 1 | 0 |
| Collection action statements | 2 | 1 |
| Structural action statements | 5 | 3 |
| Actual nonterminal arguments | 17 | 16 |
| Generated BSL functions | 82 | 81 |
| Generated BSL LOC | 2171 | 2155 |
| Generated SELECT rows | 137 | 46 |
| Legacy matcher rows | 10283 | 10482 |

The legacy matcher row count is reported independently and is not used as a
canonical quality metric. Canonical LL(2) conflicts and legacy runtime
conflicts are both empty after the slice.
