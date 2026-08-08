# Parsergen Declarative AST Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить минимальный declarative AST-binding DSL, достаточный для constructor, scalar/optional, repeated collection, token и constant bindings без arbitrary BSL actions в canonical grammar.

**Architecture:** Binding nodes живут только в Source Grammar AST и при canonical CFG lowering исчезают, сохраняя только обёрнутый grammar value и origin metadata. High-level validator доказывает constructor scope, cardinality и совместимость binding modes до lowering. Parser IR получает явные `ConstructNode`, `BindScalar`, `AppendCollection` и `AssignConstant`; optimized BSL codegen будет отдельным следующим этапом.

**Tech Stack:** Python 3.11+, frozen dataclasses, existing EBNF Source AST/lowering/Parser IR, `unittest`/`pytest`.

**Status:** completed on 2026-08-07. Final gate: `322 passed, 1 skipped,
4051 subtests`; repository audit preserved `124/281`, `63` epsilon
alternatives, `11273` legacy matcher rows, two known canonical `LLK202`, zero
legacy runtime conflicts and `artifacts.changed == []`.

## Global Constraints

- Утверждённый DSL: `@Constructor`, `Property = value`, `Property += value`, `Property := constant`.
- Property и constructor names — BSL identifiers; constant — `Истина`, `Ложь`, `Неопределено` или dotted symbolic name.
- Binding analysis-neutral: nullable/FIRST/FOLLOW/SELECT видят только bound grammar value.
- Constructor и constant assignment не потребляют input.
- `=` поддерживает scalar и optional value; repeated/multi-valued value для `=` запрещён.
- `+=` добавляет каждое реально разобранное value и является единственным collection mode.
- Binding внутри repeat с `=` запрещён; `+=` разрешён.
- В одной alternative property не может смешивать `=` и `+=`.
- Binding требует ровно один active constructor в той же source alternative, включая nested group/repeat scope.
- Alternative с canonical directives не может содержать arbitrary `Action`.
- Pure legacy BNF alternatives и production artifacts остаются byte-identical.
- Python не дублирует схему 91 BSL factory constructor и не проверяет фактическое наличие property.
- SELECT disjointness и legacy boundary из предыдущего этапа не меняются.
- Каждый production change проходит наблюдаемый RED, focused GREEN, full parsergen gate, commit и push.

---

## File Structure

- Modify `source_model.py`: constructor/binding/value cardinality source nodes.
- Modify `grammar_parser.py`: lexical parsing of `@`, `=`, `+=`, `:=` without changing legacy actions.
- Create `binding_validation.py`: constructor scope, modes, cardinality and constant validation.
- Modify `source_validation.py`: semantic nodes are epsilon; bound values contribute grammar facts.
- Modify `lowering.py`: erase semantic directives while lowering bound values and preserve binding origins.
- Modify `parser_ir.py`: explicit semantic IR operations.
- Add focused parser, validation, lowering and IR tests.

---

### Task 1: Source binding nodes and parser syntax

**Files:**
- Modify: `tools/parsergen/src/parsergen/source_model.py`
- Modify: `tools/parsergen/src/parsergen/grammar_parser.py`
- Create: `tools/parsergen/tests/test_binding_parser.py`
- Test: `tools/parsergen/tests/test_source_grammar_parser.py`

**Interfaces:**
- Produce `BindingMode.SCALAR`, `BindingMode.APPEND`.
- Produce `SourceConstructor(name, span)`, `SourceBinding(property, mode, value, span, operator_span)`, `SourceConstantBinding(property, value, span, operator_span)`.

- [x] Write RED tests for `@НовыйУзел`, scalar nonterminal, optional scalar, repeated append, terminal/identifier capture and dotted constant.
- [x] Verify collection fails because source binding types/parser support do not exist.
- [x] Parse a binding RHS as exactly one primary plus optional postfix; preserve its original span and make the binding span cover property through RHS.
- [x] Parse `:=` RHS as one allowed lexical constant candidate; semantic validity remains Task 2.
- [x] Preserve quoted `@`, `=`, `+=`, `:=` as lexeme content when inside quotes and preserve every delimiter inside legacy `{...}` actions.
- [x] Report `GP010` for missing constructor name, missing property, missing RHS, unknown binding operator and malformed dotted constant tokenization.
- [x] Run focused parser tests plus all existing source/legacy grammar parser tests GREEN.
- [x] Commit and push as `Добавить syntax declarative AST binding`.

Representative contract:

```python
parsed = parse_source_grammar(
    "<List> ::= @НовыйСписок Items += <Item> (',' Items += <Item>)*"
)
alternative = parsed.grammar.productions[0].alternatives[0]
assert isinstance(alternative.body.items[0], SourceConstructor)
assert alternative.body.items[1].mode is BindingMode.APPEND
```

---

### Task 2: Constructor scope and binding cardinality validation

**Files:**
- Create: `tools/parsergen/src/parsergen/binding_validation.py`
- Create: `tools/parsergen/tests/test_binding_validation.py`
- Modify: `tools/parsergen/src/parsergen/grammar_parser.py`
- Modify: `tools/parsergen/src/parsergen/source_validation.py`

**Interfaces:**
- Produce `BindingCardinality(min_values: int, max_values: int | None)`.
- Produce `validate_bindings(grammar: SourceGrammar) -> BindingValidationReport`.
- Merge binding diagnostics into `parse_grammar` before lowering.

- [x] Write RED tests for missing/duplicate constructor, binding before/without constructor scope, mixed modes, duplicate scalar, scalar inside repeat, scalar wrapping `*`/`+`, invalid constant and action/directive mixing.
- [x] Add GREEN cases for optional scalar, first-item append plus repeated append, same scalar property in mutually exclusive source alternatives, token capture and constants.
- [x] Compute value cardinality structurally: atom `1..1`, optional `0..1`, star `0..*`, plus `1..*`, group choice min/max, sequence binding value from its wrapped node only.
- [x] Use stable diagnostics: `BIND200` constructor scope, `BIND201` binding without constructor, `BIND202` conflicting modes, `BIND203` repeated/multi-valued scalar, `BIND204` invalid constant, `BIND205` action mixed with canonical directives, `BIND206` ambiguous transparent alternative.
- [x] Validate properties by control-flow branch: mutually exclusive alternatives may assign the same scalar once; a single execution path may not assign it twice.
- [x] Treat constructor/constant directives as productive nullable zero-token nodes; SourceBinding inherits facts from its value.
- [x] Ensure unknown nonterminal errors remain owned by resolver and are not masked by cardinality diagnostics.
- [x] Run binding/source/validation suites GREEN.
- [x] Commit and push as `Проверять declarative AST bindings`.

---

### Task 3: Analysis-neutral lowering and origin parity

**Files:**
- Modify: `tools/parsergen/src/parsergen/lowering.py`
- Create: `tools/parsergen/tests/test_binding_lowering.py`
- Modify: `tools/parsergen/tests/test_ebnf_analysis.py`

**Interfaces:**
- `LoweringResult` adds immutable binding origins keyed by source production/alternative/path.
- Canonical CFG contains no constructor/binding nodes.

- [x] Write RED tests proving constructor and constant directives disappear and scalar/append bindings lower to exactly their grammar values.
- [x] Prove binding-wrapped `?`, `*`, `+` keep the same deterministic synthetic shape and SELECT as unbound EBNF.
- [x] Preserve binding source path/origin for Parser IR; never reconstruct binding from synthetic names.
- [x] Verify BNF identity and repository `124/281` counts remain unchanged.
- [x] Compare nullable/FIRST/FOLLOW/SELECT for bound grammar against the equivalent unbound grammar at `k=1..3`.
- [x] Run lowering/oracle/repository/reference artifact tests GREEN.
- [x] Commit and push as `Lowered AST bindings без изменения grammar semantics`.

---

### Task 4: Semantic Parser IR operations

**Files:**
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/tests/test_parser_ir.py`
- Create: `tools/parsergen/tests/test_binding_parser_ir.py`

**Interfaces:**
- Produce `ConstructNode(constructor, source_span)`.
- Produce `BindScalar(property, value, source_span)`.
- Produce `AppendCollection(property, value, source_span)`.
- Produce `AssignConstant(property, value, source_span)`.
- Preserve `RepeatLoop`/`OptionalBranch` as the control-flow owner of nested binding operations.

- [x] Write RED IR tests for constructor + scalar, optional scalar, append in separator repeat, token capture and constant assignment.
- [x] Define bound value as one explicit nested parse/control-flow operation, not an implicit “last temporary” convention.
- [x] For scalar optional, represent absent result explicitly so codegen assigns `Неопределено` deterministically.
- [x] For append in repeat, place `AppendCollection` inside each consuming loop branch; exit performs no append.
- [x] Reject legacy `Action` in a production containing semantic IR directives.
- [x] Verify Parser IR contains no synthetic productions and no legacy artifact references.
- [x] Run Parser IR and canonical decision tests GREEN.
- [x] Commit and push as `Добавить semantic operations в Parser IR`.

---

### Task 5: Binding infrastructure regression gate

**Files:**
- Modify: `docs/architecture/parser-generator.md`
- Modify: this plan status markers.
- Test: all `tools/parsergen/tests`.

- [x] Run full parsergen suite and record exact pass/skip/subtest counts.
- [x] Run repository `validate`, `analyze`, `generate --check` read-only; preserve two known canonical `LLK202` and code `1` baseline.
- [x] Run migration audit; require `124/281`, unchanged structural metrics, `11273` legacy rows and `artifacts.changed == []`.
- [x] Document binding syntax, validation/cardinality, analysis neutrality and Parser IR semantics.
- [x] Run `git diff --check`, inspect changed paths and confirm no production grammar/BSL/form changes.
- [x] Commit and push as `Документировать declarative AST binding`.

---

## Deferred to the next plans

- Optimized BSL rendering for `RepeatLoop`, `OptionalBranch` and semantic operations.
- Direct productive left recursion and `LeftFold`.
- Real `СписокВыражений` vertical slice and production grammar/model migration.
- Runtime YAxUnit/Vanessa execution of generated canonical BSL.

These are deferred boundaries, not placeholders in this plan: this delivery ends with a fully validated and analyzed Parser IR contract.
