# Baseline миграции grammar/query model

## Reproduction

`python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml`

## Structural

- productions: 124
- alternatives: 281
- epsilon alternatives: 63
- action blocks/statements: 398/431
- constructor/collection/constant/structural/other-assignment/other statements:
  102/37/33/254/0/5
- formal parameters/actual arguments: 8/26

## Canonical analysis

- packed FIRST rows: 10 758
- packed FOLLOW rows: 42 545
- direct SELECT facts: 10 438
- short complete SELECT prefixes: 320
- packed SELECT upper bound with FOLLOW projections: 32 050
- public SELECT expansions: 0
- SELECT Cartesian materializations: 0
- LLK202 `ЛогическийОператор` 2/5: `ССЫЛКА АВТОУПОРЯДОЧИВАНИЕ`
- LLK202 `ОперандВ` 1/2: `ВЫБРАТЬ *`

## Legacy compatibility

- normalized matcher rows: 11 273
- runtime conflicts: 0
- artifact comparison changes: 0

## Generated parser

- BSL functions: 135
- BSL LOC: 3394
- constructor names: 79
- SELECT ValueTable rows: 11 273
- identifier ValueTable rows: 227

## Runtime parser baseline gap

No runtime median/p95, call-count or recursion-depth harness exists yet.
Phase 2.5 must implement and run it before the first production grammar/model
change. Python analysis timings are not a substitute for BSL runtime timings.
