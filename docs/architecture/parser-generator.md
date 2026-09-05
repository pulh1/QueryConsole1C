# Архитектура parsergen

## Граница пакета

`tools/parsergen` преобразует combined `.grammar` в два production targets:
канонический BSL-парсер QueryConsole и прямой семантический Python-парсер.
Пакет не знает о Worker, hot reload, runtime 1C или projection-потребителях.
Несколько entrypoints являются несколькими корнями одной grammar, а не
вариантами её семантики.

Единственный authoring format — combined grammar. В нём синтаксис и
декларативная семантика находятся в одном файле: constructors, scalar и
collection bindings, wraps, folds, repeats и constants. Произвольные inline
source actions запрещены ранней диагностикой `arbitrary source actions require
declarative bindings`; renderer не пытается их интерпретировать.

## Общий pipeline

```text
combined .grammar
  -> SourceGrammar
  -> lowering и resolved grammar
  -> FIRST/FOLLOW/SELECT, validation и canonical decision DAG
  -> ParserIr
  -> semantic optimization
  -> immutable RecursionPlan
  -> canonical BSL renderer | direct Python renderer
```

`ParserIr` — общее семантическое представление обоих targets. Lowering
создаёт synthetic CFG только для анализа; synthetic productions не становятся
runtime functions. Optimizer работает над общим IR до создания
`RecursionPlan` и сохраняет только доказанные semantic-transparent
преобразования.

`RecursionPlan` строится один раз над финальным optimized `ParserIr`.
Он содержит immutable ссылки на точные IR sites, proven input progress,
result-flow/liveness и при необходимости continuation layout. Eligibility
direct recursion не вычисляется в renderer: BSL и Python только потребляют
sites из общего плана и выражают их средствами целевого языка.

## Renderers

В package ровно два production renderer.

- Canonical BSL renderer строит structured BSL из validated decision DAG и
  semantic `ParserIr`; он обслуживает полный достижимый graph от configured
  entrypoints.
- Direct Python renderer создаёт standalone Python module с AST dataclasses,
  обычными production methods, `if`/`while` и локальными continuation stacks
  только для sites из `RecursionPlan`. Generated module не содержит parsergen
  dependency или универсальную parser VM.

Оба renderer используют одни и те же combined semantics, IR, optimized graph
и recursion eligibility. Legacy/hybrid BSL paths, semantic profiles,
owner/scoped effects, `AppendNearestOwner`, projection semantics и selector
`canonical_productions` отсутствуют.

## Канонический BSL target

BSL renderer получает полный `ParserIr` и не использует migration routing.
Его decisions основываются на pairwise-disjoint canonical SELECT languages;
порядок generated conditions не разрешает конфликт. EBNF repeats и direct
left folds остаются structured control flow, а runtime parser не получает
synthetic EBNF productions.

Production artifacts остаются тремя разрешёнными файлами QueryConsole:
`ObjectModule.bsl`, first-symbol template и identifier template. `generate
--check` — read-only freshness gate; отдельный fresh-byte fence фиксирует
точные raw bytes. Изменение production artifacts должно быть самостоятельным
осознанным действием.

Recursive BSL code generation покрыта unit- и byte-fences, но live compilation
в 1C пока не заявляется: финальная проверка в 1C остаётся отдельным pending
gate.

## Проверка

Из корня repository с worktree-local import path:

```powershell
$env:PYTHONPATH = "tools/parsergen/src"
python -B -m pytest -p no:cacheprovider tools/parsergen/tests
python -B -m parsergen validate --config parsergen.toml
python -B -m parsergen generate --config parsergen.toml --check
```

`generate` без `--check` заменяет production artifacts и выполняется только в
задаче, явно разрешающей регенерацию.

Подробное согласованное решение и исторические baselines:
[`2026-09-05-parsergen-minimal-multi-target-design.md`](../superpowers/specs/2026-09-05-parsergen-minimal-multi-target-design.md).
