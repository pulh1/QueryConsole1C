# Full-canonical runtime checkpoint

## Result

Production generation now selects the standalone canonical BSL module when
canonical Parser IR owns every source production. It no longer assembles the
production parser through `BslGenerator` and therefore does not build or load
the legacy matcher artifact at runtime.

The partial-hybrid path remains explicit and unchanged: it still assembles
canonical functions with legacy islands, preserves the two-slot legacy ABI,
and generates matcher rows only for those islands.

`GeneratedParser` was moved to a neutral module so CLI and artifact rendering
do not obtain their shared result type from the legacy backend. The canonical
production result carries an empty SELECT value table with the existing
artifact schema. This preserves the current EDT metadata layout while the BSL
module no longer reads that template.

## Removed from production BSL runtime

- `ТаблицаПервыхСимволовВариантов` variable and maket load;
- matcher-table index construction;
- `НомерВариантаПродукции`;
- `ПоследняяПродукция`;
- legacy `ВызватьИсключениеНеУдалосьВыпполнитьРазбор` dispatcher;
- the duplicate canonical-error helper name required only to coexist with the
  legacy template.

Canonical production bodies are unchanged apart from using the standalone
canonical error-helper name. Their source remains the same Parser IR and
canonical decision renderer.

The standalone helper preserves the established syntax-error contract:
concrete terminal/identifier/constant mismatches report the expected token,
dispatch failures report an unexpected token type, and available lexer
coordinates are formatted as `{(line, column)}`. This is protected by a
focused generated-code test because expression/full-parser YAxUnit suites
assert both coordinates and token types.

## Structural delta

| Generated parser metric | Before | After |
| --- | ---: | ---: |
| BSL functions | 79 | 78 |
| BSL procedures | 6 | 5 |
| Generated BSL LOC | 2194 | 2105 |
| Nonterminal functions | 67 | 67 |
| Runtime legacy dispatch references | present | 0 |
| Generated SELECT rows | 0 | 0 |
| Identifier rows | 276 | 276 |

Production lookahead remains `k=2`. Canonical conflicts and diagnostics are
empty. The independent legacy audit still reports 10283 normalized matcher
rows and no runtime conflicts; those rows are compatibility evidence and are
not consumed by production generation.

## Gates

- focused canonical, hybrid, artifact and repository code-shape tests;
- full parsergen suite: `498 passed, 1 skipped, 4558 subtests passed`; the
  skip is the known Windows symlink-privilege case;
- production/reference artifact parity;
- `parsergen validate`;
- `parsergen generate --check`;
- migration audit with `artifacts.changed = []`;
- exact EDT revalidation of `DataProcessor.Парсер` with no errors.

Interactive YAxUnit and runtime performance comparison remain final
integration gates.
