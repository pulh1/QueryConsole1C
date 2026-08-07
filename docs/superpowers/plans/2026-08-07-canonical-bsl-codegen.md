# Canonical BSL Codegen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Сгенерировать из canonical Parser IR отдельный BSL parser с iterative EBNF control flow, declarative AST operations и inline canonical lookahead без legacy matcher artifact.

**Architecture:** `canonical_bsl_codegen.py` рендерит высокоуровневый Parser IR в отдельный canonical runtime template. `canonical_bsl_conditions.py` превращает factorized canonical decision rows в disjoint BSL predicates. Legacy generator сохраняет output parity; только общие lexical/string safety helpers выносятся в neutral module.

**Tech Stack:** Python 3.11+, frozen dataclasses, existing canonical Parser IR, BSL text templates, `unittest`/`pytest`, EDT read-only verification.

## Global Constraints

- SELECT alternatives должны быть disjoint; generated `Если` order никогда не разрешает conflict.
- `k` берётся из `ParserIr.lookahead` и не имеет architectural maximum `2`.
- Canonical backend не импортирует и не вызывает legacy matcher APIs.
- `RepeatLoop` генерирует BSL `Пока`, а не recursive synthetic function.
- `OptionalBranch` принимает epsilon только по canonical exit SELECT; посторонний token вызывает error.
- Grouped/transparent semantic result выбирается явным index, а не «последним temporary».
- Canonical nonterminal calls передают только declared arguments; `Родитель` и `ЛевыйЭлемент` не инжектируются.
- Production grammar, query model, BSL module и checked-in templates текущего parser не регенерируются на Phase 5.
- Runtime YAxUnit/Vanessa остаётся финальным interactive gate; Phase 5 закрывает все headless tests.

---

### Task 1: Neutral BSL rendering safety

**Files:**
- Create: `tools/parsergen/src/parsergen/bsl_rendering.py`
- Modify: `tools/parsergen/src/parsergen/bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_bsl_codegen.py`
- Create: `tools/parsergen/tests/test_bsl_rendering.py`

**Interfaces:**
- Produce `validate_bsl_identifier(name: str, origin: str) -> None`.
- Produce `bsl_string(value: str) -> str`.
- Produce `normalize_newlines(text: str) -> str`.
- Legacy `generate_parser(...)` output remains byte-identical.

- [x] Write tests for Cyrillic/Latin identifiers, every existing reserved-keyword category, quote escaping and CR/LF normalization.
- [x] Run the new tests RED because `bsl_rendering` does not exist.
- [x] Move the existing keyword sets and three pure helpers without changing their messages or output.
- [x] Make legacy `bsl_codegen.py` import the neutral helpers and remove only their duplicate definitions.
- [x] Run `test_bsl_rendering.py`, full `test_bsl_codegen.py`, reference renderer/artifact tests and verify exact production artifact parity.
- [x] Commit and push as `Выделить общие BSL rendering helpers`.

---

### Task 2: Explicit transparent result contract

**Files:**
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/tests/test_parser_ir.py`
- Modify: `tools/parsergen/tests/test_binding_parser_ir.py`

**Interfaces:**
- `BranchIr` adds `result_index: int | None`.
- `AlternativeIr` adds `result_index: int | None`.
- `result_index` points to the sole operation producing the transparent value.
- Constructor alternatives keep `result_index = None`; `ConstructNode` owns their result.

- [x] Write RED tests for transparent nonterminal/identifier/constant, syntax-only branch, grouped alternative and two-semantic-child rejection.
- [x] Compute semantic indices from source operations before constructing `BranchIr`/`AlternativeIr`.
- [x] Treat `ParseSymbol(NonterminalCall|IdentifierRef|Constant)`, value-producing `Dispatch` and value-producing `OptionalBranch` as transparent values; terminals/lexemes alone are syntax-only unless directly wrapped by a binding.
- [x] Reject more than one transparent semantic operation during `build_parser_ir`, before codegen.
- [x] Update all EBNF/binding IR tests for the explicit fields and verify no synthetic production enters `ParserIr.productions`.
- [x] Run Parser IR, source validation and canonical SELECT suites GREEN.
- [x] Commit and push as `Зафиксировать transparent result в Parser IR`.

---

### Task 3: Canonical lookahead predicates

**Files:**
- Create: `tools/parsergen/src/parsergen/canonical_bsl_conditions.py`
- Create: `tools/parsergen/tests/test_canonical_bsl_conditions.py`

**Interfaces:**
- Produce `CanonicalConditionRenderer(matcher_definitions)`.
- Produce `for_alternative(decision: CanonicalDecision, alternative: int) -> str`.
- Produce `for_alternatives(decision: CanonicalDecision, alternatives: tuple[int, ...]) -> str`.
- Conditions call `ТипТокенаПросмотра(offset)` with zero-based offsets.

- [x] Write RED tests for one token, identifier matcher with several token types, several rows joined by `Или`, `k=3`, short prefix and `$`/EOF.
- [x] Render every row as a parenthesized conjunction and every matcher token set as a parenthesized disjunction in stable artifact order.
- [x] Render `$` only as `ТипТокенаПросмотра(offset) = Неопределено`.
- [x] Reject unknown labels, empty matcher definitions, malformed `$` definitions, missing alternative rows and a requested position beyond `decision` rows.
- [x] Add a truth-table helper in tests proving every sampled lookahead word selects at most one alternative; do not encode branch order as precedence.
- [x] Run condition, analysis artifact, identifier matcher and canonical conflict tests GREEN.
- [x] Commit and push as `Рендерить canonical lookahead predicates`.

---

### Task 4: Canonical runtime shell and production dispatch

**Files:**
- Create: `tools/parsergen/src/parsergen/templates/canonical_parser_module.bsl`
- Create: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Create: `tools/parsergen/tests/test_canonical_bsl_codegen.py`

**Interfaces:**
- Produce frozen `CanonicalGeneratedParser(module_text, identifier_table, constructor_names)`.
- Produce `generate_canonical_parser(source: SourceGrammar, parser_ir: ParserIr, entrypoints: Mapping[str, str]) -> CanonicalGeneratedParser`.
- Canonical template provides `ТипТокенаПросмотра(Смещение)` and no legacy matcher globals/functions.

- [x] Write RED tests for module markers, entrypoint order, `lookahead=3`, identifier table, single production, multi-alternative dispatch and explicit syntax-error fallback.
- [x] Create the canonical template with lexer initialization, token buffer, terminal/lexeme/identifier/constant helpers, entry markers and simplified syntax-error helpers.
- [x] Verify the template contains neither `ТаблицаПервыхСимволовВариантов` nor `НомерВариантаПродукции`.
- [x] Validate source/IR production and parameter identity, entrypoints, BSL identifiers, generated symbol collisions and reserved `$`.
- [x] Render canonical `ParseSymbol`; nonterminal calls pass only `symbol.arguments`.
- [x] Render `ProductionIr.decision` with `CanonicalConditionRenderer`; every uncovered input reaches the syntax-error helper.
- [x] Render transparent results using `AlternativeIr.result_index`; syntax-only production returns `Неопределено`.
- [x] Run module-shell/code-shape tests and confirm imports contain no legacy matcher API names.
- [x] Commit and push as `Добавить canonical BSL runtime shell`.

---

### Task 5: Iterative EBNF control flow

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Create: `tools/parsergen/tests/test_canonical_bsl_ebnf.py`

**Interfaces:**
- `Dispatch` renders a disjoint conditional chain.
- `OptionalBranch` renders consuming alternatives, exit condition and exit operations.
- `RepeatLoop` renders one BSL `Пока` with consuming union and post-loop exit validation.

- [x] Write RED code-shape tests for empty/single/many `*`, `+`, separator repeat, nested repeat/optional and `k=3` decisions.
- [x] Render `Dispatch` through the canonical condition renderer and return its explicit branch value when `BranchIr.result_index` is set.
- [x] Render `OptionalBranch` with explicit exit `ИначеЕсли`; render `exit_operations` only for the exit alternative and throw for tokens outside all SELECT rows.
- [x] Render `RepeatLoop` with the OR-union of consuming alternatives in `Пока`; when several branches exist, dispatch inside the body using the same disjoint conditions.
- [x] After loop termination, require the canonical exit condition; emit no append or parse operation for exit.
- [x] Prove generated module contains one loop, no function named from `__parsergen_ebnf__`, no recursive synthetic call and no legacy dispatch name.
- [x] Add a long-list grammar test whose generated function count and loop count are constant as the conceptual item count grows.
- [x] Run EBNF codegen, Parser IR, analysis oracle and diagnostics suites GREEN.
- [x] Commit and push as `Генерировать BSL loops для EBNF`.

---

### Task 6: Declarative AST operations

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Create: `tools/parsergen/tests/test_canonical_bsl_bindings.py`

**Interfaces:**
- `ConstructNode` calls `ЭлементыМоделиЗапроса.<constructor>(ТекущийТокен)` once.
- `BindScalar`, `AppendCollection`, `AssignConstant` render direct BSL mutations.
- `ParseBranchValue` and `DispatchValue` return the explicitly indexed nested parse result.

- [ ] Write RED tests for constructor + scalar, optional present/absent, repeated append, separator exclusion, terminal/identifier/constant capture, boolean/symbolic constants and grouped value dispatch.
- [ ] Give every value-producing operation a deterministic generated temporary; never reuse an untracked `ТекущийЭлемент` convention.
- [ ] Render `ParseBranchValue.operations` in order and select exactly `result_index`; render suffix operations even when they do not produce the bound value.
- [ ] Render `DispatchValue` so every disjoint branch assigns one shared result temporary and invalid lookahead throws.
- [ ] Render scalar optional exit as `ЭтотУзел.<property> = Неопределено`; render append only in consuming loop branches.
- [ ] Validate property and constructor identifiers again at codegen boundary; collect constructor names in stable first-use order.
- [ ] Verify canonical code contains zero arbitrary source actions, zero `Родитель`, zero `ЛевыйЭлемент` and zero synthetic function names.
- [ ] Run binding codegen, binding IR, binding validation and full canonical codegen suites GREEN.
- [ ] Commit and push as `Генерировать declarative AST operations в BSL`.

---

### Task 7: Phase 5 regression and architecture gate

**Files:**
- Modify: `docs/architecture/parser-generator.md`
- Modify: this plan status/checklists.
- Test: all `tools/parsergen/tests`.

**Interfaces:**
- Document the production-ready canonical backend API without switching production config.
- Record exact test counts and repository audit metrics.

- [ ] Run the complete parsergen suite and record pass/skip/subtest counts.
- [ ] Run `validate`, `analyze`, `generate --check` read-only; preserve two canonical `LLK202` and exit code `1` baseline.
- [ ] Run migration audit and require `124/281`, `63` epsilon, `11273` legacy rows, `runtime_conflicts == []` and `artifacts.changed == []`.
- [ ] Run exact legacy BSL renderer/reference artifact tests after the neutral helper extraction.
- [ ] Generate representative canonical modules for star/plus/optional/bindings and machine-check absence of legacy matcher and synthetic function names.
- [ ] Use EDT read-only structure/source evidence to document the unchanged production parser baseline and future cutover boundary.
- [ ] Update architecture documentation with canonical template, inline predicate semantics, explicit errors, loop/optional shapes and remaining runtime-test limitation.
- [ ] Run `git diff --check`; confirm no production grammar/query model/BSL/form diff.
- [ ] Commit and push as `Документировать canonical BSL codegen`.

---

## Deferred to next phases

- Direct productive left recursion and iterative `LeftFold`.
- Production grammar/query model migration by coherent vertical slices.
- Differential production parser cutover and artifact integration.
- Runtime benchmark after real production slices.
- YAxUnit/Vanessa and UI-only Query Constructor checks at the final gate.

## Self-review

- Spec coverage: canonical/legacy separation, arbitrary finite `k`, disjoint SELECT, EOF, malformed input, loop/optional lowering, semantic bindings and test boundaries each have an owning task.
- Scope: direct LR and production migration are excluded so Phase 5 remains independently testable.
- Type consistency: `SourceGrammar + ParserIr + entrypoints -> CanonicalGeneratedParser`; condition renderer consumes the exact `CanonicalDecision`/`MatcherDefinition` types already published by Parser IR.
- Placeholder scan: no unnamed test action, generic error-handling step or deferred implementation remains inside Tasks 1–7.
