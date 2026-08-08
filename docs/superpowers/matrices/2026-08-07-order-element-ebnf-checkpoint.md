# Production checkpoint: order element and direction

`ЭлементУпорядочивания` переведён на constructor, scalar binding и две
EBNF optional-ветки:

```text
@НовыйЭлементПорядка
Выражение = <ВыражениеМоделиЗапроса>
(ИЕРАРХИЯ Иерархия := Истина)?
(Направление = <НаправлениеУпорядочивания>)?
```

`НаправлениеУпорядочивания` стал не-nullable constructor choice:

```text
@НовыйНаправлениеВозрастание ВОЗР
| @НовыйНаправлениеУбывание УБЫВ
```

## Semantic boundary

Nullable canonical child не используется как замена legacy sentinel
`"ПУСТО"`. Optional binding находится внутри EBNF-ветки, поэтому
при отсутствии `ВОЗР` / `УБЫВ` generated parser не присваивает
`Направление = Неопределено` и сохраняет factory-default `"Возр"`.
`ИерархияОпционально` удалён.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 111 / 259 | 110 / 256 |
| Lowered CFG productions / alternatives / epsilon | 125 / 283 / 64 | 126 / 284 / 64 |
| Semantic action blocks / statements | 300 / 325 | 293 / 318 |
| Constructor statements | 73 | 70 |
| Collection / constant statements | 27 / 22 | 27 / 20 |
| Structural / other statements | 199 / 4 | 197 / 4 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 123 / 3 105 | 122 / 3 088 |
| Production SELECT rows | 6 472 | 6 223 |
| Full legacy matcher rows | 9 079 | 9 081 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

Two internal optional CFG productions exist only for canonical analysis and are
omitted from runtime functions. Full legacy audit counts the complete lowered
compatibility artifact; hybrid runtime matcher ownership still excludes
canonical productions and their synthetic CFG.

## Coverage

- Focused Python tests verify both constructors, optional hierarchy binding,
  absence of the removed helper and preservation of the direction default.
- Existing full-parser cases `C06`-`C10` cover absent direction, explicit
  ascending/descending direction, hierarchy and multiple order elements.
- Interactive YAxUnit/Vanessa execution remains the final integration gate by
  agreement.

## Verification

- Focused repository/config/audit/codec/reference: `57 passed`,
  `67 subtests passed`.
- Full `tools/parsergen/tests`: `425 passed`, `1 skipped`,
  `4 100 subtests passed`; the skip is the known Windows symlink privilege case.
- `parsergen validate`: exit `0`, with the two existing `VAL102` unreachable
  production warnings.
- `parsergen generate --check`: exit `0`, artifacts are current.
- Canonical SELECT conflicts: `0`; legacy runtime conflicts: `0` at `k=2`.
- Migration audit reports changed artifacts `0`.
- EDT revalidation of `DataProcessor.Парсер`: diagnostics improved from 8 to
  7 because one unused `ТекущийЭлемент` disappeared. Remaining baseline is the
  object prefix, `НСтр`, four unused `ТекущийЭлемент` variables and the unused
  `НеТерминалКакОпционально` method; no new syntax diagnostics.
- Post-gate process checks found no Python process with working set above 1 GB.

## Remaining

The surrounding order list still uses `СписокЭлементовУпорядочивания` and
recursive `ПродолжениеСпискаЭлементовУпорядочивания`; they require the next coherent
collection-loop slice.
