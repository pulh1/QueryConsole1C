# Parser Generator Canonical SELECT Conflicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Сделать canonical LL(k) conflict detection и `LLK202` точным, representation-independent и отделённым от legacy BSL runtime dispatch без изменения FIRST/FOLLOW/SELECT и generated production artifacts.

**Architecture:** Canonical scanner выполняет memoized symbolic intersection существующих factorized SELECT automata, а текущий runtime-row scanner и matcher artifact получают отдельные legacy-имена. Validation использует только canonical API; codegen продолжает использовать legacy artifact явно.

**Tech Stack:** Python 3.11+, dataclasses, packed/factorized LL(k) analysis, unittest/pytest, PowerShell, EDT-backed BSL runtime source.

## Global Constraints

- Не изменять алгоритмы `nullable`, FIRST, FOLLOW или SELECT.
- Не убирать и не ослаблять projection optimization FOLLOW.
- Не материализовывать concrete SELECT в compressed conflict scan.
- Не изменять `tools/parsergen/grammar/query-language.grammar`.
- Не изменять `QueryConsoleZUP/src/DataProcessors/Парсер` и BSL template.
- Сохранить generated legacy matcher rows и reference artifacts.
- `find_select_conflicts` после изменения имеет только canonical семантику.
- `LLK202` после изменения имеет только canonical семантику и не подавляет nullable/consuming пары.
- Два production-конфликта не скрывать; `validate` и `generate --check` ожидаемо возвращают code `1`.
- Реализацию вести через TDD: сначала наблюдать целевое падение, затем вносить минимальный production diff.
- Для кода использовать `gpt-5.6-terra` с низким reasoning; для аналитики и независимого review — `gpt-5.6-sol`.

## File Map

- `tools/parsergen/src/parsergen/analysis.py` — canonical symbolic intersection, explicit canonical/runtime APIs, compatibility wrappers и invariant packed facts.
- `tools/parsergen/src/parsergen/validation.py` — canonical `LLK202` без legacy nullable suppression.
- `tools/parsergen/src/parsergen/bsl_codegen.py` — явное использование legacy matcher artifact.
- `tools/parsergen/tests/test_follow_select.py` — counterexample, API invariant, matcher overlap, no-materialization и random oracle.
- `tools/parsergen/tests/test_validation.py` — canonical nullable/FOLLOW diagnostic.
- `tools/parsergen/tests/test_bsl_codegen.py` — executable legacy generated-table regression.
- `tools/parsergen/tests/test_nullable_first.py` — saturated `complete=False` invariant.
- `tools/parsergen/tests/test_repository_grammar.py` — два canonical production conflicts и отдельный clean legacy scan.
- `docs/architecture/parser-generator.md` — публичная граница canonical analysis и legacy runtime compatibility.
- `docs/superpowers/specs/2026-08-07-parser-generator-canonical-select-conflicts-design.md` — утверждённая спецификация; при реализации не изменяется.

---

### Task 1: Canonical counterexample and representation invariant

**Files:**
- Modify: `tools/parsergen/tests/test_follow_select.py:10-20`
- Modify: `tools/parsergen/tests/test_follow_select.py:250-336`
- Modify: `tools/parsergen/src/parsergen/analysis.py:242-322`
- Modify: `tools/parsergen/src/parsergen/analysis.py:1120-1641`
- Modify: `tools/parsergen/src/parsergen/analysis.py:2073-2088`

**Interfaces:**
- Consumes: `_descriptor_state(position) -> _FactorState`, `_children(state)`, `_terminal(state)`, `_intersection(left_matcher, right_matcher)`.
- Produces: `find_canonical_select_conflicts(grammar, analysis) -> tuple[SelectConflict, ...]`, canonical alias `find_select_conflicts`, and `_CompressedAnalysis.canonical_conflict_witness(left_position, right_position) -> LookaheadWord | None`.

- [ ] **Step 1: Run the current focused baseline**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_follow_select.py -q
```

Expected: PASS before new tests are added.

- [ ] **Step 2: Add the failing FOLLOW-derived counterexample**

Add this test to `FollowSelectTests` next to the current conflict tests:

```python
def test_canonical_conflict_includes_follow_continuation(self) -> None:
    grammar = resolved(
        "<S> ::= <A>\n"
        "<A> ::= a <B> | a b d\n"
        "<B> ::= ПУСТО | b c"
    )
    result = compute_analysis(grammar, 2, ("S",))

    self.assertEqual(
        result.select[("A", 1)],
        frozenset({("a", END), ("a", "b")}),
    )
    self.assertEqual(
        result.select[("A", 2)],
        frozenset({("a", "b")}),
    )
    self.assertEqual(
        find_select_conflicts(grammar, result),
        (SelectConflict("A", 1, 2, ("a", "b")),),
    )
```

- [ ] **Step 3: Add the compressed/materialized API invariant test**

```python
def test_canonical_conflicts_do_not_depend_on_analysis_representation(
    self,
) -> None:
    grammar = resolved(
        "<S> ::= <A>\n"
        "<A> ::= a <B> | a b d\n"
        "<B> ::= ПУСТО | b c"
    )
    compressed = compute_analysis(grammar, 2, ("S",))
    materialized = AnalysisResult(
        k=compressed.k,
        nullable=compressed.nullable,
        first=MappingProxyType(dict(compressed.first.items())),
        follow=MappingProxyType(dict(compressed.follow.items())),
        select=MappingProxyType(dict(compressed.select.items())),
        updates=compressed.updates,
    )

    self.assertEqual(
        find_select_conflicts(grammar, compressed),
        find_select_conflicts(grammar, materialized),
    )
```

- [ ] **Step 4: Run both tests and verify the defect**

```powershell
python -m pytest tools/parsergen/tests/test_follow_select.py -k "canonical_conflict_includes_follow_continuation or canonical_conflicts_do_not_depend" -v
```

Expected: FAIL; compressed scan returns no conflict while materialized scan returns witness `('a', 'b')`.

- [ ] **Step 5: Implement exact symbolic canonical witness**

Change `_conflict_memo` to use keys
`tuple[_FactorState, _FactorState, int]`, then add:

```python
def canonical_conflict_witness(
    self,
    left_position: int,
    right_position: int,
) -> LookaheadWord | None:
    def visit(
        left: _FactorState,
        right: _FactorState,
        remaining: int,
    ) -> LookaheadWord | None:
        if right < left:
            left, right = right, left
        key = (left, right, remaining)
        if key in self._conflict_memo:
            return self._conflict_memo[key]
        self._stats["conflict_work_items"] += 1

        if remaining == 0 or (
            self._terminal(left) and self._terminal(right)
        ):
            result: LookaheadWord | None = EPSILON
        else:
            candidates: list[LookaheadWord] = []
            for left_matcher, left_child in self._children(left):
                for right_matcher, right_child in self._children(right):
                    tokens = self._intersection(left_matcher, right_matcher)
                    if not tokens:
                        continue
                    suffix = visit(left_child, right_child, remaining - 1)
                    if suffix is not None:
                        candidates.append((tokens[0], *suffix))
            result = min(
                candidates,
                key=lambda word: (len(word), word),
                default=None,
            )
        self._conflict_memo[key] = result
        return result

    return visit(
        self._descriptor_state(left_position),
        self._descriptor_state(right_position),
        self.k,
    )
```

Do not add an XOR-terminal early return: a terminal factor state can also have descendants.

- [ ] **Step 6: Make the public canonical API explicit**

Move the existing production-order loop into
`find_canonical_select_conflicts`. In the compressed branch call
`canonical_conflict_witness`; in the materialized branch compute the exact
intersection:

```python
def _select_conflict_witness(
    left: LookaheadSet,
    right: LookaheadSet,
) -> LookaheadWord | None:
    return min(
        left.intersection(right),
        key=lambda word: (len(word), word),
        default=None,
    )


def find_select_conflicts(
    grammar: ResolvedGrammar,
    analysis: AnalysisResult,
) -> tuple[SelectConflict, ...]:
    return find_canonical_select_conflicts(grammar, analysis)
```

- [ ] **Step 7: Run focused tests**

```powershell
python -m pytest tools/parsergen/tests/test_follow_select.py -k "conflict or identifier or factorized" -q
```

Expected: the new tests PASS. Existing tests that intentionally assert legacy semantics may FAIL and are migrated in Task 2.

- [ ] **Step 8: Commit the canonical scanner**

```powershell
git add -- tools/parsergen/src/parsergen/analysis.py tools/parsergen/tests/test_follow_select.py
git commit -m "fix: проверять canonical SELECT conflicts"
```

---

### Task 2: Explicit legacy runtime conflict API and strict-prefix semantics

**Files:**
- Modify: `tools/parsergen/src/parsergen/analysis.py:242-322`
- Modify: `tools/parsergen/src/parsergen/analysis.py:1555-1641`
- Modify: `tools/parsergen/tests/test_follow_select.py:250-300`
- Modify: `tools/parsergen/tests/test_follow_select.py:549-575`

**Interfaces:**
- Consumes: `_runtime_trie(position)` and the current exact-row collision algorithm.
- Produces: `find_runtime_dispatch_conflicts(grammar, analysis)`, `_CompressedAnalysis.runtime_dispatch_conflict_witness`, `runtime_rows_overlap`, and compatibility wrapper `compatible_lookahead`.

- [ ] **Step 1: Convert old legacy expectations into explicit dual-contract tests**

Replace the nullable fallback test with:

```python
def test_nullable_fallback_is_canonical_conflict_but_runtime_clean(self) -> None:
    grammar = resolved("<S> ::= <A> a\n<A> ::= a | ПУСТО")
    result = compute_analysis(grammar, 1, ("S",))

    self.assertEqual(
        find_select_conflicts(grammar, result),
        (SelectConflict("A", 1, 2, ("a",)),),
    )
    self.assertEqual(find_runtime_dispatch_conflicts(grammar, result), ())
```

Replace the shadowing test with:

```python
def test_runtime_shadowing_is_not_used_as_canonical_semantics(self) -> None:
    grammar = resolved("<S> ::= <A> | a b\n<A> ::= a | a b")
    result = compute_analysis(grammar, 2, ("S",))

    self.assertEqual(
        find_select_conflicts(grammar, result),
        (SelectConflict("S", 1, 2, ("a", "b")),),
    )
    self.assertEqual(find_runtime_dispatch_conflicts(grammar, result), ())
```

Add `find_runtime_dispatch_conflicts` and `runtime_rows_overlap` to the import list.

- [ ] **Step 2: Keep strict-prefix word equality explicit**

Rename `LookaheadCompatibilityTests` to `RuntimeRowCompatibilityTests` and use:

```python
def test_strict_prefix_rows_are_distinct_exact_rows(self) -> None:
    self.assertFalse(runtime_rows_overlap(("a",), ("a", "b")))
    self.assertFalse(runtime_rows_overlap(("a", "b"), ("a",)))

def test_materialized_canonical_scan_uses_exact_word_intersection(self) -> None:
    grammar = resolved("<S> ::= a | b")
    analysis = AnalysisResult(
        k=2,
        nullable=frozenset(),
        first=MappingProxyType({"S": frozenset({("a",), ("b",)})}),
        follow=MappingProxyType({"S": frozenset({(END,)})}),
        select=MappingProxyType({
            ("S", 1): frozenset({("a",)}),
            ("S", 2): frozenset({("a", "b")}),
        }),
        updates=MappingProxyType({"S": 1}),
    )
    self.assertEqual(find_select_conflicts(grammar, analysis), ())
```

- [ ] **Step 3: Run tests and verify the missing legacy API**

```powershell
python -m pytest tools/parsergen/tests/test_follow_select.py -k "nullable_fallback or runtime_shadowing or strict_prefix" -v
```

Expected: FAIL because `find_runtime_dispatch_conflicts` and `runtime_rows_overlap` are not yet defined.

- [ ] **Step 4: Isolate the current runtime scanner**

Rename the current `_CompressedAnalysis.conflict_witness` implementation to:

```python
def runtime_dispatch_conflict_witness(
    self,
    left_position: int,
    right_position: int,
) -> LookaheadWord | None:
```

Keep its `_runtime_trie`, both-terminal acceptance and XOR-terminal rejection unchanged. Add:

```python
def runtime_rows_overlap(
    left: LookaheadWord,
    right: LookaheadWord,
) -> bool:
    return left == right


def compatible_lookahead(
    left: LookaheadWord,
    right: LookaheadWord,
) -> bool:
    return runtime_rows_overlap(left, right)
```

Implement `find_runtime_dispatch_conflicts` with the same deterministic
production/alternative loop as the canonical function. Require compressed
analysis explicitly:

```python
if analysis._compressed is None:
    raise ValueError("compressed analysis is required for runtime dispatch")
```

- [ ] **Step 5: Run the focused and full follow/select modules**

```powershell
python -m pytest tools/parsergen/tests/test_follow_select.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the API boundary**

```powershell
git add -- tools/parsergen/src/parsergen/analysis.py tools/parsergen/tests/test_follow_select.py
git commit -m "refactor: отделить legacy runtime dispatch"
```

---

### Task 3: Canonical LLK202 validation

**Files:**
- Modify: `tools/parsergen/src/parsergen/validation.py:677-725`
- Modify: `tools/parsergen/tests/test_validation.py:200-280`

**Interfaces:**
- Consumes: canonical `find_select_conflicts`.
- Produces: `LLK202` for every reachable, otherwise valid canonical SELECT intersection, including nullable/consuming pairs.

- [ ] **Step 1: Change the nullable regression to canonical expectation**

Replace `test_consuming_alternative_precedes_nullable_fallback` with:

```python
def test_nullable_runtime_fallback_does_not_hide_canonical_conflict(
    self,
) -> None:
    report = validate_text(
        "<S> ::= <A> a\n<A> ::= a | ПУСТО",
        {"Разобрать": "S"},
        k=1,
    )

    conflicts = [
        item for item in report.diagnostics if item.code == "LLK202"
    ]
    self.assertEqual(len(conflicts), 1)
    self.assertEqual(conflicts[0].details["witness"], ("a",))
```

Add a validation-level version of the audit counterexample expecting witness
`("a", "b")` and alternative spans on the two `A` lines.

- [ ] **Step 2: Run and observe legacy suppression**

```powershell
python -m pytest tools/parsergen/tests/test_validation.py -k "nullable_runtime_fallback or follow_continuation" -v
```

Expected: FAIL because `validation.py` suppresses nullable/consuming conflicts.

- [ ] **Step 3: Remove only the legacy nullable suppression**

Delete the block that resolves `left`/`right` only to compare
`_resolved_alternative_nullable(...)` and `continue`. Preserve the filters for
unreachable productions and `invalid_conflict_alternatives`, then emit `LLK202`
from canonical conflicts unchanged.

- [ ] **Step 4: Run validation tests**

```powershell
python -m pytest tools/parsergen/tests/test_validation.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit canonical validation**

```powershell
git add -- tools/parsergen/src/parsergen/validation.py tools/parsergen/tests/test_validation.py
git commit -m "fix: валидировать canonical LL(k) conflicts"
```

---

### Task 4: Explicit legacy matcher artifact and executable runtime regression

**Files:**
- Modify: `tools/parsergen/src/parsergen/analysis.py:242-249`
- Modify: `tools/parsergen/src/parsergen/bsl_codegen.py:15-25`
- Modify: `tools/parsergen/src/parsergen/bsl_codegen.py:165-180`
- Modify: `tools/parsergen/tests/test_bsl_codegen.py:1-30`
- Modify: `tools/parsergen/tests/test_bsl_codegen.py:280-360`

**Interfaces:**
- Consumes: `_CompressedAnalysis.build_matcher_artifact(max_rows=...)` and `GeneratedParser.select_table`.
- Produces: `build_legacy_matcher_artifact`; compatibility wrapper `build_select_matcher_artifact`; codegen bound explicitly to the legacy artifact.

- [ ] **Step 1: Add a generated-table runtime helper in tests**

Add imports for `ResolvedGrammar`, `ResolvedNonterminal`, `ResolvedToken` and
`ValueTable`, then add:

```python
def _legacy_choice(
    table: ValueTable,
    production: str,
    tokens: tuple[str, ...],
    position: int,
    k: int,
) -> int | None:
    available = min(k, len(tokens) - position)
    for length in range(available, -1, -1):
        prefix = tokens[position : position + length]
        for row in table.rows:
            if (
                row[0] == length
                and row[-2] == production
                and tuple(row[1 : 1 + length]) == prefix
            ):
                return int(row[-1])
    return None


def _legacy_generated_accepts(
    grammar: ResolvedGrammar,
    table: ValueTable,
    start: str,
    tokens: tuple[str, ...],
    k: int,
) -> bool:
    def parse(production: str, position: int) -> int | None:
        alternative = _legacy_choice(table, production, tokens, position, k)
        if alternative is None:
            return None
        current = position
        for symbol in grammar.productions[production][alternative - 1].symbols:
            if isinstance(symbol, ResolvedToken):
                if current >= len(tokens) or tokens[current] not in symbol.token_types:
                    return None
                current += 1
            else:
                assert isinstance(symbol, ResolvedNonterminal)
                nested = parse(symbol.name, current)
                if nested is None:
                    return None
                current = nested
        return current

    return parse(start, 0) == len(tokens)


def _cfg_accepts(
    grammar: ResolvedGrammar,
    start: str,
    tokens: tuple[str, ...],
) -> bool:
    def parse(production: str, position: int) -> frozenset[int]:
        ends: set[int] = set()
        for alternative in grammar.productions[production]:
            positions = {position}
            for symbol in alternative.symbols:
                next_positions: set[int] = set()
                for current in positions:
                    if isinstance(symbol, ResolvedToken):
                        if (
                            current < len(tokens)
                            and tokens[current] in symbol.token_types
                        ):
                            next_positions.add(current + 1)
                    else:
                        assert isinstance(symbol, ResolvedNonterminal)
                        next_positions.update(parse(symbol.name, current))
                positions = next_positions
            ends.update(positions)
        return frozenset(ends)

    return len(tokens) in parse(start, 0)
```

The oracle is intentionally limited to the acyclic audit grammar used by this
test; do not generalize it into production parser code.

- [ ] **Step 2: Add the executable runtime mismatch test**

```python
def test_legacy_generated_dispatch_rejects_the_canonical_counterexample(
    self,
) -> None:
    entries = {"Разобрать": "S"}
    parsed = parse_grammar(
        "<S> ::= <A>\n"
        "<A> ::= a <B> | a b d\n"
        "<B> ::= ПУСТО | b c"
    )
    assert parsed.grammar is not None
    resolution = resolve_grammar(parsed.grammar)
    assert resolution.grammar is not None
    grammar = resolution.grammar
    analysis = compute_analysis(grammar, 2, tuple(entries.values()))
    generated = generate_parser(parsed.grammar, grammar, analysis, entries)
    tokens = ("a", "b", "c")

    self.assertEqual(
        _legacy_choice(generated.select_table, "A", tokens, 0, 2),
        2,
    )
    self.assertFalse(
        _legacy_generated_accepts(grammar, generated.select_table, "S", tokens, 2)
    )
    self.assertTrue(_cfg_accepts(grammar, "S", tokens))
```

- [ ] **Step 3: Run the new runtime regression**

```powershell
python -m pytest tools/parsergen/tests/test_bsl_codegen.py -k "legacy_generated_dispatch" -v
```

Expected before API rename: PASS and demonstrate the known mismatch. This test
is characterization, not a request to change BSL runtime.

- [ ] **Step 4: Introduce the explicit artifact API**

```python
def build_legacy_matcher_artifact(
    analysis: AnalysisResult,
    *,
    max_rows: int,
) -> SelectMatcherArtifact:
    if analysis._compressed is None:
        raise ValueError("compressed analysis is required for matcher artifacts")
    return analysis._compressed.build_matcher_artifact(max_rows=max_rows)


def build_select_matcher_artifact(
    analysis: AnalysisResult,
    *,
    max_rows: int,
) -> SelectMatcherArtifact:
    return build_legacy_matcher_artifact(analysis, max_rows=max_rows)
```

Change `BslGenerator.generate()` to import and call
`build_legacy_matcher_artifact`. Do not alter `_select_table`, matcher rows or
templates.

- [ ] **Step 5: Verify codegen and reference artifacts**

```powershell
python -m pytest tools/parsergen/tests/test_bsl_codegen.py tools/parsergen/tests/test_reference_parser.py -q
```

Expected: PASS with unchanged snapshots/reference artifacts.

- [ ] **Step 6: Commit the legacy artifact boundary**

```powershell
git add -- tools/parsergen/src/parsergen/analysis.py tools/parsergen/src/parsergen/bsl_codegen.py tools/parsergen/tests/test_bsl_codegen.py
git commit -m "refactor: назвать legacy matcher artifact явно"
```

---

### Task 5: `complete` invariant and random canonical oracle

**Files:**
- Modify: `tools/parsergen/src/parsergen/analysis.py:369-373`
- Modify: `tools/parsergen/tests/test_nullable_first.py`
- Modify: `tools/parsergen/tests/test_follow_select.py:578-626`

**Interfaces:**
- Consumes: `_ContinuationFirst.variant_facts`, public FIRST/SELECT mappings, and independently materialized small SELECT sets.
- Produces: documented saturated-fact contract and property regression `symbolic conflicts == materialized intersections` for `k=1..3`.

- [ ] **Step 1: Add the saturated fact regression**

Add a private white-box test using `_ContinuationFirst`:

```python
def test_saturated_complete_flag_is_only_meaningful_for_short_facts(
    self,
) -> None:
    grammar = resolved("<X> ::= a <N>\n<N> ::= ПУСТО")
    solver = _ContinuationFirst(grammar, 1)
    solver.run_core()
    x_variant = solver.alternative_variant_ids[0]

    self.assertEqual(len(solver.variant_facts[x_variant]), 1)
    length, _, complete = solver.variant_facts[x_variant][0]
    self.assertEqual(length, 1)
    self.assertFalse(complete)

    result = compute_analysis(grammar, 1, ("X",))
    self.assertEqual(result.first["X"], frozenset({("a",)}))
    self.assertEqual(result.select[("X", 1)], frozenset({("a",)}))
```

Import `_ContinuationFirst` explicitly in this internal test module.

- [ ] **Step 2: Document the exact private contract**

Immediately above `_PackedFact`, add:

```python
# The boolean is semantically meaningful only while length < budget: True
# means the variant may finish at this short fact, so an outer RHS may resume.
# At length == budget it is deliberately ignored and may remain False even
# when a complete derivation exists with the same saturated k-prefix.
```

Do not alter `_process_frame`, `_process_resume`, FOLLOW or SELECT.

- [ ] **Step 3: Add independently materialized conflict oracle helper**

In `test_follow_select.py`, add:

```python
def _materialized_conflicts(grammar, select) -> tuple[SelectConflict, ...]:
    conflicts = []
    for production in grammar.production_order:
        alternatives = grammar.productions[production]
        for left in range(1, len(alternatives) + 1):
            for right in range(left + 1, len(alternatives) + 1):
                intersection = select[(production, left)].intersection(
                    select[(production, right)]
                )
                witness = min(
                    intersection,
                    key=lambda word: (len(word), word),
                    default=None,
                )
                if witness is not None:
                    conflicts.append(
                        SelectConflict(production, left, right, witness)
                    )
    return tuple(conflicts)
```

Inside the existing 200-seed × `k=1..3` oracle test, after comparing SELECT,
add:

```python
self.assertEqual(
    find_select_conflicts(grammar, optimized),
    _materialized_conflicts(grammar, oracle_select),
)
```

- [ ] **Step 4: Run invariant and property packages**

```powershell
python -m pytest tools/parsergen/tests/test_nullable_first.py tools/parsergen/tests/test_follow_select.py -q
```

Expected: PASS; the 600 random cases agree with the independent materialized oracle.

- [ ] **Step 5: Commit invariant and oracle coverage**

```powershell
git add -- tools/parsergen/src/parsergen/analysis.py tools/parsergen/tests/test_nullable_first.py tools/parsergen/tests/test_follow_select.py
git commit -m "test: закрепить invariants canonical анализа"
```

---

### Task 6: Production diagnostics, architecture docs and final verification

**Files:**
- Modify: `tools/parsergen/tests/test_repository_grammar.py`
- Modify: `docs/architecture/parser-generator.md`

**Interfaces:**
- Consumes: `find_select_conflicts`, `find_runtime_dispatch_conflicts`, production grammar and `parsergen.toml` entrypoints.
- Produces: stable expectation of exactly two canonical conflicts, zero legacy runtime-row collisions and documented API boundary.

- [ ] **Step 1: Replace the production zero-conflict assertion**

Use both production starts and assert:

```python
analysis = compute_analysis(
    grammar,
    2,
    ("ПакетЗапросов", "Выражение"),
)
self.assertEqual(
    find_select_conflicts(grammar, analysis),
    (
        SelectConflict(
            "ЛогическийОператор",
            2,
            5,
            ("ССЫЛКА", "АВТОУПОРЯДОЧИВАНИЕ"),
        ),
        SelectConflict("ОперандВ", 1, 2, ("ВЫБРАТЬ", "*")),
    ),
)
self.assertEqual(find_runtime_dispatch_conflicts(grammar, analysis), ())
self.assertEqual(stats["public_select_expansions"], 0)
self.assertEqual(stats["select_cartesian_materializations"], 0)
```

Import `SelectConflict` and `find_runtime_dispatch_conflicts`.

- [ ] **Step 2: Run the production regression**

```powershell
python -m pytest tools/parsergen/tests/test_repository_grammar.py -v
```

Expected: PASS and no SELECT materialization.

- [ ] **Step 3: Document canonical/legacy ownership**

Update `docs/architecture/parser-generator.md` to state:

```text
nullable/FIRST/FOLLOW/SELECT and LLK202 are canonical LL(k) contracts.
find_select_conflicts is representation-independent and intersects canonical
SELECT sets symbolically. Generated BSL intentionally consumes a separately
named legacy matcher artifact with longest exact-row lookup and nullable
fallback; that dispatch policy is not an LL(k) proof.
```

Document the two current production `LLK202` diagnostics and that grammar
repair/runtime language-preservation belongs to a separate task.

- [ ] **Step 4: Run the complete parsergen suite**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests -q
```

Expected: PASS.

- [ ] **Step 5: Run production validation and record the expected diagnostics**

```powershell
python -m parsergen validate --config parsergen.toml
```

Expected: exit code `1`; exactly two `LLK202` diagnostics with witnesses
`ССЫЛКА/АВТОУПОРЯДОЧИВАНИЕ` and `ВЫБРАТЬ/*`.

- [ ] **Step 6: Run generation check and record the expected validation gate**

```powershell
python -m parsergen generate --config parsergen.toml --check
```

Expected: exit code `1` with the same two `LLK202`; artifact comparison is not
reached because CLI validation is intentionally canonical.

- [ ] **Step 7: Prove protected files and legacy artifacts were not changed**

```powershell
git diff --exit-code 78878bd -- tools/parsergen/grammar/query-language.grammar 'QueryConsoleZUP/src/DataProcessors/Парсер' tools/parsergen/src/parsergen/templates/parser_module.bsl
git diff --check
```

Expected: both commands exit `0`.

- [ ] **Step 8: Commit production expectations and docs**

```powershell
git add -- tools/parsergen/tests/test_repository_grammar.py docs/architecture/parser-generator.md
git commit -m "docs: зафиксировать canonical и legacy контракты"
```

- [ ] **Step 9: Request independent review**

Dispatch `gpt-5.6-sol` reviewers for:

1. formal correctness and representation invariance of symbolic intersection;
2. API/validation boundary and legacy runtime isolation;
3. test completeness, production diagnostics and absence of hidden materialization.

Address only verified actionable findings, rerun the affected focused tests,
then repeat Steps 4–7 before publishing the result.
