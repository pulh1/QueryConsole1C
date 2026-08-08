# Full-canonical ABI checkpoint

## Result

Production grammar is now owned by the canonical backend in full. Generated
nonterminal functions no longer expose the legacy implicit parameters
`Родитель` and `ЛевыйЭлемент`, and both public parser entrypoints invoke
their roots without two placeholder `Неопределено` arguments.

The assembly boundary detects full canonical ownership by comparing the
canonical Parser IR ownership with all source productions. In that mode it
generates canonical functions with an empty ABI and disables legacy implicit
arguments in entrypoint result functions.

Partial hybrid generation retains the old two-slot ABI. This is covered as a
separate compatibility contract for canonical-to-legacy calls and is not used
by the production grammar.

## Structural delta

| Generated parser metric | Before | After |
| --- | ---: | ---: |
| Nonterminal functions | 67 | 67 |
| Generated functions | 79 | 79 |
| Generated BSL LOC | 2194 | 2194 |
| `Родитель` occurrences | 67 | 0 |
| `ЛевыйЭлемент` occurrences | 67 | 0 |
| Generated SELECT rows | 0 | 0 |

Source grammar remains parameterless and action-free. Canonical LL(2)
analysis remains the production decision contract; source lookahead stays at
`k=2`.

## Compatibility boundary

- `build_legacy_matcher_artifact` and its normalized-row parity tests remain
  available for the migration compatibility layer.
- Partial hybrid fixtures continue to receive `Родитель`/`ЛевыйЭлемент`
  ABI slots where a canonical function calls a legacy island.
- Production canonical functions, calls and entrypoints do not depend on that
  ABI.
- The generated module still contains the legacy runtime shell helper while
  its production SELECT table is empty. Removing that unused shell is a
  separate cleanup package after equivalence and runtime gates.

## Automated evidence

- focused hybrid/codegen tests distinguish full-canonical and partial-hybrid
  ABI behavior;
- repository code-shape tests require absence of both legacy parameters in
  migrated expression functions;
- the production parser and Python reference artifact were regenerated from
  the same canonical compilation;
- full parsergen suite: `497 passed, 1 skipped, 4558 subtests passed`; the
  skip is the known Windows symlink-privilege case;
- `validate`, `generate --check` and migration audit are green; audit reports
  `artifacts.changed = []`;
- exact EDT revalidation of `DataProcessor.Парсер` reports no errors;
- interactive YAxUnit execution remains the final integration gate.
