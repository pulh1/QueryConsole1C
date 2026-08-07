# Parsergen Direct Left Recursion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Поддержать direct productive left recursion в source grammar и генерировать iterative BSL left fold без synthetic runtime recursion и legacy dispatch.

**Architecture:** Единый source classifier выделяет leading self-reference и публикует immutable descriptor. Lowering преобразует direct LR в canonical base/tail CFG только для FIRST/FOLLOW/SELECT, Parser IR восстанавливает high-level `LeftFold`, а canonical BSL backend рендерит base dispatch и iterative recursive-suffix loop.

**Tech Stack:** Python 3.12, immutable dataclasses, существующие parsergen Source AST/CFG/analysis/Parser IR, pytest/unittest, generated BSL.

## Global Constraints

- Поддерживается только `A ::= A α1 | ... | β1 | ...`; indirect и nullable-prefix left recursion остаются `VAL202` unsupported.
- Каждый recursive suffix productive и имеет `min_consumed_tokens >= 1`.
- Recursive call arguments обязаны точно совпадать с formal parameters.
- Любой decision использует pairwise-disjoint canonical SELECT для configured произвольного конечного `k`; порядок `Если` никогда не разрешает conflict.
- Existing nullable/FIRST/FOLLOW/SELECT algorithms и legacy matcher normalization не переписываются.
- Runtime не создаёт synthetic tail function и не вызывает left-recursive production из собственного body.
- Semantic recursive alternative использует constructor + scalar binding leading self-reference; arbitrary BSL actions не поддерживаются.
- Production grammar/query model/generated EDT artifacts не меняются в Phase 6.
- Каждый task выполняется RED → GREEN → regression → отдельный commit/push.

---

### Task 1: Единая классификация и source validation direct LR

**Files:**
- Create: `tools/parsergen/src/parsergen/left_recursion.py`
- Modify: `tools/parsergen/src/parsergen/source_validation.py`
- Create: `tools/parsergen/tests/test_left_recursion_validation.py`

**Interfaces:**
- Produce `DirectSelfReference(item_index: int, call: NonterminalCall, property: str | None, binding_mode: BindingMode | None, source_span: SourceSpan)`.
- Produce `DirectRecursiveAlternative(alternative: int, self_reference: DirectSelfReference, source_span: SourceSpan)`.
- Produce `DirectLeftRecursion(production: str, base_alternatives: tuple[int, ...], recursive_alternatives: tuple[DirectRecursiveAlternative, ...], source_span: SourceSpan)`.
- Produce `classify_direct_left_recursion(grammar: SourceGrammar) -> Mapping[str, DirectLeftRecursion]`.
- Extend `SourceValidationReport.left_recursions` with the exact immutable mapping used by lowering.

- [x] Add literal RED cases for `<Expr> ::= <Expr> '+' <Term> | <Term>`, constructor-before-`Left=<Expr>`, multiple recursive alternatives and parameter-preserving `<A>(P) ::= <A>(P) x | y`.
- [x] Run `python -m pytest tools/parsergen/tests/test_left_recursion_validation.py -q`; require failures because classifier/report do not exist.
- [x] Implement a single classifier that ignores only zero-width directives when locating the first grammar value and unwraps only a direct scalar/append binding whose RHS is `NonterminalCall`.
- [x] Add RED diagnostics for no base (`LR200`), empty/nullable/nonproductive suffix (`LR201`), changed recursive arguments (`LR202`), missing/inconsistent semantic accumulator binding (`LR203`) and arbitrary action (`LR204`). Assert source spans and absence of synthetic names.
- [x] Compute suffix facts with existing source-fact functions after removing exactly the classified self item; do not modify FIRST/FOLLOW/SELECT.
- [x] Preserve recognition-only direct LR, but require every semantic recursive alternative to have one top-level constructor and scalar leading-self binding; require every semantic base to return constructor or one transparent value.
- [x] Run source grammar, source validation and binding validation suites GREEN.
- [x] Commit and push as `Проверять direct productive left recursion`.

### Task 2: Canonical CFG lowering и origin sidecar

**Files:**
- Modify: `tools/parsergen/src/parsergen/lowering.py`
- Create: `tools/parsergen/tests/test_left_recursion_lowering.py`
- Create: `tools/parsergen/tests/test_left_recursion_analysis.py`

**Interfaces:**
- Produce `LoweredLeftRecursion(production: str, tail_production: str, base_alternatives: tuple[int, ...], recursive_alternatives: tuple[int, ...], source_span: SourceSpan)`.
- Extend `LoweringResult.left_recursions: tuple[LoweredLeftRecursion, ...]`.
- Lower public `A` to base rows `β TailA`; lower synthetic tail to `α TailA | epsilon`.

- [x] Write RED lowering test that asserts exact public/tail symbols, stable base/recursive source order, one epsilon tail row, parameter forwarding and no leading self-call in suffix.
- [x] Run the focused lowering test and verify failure because direct LR is still emitted unchanged.
- [x] Implement `_lower_left_recursive_production`; lower every original sequence once so binding origins remain complete, remove exactly its classified leading self-call from recursive syntax, then add the tail call.
- [x] Record public base and synthetic recursive/exit `alternative_origins` against original source spans; record one `LoweredLeftRecursion` descriptor.
- [x] Add RED analysis tests proving base rows and recursive/exit rows are disjoint, multiple recursive alternatives conflict at insufficient `k`, and the conflict disappears at a sufficient finite `k`.
- [x] Assert indirect and nullable-prefix recursion still produce source-located `VAL202`, while valid direct LR no longer does.
- [x] Run EBNF lowering/analysis, FIRST/FOLLOW/SELECT oracle and validation suites GREEN.
- [x] Commit and push as `Lowerить direct recursion для canonical analysis`.

### Task 3: High-level `LeftFold` Parser IR

**Files:**
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Create: `tools/parsergen/tests/test_left_fold_parser_ir.py`

**Interfaces:**
- Produce `FoldLeftValue(source_span: SourceSpan)` as a `BoundValue`.
- Produce `LeftFold(base_decision: CanonicalDecision | None, base_branches: tuple[BranchIr, ...], recursive_decision: CanonicalDecision, recursive_branches: tuple[BranchIr, ...], exit_alternative: int, source_span: SourceSpan)` as a value-producing `Operation`.
- A direct-LR `ProductionIr` contains one runtime alternative with one `LeftFold`; synthetic tail is absent from `ParserIr.productions`.

- [x] Write RED IR tests for one base, several bases, two recursive alternatives, recognition-only form and declarative `Left=<Expr>` form.
- [x] Assert recursive runtime operations contain no `ParseSymbol(Expr)`; the leading scalar binding contains `FoldLeftValue`; constructor and suffix bindings preserve source order.
- [x] Run the focused IR test and verify failure because `LeftFold` is absent.
- [x] Teach `_ParserIrBuilder._production` to find the matching `LoweredLeftRecursion` and build base/tail canonical decisions using the sidecar alternative mapping.
- [x] Transform only the classified leading self operation: remove an unbound self parse or replace its scalar bound value with `FoldLeftValue`. Reject sidecar/operation mismatches instead of guessing.
- [x] Mark `LeftFold` value-producing so the enclosing alternative returns its accumulator.
- [x] Add IR guard tests for forged/mismatched lowering, overlapping SELECT and missing semantic base result.
- [x] Run Parser IR, binding IR and canonical condition suites GREEN.
- [x] Commit and push as `Добавить LeftFold в canonical Parser IR`.

### Task 4: Iterative BSL left-fold codegen

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Create: `tools/parsergen/tests/test_canonical_bsl_left_fold.py`

**Interfaces:**
- `LeftFold` renders one base selection followed by one `Пока` over recursive SELECT and a post-loop exit SELECT check.
- `FoldLeftValue` resolves only inside its owning fold to the generated accumulator temporary.
- A semantic recursive branch assigns `ЭтотУзел` back to the accumulator exactly once; a recognition-only branch preserves it.

- [x] Write RED codegen test for `Expr ::= Expr '+' Term | Term`: one `Пока`, no self-call in `НеТерминалExpr`, no synthetic tail function, explicit malformed-input error.
- [x] Write RED semantic test for `@НовыйБинарный Левый=<Expr> Оператор='+' Правый=<Term>`: constructor once in branch text, left property gets accumulator before right parse, accumulator gets `ЭтотУзел` after suffix.
- [x] Run the focused codegen test and verify failure on unsupported `LeftFold`.
- [x] Implement base rendering with canonical dispatch. Initialize one deterministic accumulator from constructor node, explicit branch result or `Неопределено` in recognition-only mode.
- [x] Implement recursive loop using the union of recursive SELECT rows, branch dispatch for multiple suffixes, and the canonical exit/error check already used by `RepeatLoop`.
- [x] Resolve nested `FoldLeftValue` through an explicitly scoped generator stack; reject use outside a fold.
- [x] Add structural cases for `+`/`-` recursive alternatives and separate `Expr -> Term -> Factor` productions; assert the assignment order that implements left associativity and the calls that preserve precedence.
- [x] Prove stack shape statically: the generated same-precedence production has one loop and no self-call, independent of input length. Record 10,000-operator runtime execution as a YAxUnit/Vanessa gate rather than pretending Python executed BSL.
- [x] Run all canonical BSL, EBNF, binding and Parser IR suites GREEN.
- [x] Commit and push as `Генерировать iterative BSL left fold`.

### Task 5: Phase 6 regression and architecture gate

**Files:**
- Modify: `docs/architecture/parser-generator.md`
- Modify: `docs/superpowers/plans/2026-08-07-parsergen-direct-left-recursion.md`
- Test: `tools/parsergen/tests`

**Interfaces:**
- Document direct-LR source contract, analysis tail, `LeftFold`, associativity/precedence and unsupported forms.
- Preserve production legacy artifacts and Phase 5 structural metrics.

- [ ] Run the complete `tools/parsergen/tests` suite and record exact pass/skip/subtest counts.
- [ ] Run current-checkout `validate`, `analyze` and `generate --check`; require the same two production `LLK202` and exit `1`.
- [ ] Run migration audit; require `124/281/63`, 11273 legacy matcher rows, `runtime_conflicts == []` and `artifacts.changed == []`.
- [ ] Run exact legacy BSL/reference/artifact subset GREEN.
- [ ] Generate a representative arithmetic/logical precedence grammar with direct LR and machine-check: loops present, self-calls/synthetic functions/legacy matcher absent, constructors and left bindings ordered.
- [ ] Use EDT read-only structure evidence to reconfirm production `ObjectModule.bsl` remains 135 functions / 3394 LOC before migration.
- [ ] Document that Python proves lowering/code shape, while actual generated BSL execution, AST associativity and long-chain runtime behavior remain required YAxUnit/Vanessa gates after the first production expression slice.
- [ ] Run `git diff --check`; confirm no production grammar/query model/BSL/form diff.
- [ ] Commit and push as `Документировать direct left recursion`.

---

## Deferred to Phase 7+

- Первый production expression family и совместная migration query model/consumers.
- YAxUnit/Vanessa execution of generated left fold and semantic AST assertions.
- Indirect left recursion or generalized parsing.
- Production cutover, differential corpus, runtime benchmark and legacy removal.

## Self-review

- Spec coverage: classification, progress, parameters, semantic binding, CFG lowering, canonical conflicts, IR, codegen, associativity, precedence, malformed input, long chain and legacy boundary each have an owning task.
- Placeholder scan: tasks contain exact files, interfaces, diagnostics, commands and expected outcomes; no unspecified implementation step remains.
- Type consistency: `SourceValidationReport.left_recursions` feeds `LoweringResult.left_recursions`; Parser IR publishes `FoldLeftValue`/`LeftFold`; canonical codegen consumes those exact types.
- Scope: production grammar/query model and 1C runtime execution are explicitly outside this independently verifiable infrastructure phase.
