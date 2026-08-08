# Parsergen Decision Path Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve facts proven by a canonical Decision DAG path through Parser IR specialization so generated BSL consumes the proven prefix without repeating its lookahead predicates.

**Architecture:** Keep canonical SELECT, canonical outcomes, and the validated canonical DAG unchanged. Enumerate path-specific executable leaves only after outcome/action binding, attach exact lookahead facts to specialized `BranchIr` values, partially evaluate the leading semantic region, and represent proven token consumption explicitly in optimized Parser IR. Codegen remains mechanical and renders the path-specific branch selected by the existing DAG.

**Tech Stack:** Python 3.11+, immutable dataclasses, existing symbolic SELECT and Decision DAG modules, pytest/unittest, generated 1C BSL, EDT diagnostics, YAxUnit.

## Global Constraints

- Keep production `lookahead = 2`.
- Do not change canonical `CommitAlternative | Exit | ImmediateError` semantics or the canonical oracle.
- Do not materialize SELECT rows or introduce legacy priority, longest-match, first-match, or nullable fallback.
- Do not add runtime DAG objects, transition tables, or helper-per-node dispatch.
- A fact may remove validation, but never token consumption.
- Preserve semantic action order and execute every action exactly once.
- Do not move actions across token consumption.
- Stop specialization at the first operation not proven by the current facts.
- Treat constructor actions as failure-local under the approved design contract.
- Keep large `#ID_*` predicate emission out of this implementation; preserve symbolic token-set identity for its later plan.
- Do not run the final runtime benchmark in this plan.
- Force repository imports for every parsergen command:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
$env:PYTHONIOENCODING='utf-8'
python -c "import parsergen; print(parsergen.__file__)"
```

The printed path must be inside this repository.

## File Structure

- Modify `tools/parsergen/src/parsergen/decision_dag.py`: deterministic grouped DAG edges and root-to-leaf decision-path facts.
- Modify `tools/parsergen/src/parsergen/parser_ir.py`: path-specific branch identity plus explicit proven-consume and resolved-region operations.
- Modify `tools/parsergen/src/parsergen/parser_ir_optimization.py`: executable-path expansion and bounded partial evaluation of leading semantic regions.
- Modify `tools/parsergen/src/parsergen/canonical_bsl_decisions.py`: pass the exact rendered path to the leaf callback; do not infer semantics.
- Modify `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`: render proven consumes and path-specific specialized branches directly.
- Modify `tools/parsergen/benchmarks/audit_migration.py`: structural metrics for specialized paths and proven consumes.
- Modify focused tests in `tools/parsergen/tests/`: oracle/path, optimizer/action-trace, codegen shape, production grammar, and migration audit.
- Regenerate `QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl` and copy it byte-for-byte to `tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl`.
- Update `docs/architecture/parser-generator.md`, `docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json`, and `docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md` with the final shape and metrics.

---

### Task 1: Seal the already verified canonical-DAG generation checkpoint

**Files:**
- Commit existing modifications in `QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl`
- Commit existing modifications in `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Commit existing modifications in `tools/parsergen/src/parsergen/templates/canonical_parser_module.bsl`
- Commit existing modifications in `tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl`
- Commit existing modifications in `tools/parsergen/tests/test_canonical_bsl_codegen.py`
- Commit existing modifications in `tools/parsergen/tests/test_canonical_bsl_ebnf.py`
- Commit existing modifications in `tools/parsergen/tests/test_migration_audit.py`
- Commit existing modifications in `docs/architecture/parser-generator.md`
- Commit existing `docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json`
- Commit existing `docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md`
- Commit the two existing YAxUnit diagnostic expectation changes under `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl` and `yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl`

**Interfaces:**
- Consumes the verified Wave 1–3 implementation at commits `dd2e161..1ea2ab1` and the uncommitted Task 13 generated/diagnostic package.
- Produces a clean, reproducible pre-path-facts baseline commit; it does not change behavior beyond the already verified package.

- [ ] **Step 1: Verify the exact pending scope**

Run:

```powershell
git status --short
git diff --name-only
git diff --check
```

Expected: only the generated parser/reference, canonical diagnostic helper/template/tests, architecture/checkpoint files, and two YAxUnit expected-diagnostic modules listed above. Stop if another path appears.

- [ ] **Step 2: Re-run the repository-local generation and focused diagnostic gate**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m parsergen generate --config parsergen.toml --check
python -m pytest tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_ebnf.py tools/parsergen/tests/test_migration_audit.py -q
```

Expected: artifacts current and all focused tests PASS.

- [ ] **Step 3: Confirm production/reference byte identity**

Run:

```powershell
$production='QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl'
$reference='tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $production).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $reference).Hash) { throw 'production/reference parser mismatch' }
```

Expected: exit `0`.

- [ ] **Step 4: Commit only the verified checkpoint package**

```powershell
git add -- 'QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl' 'docs/architecture/parser-generator.md' 'tools/parsergen/src/parsergen/canonical_bsl_codegen.py' 'tools/parsergen/src/parsergen/templates/canonical_parser_module.bsl' 'tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl' 'tools/parsergen/tests/test_canonical_bsl_codegen.py' 'tools/parsergen/tests/test_canonical_bsl_ebnf.py' 'tools/parsergen/tests/test_migration_audit.py' 'yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl' 'yaxunit/src/CommonModules/КОНС_Обр_ПарсерЗапросов_МО/Module.bsl' 'docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json' 'docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md'
git diff --cached --check
git commit -m "Сгенерировать parser через canonical Decision DAG"
```

Expected: one checkpoint commit and a clean working tree.

### Task 2: Add executable path facts and partially evaluate leading Parser IR regions

**Files:**
- Modify: `tools/parsergen/src/parsergen/decision_dag.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir_optimization.py`
- Modify: `tools/parsergen/tests/test_decision_dag.py`
- Modify: `tools/parsergen/tests/test_parser_ir_optimization.py`

**Interfaces:**
- Produces `DecisionPathFact(offset: int, predicate: TokenSetPredicate)`.
- Produces `DecisionPath(leaf: DecisionLeaf, facts: tuple[DecisionPathFact, ...])`.
- Produces `grouped_decision_edges(node: LookaheadDecision) -> tuple[DecisionEdge, ...]`.
- Produces `decision_paths(dag: CanonicalDecisionDag) -> tuple[DecisionPath, ...]`.
- Extends `BranchIr` with `path_facts: tuple[DecisionPathFact, ...] | None = None`; `None` means ordinary outcome-bound branch, including an unspecialized root commit.
- Produces `ConsumeKnownSymbol(symbol: SyntaxSymbol, capture_value: bool, proven_token_types: tuple[str, ...], source_span: SourceSpan)`.
- Produces `ResolvedRegion(operations: tuple[Operation, ...], result_index: int | None, source_span: SourceSpan)`.
- `optimize_parser_ir()` expands a specialized caller/callee branch only for paths whose facts change its leading executable fragment.
- Defines `MAX_PATH_SPECIALIZATION_EXTRA_OPERATIONS = 32`; a larger projected duplicate operation-tree cost keeps the original unspecialized branch.

- [ ] **Step 1: Write one grouped RED suite for path enumeration and exact grouping**

Add to `test_decision_dag.py` a manually constructed DAG in which `A` commits alternative 1 directly while `НЕ → A` commits the same alternative and `НЕ → B` commits alternative 2:

```python
def test_decision_paths_keep_distinct_facts_for_the_same_outcome(self) -> None:
    alt1 = AlternativeOutcome("Choice", 1)
    alt2 = AlternativeOutcome("Choice", 2)
    dag = CanonicalDecisionDag(
        production="Choice",
        lookahead=2,
        root=3,
        nodes=(
            CommitAlternative(alt1),
            CommitAlternative(alt2),
            LookaheadDecision(
                1,
                ("A", "B"),
                (
                    DecisionEdge(TokenSetPredicate(("A",)), 0),
                    DecisionEdge(TokenSetPredicate(("B",)), 1),
                ),
            ),
            LookaheadDecision(
                0,
                ("A", "НЕ"),
                (
                    DecisionEdge(TokenSetPredicate(("A",)), 0),
                    DecisionEdge(TokenSetPredicate(("НЕ",)), 2),
                ),
            ),
        ),
        stats={},
    )
    paths = decision_paths(dag)
    actual = {
        tuple((fact.offset, fact.predicate.token_types) for fact in path.facts)
        for path in paths
        if path.leaf == CommitAlternative(alt1)
    }
    self.assertEqual(
        actual,
        {
            ((0, ("A",)),),
            ((0, ("НЕ",)), (1, ("A",))),
        },
    )
```

Also assert that multiple edges to one target are exposed as one sorted union predicate, matching renderer behavior.

- [ ] **Step 2: Write one grouped RED suite for semantic specialization**

Add a synthetic grammar fixture to `test_parser_ir_optimization.py`:

```text
<S> ::= <Base> Child => <Choice>?
<Base> ::= @НовыйBase BASE
<Choice> ::= @НовыйBetween (NOT Inverted := Истина)? BETWEEN <Tail>
<Choice> ::= @НовыйIn (NOT Inverted := Истина)? IN <Tail>
<Tail> ::= VALUE
```

Assert after `optimize_parser_ir()`:

```python
def _flatten_operations(operations):
    for operation in operations:
        yield operation
        if isinstance(operation, ResolvedRegion):
            yield from _flatten_operations(operation.operations)


between = [
    branch for branch in optional.branches
    if branch.outcome == AlternativeOutcome("Choice", 1)
]
self.assertEqual(len(between), 2)
self.assertNotEqual(between[0].path_facts, between[1].path_facts)
self.assertTrue(all(
    any(isinstance(operation, ConsumeKnownSymbol)
        for operation in _flatten_operations(branch.operations))
    for branch in between
))
self.assertTrue(all(
    sum(isinstance(operation, ConstructNode)
        for operation in _flatten_operations(branch.operations)) == 1
    for branch in between
))
```

Add action/token trace assertions for direct `BETWEEN`, inverted `NOT BETWEEN`, direct/inverted `IN`, exit, and invalid suffix. The optimized and unoptimized traces must agree after normalizing `ConsumeKnownSymbol` to the original symbol-consume event.

Add a second synthetic branch whose duplicated operation-tree cost would be
`33`; assert that it remains one unspecialized `BranchIr` with
`path_facts is None`. This locks the code-size guard independently of
production grammar.

- [ ] **Step 3: Run the grouped suite and verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_decision_dag.py tools/parsergen/tests/test_parser_ir_optimization.py -k "path or known or semantic_callee" -v
```

Expected: FAIL because path facts, known consumes, and partial evaluation do not exist.

- [ ] **Step 4: Implement deterministic path enumeration without changing canonical leaves**

In `decision_dag.py`, group edges by target once and use the same function for enumeration and later rendering:

```python
@dataclass(frozen=True, slots=True)
class DecisionPathFact:
    offset: int
    predicate: TokenSetPredicate


@dataclass(frozen=True, slots=True)
class DecisionPath:
    leaf: DecisionLeaf
    facts: tuple[DecisionPathFact, ...]


def grouped_decision_edges(node: LookaheadDecision) -> tuple[DecisionEdge, ...]:
    tokens_by_target: dict[int, set[str]] = {}
    target_order: list[int] = []
    for edge in node.edges:
        if edge.target not in tokens_by_target:
            tokens_by_target[edge.target] = set()
            target_order.append(edge.target)
        tokens_by_target[edge.target].update(edge.predicate.token_types)
    return tuple(
        DecisionEdge(
            TokenSetPredicate(tuple(sorted(tokens_by_target[target]))),
            target,
        )
        for target in target_order
    )


def decision_paths(dag: CanonicalDecisionDag) -> tuple[DecisionPath, ...]:
    result: list[DecisionPath] = []

    def visit(index: int, facts: tuple[DecisionPathFact, ...]) -> None:
        node = dag.nodes[index]
        if not isinstance(node, LookaheadDecision):
            result.append(DecisionPath(node, facts))
            return
        if any(fact.offset == node.offset for fact in facts):
            raise ValueError("decision path reads one offset twice")
        for edge in grouped_decision_edges(node):
            visit(
                edge.target,
                (*facts, DecisionPathFact(node.offset, edge.predicate)),
            )

    visit(dag.root, ())
    return tuple(result)
```

Reject a path that contains two different facts for the same offset; EOF may only terminate a path.

- [ ] **Step 5: Add explicit optimized-IR operations and structural validation**

In `parser_ir.py` add immutable `ConsumeKnownSymbol` and `ResolvedRegion` to `Operation`. Reject `NonterminalCall` and `Action` inside `ConsumeKnownSymbol`; require sorted, unique, non-empty `proven_token_types`. Add `path_facts` to `BranchIr` with a default of `None` so ordinary IR construction stays source-compatible.

The semantic value contract is:

```python
def _known_symbol_value_kind(symbol: SyntaxSymbol) -> str:
    if isinstance(symbol, (Terminal, Lexeme)):
        return "type"
    if isinstance(symbol, IdentifierRef):
        return "lexeme"
    if isinstance(symbol, Constant):
        return "value"
    raise ValueError("known consume requires a terminal-like symbol")
```

Import `Terminal` and `Lexeme` from `model.py`. `ConsumeKnownSymbol` accepts
exactly `Terminal | Lexeme | Constant | IdentifierRef`; reject
`NonterminalCall`.

- [ ] **Step 6: Implement bounded partial evaluation after caller/callee composition**

In `parser_ir_optimization.py`, after `specialize_outcome(...)` builds and validates the fresh canonical DAG:

1. Enumerate only `CommitAlternative` paths.
2. Find the original replacement branch by canonical outcome.
3. Partially evaluate its leading operations under that path's facts.
4. Emit separate `BranchIr` values only when their optimized operation tuples differ.
5. Store the exact `path_facts` for lookup by codegen.
6. Compute added recursive operation-tree cost before accepting expansion and
   retain the original branch when it exceeds
   `MAX_PATH_SPECIALIZATION_EXTRA_OPERATIONS`.

The evaluator carries `cursor`, initially zero. Constructors and bindings are retained and do not advance it. A terminal-like `ParseSymbol`/`DiscardSymbol` becomes `ConsumeKnownSymbol` only when the fact at `cursor` is a subset of the symbol's exact accepted token set. A resolvable nested Optional/Dispatch becomes one `ResolvedRegion` so its outer operation index and result behavior remain stable. After a nonterminal call, an unproven token operation, or an ambiguous nested decision, append the untouched remainder and stop.

Do not specialize `ЕСТЬ НЕ? NULL` beyond the proven `ЕСТЬ` token: the caller path has no fact about the following optional `НЕ`.

- [ ] **Step 7: Run the grouped GREEN and full optimizer regressions**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_decision_dag.py tools/parsergen/tests/test_decision_dag_property.py tools/parsergen/tests/test_parser_ir.py tools/parsergen/tests/test_parser_ir_optimization.py -v
```

Expected: PASS; property/oracle results unchanged and all action/token traces equivalent.

- [ ] **Step 8: Commit the IR package**

```powershell
git add -- 'tools/parsergen/src/parsergen/decision_dag.py' 'tools/parsergen/src/parsergen/parser_ir.py' 'tools/parsergen/src/parsergen/parser_ir_optimization.py' 'tools/parsergen/tests/test_decision_dag.py' 'tools/parsergen/tests/test_parser_ir_optimization.py'
git diff --cached --check
git commit -m "Сохранить facts путей Decision DAG в Parser IR"
```

### Task 3: Emit path-specific semantic fragments directly and lock production shape

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_decisions.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Modify: `tools/parsergen/benchmarks/audit_migration.py`
- Modify: `tools/parsergen/tests/test_canonical_bsl_decisions.py`
- Modify: `tools/parsergen/tests/test_canonical_bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_repository_grammar.py`
- Modify: `tools/parsergen/tests/test_migration_audit.py`

**Interfaces:**
- `CanonicalDecisionRenderer.render(..., render_leaf: Callable[[DecisionLeaf, tuple[DecisionPathFact, ...], str], list[str]]) -> list[str]`.
- Renderer obtains facts only from `grouped_decision_edges`; predicates still read cached `ТокенРешенияN` values once.
- Codegen maps `(CommitAlternative.outcome, path_facts)` to the already specialized `BranchIr`; it never simplifies operations from facts.
- `ConsumeKnownSymbol` emits value capture when requested followed by one `УстановитьТекущийТокен()` and no token-type validation.
- Audit adds `decision_path.specialized_paths`, `decision_path.known_symbol_consumes`, and `decision_path.redundant_validations`.

- [ ] **Step 1: Write one grouped RED codegen suite**

Update renderer callbacks in `test_canonical_bsl_decisions.py` and assert exact facts for direct and two-token paths. In `test_canonical_bsl_codegen.py`, generate the synthetic grammar from Task 2 and assert:

```python
def _constructor_fragment(function: str, constructor: str, following: str) -> str:
    return function.split(constructor, 1)[1].split(following, 1)[0]


between = _constructor_fragment(function, "НовыйBetween", "НовыйIn")
self.assertEqual(function.count('ТипТокенаПросмотра(1)'), 1)
self.assertNotIn('Если ТокенРешения0 = "BETWEEN"', between)
self.assertNotIn('Если ТокенРешения0 = "NOT"', between)
self.assertNotIn('Терминал("BETWEEN")', between)
self.assertGreaterEqual(between.count("УстановитьТекущийТокен();"), 1)
self.assertNotIn("ЗначениеВыбора", function)
```

Use structural extraction helpers rather than whole-module substring counts so unrelated decisions do not affect the assertions.

- [ ] **Step 2: Add production RED assertions for `ЛогическийМножитель`**

In `test_repository_grammar.py`, retain the assertions that `НеТерминалЛогическийОператор` is absent and add:

- direct `МЕЖДУ`, `В`, `ЕСТЬ` do not read `ТипТокенаПросмотра(1)`;
- only the `НЕ` and ambiguous `ССЫЛКА` paths read offset 1;
- BETWEEN/IN semantic fragments contain no second `МЕЖДУ versus НЕ` or `В versus НЕ` decision;
- known `НЕ`, `МЕЖДУ`, and `В` terminals are not validated twice;
- `Операнд = left` appears after the selected operator actions and once in the common continuation;
- `ЕСТЬ` retains its nested `NULL versus НЕ` decision.

- [ ] **Step 3: Run the grouped suite and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_decisions.py tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_repository_grammar.py -k "path or logical or specialized or known" -v
```

Expected: FAIL because renderer does not pass facts and specialized codegen still emits a variant-id switch followed by repeated predicates.

- [ ] **Step 4: Pass exact path facts through the renderer**

Change `_render_node` to accumulate an immutable fact tuple:

```python
fact = DecisionPathFact(node.offset, edge.predicate)
child_facts = (*path_facts, fact)
```

Call `render_leaf(node, path_facts, indent)` for every canonical leaf, including `ExitDecision` and `ImmediateError`. Update all existing callbacks mechanically; ordinary branches ignore facts.

- [ ] **Step 5: Render explicit proven consumes and resolved regions**

In `_render_operation`:

```python
if isinstance(operation, ConsumeKnownSymbol):
    value = self._new_temporary() if operation.capture_value else None
    lines = []
    if value is not None:
        lines.append(f"{indent}{value} = {self._known_current_value(operation.symbol)};")
    lines.append(f"{indent}УстановитьТекущийТокен();")
    return lines, value

if isinstance(operation, ResolvedRegion):
    lines, values = self._render_operations(
        operation.operations,
        indent,
        error_label,
        required_result_index=operation.result_index,
    )
    return lines, None if operation.result_index is None else values[operation.result_index]
```

`_known_current_value` maps the repository's actual terminal, identifier, and constant symbol types to `ТекущийТокен.Тип`, `.Лексема`, and `.Значение` respectively.

- [ ] **Step 6: Replace the specialized WrapOptional variant switch with direct leaf execution**

Build a lookup by `(outcome, path_facts)` and render the selected branch inside the canonical leaf. Each present leaf assigns `branch_result` and `present = Истина`; exit assigns `present = Ложь`. After the decision, retain one common block:

```bsl
Если ЕстьСпециализированноеЗначение Тогда
    РезультатВетки.Операнд = Аккумулятор;
    Аккумулятор = РезультатВетки;
КонецЕсли;
```

Use the actual property and prepend/assign binding from `WrapOptional`; the snippet illustrates shape only. Remove the outcome-number temporary and subsequent alternative switch. Reject missing or duplicate `(outcome, path_facts)` mappings during generation.

- [ ] **Step 7: Add structural decision-path metrics**

Walk optimized Parser IR recursively in `audit_migration.py` and report:

```json
"decision_path": {
  "specialized_paths": 0,
  "known_symbol_consumes": 0,
  "redundant_validations": 0
}
```

`redundant_validations` counts a normal terminal-like validation that is still covered by a branch fact before any cursor-invalidating operation. The production audit must assert zero. `known_symbol_consumes` must be positive, proving that zero was not achieved by disabling specialization.

- [ ] **Step 8: Run grouped GREEN and canonical codegen regressions**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_decisions.py tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_bindings.py tools/parsergen/tests/test_canonical_bsl_ebnf.py tools/parsergen/tests/test_canonical_bsl_left_fold.py tools/parsergen/tests/test_repository_grammar.py tools/parsergen/tests/test_migration_audit.py -v
```

Expected: PASS; no runtime DAG interpreter, no repeated path predicate, explicit EBNF exits/errors unchanged.

- [ ] **Step 9: Commit direct codegen and metrics**

```powershell
git add -- 'tools/parsergen/src/parsergen/canonical_bsl_decisions.py' 'tools/parsergen/src/parsergen/canonical_bsl_codegen.py' 'tools/parsergen/benchmarks/audit_migration.py' 'tools/parsergen/tests/test_canonical_bsl_decisions.py' 'tools/parsergen/tests/test_canonical_bsl_codegen.py' 'tools/parsergen/tests/test_repository_grammar.py' 'tools/parsergen/tests/test_migration_audit.py'
git diff --cached --check
git commit -m "Устранить повторные predicates после Decision DAG"
```

### Task 4: Regenerate production parser and complete the non-benchmark verification

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl`
- Modify: `tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl`
- Modify: `docs/architecture/parser-generator.md`
- Modify: `docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json`
- Modify: `docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md`
- Do not modify the two parser YAxUnit modules from Task 1; if their expected diagnostics change, stop and amend this plan before accepting the change.

**Interfaces:**
- Produces the reviewed production/reference artifact pair generated from optimized Parser IR.
- Produces final static metrics including decision-path facts.
- Leaves the runtime benchmark pending for the separately approved methodology update.

- [ ] **Step 1: Run the complete read-only gate before regeneration**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
$env:PYTHONIOENCODING='utf-8'
python -c "import parsergen; print(parsergen.__file__)"
python -m parsergen validate --config parsergen.toml
python -m pytest tools/parsergen/tests -q
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
git diff --check
```

Expected: repository import, zero canonical/legacy conflicts, zero SELECT materializations, full Python GREEN, and only the production artifact reported stale.

- [ ] **Step 2: Generate and review the production parser**

```powershell
python -m parsergen generate --config parsergen.toml
git diff -- 'QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl' 'QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt' 'QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt'
```

Expected: only `ObjectModule.bsl` changes. Verify `ЛогическийМножитель`, direct known-token consumption, preserved `ЕСТЬ НЕ? NULL`, explicit exit/error, and absence of runtime DAG objects.

- [ ] **Step 3: Copy the exact reviewed artifact and refresh static evidence**

```powershell
Copy-Item -LiteralPath 'QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl' -Destination 'tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl'
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml | Set-Content -LiteralPath 'docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json' -Encoding utf8
```

Update the checkpoint and architecture document with exact before/after values and the path-fact contract. Do not copy templates unless their production bytes changed.

- [ ] **Step 4: Run final Python and artifact verification**

```powershell
python -m parsergen validate --config parsergen.toml
python -m parsergen generate --config parsergen.toml --check
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
python -m pytest tools/parsergen/tests -q
git diff --check
$production='QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl'
$reference='tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $production).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $reference).Hash) { throw 'production/reference parser mismatch' }
```

Expected: all commands PASS; artifacts are current and byte-identical.

- [ ] **Step 5: Validate changed EDT objects and run parser YAxUnit modules**

Use EDT-MCP as the source of truth. Revalidate `DataProcessor.Парсер` and every changed YAxUnit common module. Run the established parser suites, including:

```text
КОНС_Обр_Парсер_МО
КОНС_Обр_ПарсерЗапросов_МО
КОНС_Обр_МодельВыражений_МО
```

Also run lexer tests only if a lexer artifact or shared lexer contract changed; this plan does not intentionally change them. Record exact totals, failures, errors, skips, and the existing EDT diagnostic background in the checkpoint.

- [ ] **Step 6: Commit the coherent generated package**

```powershell
git add -- 'QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl' 'tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl' 'docs/architecture/parser-generator.md' 'docs/superpowers/matrices/2026-08-08-decision-dag-static-after.json' 'docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md'
git diff --cached --check
git commit -m "Сгенерировать parser с decision path facts"
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

- repository-local parsergen import;
- zero canonical conflicts and zero legacy runtime conflicts;
- zero public SELECT expansions/materializations in the DAG path;
- `decision_path.redundant_validations == 0` and `known_symbol_consumes > 0`;
- current and reference parser artifacts are byte-identical;
- full Python, EDT, and YAxUnit gates pass with exact results recorded;
- no final runtime benchmark has been executed.
