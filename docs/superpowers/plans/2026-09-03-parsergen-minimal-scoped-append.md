# Minimal Parsergen Scoped Append Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать `^Owner.Collection += anchor/$CurrentField` непосредственно поверх separated semantics без coalesced/FactSeq слоя.

**Architecture:** Отдельный parsed/source scoped wrapper сводится к одному `AppendNearestOwner` value-tap. Python runtime условно включает owner stacks; legacy IR и generated text не меняются.

**Tech Stack:** Python 3.12, dataclasses, pytest, parsergen semantic IR/codegen.

**Spec:** `docs/superpowers/specs/2026-09-03-parsergen-minimal-scoped-append-design.md`

## Global Constraints

- Base: `origin/master` с уже слитым #78.
- Запрещены `FactSeq`, `SemanticResultKind`, coalescer operations и result-shape subsystem.
- Не менять поля существующих `SemanticAlternative`, `SourceConstructor`, `ConstructNode`, `ParserIr`.
- Legacy generated module byte-identical; canonical/hybrid BSL fail closed.
- Каждый production change следует TDD: RED фиксируется до реализации.
- Production additions ≤ 2 000, total additions ≤ 4 000 либо задача останавливается для пересмотра.

---

### Task 1: DSL, source binding и validation

**Files:**
- Modify: `tools/parsergen/src/parsergen/separated_model.py`
- Modify: `tools/parsergen/src/parsergen/semantic_profile_parser.py`
- Modify: `tools/parsergen/src/parsergen/semantic_profile_binding.py`
- Modify: `tools/parsergen/src/parsergen/source_model.py`
- Modify: `tools/parsergen/src/parsergen/binding_validation.py`
- Modify: `tools/parsergen/src/parsergen/source_validation.py`
- Modify: `tools/parsergen/src/parsergen/left_recursion.py`
- Create: `tools/parsergen/src/parsergen/scoped_append_validation.py`
- Test: focused existing parser/binding test modules plus one new scoped profile test module.

**Produces:** Parsed scoped directive, source value-tap wrapper and authoritative schema/definite-write validation.

- [ ] Add parser tests for both forms, exact spans, malformed/trailing input and legacy ambiguity; run and record RED.
- [ ] Implement only the parsed records and exact DSL recognition; run focused GREEN.
- [ ] Add binding/validation tests for one value edge, receiver preservation, textual order, unknown owner/anchor, field conflicts, `$CurrentField`, group/optional/repeat, and LR base/recursive behavior; run RED.
- [ ] Implement minimal source wrapper and isolated validator without public schema API; run focused GREEN.
- [ ] Run all Task 1 related tests, `git diff --check`, check forbidden symbols, then commit.

### Task 2: Minimal IR и optimizer barrier

**Files:**
- Modify: `tools/parsergen/src/parsergen/lowering.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir_optimization.py`
- Test: new focused scoped IR tests and existing optimizer regressions.

**Consumes:** Task 1 `SourceScopedValue` and scoped suffix effects.

**Produces:** `AppendNearestOwner` with either one bound value or one current field; scoped IR is optimizer-stable.

- [ ] Add tests for tap chain, transparent result, punctuation/discard payload, optional/group/repeat and `$CurrentField`; run RED.
- [ ] Lower the wrapper to the single IR operation without changing existing IR record fields; run GREEN.
- [ ] Add optimizer tests proving scoped semantic operations are preserved and legacy optimization still runs; run RED.
- [ ] Implement scoped feature detection and reachability-only optimizer path; run GREEN.
- [ ] Run focused tests, `git diff --check`, size/forbidden-symbol gates, then commit.

### Task 3: Conditional Python runtime и backend fences

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_semantic_codegen.py`
- Modify: `tools/parsergen/src/parsergen/grammar_parser.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Modify: `tools/parsergen/src/parsergen/hybrid_bsl_codegen.py`
- Test: focused generated-Python runtime tests and backend tests.

**Consumes:** Task 2 `AppendNearestOwner`.

**Produces:** Instance-local owner stacks, close-before-delivery lifecycle and early rejection by unsupported backends.

- [ ] Add runtime tests for nearest owner, same-type shadowing, missing-owner no-op, one delivery, `$CurrentField`, caller receiving frozen child, cleanup and parser reuse after three error classes; run RED.
- [ ] Implement conditional serialization/runtime support; run GREEN.
- [ ] Add combined grammar `GP010`, canonical and hybrid fail-closed tests for source and live IR; run RED.
- [ ] Implement early fences before rendering/routing; run GREEN.
- [ ] Prove a legacy generated artifact is byte-identical, run focused tests and commit.

### Task 4: Compatibility, documentation и полная проверка

**Files:**
- Modify: `docs/architecture/parser-generator.md`
- Test: existing compatibility and full parsergen suite.

- [ ] Add compact public syntax/semantics documentation (30–60 lines).
- [ ] Add/retain regressions for dataclass field compatibility and ordinary heterogeneous WRAP/WRAP_PREPEND.
- [ ] Run `python -m pytest tools/parsergen/tests -q`.
- [ ] Run `git diff --check`, forbidden-symbol scan and neutral-name scan.
- [ ] Measure production/test/docs lines and actual patch bytes against `origin/master`; fail the task if budgets are exceeded without redesign.
- [ ] Commit, perform independent whole-branch review, and fix/re-review any Important findings.
