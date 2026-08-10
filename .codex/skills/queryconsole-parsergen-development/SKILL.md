---
name: queryconsole-parsergen-development
description: Use when changing, diagnosing, generating, benchmarking, or reviewing QueryConsoleZUP tools/parsergen, query-language.grammar, parsergen.toml, generated parser artifacts, canonical analysis, or legacy matcher compatibility.
---

# QueryConsole parsergen development

## Core contract

Read the active design/plan under `docs/superpowers/` before changing code.
**REQUIRED SUB-SKILL:** Use `queryconsole-parser-benchmarking` for runtime
parser/lexer measurements, YAxUnit benchmark execution, sidecar validation or
performance comparisons.

Keep canonical nullable/FIRST/FOLLOW/SELECT and legacy runtime matcher semantics
separate. SELECT alternatives must be disjoint; generated branch order never
resolves a conflict. Keep production lookahead at the configured value unless
the grammar contract explicitly changes.

Use TDD for DSL, lowering, IR, codegen, and diagnostics. Migrate production
grammar in coherent vertical slices and update downstream BSL consumers when
the query model changes.

## Local package invariant

In PowerShell, force every parsergen command to load repository sources:

```powershell
$env:PYTHONPATH='tools/parsergen/src'
python -c "import parsergen; print(parsergen.__file__)"
```

The printed path must be inside this repository. Without `PYTHONPATH`, this
machine may load an older `parsergen` from `site-packages` and generate stale
artifacts without an obvious command failure.

## Verification workflow

Run the smallest focused RED/GREEN test first. Before a commit run:

```powershell
$env:PYTHONPATH='tools/parsergen/src'
python -m parsergen validate --config parsergen.toml
python -m parsergen generate --config parsergen.toml --check
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
python -m pytest tools/parsergen/tests -q
git diff --check
```

For intentional generated changes, first run `generate` without `--check`,
review all three target artifacts, then copy those exact artifacts to
`tools/parsergen/tests/fixtures/reference_parser/`. Re-run `generate --check`,
reference tests, audit tests, and the full suite.

For BSL/query-model changes, revalidate every changed EDT object and changed
YAxUnit common module. Query Constructor form behavior remains a manual or
interactive final gate unless the current task explicitly schedules it sooner.

## Review checklist

- Confirm `canonical.conflicts`, canonical diagnostics, and legacy runtime
  conflicts independently.
- Confirm legacy checker still validates actual normalized artifact rows.
- Confirm EBNF repeat/optional and direct LR generate loops, not synthetic
  runtime recursion.
- Search all query-model references; do not add compatibility wrappers without
  a demonstrated external consumer.
- Update structural metrics, golden artifacts, focused tests, downstream tests,
  and the checkpoint document in the same coherent package.
