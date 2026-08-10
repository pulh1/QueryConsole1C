---
name: queryconsole-parser-benchmarking
description: Use when running, repeating, comparing, validating, or publishing QueryConsoleZUP parser or lexer runtime benchmarks, including old/current implementations, YAxUnit sidecars, corpus timings, median/p95, batch calibration, and performance verdicts
---

# QueryConsole parser benchmarking

## Core contract

Treat the current repository, EDT runtime and emitted sidecar as sources of
truth. Measure only requested implementations, prove artifact provenance
before timing, and state conclusions no more strongly than run order permits.

**REQUIRED SUB-SKILL:** Use `queryconsole-parsergen-development` when benchmark
preparation changes parsergen, grammar or generated artifacts.

## Discover current state

Read rather than remember:

- the active benchmark plan under `docs/superpowers/plans/`;
- registered tests, descriptors, methodology and sidecar names in
  `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`;
- provenance and validation commands in `tools/parsergen/benchmarks/`;
- launch configuration and database state through EDT-MCP;
- corpus manifest, runtime version, batches and samples from emitted JSON.

Never copy historical commit IDs, hashes, dates, corpus counts, warmup/sample
counts or batch targets into a new measurement without rediscovery.

## Execute a measurement

1. Define the exact matrix: old/current, parser/lexer, timing/counters. Name
   excluded registrations explicitly.
2. Check branch and worktree. Compute current artifact hashes with repository
   utilities. Compare descriptor commit/hash/roles with the measured runtime.
   Fix stale provenance and refresh the test infobase before timing; never
   publish correct timings under a false identity.
3. Discover the EDT runtime-client configuration. Call EDT-MCP
   `run_yaxunit_tests` with `tests=[Module.Method]` for each requested test.
   Do not use a module/tag filter for one registration.
   If the user requested confirmation immediately before timing, stop at this
   boundary; otherwise proceed.
4. Keep production timing uninstrumented. Run counters, profiling or debug
   passes separately from warmups and timed samples.
5. Copy the sidecar to a new durable path without rewriting bytes. Preserve
   previous evidence and verify source/destination SHA-256.
6. Validate schema, artifact rows, corpus order, input identity and length,
   warmups, sample count, operations per sample, batch size and positive
   samples. Use the current validator when one exists.
7. Report median, p95, batch size and CV. For aggregate corpora, distinguish
   corpus-iteration timing from per-operation timing.

## Compare evidence

| Evidence | Allowed conclusion |
|---|---|
| One implementation, one run | Absolute timing and within-run variability |
| Sequential old/current runs | Directional comparison with order caveat |
| Counterbalanced repeated runs | Final performance verdict when corpus, runtime and methodology align |

Reject a comparison when corpus IDs/order, inputs, entrypoints, runtime,
methodology or measurement scope differ. Re-run rather than silently normalize
incompatible evidence.

## Required handoff

Lead with the result, then list:

- tests and implementations actually executed, plus explicit exclusions;
- artifact commit/SHA and runtime/platform;
- methodology, median/p95/batch/CV and corpus alignment;
- durable JSON/report paths and sidecar SHA;
- validation results, order effects, unavailable counters and remaining errors.

## Red flags

- Running all four harness registrations for a single-parser request.
- Timing an updated parser with a stale descriptor.
- Overwriting an earlier baseline or editing raw samples.
- Comparing medians without checking batch/operation semantics.
- Calling a sequential series a final verdict.
- Mixing profiler/instrumentation overhead into production timing.
