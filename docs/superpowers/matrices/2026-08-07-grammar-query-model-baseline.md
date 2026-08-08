# Baseline миграции grammar/query model

## Reproduction

`python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml`

Команда печатает canonical JSON schema version 1 и только сравнивает три
production artifacts с результатом генерации. Exact regression выполняет её
также над заведомо изменённым временным target и подтверждает неизменность
bytes и mtime всех трёх файлов.

## Structural

- productions: 124
- alternatives: 281
- epsilon alternatives: 63
- action blocks/statements: 398/431
- constructor/collection/constant/structural/other-assignment/other statements:
  102/37/33/254/0/5
- formal parameters/actual arguments: 8/26

## Canonical analysis

Секция `canonical.stats` команды audit воспроизводит все exact поля:

- `packed_first_rows`: 10 758
- `packed_follow_rows`: 42 545
- `select_descriptors`: 281
- `select_direct_facts`: 10 438
- `select_short_complete_prefixes`: 320
- `packed_select_upper_bound`: 32 050
- `conflict_work_items`: 531
- `public_select_expansions`: 0
- `select_cartesian_materializations`: 0

Последние два нулевых счётчика подтверждают, что публикация этих метрик не
материализует public SELECT или Cartesian SELECT. `canonical.diagnostics`
содержит ровно две `VAL102` severity `warning` и две `LLK202` severity `error`.
`canonical.conflicts` содержит ровно:

- `LLK202` `ЛогическийОператор` 2/5: `ССЫЛКА АВТОУПОРЯДОЧИВАНИЕ`
- `LLK202` `ОперандВ` 1/2: `ВЫБРАТЬ *`

## Legacy compatibility

- `legacy.matcher_rows`: 11 273
- `legacy.matcher_definitions`: 0
- `legacy.runtime_conflicts`: 0
- `artifacts.changed`: 0

## Generated parser

- `generated.bsl_functions`: 135
- `generated.bsl_loc`: 3394
- `generated.constructor_names`: 79
- `generated.select_rows`: 11 273
- `generated.identifier_rows`: 227

## Runtime parser baseline gap

No runtime median/p95, call-count or recursion-depth harness exists yet.
Phase 2.5 must implement and run it before the first production grammar/model
change. Python analysis timings are not a substitute for BSL runtime timings.

## Foundation Phase 0–2 status

- impact matrix:
  [query-model consumer impact](2026-08-07-query-model-consumer-impact.md)
- coverage matrix:
  [grammar/query-model coverage](2026-08-07-grammar-query-model-coverage.md)
- approved architecture:
  [grammar/query-model optimization design](../specs/2026-08-07-grammar-query-model-optimization-design.md)
- pre-change Python baseline: 226 passed, 1 skipped, 4011 subtests passed
- current Python suite after final audit tests: 234 passed, 1 skipped,
  4011 subtests passed; 235 collected
- current YAxUnit status: static inventory only; fresh incremental run belongs
  to Phase 2.5
- production grammar/model/artifacts changed: no
