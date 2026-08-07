# Parsergen EBNF Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в `tools/parsergen` source-level grouping и postfix-конструкции `*`, `+`, `?`, lowered их в существующую canonical CFG для анализа и подготовить optimized Parser IR без изменения production grammar и legacy artifacts.

**Architecture:** Новый immutable Source Grammar AST хранит EBNF и source spans, а отдельный lowerer создаёт детерминированную synthetic CFG и origin sidecar. Существующие `resolve_grammar`, `nullable/FIRST/FOLLOW/SELECT` и legacy artifact APIs продолжают принимать только прежнюю плоскую `model.Grammar`; canonical validation проверяет disjoint SELECT, включая consume/exit, без разрешения конфликтов порядком веток. После успешной валидации Parser IR сохраняет `RepeatLoop`/`OptionalBranch`, поэтому synthetic productions никогда не становятся recursive BSL-функциями.

**Tech Stack:** Python 3.11+, frozen dataclasses, `unittest`/`pytest`, существующие packed FIRST/FOLLOW/SELECT, generated BSL.

## Global Constraints

- Не менять production grammar и три production artifacts на этом этапе.
- Не переписывать алгоритмы nullable/FIRST/FOLLOW/SELECT.
- `SELECT_k(alt_i) ∩ SELECT_k(alt_j) = ∅` для всех alternatives; порядок `Если` не разрешает конфликт.
- Не использовать legacy matcher normalization, shadowing, cycle-prefix injection, nullable fallback или longest-prefix dispatch для новых constructs.
- Synthetic CFG допустима только для analysis; runtime recursion для `*`, `+`, `?` запрещена.
- `*` и `+` принимают только productive body с `min_consumed_tokens >= 1`; nullable/non-consuming body — validation error.
- `?` над nullable body — validation error; repeated postfix вроде `X*?` — syntax error.
- Arbitrary BSL actions внутри EBNF construct до declarative binding не поддерживаются.
- Synthetic production names не попадают в пользовательские diagnostics.
- Existing BNF parsing, production counts `124/281`, legacy artifacts и reference parser parity остаются неизменными.
- Выполнять TDD: каждый production change следует только после наблюдаемого корректного RED.
- Коммитить и пушить каждый coherent task.

---

## File Structure

- Create `tools/parsergen/src/parsergen/source_model.py`: immutable high-level grammar nodes and quantifier kinds.
- Create `tools/parsergen/src/parsergen/source_validation.py`: high-level productivity/nullability/minimum-consumption facts and EBNF diagnostics.
- Create `tools/parsergen/src/parsergen/lowering.py`: deterministic EBNF-to-CFG lowering and origin sidecar.
- Create `tools/parsergen/src/parsergen/parser_ir.py`: canonical executable IR preserving repeat/optional constructs.
- Modify `tools/parsergen/src/parsergen/grammar_parser.py`: one source parser, backward-compatible parse/lower facade.
- Modify `tools/parsergen/src/parsergen/cli.py`: carry source/lowering through compilation and stop before codegen on EBNF until canonical backend is ready.
- Modify `tools/parsergen/src/parsergen/validation.py`: remap synthetic canonical diagnostics to source constructs.
- Modify `tools/parsergen/src/parsergen/bsl_codegen.py`: defensively reject synthetic CFG in legacy backend.
- Create focused tests beside the existing parsergen suites; do not mix oracle, parser, lowering and code-shape contracts in one module.

---

### Task 1: Source Grammar model and backward-compatible parser facade

**Status:** completed in `4f3159c`.

**Files:**
- Create: `tools/parsergen/src/parsergen/source_model.py`
- Modify: `tools/parsergen/src/parsergen/grammar_parser.py`
- Create: `tools/parsergen/tests/test_source_model.py`
- Create: `tools/parsergen/tests/test_source_grammar_parser.py`
- Test: `tools/parsergen/tests/test_grammar_parser.py`

**Interfaces:**
- Produces: `QuantifierKind`, `SourceSequence`, `SourceGroup`, `SourceRepeat`, `SourceOptional`, `SourceAlternative`, `SourceProduction`, `SourceGrammar`.
- Produces: `parse_source_grammar(text: str, path: str = "<memory>") -> SourceParseResult`.
- Preserves: `parse_grammar(...) -> ParseResult` and the first two positional fields `grammar`, `diagnostics`.

- [ ] **Step 1: Add immutable Source IR tests**

```python
def test_source_nodes_preserve_group_and_postfix_origins() -> None:
    result = parse_source_grammar("<S> ::= 'a' (',' 'a')*")
    assert result.diagnostics == ()
    sequence = result.grammar.productions[0].alternatives[0].body
    repeat = sequence.items[1]
    assert isinstance(repeat, SourceRepeat)
    assert repeat.kind is QuantifierKind.ZERO_OR_MORE
    assert isinstance(repeat.body, SourceGroup)
    assert repeat.operator_span.start.column == 22
```

- [ ] **Step 2: Run the focused test and observe RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_source_model.py tools/parsergen/tests/test_source_grammar_parser.py
```

Expected: collection/import failure because `source_model` and `parse_source_grammar` do not exist.

- [ ] **Step 3: Implement the Source IR dataclasses**

Use frozen, slotted dataclasses. `SourceRepeat.body` and `SourceOptional.body` contain exactly one primary; a group contains one or more source alternatives; every structural node has its full span and postfix nodes additionally have `operator_span`. Reuse existing atomic `Terminal`, `Lexeme`, `Constant`, `IdentifierRef`, `NonterminalCall`, and `Action` types rather than duplicating their semantics.

- [ ] **Step 4: Parse sequences, groups and postfix operators into Source IR**

Reserve unquoted `(`, `)`, `*`, `+`, `?`, and `|` as grammar syntax. Preserve nonterminal argument lists as part of `NonterminalCall`; preserve quoted forms such as `'*'`, `'+'`, `'?'`, `'('`, `')'` as `Lexeme`. Parse postfix only when directly following one primary, while allowing whitespace between primary and postfix.

- [ ] **Step 5: Keep `parse_grammar` backward compatible**

Append optional `source_grammar` and `lowering` fields after the existing `ParseResult` fields. For BNF-only input, return a canonical `Grammar` structurally equal to the old result: same production/alternative order, elements, action boundaries and spans. EBNF input may initially return the source tree with a controlled diagnostic until Task 3 installs lowering; it must never be passed silently to legacy codegen.

- [ ] **Step 6: Cover parser errors and delimiter protection**

Add separate cases for `*`, `+`, `?`, separator repeat, nested groups, empty group, unclosed group, postfix without operand, repeated postfix `X*?`, comments/actions containing delimiters, quoted operator lexemes, and nonterminal BSL arguments containing parentheses.

- [ ] **Step 7: Run focused and legacy parser tests GREEN**

```powershell
python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_source_model.py tools/parsergen/tests/test_source_grammar_parser.py tools/parsergen/tests/test_grammar_parser.py tools/parsergen/tests/test_model.py
```

- [ ] **Step 8: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/source_model.py tools/parsergen/src/parsergen/grammar_parser.py tools/parsergen/tests/test_source_model.py tools/parsergen/tests/test_source_grammar_parser.py tools/parsergen/tests/test_grammar_parser.py
git commit -m "Добавить source AST для EBNF"
git push
```

---

### Task 2: High-level progress validation

**Status:** completed in `594cc14`.

**Files:**
- Create: `tools/parsergen/src/parsergen/source_validation.py`
- Create: `tools/parsergen/tests/test_source_validation.py`
- Modify: `tools/parsergen/src/parsergen/grammar_parser.py`

**Interfaces:**
- Consumes: `SourceGrammar` from Task 1.
- Produces: `SourceFacts(productive, nullable, min_consumed_tokens)` indexed by production and source node.
- Produces: `validate_source_grammar(grammar: SourceGrammar) -> SourceValidationReport`.

- [ ] **Step 1: Write fixpoint and diagnostic RED tests**

```python
def test_rejects_transitively_nullable_repeat_body() -> None:
    parsed = parse_source_grammar("<S> ::= <N>*\n<N> ::= ПУСТО")
    report = validate_source_grammar(parsed.grammar)
    assert [item.code for item in report.diagnostics] == ["EBNF201"]

def test_rejects_nullable_optional_body() -> None:
    parsed = parse_source_grammar("<S> ::= (<N>)?\n<N> ::= ПУСТО | a")
    report = validate_source_grammar(parsed.grammar)
    assert [item.code for item in report.diagnostics] == ["EBNF202"]
```

- [ ] **Step 2: Observe focused RED**

Run `python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_source_validation.py` and confirm failure is caused by the missing validator.

- [ ] **Step 3: Implement source facts as a monotone fixpoint**

Token atom: productive, non-nullable, minimum `1`. Action: productive, nullable, minimum `0`. Sequence: productive only when every item is productive; nullable only when every item is nullable; minimum is the sum. Alternative/group: productive when one branch is productive; nullable when one branch is nullable; minimum is the minimum productive branch. `*` and `?` are nullable with minimum `0`; `+` inherits body facts. Nonterminal calls use production facts until convergence.

- [ ] **Step 4: Emit stable source-level errors**

Use:

- `EBNF200`: nonproductive quantified body;
- `EBNF201`: nullable/non-consuming `*` or `+` body;
- `EBNF202`: nullable optional body;
- `EBNF204`: arbitrary `Action` nested inside group/quantifier;
- `GR005`: source production uses reserved case-insensitive prefix `__parsergen_ebnf__`.

Point the primary diagnostic at `operator_span`; attach body/production source details without synthetic names.

- [ ] **Step 5: Cover direct, transitive and nested cases**

Add action-only body, nonproductive cycle, transitively nullable call, nested `(a?)*`, productive token repeat, recursive-but-consuming production, nullable optional and reserved-prefix cases. Verify exact codes and line/column spans.

- [ ] **Step 6: Run source validation and existing validation suites GREEN**

```powershell
python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_source_validation.py tools/parsergen/tests/test_validation.py
```

- [ ] **Step 7: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/source_validation.py tools/parsergen/src/parsergen/grammar_parser.py tools/parsergen/tests/test_source_validation.py
git commit -m "Проверять прогресс EBNF конструкций"
git push
```

---

### Task 3: Deterministic canonical CFG lowering and origin map

**Status:** completed in `7ff38ce`.

**Files:**
- Create: `tools/parsergen/src/parsergen/lowering.py`
- Create: `tools/parsergen/tests/test_ebnf_lowering.py`
- Modify: `tools/parsergen/src/parsergen/grammar_parser.py`
- Modify: `tools/parsergen/src/parsergen/cli.py`
- Test: `tools/parsergen/tests/test_resolver.py`

**Interfaces:**
- Produces: `LoweredConstruct`, `LoweringResult(grammar: Grammar, constructs: tuple[LoweredConstruct, ...], diagnostics: tuple[Diagnostic, ...])`.
- Produces: `lower_source_grammar(grammar: SourceGrammar) -> LoweringResult`.
- `ParseResult.grammar` becomes the lowered canonical CFG for valid EBNF input.
- `Compilation` appends source/lowering fields without reordering existing positional fields.

- [ ] **Step 1: Write exact lowering RED tests**

```python
def test_star_lowers_to_body_recursion_and_epsilon_with_origin() -> None:
    parsed = parse_source_grammar("<S> ::= 'a' (',' 'a')*")
    lowered = lower_source_grammar(parsed.grammar)
    repeat = next(item for item in lowered.constructs if item.kind == "star")
    production = next(item for item in lowered.grammar.productions if item.name == repeat.production)
    assert len(production.alternatives) == 2
    assert production.alternatives[1].syntax_symbols == ()
    assert repeat.source_span.start.line == 1
```

- [ ] **Step 2: Observe focused RED**

Run `python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_ebnf_lowering.py` and confirm the missing lowering API is the cause.

- [ ] **Step 3: Implement deterministic names and lowering**

Use reserved names based on tree coordinates, for example `__parsergen_ebnf__p0_a0_n1_star`; never hash source text or offsets. Lower:

```text
X* -> R ::= X R | ε
X? -> O ::= X | ε
X+ -> P ::= X R
      R ::= X R | ε
```

Groups with alternatives expand through stable synthetic productions when needed. Lower nested constructs from the inside out. Recompute flat action boundaries only for legacy top-level actions; nested actions were rejected by Task 2.

- [ ] **Step 4: Preserve BNF identity**

For a grammar without EBNF, `lower_source_grammar(...).grammar` must equal the pre-Phase-3 `parse_grammar` result and `constructs` must be empty. No synthetic production may appear in the repository grammar.

- [ ] **Step 5: Integrate parse and compilation without changing analysis**

`parse_grammar` performs source parse, source validation and lowering, then returns the canonical CFG. `compile_from_config` carries `source_grammar` and `lowering` for later Parser IR but calls existing `resolve_grammar`, `compute_analysis` and `validate_grammar` exactly on the lowered CFG.

- [ ] **Step 6: Cover resolver behavior**

Verify nonterminal references inside group/repeat resolve through the canonical CFG, unknown references retain the source span, and synthetic occurrence indexes are deterministic.

- [ ] **Step 7: Run focused integration GREEN**

```powershell
python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_ebnf_lowering.py tools/parsergen/tests/test_resolver.py tools/parsergen/tests/test_cli.py tools/parsergen/tests/test_repository_grammar.py
```

- [ ] **Step 8: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/lowering.py tools/parsergen/src/parsergen/grammar_parser.py tools/parsergen/src/parsergen/cli.py tools/parsergen/tests/test_ebnf_lowering.py tools/parsergen/tests/test_resolver.py tools/parsergen/tests/test_cli.py
git commit -m "Lowered EBNF в canonical CFG"
git push
```

---

### Task 4: Canonical oracle equivalence and source-mapped SELECT diagnostics

**Status:** completed in `bf045f3`.

**Files:**
- Create: `tools/parsergen/tests/test_ebnf_analysis.py`
- Modify: `tools/parsergen/src/parsergen/validation.py`
- Modify: `tools/parsergen/src/parsergen/cli.py`
- Create: `tools/parsergen/tests/test_ebnf_validation.py`

**Interfaces:**
- Consumes: existing `compute_analysis` without modifying its algorithms.
- Produces: source-remapped diagnostics for synthetic productions and alternatives.
- Preserves: canonical conflict witness and pairwise-disjoint SELECT invariant.

- [ ] **Step 1: Write lowered-vs-handwritten BNF oracle tests**

For lookahead `k=1,2,3`, compare nullable, FIRST, FOLLOW and factorized SELECT for EBNF grammars against explicit handwritten BNF for star, plus, optional, separator repeat, nested repeat and EOF context. Compare language-bearing decisions after mapping synthetic names through the origin sidecar.

- [ ] **Step 2: Run oracle tests and observe RED**

Expected initial failure: no origin-aware equivalence helper/source-remapped construct decision exists; the canonical solver itself must not be changed merely to satisfy the test.

- [ ] **Step 3: Add canonical conflict integration RED tests**

```python
def test_repeat_body_and_exit_select_must_be_disjoint() -> None:
    compilation = compile_text("<S> ::= 'a'* 'a'", lookahead=1, start="S")
    conflicts = [d for d in compilation.report.diagnostics if d.code == "LLK202"]
    assert len(conflicts) == 1
    assert "__parsergen_ebnf__" not in conflicts[0].message
    assert conflicts[0].span.start.column == 11
```

Also cover overlapping group alternatives and optional body/exit. Never expect the first branch to win.

- [ ] **Step 4: Remap diagnostics through lowering origins**

Before returning `Compilation.report`, translate synthetic production/alternative spans to the corresponding source group/postfix spans while preserving canonical witness/details. If a synthetic mapping is missing, fail compilation defensively rather than expose a generated name.

- [ ] **Step 5: Run canonical and legacy suites GREEN**

```powershell
python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_ebnf_analysis.py tools/parsergen/tests/test_ebnf_validation.py tools/parsergen/tests/test_nullable_first.py tools/parsergen/tests/test_follow_select.py tools/parsergen/tests/test_validation.py
```

- [ ] **Step 6: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/validation.py tools/parsergen/src/parsergen/cli.py tools/parsergen/tests/test_ebnf_analysis.py tools/parsergen/tests/test_ebnf_validation.py
git commit -m "Проверять canonical SELECT для EBNF"
git push
```

---

### Task 5: Parser IR boundary and legacy backend guard

**Status:** completed in `8f046c7`.

**Files:**
- Create: `tools/parsergen/src/parsergen/parser_ir.py`
- Create: `tools/parsergen/tests/test_parser_ir.py`
- Modify: `tools/parsergen/src/parsergen/bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_reference_parser.py`

**Interfaces:**
- Produces: `ParserIr`, `ProductionIr`, `Dispatch`, `ParseSymbol`, `RepeatLoop`, `OptionalBranch`.
- Produces: `build_parser_ir(source: SourceGrammar, lowering: LoweringResult, resolved: ResolvedGrammar, analysis: AnalysisResult) -> ParserIr`.
- Preserves: `generate_parser(...)` as legacy-only API for the untouched production grammar.

- [ ] **Step 1: Write Parser IR RED tests for the first synthetic slice**

For `<List> ::= 'a' (',' 'a')*`, assert that the public production contains `ParseSymbol('a')` followed by one `RepeatLoop`; the loop body contains separator then item; no synthetic production appears in `ParserIr.productions`.

- [ ] **Step 2: Add plus and optional RED tests**

Assert `+` emits one mandatory body parse followed by `RepeatLoop`, and `?` emits `OptionalBranch`. Each decision references canonical factorized SELECT/origin data, not a legacy matcher artifact.

- [ ] **Step 3: Observe focused RED**

Run `python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_parser_ir.py` and confirm the missing IR module causes failure.

- [ ] **Step 4: Implement the minimal IR builder**

Build only `Dispatch`, `ParseSymbol`, `RepeatLoop`, and `OptionalBranch`. Filter analysis-only synthetic productions from runtime productions. Do not implement declarative bindings or direct LR in this task. Reject building IR when source or canonical validation has errors.

- [ ] **Step 5: Guard the legacy generator**

Before legacy artifact construction, reject any grammar containing the reserved synthetic prefix with a message that canonical Parser IR/codegen is required. Existing BNF repository generation must remain byte-for-byte unchanged.

- [ ] **Step 6: Run IR, codegen and exact reference parity GREEN**

```powershell
python -m pytest -q -p no:cacheprovider tools/parsergen/tests/test_parser_ir.py tools/parsergen/tests/test_bsl_codegen.py tools/parsergen/tests/test_reference_parser.py tools/parsergen/tests/test_artifacts.py
```

- [ ] **Step 7: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/parser_ir.py tools/parsergen/src/parsergen/bsl_codegen.py tools/parsergen/tests/test_parser_ir.py tools/parsergen/tests/test_bsl_codegen.py tools/parsergen/tests/test_reference_parser.py
git commit -m "Отделить Parser IR от legacy backend"
git push
```

---

### Task 6: Phase 3 regression gate and documentation

**Status:** completed on 2026-08-07; repository CLI preserved the documented
two-`LLK202` baseline and migration audit reported no artifact changes.

**Files:**
- Modify: `docs/architecture/parser-generator.md`
- Modify: `docs/superpowers/plans/2026-08-07-parsergen-ebnf-infrastructure.md`
- Test: all `tools/parsergen/tests`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: reproducible Phase 3 evidence without production artifact changes.

- [ ] **Step 1: Run the full parsergen suite**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest -q -p no:cacheprovider tools/parsergen/tests
```

Expected: all tests pass; the existing Windows symlink test may remain the single explicitly documented skip.

- [ ] **Step 2: Run repository validation commands read-only**

```powershell
python -m parsergen validate --config parsergen.toml
python -m parsergen analyze --config parsergen.toml --format json
python -m parsergen generate --config parsergen.toml --check
```

Record actual results. The current repository baseline has two known canonical `LLK202`; therefore `validate` and `generate --check` may return code `1` before artifact comparison. Do not reinterpret them as legacy conflicts and do not regenerate artifacts.

- [ ] **Step 3: Verify structural and artifact parity**

Assert repository source/canonical production counts remain `124/281`, no synthetic names occur, and exact reference parser/artifact tests pass. Confirm the three production parser artifacts have no diff.

- [ ] **Step 4: Update architecture documentation**

Document Source AST, deterministic lowering, progress restrictions, disjoint consume/exit SELECT, Parser IR boundary, legacy backend guard, and that optimized BSL loop/conditional emission is the next Phase 3 delivery before any production grammar migration.

- [ ] **Step 5: Review worktree and diff**

```powershell
git diff --check
git status --short
git diff --stat d84cca4..HEAD
```

- [ ] **Step 6: Commit and push**

```powershell
git add docs/architecture/parser-generator.md docs/superpowers/plans/2026-08-07-parsergen-ebnf-infrastructure.md
git commit -m "Документировать EBNF infrastructure"
git push
```

---

## Self-review

- Spec coverage: source AST, grouping/postfix syntax, progress validation, canonical lowering, oracle equivalence, disjoint SELECT, source diagnostics, Parser IR and legacy isolation are assigned to concrete tasks.
- Deferred intentionally: declarative AST binding, optimized BSL emission, direct productive LR and production grammar migration remain separate coherent plans after this infrastructure gate.
- Placeholder scan: no `TBD`, generic error-handling step or unnamed test action remains.
- Type consistency: `SourceGrammar -> LoweringResult -> existing Grammar/ResolvedGrammar/AnalysisResult -> ParserIr` is used consistently; legacy `generate_parser` remains separate.
