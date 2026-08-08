# Parsergen Canonical Decision DAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace materialized canonical decision rows with an exact symbolic Decision DAG, bind its leaves to Parser IR actions, emit direct BSL control flow, and remove provably redundant caller/callee and structural runtime nodes.

**Architecture:** Export each alternative's factorized canonical SELECT as a finite symbolic language over exact token sets, determinize the relevant alternatives together into an immutable early-commit DAG, and store both the symbolic source and validated DAG in Parser IR. A direct BSL renderer emits cached lookahead variables and structured branches; a separate Parser IR optimizer performs symbolic caller/callee composition, semantic-transparency checks, and reachability cleanup.

**Tech Stack:** Python 3.11+, immutable dataclasses, `unittest`/pytest, existing parsergen factor graphs and canonical analysis, generated 1C BSL, YAxUnit/EDT for final runtime validation.

## Global Constraints

- Keep production `lookahead = 2`; all algorithms remain valid for arbitrary configured `k >= 1`.
- Canonical semantics is exactly `SELECT_k(A → α) = FIRST_k(α FOLLOW_k(A))`.
- Never use branch order, first-match, longest-match, priority, or nullable fallback to resolve canonical alternatives.
- Never materialize the SELECT Cartesian product for DAG construction or production codegen.
- Treat `#ID_*` as grammar sugar over exact immutable token sets; derive overlaps from set algebra, not names.
- Allow early commit when exactly one non-error outcome remains; never roll back after commit.
- Treat constructors as failure-local by default: local allocation, UUID creation, and mutation of owned parse results are allowed; external effects are not.
- Preserve semantic action order and execute each action exactly once.
- Do not move semantic actions across token consumption.
- Generate direct BSL; no runtime DAG objects, transition interpreter, or helper function per decision node.
- Preserve source/provenance diagnostics when runtime function boundaries disappear.
- Force repository imports for every parsergen command:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
$env:PYTHONIOENCODING='utf-8'
python -c "import parsergen; print(parsergen.__file__)"
```

The printed path must be inside this repository.

## File Structure

- Create `tools/parsergen/src/parsergen/canonical_select.py`: public immutable symbolic SELECT language, exact token-set edges, factor-graph adapter, language intersection, and call-site specialization.
- Create `tools/parsergen/src/parsergen/decision_dag.py`: immutable DAG nodes, early-commit builder, validator, evaluator, and statistics.
- Create `tools/parsergen/src/parsergen/canonical_bsl_decisions.py`: direct structured BSL renderer and exact token-set predicate emitter using cached lookahead variables.
- Create `tools/parsergen/src/parsergen/parser_ir_optimization.py`: semantic-transparency proof, caller/callee specialization, forwarding collapse, call graph, and reachability cleanup.
- Modify `tools/parsergen/src/parsergen/analysis.py`: expose only the minimal factor-state adapter needed by `canonical_select.py`; keep legacy matcher materialization APIs intact for legacy artifacts.
- Modify `tools/parsergen/src/parsergen/parser_ir.py`: replace row-backed decisions with symbolic source + DAG and use outcome identities rather than local alternative integers.
- Modify `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`: render every production/group/optional/repeat/LeftFold decision through the new renderer.
- Delete `tools/parsergen/src/parsergen/canonical_bsl_conditions.py` after all consumers migrate.
- Modify `tools/parsergen/src/parsergen/cli.py`: pass actual entrypoint productions to Parser IR optimization.
- Modify `tools/parsergen/benchmarks/audit_migration.py`: durable static DAG/generated-BSL metrics.
- Create focused tests: `test_canonical_select.py`, `test_decision_dag.py`, `test_decision_dag_property.py`, `test_canonical_bsl_decisions.py`, and `test_parser_ir_optimization.py`.
- Update existing Parser IR, canonical BSL, EBNF, LeftFold, repository grammar, reference artifact, migration audit, and architecture tests/docs.

---

### Task 1: Freeze the pre-DAG static baseline in the migration audit

**Files:**
- Modify: `tools/parsergen/benchmarks/audit_migration.py`
- Modify: `tools/parsergen/tests/test_migration_audit.py`

**Interfaces:**
- Produces: `generated_bsl_metrics(module_text: str) -> dict[str, int]`.
- Produces durable keys under `report["generated"]`: `lookahead_calls`, `decision_lines`, `predicate_atoms`, `nonterminal_functions`, `nonterminal_call_sites`, `max_condition_chars`, `max_condition_predicate_atoms`, `max_condition_lookahead_calls`, and `max_condition_nesting`.

- [ ] **Step 1: Write the failing unit test for deterministic static metrics**

```python
def test_generated_bsl_metrics_count_decisions_and_lookahead_atoms(self) -> None:
    module = (
        'Функция НеТерминалS()\n'
        'Если ТипТокенаПросмотра(0) = "A" Или '
        'ТипТокенаПросмотра(1) = "B" Тогда\n'
        'КонецЕсли;\n'
        'КонецФункции\n'
    )
    self.assertEqual(
        audit_migration.generated_bsl_metrics(module),
        {
            "lookahead_calls": 2,
            "decision_lines": 1,
            "predicate_atoms": 2,
            "nonterminal_functions": 1,
            "nonterminal_call_sites": 0,
            "max_condition_chars": 70,
            "max_condition_predicate_atoms": 2,
            "max_condition_lookahead_calls": 2,
            "max_condition_nesting": 1,
        },
    )
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_migration_audit.py -k generated_bsl_metrics -v
```

Expected: FAIL because `generated_bsl_metrics` does not exist.

- [ ] **Step 3: Implement the metric scanner and merge it into the report**

```python
DECISION_LINE = re.compile(r"^\s*(?:Если|ИначеЕсли|Пока)\b", re.IGNORECASE)
NONTERMINAL_FUNCTION = re.compile(
    r"^\s*Функция\s+НеТерминал", re.IGNORECASE
)
NONTERMINAL_REFERENCE = re.compile(
    r"\bНеТерминал[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*\s*\(",
    re.IGNORECASE,
)
PREDICATE_ATOM = re.compile(
    r"(?:ТипТокенаПросмотра\(\d+\)|ТокенРешения\d+)\s*(?:=|<>)",
    re.IGNORECASE,
)


def _parenthesis_depth(value: str) -> int:
    depth = 0
    maximum = 0
    for char in value:
        if char == "(":
            depth += 1
            maximum = max(maximum, depth)
        elif char == ")":
            depth = max(0, depth - 1)
    return maximum


def generated_bsl_metrics(module_text: str) -> dict[str, int]:
    lines = module_text.splitlines()
    decisions = [line.strip() for line in lines if DECISION_LINE.match(line)]
    return {
        "lookahead_calls": module_text.count("ТипТокенаПросмотра("),
        "decision_lines": len(decisions),
        "predicate_atoms": sum(
            len(PREDICATE_ATOM.findall(line)) for line in decisions
        ),
        "nonterminal_functions": sum(
            NONTERMINAL_FUNCTION.match(line) is not None for line in lines
        ),
        "nonterminal_call_sites": max(
            0,
            len(NONTERMINAL_REFERENCE.findall(module_text))
            - sum(NONTERMINAL_FUNCTION.match(line) is not None for line in lines),
        ),
        "max_condition_chars": max(map(len, decisions), default=0),
        "max_condition_predicate_atoms": max(
            (len(PREDICATE_ATOM.findall(line)) for line in decisions),
            default=0,
        ),
        "max_condition_lookahead_calls": max(
            (line.count("ТипТокенаПросмотра(") for line in decisions),
            default=0,
        ),
        "max_condition_nesting": max(
            (_parenthesis_depth(line) for line in decisions),
            default=0,
        ),
}
```

Use the scanner on `generated.module_text` and spread its keys into the existing `generated` report section.

- [ ] **Step 4: Update the production baseline assertion and run the audit tests**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_migration_audit.py -v
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml > docs/superpowers/matrices/2026-08-08-decision-dag-static-before.json
```

Expected: PASS; JSON contains the current pre-DAG values, including 66 nonterminal functions and 1,983 textual lookahead calls.

- [ ] **Step 5: Commit the baseline audit**

```powershell
git add tools/parsergen/benchmarks/audit_migration.py tools/parsergen/tests/test_migration_audit.py docs/superpowers/matrices/2026-08-08-decision-dag-static-before.json
git commit -m "Зафиксировать static baseline Decision DAG"
```

### Task 2: Export factorized canonical SELECT as symbolic token-set languages

**Files:**
- Create: `tools/parsergen/src/parsergen/canonical_select.py`
- Create: `tools/parsergen/tests/test_canonical_select.py`
- Modify: `tools/parsergen/src/parsergen/analysis.py`

**Interfaces:**
- Produces: `AlternativeOutcome(production: str, alternative: int)`.
- Produces: `ExitOutcome(production: str, alternative: int)`.
- Produces: `TokenSetPredicate(token_types: tuple[str, ...])` with sorted, non-empty, unique token types.
- Produces: `SymbolicLanguage(root: int, nodes: tuple[SymbolicLanguageNode, ...])`.
- Produces: `CanonicalDecisionSource(production: str, lookahead: int, languages: tuple[OutcomeLanguage, ...])`.
- Produces: `build_canonical_decision_source(analysis, production, *, exit_alternative=None) -> CanonicalDecisionSource`.
- Produces: `canonical_matcher_definitions(analysis) -> tuple[MatcherDefinition, ...]` without row materialization.

- [ ] **Step 1: Write failing tests for exact sets, provenance-neutral equality, EOF, and no public row expansion**

```python
def _analysis(source: str, k: int = 1) -> AnalysisResult:
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.grammar is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.grammar is not None
    return compute_analysis(resolved.grammar, k, ("S",))


def _accepts(
    source: CanonicalDecisionSource,
    outcome: CanonicalOutcome,
    word: tuple[str, ...],
) -> bool:
    language = next(
        item.language for item in source.languages if item.outcome == outcome
    )
    states = {language.root}
    for token in word:
        states = {
            edge.target
            for state in states
            for edge in language.nodes[state].edges
            if token in edge.predicate.token_types
        }
    return any(language.nodes[state].accepting for state in states)


def test_source_keeps_identifier_matcher_as_exact_token_set(self) -> None:
    analysis = _analysis("#ID_X ::= ID | ГДЕ\n<S> ::= #ID_X | END", k=1)
    with patch(
        "parsergen.analysis.build_canonical_decision_artifact",
        side_effect=AssertionError("row materialization is forbidden"),
    ):
        source = build_canonical_decision_source(analysis, "S")
    predicates = {
        edge.predicate.token_types
        for language in source.languages
        for node in language.language.nodes
        for edge in node.edges
    }
    self.assertIn(("ID", "ГДЕ"), predicates)


def test_short_select_continues_through_follow_and_preserves_end(self) -> None:
    analysis = _analysis("<S> ::= <A>\n<A> ::= X | ПУСТО", k=2)
    source = build_canonical_decision_source(analysis, "A")
    self.assertTrue(_accepts(source, AlternativeOutcome("A", 2), ("$",)))
```

- [ ] **Step 2: Run the focused tests and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_select.py -v
```

Expected: collection/import failure because `canonical_select.py` does not exist.

- [ ] **Step 3: Add immutable symbolic language types and the compressed-analysis adapter**

```python
@dataclass(frozen=True, slots=True)
class TokenSetPredicate:
    token_types: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.token_types or tuple(sorted(set(self.token_types))) != self.token_types:
            raise ValueError("token predicate must be sorted, unique, and non-empty")


@dataclass(frozen=True, slots=True)
class SymbolicLanguageEdge:
    predicate: TokenSetPredicate
    target: int


@dataclass(frozen=True, slots=True)
class SymbolicLanguageNode:
    accepting: bool
    edges: tuple[SymbolicLanguageEdge, ...]


@dataclass(frozen=True, slots=True)
class SymbolicLanguage:
    root: int
    nodes: tuple[SymbolicLanguageNode, ...]


@dataclass(frozen=True, slots=True)
class AlternativeOutcome:
    production: str
    alternative: int


@dataclass(frozen=True, slots=True)
class ExitOutcome:
    production: str
    alternative: int


CanonicalOutcome = AlternativeOutcome | ExitOutcome


@dataclass(frozen=True, slots=True)
class OutcomeLanguage:
    outcome: CanonicalOutcome
    language: SymbolicLanguage


@dataclass(frozen=True, slots=True)
class CanonicalDecisionSource:
    production: str
    lookahead: int
    languages: tuple[OutcomeLanguage, ...]
```

Add narrowly named `_CompressedAnalysis` adapter methods for descriptor root, terminal test, children, and matcher token types. Traverse reachable `(factor_state, depth)` pairs only to depth `k`; do not call `iter_matcher_rows` or public SELECT mappings.

- [ ] **Step 4: Implement source construction and matcher definitions without decision rows**

```python
def build_canonical_decision_source(
    analysis: AnalysisResult,
    production: str,
    *,
    exit_alternative: int | None = None,
) -> CanonicalDecisionSource:
    compressed = _require_compressed(analysis)
    positions = compressed.select_positions(production)
    languages = tuple(
        OutcomeLanguage(
            ExitOutcome(production, alternative)
            if alternative == exit_alternative
            else AlternativeOutcome(production, alternative),
            _export_language(compressed, position),
        )
        for position, alternative in positions
    )
    return CanonicalDecisionSource(production, analysis.k, languages)
```

Validate that `exit_alternative`, when supplied, exists exactly once. Preserve `END == "$"` as its own token predicate.

- [ ] **Step 5: Run SELECT/conflict regressions and commit**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_select.py tools/parsergen/tests/test_follow_select.py -v
git add tools/parsergen/src/parsergen/analysis.py tools/parsergen/src/parsergen/canonical_select.py tools/parsergen/tests/test_canonical_select.py
git commit -m "Экспортировать factorized canonical SELECT"
```

Expected: PASS; existing canonical/legacy separation remains unchanged.

### Task 3: Build and evaluate the validated early-commit Decision DAG

**Files:**
- Create: `tools/parsergen/src/parsergen/decision_dag.py`
- Create: `tools/parsergen/tests/test_decision_dag.py`

**Interfaces:**
- Produces immutable `CommitAlternative`, `ExitDecision`, `ImmediateError`, `LookaheadDecision`, `DecisionEdge`, and `CanonicalDecisionDag`.
- Produces: `build_decision_dag(source: CanonicalDecisionSource) -> CanonicalDecisionDag`.
- Produces: `evaluate_decision(dag: CanonicalDecisionDag, lookahead: tuple[str, ...]) -> DecisionLeaf`.
- Produces: `validate_decision_dag(source, dag) -> None`.
- Produces statistics: `source_states`, `dag_states`, `shared_states`, `max_depth`.

- [ ] **Step 1: Write failing examples for common prefix, early commit, explicit exit, and immediate error**

```python
from tests.test_canonical_select import _analysis


def _source(grammar: str, k: int = 1) -> CanonicalDecisionSource:
    return build_canonical_decision_source(_analysis(grammar, k), "S")


def test_reads_second_token_only_for_shared_first_prefix(self) -> None:
    source = _source("<S> ::= A X | A Y | B Z", k=2)
    dag = build_decision_dag(source)
    self.assertEqual(evaluate_decision(dag, ("B",)), CommitAlternative(AlternativeOutcome("S", 3)))
    self.assertEqual(evaluate_decision(dag, ("A", "X")), CommitAlternative(AlternativeOutcome("S", 1)))
    self.assertEqual(dag.nodes[dag.root].offset, 0)


def test_single_viable_alternative_commits_before_invalid_suffix(self) -> None:
    dag = build_decision_dag(_source("<S> ::= A X | B Y", k=2))
    self.assertEqual(evaluate_decision(dag, ("A", "WRONG")), CommitAlternative(AlternativeOutcome("S", 1)))


def test_exit_and_immediate_error_are_distinct_leaves(self) -> None:
    source = build_canonical_decision_source(
        _analysis("<S> ::= A | ПУСТО", k=1),
        "S",
        exit_alternative=2,
    )
    dag = build_decision_dag(source)
    self.assertEqual(
        evaluate_decision(dag, ("$",)),
        ExitDecision(ExitOutcome("S", 2)),
    )
    self.assertIsInstance(evaluate_decision(dag, ("WRONG",)), ImmediateError)
```

- [ ] **Step 2: Run the focused tests and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_decision_dag.py -v
```

Expected: import failure because `decision_dag.py` does not exist.

- [ ] **Step 3: Implement exact derivatives and viability**

Use a determinized residual per outcome (`frozenset[int]` of symbolic NFA nodes). For a concrete token, union every target whose predicate contains that token. A residual is viable if an accepting node is reachable within the remaining depth. Cache viability by `(language_identity, residual, remaining)`.

```python
@dataclass(frozen=True, slots=True)
class CommitAlternative:
    outcome: AlternativeOutcome


@dataclass(frozen=True, slots=True)
class ExitDecision:
    outcome: ExitOutcome


@dataclass(frozen=True, slots=True)
class ImmediateError:
    expected: tuple[str, ...]


DecisionLeaf = CommitAlternative | ExitDecision | ImmediateError


@dataclass(frozen=True, slots=True)
class DecisionEdge:
    predicate: TokenSetPredicate
    target: int


@dataclass(frozen=True, slots=True)
class LookaheadDecision:
    offset: int
    expected: tuple[str, ...]
    edges: tuple[DecisionEdge, ...]


DecisionNode = DecisionLeaf | LookaheadDecision


@dataclass(frozen=True, slots=True)
class CanonicalDecisionDag:
    production: str
    lookahead: int
    root: int
    nodes: tuple[DecisionNode, ...]
    stats: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class _BuildState:
    offset: int
    remaining: int
    residuals: tuple[tuple[CanonicalOutcome, frozenset[int]], ...]


def _viable_outcomes(state: _BuildState) -> tuple[CanonicalOutcome, ...]:
    return tuple(
        outcome
        for outcome, residual in state.residuals
        if _can_accept(residual, state.remaining)
    )
```

Stop immediately on singleton viability. For multiple outcomes, enumerate only the union of token types on outgoing symbolic edges, group concrete tokens by identical successor signature, and recurse. Missing tokens become `ImmediateError` at evaluation time; do not create a universe-wide complement set.

- [ ] **Step 4: Add hash-consing, EOF termination, and validation**

Canonicalize state keys as `(offset, remaining, sorted outcome/residual pairs)`. On token `$`, require an accepting derivative and do not inspect a deeper offset. Raise `ValueError("canonical decision remains ambiguous at lookahead limit")` if distinct outcomes survive at depth `k`.

- [ ] **Step 5: Run tests and commit**

```powershell
python -m pytest tools/parsergen/tests/test_decision_dag.py tools/parsergen/tests/test_canonical_select.py -v
git add tools/parsergen/src/parsergen/decision_dag.py tools/parsergen/tests/test_decision_dag.py
git commit -m "Построить canonical Decision DAG"
```

### Task 4: Add an independent materialized oracle/property suite

**Files:**
- Create: `tools/parsergen/tests/test_decision_dag_property.py`

**Interfaces:**
- Consumes: `build_canonical_decision_source`, `build_decision_dag`, and `evaluate_decision`.
- Produces: deterministic exhaustive/property coverage for `k = 1..3` without production materialization.

- [ ] **Step 1: Write the finite-universe oracle**

```python
def _oracle(
    materialized_select: dict[CanonicalOutcome, frozenset[tuple[str, ...]]],
    word: tuple[str, ...],
) -> CanonicalOutcome | None:
    matches = tuple(
        outcome for outcome, words in materialized_select.items() if word in words
    )
    assert len(matches) <= 1
    return matches[0] if matches else None
```

Generate 200 deterministic small grammars/decision sets from `random.Random(0xDAD2026)`, finite alphabets containing literals, `$`, and overlapping `#ID_*` sets.

- [ ] **Step 2: Assert exact outcomes for every canonical word**

For each materialized SELECT word, assert the DAG returns the matching `CommitAlternative` or `ExitDecision`.

- [ ] **Step 3: Assert safe behavior outside SELECT**

For every noncanonical word in the finite product, accept only `ImmediateError` or early commit to the sole prefix-viable alternative. Explicitly reject a different alternative and every incorrect `ExitDecision`.

- [ ] **Step 4: Run the property suite across hash seeds**

```powershell
$env:PYTHONHASHSEED='1'; python -m pytest tools/parsergen/tests/test_decision_dag_property.py -q
$env:PYTHONHASHSEED='777'; python -m pytest tools/parsergen/tests/test_decision_dag_property.py -q
Remove-Item Env:PYTHONHASHSEED
```

Expected: both runs PASS with identical serialized DAG shapes.

- [ ] **Step 5: Commit the oracle suite**

```powershell
git add tools/parsergen/tests/test_decision_dag_property.py
git commit -m "Добавить oracle-тесты Decision DAG"
```

### Task 5: Replace row-backed Parser IR decisions with outcome-bound DAGs

**Files:**
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/src/parsergen/cli.py`
- Modify: `tools/parsergen/tests/test_parser_ir.py`

**Interfaces:**
- `CanonicalDecision` becomes `{source: CanonicalDecisionSource, dag: CanonicalDecisionDag}`.
- `BranchIr` and `ValueBranchIr` consume `AlternativeOutcome`, not a bare integer.
- `ParserIr` adds `entrypoint_productions: frozenset[str]`.
- `build_parser_ir(..., entrypoint_productions: Collection[str] | None = None)` defaults to treating selected productions as protected entrypoints; CLI passes `config.entrypoints.values()` explicitly.

- [ ] **Step 1: Replace row-shape assertions with DAG/outcome assertions**

```python
def test_canonical_decision_is_symbolic_and_does_not_materialize_rows(self) -> None:
    with patch(
        "parsergen.parser_ir.build_canonical_decision_artifact",
        side_effect=AssertionError("rows are forbidden"),
        create=True,
    ):
        parser_ir = _build("#ID_A ::= ID | WORD\n<S> ::= #ID_A?")
    optional = parser_ir.productions[0].alternatives[0].operations[0]
    self.assertIsInstance(optional, OptionalBranch)
    self.assertIsInstance(optional.decision.dag.nodes[optional.decision.dag.root], LookaheadDecision)
    self.assertTrue(any(isinstance(node, ExitDecision) for node in optional.decision.dag.nodes))
```

- [ ] **Step 2: Run Parser IR tests and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_parser_ir.py -v
```

Expected: FAIL because `CanonicalDecision` still contains rows.

- [ ] **Step 3: Introduce outcome identities throughout branches**

```python
@dataclass(frozen=True, slots=True)
class CanonicalDecision:
    source: CanonicalDecisionSource
    dag: CanonicalDecisionDag


@dataclass(frozen=True, slots=True)
class BranchIr:
    outcome: AlternativeOutcome
    operations: tuple[Operation, ...]
    result_index: int | None
    source_span: SourceSpan
```

Pass the decision production into `_branch_ir`, `_primary_branches`, `_group_branches`, and left-fold branch builders so each outcome retains its true lowered production and alternative.

- [ ] **Step 4: Build and cache decisions without `build_canonical_decision_artifact`**

Store `analysis` in `_ParserIrBuilder` and cache by `(production, exit_alternative)`. For Optional/Repeat/WrapOptional/LeftFold-tail pass the exact epsilon alternative as `exit_alternative`; for normal dispatch pass `None`. Obtain matcher definitions through `canonical_matcher_definitions(analysis)`.

- [ ] **Step 5: Run Parser IR and CLI tests, then commit**

```powershell
python -m pytest tools/parsergen/tests/test_parser_ir.py tools/parsergen/tests/test_cli.py -v
git add tools/parsergen/src/parsergen/parser_ir.py tools/parsergen/src/parsergen/cli.py tools/parsergen/tests/test_parser_ir.py
git commit -m "Перевести Parser IR на Decision DAG"
```

### Task 6: Emit direct structured BSL from one DAG

**Files:**
- Create: `tools/parsergen/src/parsergen/canonical_bsl_decisions.py`
- Create: `tools/parsergen/tests/test_canonical_bsl_decisions.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`

**Interfaces:**
- Produces `CanonicalDecisionRenderer(matcher_definitions)`.
- Produces `render(decision, *, indent, token_prefix, render_leaf) -> list[str]`.
- `render_leaf(leaf: DecisionLeaf, indent: str) -> list[str]` supplies Parser IR actions.
- Token variables are `ТокенРешения0`, `ТокенРешения1`, ... and predicates never call `ТипТокенаПросмотра`.

- [ ] **Step 1: Write failing renderer shape tests**

```python
from tests.test_parser_ir import _build as _build_ir


def _render(grammar: str, k: int = 1) -> list[str]:
    parser_ir = _build_ir(grammar, k)
    production = next(item for item in parser_ir.productions if item.name == "S")
    assert production.decision is not None
    renderer = CanonicalDecisionRenderer(parser_ir.matcher_definitions)
    return renderer.render(
        production.decision,
        indent="",
        token_prefix="ТокенРешения",
        render_leaf=lambda leaf, indent: [
            f"{indent}// {type(leaf).__name__}"
        ],
    )


def test_renderer_caches_first_token_and_nests_second_lookup(self) -> None:
    rendered = "\n".join(_render("<S> ::= A X | A Y | B Z", k=2))
    self.assertEqual(rendered.count("ТокенРешения0 = ТипТокенаПросмотра(0);"), 1)
    self.assertEqual(rendered.count("ТипТокенаПросмотра(1)"), 1)
    self.assertLess(rendered.index('ТокенРешения0 = "A"'), rendered.index("ТипТокенаПросмотра(1)"))
    self.assertNotIn("DecisionNode", rendered)
```

- [ ] **Step 2: Run the renderer tests and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_decisions.py -v
```

Expected: import failure because the renderer does not exist.

- [ ] **Step 3: Implement exact token-set predicate emission**

```python
def _predicate(variable: str, token_types: tuple[str, ...]) -> str:
    comparisons = tuple(
        f"{variable} = Неопределено"
        if token == END
        else f"{variable} = {bsl_string(token)}"
        for token in token_types
    )
    return comparisons[0] if len(comparisons) == 1 else f"({' Или '.join(comparisons)})"
```

First implement deterministic inline emission. Add a reverse exact-set index over matcher definitions, but keep reusable large-set helpers disabled until Task 12 benchmarks establish a profitable threshold.

- [ ] **Step 4: Implement recursive structured rendering**

Emit the assignment once at each executed offset, `Если/ИначеЕсли` for edges, and an `Иначе` leaf containing `ImmediateError(expected=current.expected)`. Group edges with the same target before emission. Add `ТокенРешения[0-9]+` to generated-local collision validation.

- [ ] **Step 5: Run renderer/codegen validation tests and commit**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_decisions.py tools/parsergen/tests/test_canonical_bsl_codegen.py -v
git add tools/parsergen/src/parsergen/canonical_bsl_decisions.py tools/parsergen/src/parsergen/canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_decisions.py
git commit -m "Генерировать прямой BSL из Decision DAG"
```

### Task 7: Route production, group, and value dispatch through the DAG renderer

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_canonical_bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_canonical_bsl_bindings.py`

**Interfaces:**
- Consumes outcome-bound `BranchIr`/`ValueBranchIr` and `CanonicalDecisionRenderer`.
- Produces one shared decision region per production/group/value dispatch and a common result join.

- [ ] **Step 1: Tighten codegen tests around one shared prefix and early commit**

Add assertions for:

```python
self.assertEqual(function.count("ТипТокенаПросмотра(0)"), 1)
self.assertEqual(function.count("ТипТокенаПросмотра(1)"), 1)
self.assertIn('ТокенРешения0 = "A"', function)
self.assertNotIn('ТипТокенаПросмотра(1) = "X"', early_commit_function)
```

Use grammars `A X | A Y | B Z` and `A X | B Y` separately.

- [ ] **Step 2: Run the focused tests and verify RED against per-alternative conditions**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_bindings.py -v
```

Expected: shape assertions FAIL because current code renders one condition per alternative.

- [ ] **Step 3: Replace production dispatch rendering**

Build `branches_by_outcome = {branch.outcome: branch}` and pass a closure to the renderer. `CommitAlternative` renders exactly one `_render_alternative`; `ImmediateError` uses `_syntax_error_line`. Store a common branch result temporary after each leaf and return it after the generated `КонецЕсли` join.

- [ ] **Step 4: Replace nested `Dispatch` and `DispatchValue` rendering**

Use the same outcome map and leaf callback. Preserve `required_result_index`, constructor ownership, and the single shared result temporary. Do not duplicate common continuation operations after the decision.

- [ ] **Step 5: Run focused tests and commit**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_bindings.py tools/parsergen/tests/test_canonical_bsl_decisions.py -v
git add tools/parsergen/src/parsergen/canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_bindings.py
git commit -m "Факторизовать canonical dispatch в BSL"
```

### Task 8: Give Optional and Repeat explicit body/exit/error DAG semantics

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/tests/test_canonical_bsl_ebnf.py`
- Modify: `tools/parsergen/tests/test_parser_ir.py`

**Interfaces:**
- Remove redundant `exit_alternative` integer fields after tests prove `ExitDecision` is present in each decision DAG.
- Optional leaf behavior: body actions, exit operations/undefined result, or syntax error.
- Repeat leaf behavior: iteration actions, `Прервать`, or syntax error inside `Пока Истина`.

- [ ] **Step 1: Replace legacy fallback tests with explicit exit/error shape tests**

```python
def test_star_uses_one_explicit_iteration_exit_error_decision(self) -> None:
    function = _function(_build("<S> ::= ITEM* END").module_text, "НеТерминалS")
    self.assertIn("Пока Истина Цикл", function)
    self.assertIn("Прервать;", function)
    self.assertIn("ВызватьИсключениеСинтаксическаяОшибка", function)
    self.assertEqual(function.count("ТипТокенаПросмотра(0)"), 1)


def test_optional_rejects_token_outside_body_and_canonical_exit(self) -> None:
    function = _function(_build("<S> ::= HEAD? END").module_text, "НеТерминалS")
    self.assertIn('ТокенРешения0 = "HEAD"', function)
    self.assertIn('ТокенРешения0 = "END"', function)
    self.assertIn("ВызватьИсключениеСинтаксическаяОшибка", function)
```

- [ ] **Step 2: Run EBNF tests and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_ebnf.py -v
```

Expected: FAIL because repeat uses a consume-condition guard and optional uses implicit `Иначе` exit.

- [ ] **Step 3: Render Optional through the leaf callback**

Map `CommitAlternative` to the exact body branch, `ExitDecision` to `exit_operations` plus `Неопределено` result where required, and `ImmediateError` to syntax error. Preserve WrapOptional accumulator semantics with the same three leaf kinds.

- [ ] **Step 4: Render Repeat as one infinite loop with one DAG per iteration**

```bsl
Пока Истина Цикл
	ТокенРешения0 = ТипТокенаПросмотра(0);
	Если ... Тогда
		// iteration
	ИначеЕсли ... Тогда
		Прервать;
	Иначе
		// syntax error
	КонецЕсли;
КонецЦикла;
```

For `+`, keep the required first body parse before this loop. Then remove redundant `exit_alternative` fields from IR dataclasses and constructors.

- [ ] **Step 5: Run EBNF/IR regressions and commit**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_ebnf.py tools/parsergen/tests/test_parser_ir.py -v
git add tools/parsergen/src/parsergen/canonical_bsl_codegen.py tools/parsergen/src/parsergen/parser_ir.py tools/parsergen/tests/test_canonical_bsl_ebnf.py tools/parsergen/tests/test_parser_ir.py
git commit -m "Сделать EBNF exit частью canonical DAG"
```

### Task 9: Route LeftFold through the same loop DAG and retire row conditions

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_canonical_bsl_left_fold.py`
- Delete: `tools/parsergen/src/parsergen/canonical_bsl_conditions.py`
- Delete: `tools/parsergen/tests/test_canonical_bsl_conditions.py`

**Interfaces:**
- LeftFold base dispatch uses its base DAG.
- Recursive loop uses `suffix | exit | error` leaves and preserves accumulator action order.
- No production import or call remains to `CanonicalConditionRenderer`.

- [ ] **Step 1: Add explicit recursive exit/error and action-order assertions**

```python
self.assertIn("Пока Истина Цикл", function)
self.assertIn("Прервать;", function)
self.assertEqual(function.count("ТипТокенаПросмотра(0)"), 1)
self.assertLess(constructor, left_binding)
self.assertLess(left_binding, operator_parse)
self.assertLess(operator_parse, right_parse)
self.assertLess(right_parse, replace_accumulator)
```

- [ ] **Step 2: Run LeftFold tests and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_left_fold.py -v
```

Expected: FAIL because the recursive loop still uses a separate guard and inner dispatch.

- [ ] **Step 3: Render base and recursive decisions with the DAG renderer**

Keep base accumulator initialization outside the loop. Push the accumulator name before rendering a committed recursive branch; pop it immediately afterwards. Map `ExitDecision` only to `Прервать`, never to a fallback branch.

- [ ] **Step 4: Delete the obsolete row-condition renderer and migrate imports/tests**

```powershell
rg -n "CanonicalConditionRenderer|canonical_bsl_conditions|for_alternative_with_unique_first" tools/parsergen
```

Expected after edits: no matches.

- [ ] **Step 5: Run all canonical codegen tests and commit**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_bindings.py tools/parsergen/tests/test_canonical_bsl_ebnf.py tools/parsergen/tests/test_canonical_bsl_left_fold.py tools/parsergen/tests/test_canonical_bsl_decisions.py -v
git add -A tools/parsergen/src/parsergen/canonical_bsl_conditions.py tools/parsergen/tests/test_canonical_bsl_conditions.py tools/parsergen/src/parsergen/canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_left_fold.py
git commit -m "Перевести LeftFold на общий Decision DAG"
```

### Task 10: Prove semantic transparency and preserve action traces

**Files:**
- Create: `tools/parsergen/src/parsergen/parser_ir_optimization.py`
- Create: `tools/parsergen/tests/test_parser_ir_optimization.py`

**Interfaces:**
- Produces `TransparencyResult(transparent: bool, reason: str)`.
- Produces `classify_semantic_transparency(production, *, entrypoints, recursive_productions) -> TransparencyResult`.
- Produces `optimize_parser_ir(parser_ir: ParserIr) -> ParserIr`.
- Constructors are failure-local by default; `ConstructNode` still makes a wrapper semantic and therefore not transparent.

Add the exact result type before implementing the classifier:

```python
@dataclass(frozen=True, slots=True)
class TransparencyResult:
    transparent: bool
    reason: str
```

- [ ] **Step 1: Write table-driven transparency tests**

```python
def test_transparency_is_structural_not_name_based(self) -> None:
    cases = (
        ("forward", "<S> ::= <Wrapper>\n<Wrapper> ::= <A>\n<A> ::= ITEM", True),
        ("constructor", "<S> ::= <Wrapper>\n<Wrapper> ::= @НовыйУзел <A>\n<A> ::= ITEM", False),
        ("binding", "<S> ::= <Wrapper>\n<Wrapper> ::= @НовыйУзел Значение = <A>\n<A> ::= ITEM", False),
    )
    for name, grammar, expected in cases:
        with self.subTest(name=name):
            parser_ir = _build(grammar)
            wrapper = next(
                item for item in parser_ir.productions if item.name == "Wrapper"
            )
            result = classify_semantic_transparency(
                wrapper,
                entrypoints=frozenset({"S"}),
                recursive_productions=frozenset(),
            )
            self.assertEqual(result.transparent, expected)
```

Add separate cases for public entrypoints, recursive SCCs, LeftFold, `ReturnConstant`, source boundaries, and syntax-only wrappers.

- [ ] **Step 2: Run the optimizer tests and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_parser_ir_optimization.py -v
```

Expected: import failure because the optimizer does not exist.

- [ ] **Step 3: Implement recursive operation inspection and call-graph SCCs**

Walk nested `Dispatch`, `OptionalBranch`, `RepeatLoop`, `WrapOptional`, `WrapValue`, `DispatchValue`, and `LeftFold`. Mark constructors, bindings, collection/scalar mutations, constants, wrappers, and folds semantic. A transparent successful path must expose exactly one unchanged child result or be uniformly syntax-only.

- [ ] **Step 4: Add a test-only action trace evaluator and compare before/after**

The evaluator records tuples such as `("construct", name)`, `("parse", symbol)`, `("bind", property)`, and `("fold-update", production)`. Assert identical successful traces and exactly-once behavior for semantic operations. For failure cases assert no alternative/exit rollback and no returned partial result.

- [ ] **Step 5: Run tests and commit**

```powershell
python -m pytest tools/parsergen/tests/test_parser_ir_optimization.py tools/parsergen/tests/test_parser_ir.py -v
git add tools/parsergen/src/parsergen/parser_ir_optimization.py tools/parsergen/tests/test_parser_ir_optimization.py
git commit -m "Доказать semantic transparency Parser IR"
```

### Task 11: Compose caller/callee decisions and remove unreachable runtime functions

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_select.py`
- Modify: `tools/parsergen/src/parsergen/decision_dag.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir_optimization.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/tests/test_parser_ir_optimization.py`
- Modify: `tools/parsergen/tests/test_repository_grammar.py`

**Interfaces:**
- Produces `intersect_languages(left, right) -> SymbolicLanguage`.
- Produces `specialize_outcome(source, outcome, callee) -> CanonicalDecisionSource`.
- `build_parser_ir` invokes `optimize_parser_ir` after initial IR construction.
- Initial specialization supports a direct, parameter-free callee call before any caller token consumption or semantic action; unsupported calls remain unchanged.

- [ ] **Step 1: Write a focused semantic-callee specialization test**

```python
def test_optional_semantic_callee_is_selected_once_and_actions_are_preserved(self) -> None:
    generated = _build(
        "<S> ::= <Base> Child => <Choice>?\n"
        "<Base> ::= @НовыйBase BASE\n"
        "<Choice> ::= @НовыйA A X | @НовыйB B Y"
    )
    function = _function(generated.module_text, "НеТерминалS")
    self.assertNotIn("НеТерминалChoice()", function)
    self.assertEqual(function.count("ТипТокенаПросмотра(0)"), 1)
    self.assertEqual(function.count("НовыйA"), 1)
    self.assertEqual(function.count("НовыйB"), 1)
    self.assertEqual(function.count(".Child = "), 1)
```

- [ ] **Step 2: Write the production logical-operator shape assertion and verify RED**

Locate `НеТерминалЛогическийМножитель` in generated repository BSL and assert it does not call `НеТерминалЛогическийОператор`, contains one decision region, and preserves the four operator constructors/bindings. Assert the standalone callee function disappears only if the optimized call graph has no remaining references.

- [ ] **Step 3: Implement symbolic call-site intersection**

For each callee outcome, intersect its language with the caller outcome language. Retain caller exit and unrelated outcomes unchanged. Drop empty intersections. Build and validate a fresh DAG from the specialized source; never compose already early-committed DAG leaves because they have intentionally discarded residual detail.

- [ ] **Step 4: Implement safe IR substitution and reachability cleanup**

Eligibility requires a branch whose operations are exactly one parameter-free `ParseSymbol(NonterminalCall)` before caller-specific actions. Replace it with callee branches, preserving each callee `AlternativeOutcome`, operations, result index, and source span. Keep caller continuation in its existing join. Collapse chains of transparent single-child forwarding calls. Recompute references recursively and remove only non-entrypoint productions with zero remaining references.

- [ ] **Step 5: Run focused and repository tests, then commit**

```powershell
python -m pytest tools/parsergen/tests/test_parser_ir_optimization.py tools/parsergen/tests/test_repository_grammar.py -k "logical or transparent or decision" -v
git add tools/parsergen/src/parsergen/canonical_select.py tools/parsergen/src/parsergen/decision_dag.py tools/parsergen/src/parsergen/parser_ir_optimization.py tools/parsergen/src/parsergen/parser_ir.py tools/parsergen/tests/test_parser_ir_optimization.py tools/parsergen/tests/test_repository_grammar.py
git commit -m "Схлопнуть повторные caller callee decisions"
```

### Task 12: Add DAG/static metrics and choose predicate emission by measured cost

**Files:**
- Modify: `tools/parsergen/src/parsergen/decision_dag.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_decisions.py`
- Modify: `tools/parsergen/benchmarks/audit_migration.py`
- Modify: `tools/parsergen/tests/test_migration_audit.py`
- Modify: `tools/parsergen/tests/test_canonical_bsl_decisions.py`

**Interfaces:**
- Audit adds `decision_dag` section with `source_states`, `dag_states`, `shared_states`, `max_depth`, `decision_regions`, and `emitted_predicates`.
- Predicate policy remains exact and deterministic; candidate policies are inline exact sets versus reusable named-set predicates accepting a cached token value.

- [ ] **Step 1: Write failing audit assertions for DAG statistics**

```python
self.assertEqual(
    set(report["decision_dag"]),
    {
        "source_states",
        "dag_states",
        "shared_states",
        "max_depth",
        "decision_regions",
        "emitted_predicates",
    },
)
self.assertEqual(report["canonical"]["stats"]["public_select_expansions"], 0)
self.assertEqual(report["canonical"]["stats"]["select_cartesian_materializations"], 0)
```

- [ ] **Step 2: Implement aggregation from Parser IR decisions**

Deduplicate decisions by object identity while walking nested operations. Count unique DAG nodes, roots, shared incoming targets, and maximum lookahead offset. Count emitted BSL branch predicates separately from semantic DAG edges.

- [ ] **Step 3: Benchmark exact predicate strategies on generated production text**

Generate two in-memory variants: fully inline exact token sets and reusable named-set predicates for sets above 8 tokens used at least 3 times. Record BSL LOC, maximum condition size, generated helper calls, and Python generation time. Do not write production artifacts during this comparison.

- [ ] **Step 4: Select the faster/smaller non-regressing policy and lock shape tests**

The selected helper, if any, must have signature equivalent to:

```bsl
Функция ТокенПринадлежитКлассу(ТипТокена, ИмяКласса)
```

It must never call `ТипТокенаПросмотра`. If runtime timing is not yet available, prefer inline emission for small sets and reuse only exact named sets whose generated LOC is lower; the follow-up runtime-evidence plan may adjust the threshold without changing DAG semantics.

- [ ] **Step 5: Run audit/renderer tests and commit**

```powershell
python -m pytest tools/parsergen/tests/test_migration_audit.py tools/parsergen/tests/test_canonical_bsl_decisions.py -v
git add tools/parsergen/src/parsergen/decision_dag.py tools/parsergen/src/parsergen/canonical_bsl_decisions.py tools/parsergen/benchmarks/audit_migration.py tools/parsergen/tests/test_migration_audit.py tools/parsergen/tests/test_canonical_bsl_decisions.py
git commit -m "Добавить метрики canonical Decision DAG"
```

### Task 13: Regenerate production artifacts and complete parsergen verification

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl`
- Modify if content changes: `QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt`
- Modify if content changes: `QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt`
- Modify: `tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl`
- Modify corresponding reference templates only if production templates changed.
- Modify: `docs/architecture/parser-generator.md`
- Create: `docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json`
- Create: `docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md`

**Interfaces:**
- Production parser is generated only after focused and full Python suites pass.
- Reference fixtures copy the exact reviewed production artifacts.
- Checkpoint compares pre-DAG and post-DAG structural metrics and records any unavailable runtime metrics for the follow-up evidence plan.

- [ ] **Step 1: Run the complete read-only gate before regeneration**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m parsergen validate --config parsergen.toml
python -m pytest tools/parsergen/tests -q
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
git diff --check
```

Expected: validation and tests PASS; audit reports zero canonical conflicts, zero SELECT Cartesian materializations, and production artifacts as changed because regeneration has not occurred yet.

- [ ] **Step 2: Generate and review exactly three allowed production artifacts**

```powershell
python -m parsergen generate --config parsergen.toml
git diff -- QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt
```

Verify direct BSL control flow, explicit EBNF exits/errors, one logical-operator decision, no runtime DAG interpreter, and no unrelated artifact changes.

- [ ] **Step 3: Copy the reviewed artifacts to the reference fixture and update architecture docs**

Use `Copy-Item -LiteralPath` for the exact three files; do not regenerate fixtures independently. Update the architecture pipeline from row-backed canonical conditions to symbolic SELECT → Decision DAG → optimized Parser IR → direct BSL.

- [ ] **Step 4: Run the complete post-generation verification**

```powershell
python -m parsergen validate --config parsergen.toml
python -m parsergen generate --config parsergen.toml --check
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml > docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json
python -m pytest tools/parsergen/tests -q
git diff --check
```

Then use EDT-MCP to validate the changed parser object and run the existing YAxUnit parser modules, including `КОНС_Обр_ЛексическийАнализатор_МО`, `КОНС_Обр_Парсер_МО`, `КОНС_Обр_ПарсерЗапросов_МО`, `КОНС_Обр_МодельВыражений_МО`, and `КОНС_Обр_БенчмаркПарсера_МО`. Record exact results and existing diagnostic background in the checkpoint.

- [ ] **Step 5: Commit the coherent generated package**

```powershell
git add QueryConsoleZUP/src/DataProcessors/Парсер tools/parsergen/tests/fixtures/reference_parser docs/architecture/parser-generator.md docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md
git commit -m "Сгенерировать parser через canonical Decision DAG"
```

## Final Verification

Run from the repository root:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
$env:PYTHONIOENCODING='utf-8'
python -c "import parsergen; print(parsergen.__file__)"
python -m parsergen validate --config parsergen.toml
python -m parsergen generate --config parsergen.toml --check
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
python -m pytest tools/parsergen/tests -q
git diff --check
git status --short --branch
```

Expected:

- repository `parsergen` package is imported;
- canonical conflicts and diagnostics are empty;
- public SELECT expansions and Cartesian materializations are zero in the DAG path;
- generated artifacts are current;
- all parsergen tests pass;
- working tree contains only intentionally uncommitted follow-up evidence, if any.

Actual instrumented BSL call/depth counters and the three-way legacy/current/optimized timing publication are intentionally executed by the dependent runtime-evidence plan, because they require a test-only EDT metadata object and the separately approved `old_parser` baseline workflow.
