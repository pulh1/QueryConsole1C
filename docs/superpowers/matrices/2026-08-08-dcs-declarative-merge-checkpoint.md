# SKD declarative collection-merge checkpoint

## Result

The last structural semantic action and all remaining source production
parameters were removed as one coherent SKD/query-field package.

The minimal binding DSL now contains collection extension:

```text
ОтборыСКД *= <РасширениеСКД>
```

It parses one child collection and appends its elements to the named property
of the active constructor. A validated member/index path such as
`Операторы[0].ОтборыСКД` preserves the existing ORDER/TOTALS attachment to the
first UNION operator. An absent or non-observable extension returns
`Неопределено`; generated BSL checks that value before entering the merge
loop. The binding cannot target an external parameter or arbitrary BSL.

`РасширениеСКД` now returns a collection only for `{ГДЕ ...}`. Blocks
`{ВЫБРАТЬ ...}`, `{УПОРЯДОЧИТЬ ПО ...}` and `{ИТОГИ ПО ...}` remain accepted
and syntax-checked but return `Неопределено`, matching their previously
unobservable raw-model contract without allocating a temporary list.

`ПоляВыборки` was made parameterless and retained only for nested-table field
lists. Main SELECT fields are bound directly to
`Оператор.ВыбираемыеПоля`; their adjacent SKD filters are merged directly to
`Оператор.ОтборыСКД`. `СписокПолейСКД` and `ОтборСКД` were removed.

The public query model remains unchanged: `Оператор.ОтборыСКД` is the same
flat, ordered collection consumed by semantic analysis, query generation,
the query builder and Query Constructor. No compatibility property or block
container was introduced.

## Coverage

- DSL parser, validation, Parser IR and canonical BSL codegen cover `*=`;
- discard binding without a constructor is covered independently;
- code-shape tests verify eight guarded merge sites in the SELECT operator,
  iterative field lists, and absence of removed SKD functions/actions;
- existing headless YAxUnit case K07 characterizes accumulation from two
  `{ГДЕ ...}` blocks in source order; K04/K05 cover one and multiple fields;
- interactive YAxUnit execution remains the final integration gate.

## Structural delta

| Metric | Before | After |
| --- | ---: | ---: |
| Source productions / alternatives | 69 / 158 | 67 / 156 |
| Lowered productions / alternatives / epsilon | 150 / 320 / 75 | 150 / 322 / 77 |
| Action blocks / statements | 1 / 1 | 0 / 0 |
| Formal parameters / actual arguments | 5 / 16 | 0 / 0 |
| Generated BSL functions / LOC | 81 / 2147 | 79 / 2194 |
| Generated SELECT rows | 44 | 0 |
| Legacy matcher rows | 10482 | 10283 |

Canonical LL(2) conflicts, canonical diagnostics and legacy runtime conflicts
remain empty. Production generation no longer materializes any legacy SELECT
dispatch rows; the legacy matcher audit remains separate compatibility
evidence and is not consumed by canonical codegen.
