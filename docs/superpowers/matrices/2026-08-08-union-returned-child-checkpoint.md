# UNION returned-child checkpoint

## Result

The returned-child decorator now supports both optional and required children:

```text
<Seed> Property => <Child>
<Seed> Property => <Child>?
```

It parses exactly one semantic seed, parses the child, assigns the seed to the
child property and returns the child. Repetition is rejected by binding
validation. The operation is represented explicitly by `WrapValue` in Parser
IR and rendered by canonical BSL codegen; it does not use semantic actions or
legacy dispatch.

`ОператорОбъединения` now uses this declaration:

```text
ОБЪЕДИНИТЬ
<ТипОбъединенияЗапроса>
ТипОбъединения => <ОбъединяемыйЗапрос>
```

Generated runtime parses the type and operator once, assigns
`Значение2.ТипОбъединения = Значение1` and returns `Значение2`.

## Coverage

- binding validation accepts required and optional decorators and rejects a
  missing seed;
- Parser IR records required wrapping as one semantic `WrapValue` operation;
- canonical BSL codegen verifies one seed call, one child call, assignment and
  returned child;
- repository code-shape coverage verifies canonical UNION generation without
  `ТекущийЭлемент` or `НомерВариантаПродукции`;
- existing YAxUnit cases C04, C05, C13, C16 and corpus projection cover plain
  UNION, UNION ALL and mixed chains. Interactive execution remains the final
  integration gate.

## Structural delta

| Metric | Before | After |
| --- | ---: | ---: |
| Action blocks / statements | 3 / 4 | 1 / 1 |
| Structural action statements | 3 | 0 |
| Generated BSL LOC | 2155 | 2147 |
| Generated SELECT rows | 46 | 44 |

The one remaining action is the documented SKD collection merge. Canonical
LL(2) conflicts, canonical diagnostics and legacy runtime conflicts remain
empty. The legacy matcher still contains 10,482 normalized rows and is not a
dependency of the required returned-child codegen path.
