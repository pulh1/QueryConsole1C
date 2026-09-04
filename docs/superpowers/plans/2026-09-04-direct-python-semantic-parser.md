# Direct Python Semantic Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заменить интерпретируемую task VM Python semantic target прямым детерминированным Python-кодом из оптимизированного `ParserIr`, сохранив публичный API, AST, spans, diagnostics и поведение scoped semantics.

**Architecture:** `ParserIr` остаётся единственным execution IR. Новый `direct_render_analysis.py` вычисляет только immutable side tables, `python_direct_codegen.py` рендерит productions/decision DAG в обычные Python-функции, а `python_semantic_codegen.py` остаётся небольшим публичным facade и владельцем схемы AST. Старый VM используется как временный differential oracle до переключения facade и полностью удаляется из финального дерева.

**Tech Stack:** Python 3.11+, frozen/slotted dataclasses, pytest 8+, существующие `ParserIr`, canonical decision DAG и parsergen CLI.

**Spec:** `docs/superpowers/specs/2026-09-04-direct-python-semantic-parser-design.md`

## Global Constraints

- Публичная сигнатура `generate_python_semantic_parser(source, parser_ir, entrypoints) -> GeneratedPythonSemanticParser` не меняется.
- `GeneratedPythonSemanticParser` остаётся frozen/slotted dataclass ровно с полями `module_text` и `ast_schema`.
- Новый публичный selector backend не добавляется; production Python target после cutover только direct.
- `ParserIr` не копируется в дополнительный execution plan; analysis хранит только адресуемые side tables.
- Direct rendering выполняется после текущего `optimize_parser_ir()` и не меняет canonical decision DAG.
- `parser_ir.py`, `parser_ir_optimization.py`, BSL grammar, canonical BSL renderer и production BSL artifacts не изменяются.
- Глобальный optimizer barrier для `AppendNearestOwner` остаётся в этой поставке.
- Generated module не импортирует parsergen и не содержит `PRODUCTIONS`, `DECISIONS`, `_Frame` или task tuples.
- Backend ID фиксирован как `python-semantic-direct-v1`.
- Большой VM artifact и мегабайтные golden-файлы в git не добавляются.
- Ни один production BSL artifact не должен изменить raw bytes.

---

### Task 1: Зафиксировать regression fences и immutable DirectRenderAnalysis

**Files:**
- Create: `tools/parsergen/src/parsergen/direct_render_analysis.py`
- Create: `tools/parsergen/tests/test_direct_render_analysis.py`
- Create: `tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py`

**Interfaces:**
- Consumes: уже оптимизированный `ParserIr` из `build_parser_ir()`.
- Produces: `analyze_direct_render(parser_ir: ParserIr) -> DirectRenderAnalysis` и стабильный `IrSite` для последующего renderer.

- [ ] **Step 1: Добавить raw-byte fence трёх BSL artifacts**

```python
from hashlib import sha256
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[3]
EXPECTED = {
    "QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl":
        "f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf",
    "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt":
        "e26a6b3b4fe08455462145de3243338d5da1c8bbb657321a2162b0abe541e208",
    "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt":
        "107fdbdefd57f5b6fe0658037b67806fc95f24a27d3e948eeeeaeb3335ffeff2",
}


def test_direct_python_work_keeps_raw_bsl_artifacts_byte_identical() -> None:
    assert {
        relative: sha256(
            subprocess.run(
                ["git", "show", f"HEAD:{relative}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
        ).hexdigest()
        for relative in EXPECTED
    } == EXPECTED
```

Тест хеширует LF bytes committed git blobs и не зависит от `core.autocrlf`; финальный `git diff --exit-code` отдельно ловит несохранённый worktree drift.

- [ ] **Step 2: Запустить characterization fence**

Run: `python -m pytest tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py -q`

Expected: PASS на исходном состоянии.

- [ ] **Step 3: Написать RED-тесты адресов и immutable side tables**

Зафиксировать в `test_direct_render_analysis.py` следующие типы и повторяемость анализа:

```python
def test_analysis_uses_stable_ir_sites_and_is_immutable() -> None:
    parser_ir = _build_ir("<S> ::= @Node Value = ITEM")
    first = analyze_direct_render(parser_ir)
    second = analyze_direct_render(parser_ir)
    assert first == second
    assert first.sequence_liveness[0].site == IrSite("S", 0, ())
    with pytest.raises(FrozenInstanceError):
        first.sequence_liveness = ()
```

Тест дополнительно рекурсивно проверяет, что ни одно поле результата не содержит `Operation`, `BranchIr`, `ProductionIr` или `CanonicalDecision`.

- [ ] **Step 4: Убедиться, что RED-тест падает по отсутствующему модулю**

Run: `python -m pytest tools/parsergen/tests/test_direct_render_analysis.py -k immutable -q`

Expected: FAIL с `ModuleNotFoundError: parsergen.direct_render_analysis`.

- [ ] **Step 5: Реализовать минимальные analysis types и стабильный обход**

```python
from dataclasses import dataclass
from typing import Literal

from .parser_ir import ParserIr

TrailKind = Literal[
    "operation", "region", "branch", "exit", "value", "value_branch",
    "seed", "base_branch", "recursive_branch",
]


@dataclass(frozen=True, slots=True)
class IrSite:
    production: str
    alternative: int | None
    trail: tuple[tuple[TrailKind, int], ...]


@dataclass(frozen=True, slots=True)
class SequenceLiveness:
    site: IrSite
    live_after: tuple[frozenset[int], ...]


@dataclass(frozen=True, slots=True)
class DecisionRenderFacts:
    site: IrSite
    node_indegrees: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DirectRenderAnalysis:
    sequence_liveness: tuple[SequenceLiveness, ...]
    mutable_owner_types: frozenset[str]
    recursive_calls: tuple["RecursiveCallSite", ...]
    decisions: tuple["DecisionRenderFacts", ...]


def analyze_direct_render(parser_ir: ParserIr) -> DirectRenderAnalysis:
    """Compute immutable rendering facts without copying executable IR."""
```

Путь строится только из индексов исходного `ParserIr`: operation sequence использует `("operation", index)`, branch — `("branch", index)`, nested bound value — `("value", 0)`. Обход включает `ResolvedRegion`, `Dispatch`, `DispatchValue`, `OptionalBranch`, `RepeatLoop`, `WrapOptional`, `WrapValue`, `LeftFold` и nested `AppendNearestOwner.value`. Test helper строит именно production `ParserIr`, а не промежуточную grammar:

```python
def _build_ir(source: str, *, k: int = 1) -> ParserIr:
    parsed = parse_grammar(source, "direct-test.grammar")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, k, ("S",))
    return build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )
```

- [ ] **Step 6: Добавить RED/GREEN для liveness, owner types и DAG in-degree**

Тесты должны доказать:

```python
assert analysis.mutable_owner_types == frozenset({"Owner"})
assert decision.node_indegrees == (0, 1, 2, 1)
assert sequence.live_after[result_index] == frozenset({result_index})
```

`DecisionRenderFacts` хранит `site: IrSite` и `node_indegrees: tuple[int, ...]`; in-degree вычисляется из `decision.dag.nodes[*].edges[*].target`, а не из outcomes.

Run: `python -m pytest tools/parsergen/tests/test_direct_render_analysis.py -k "liveness or owner or indegree or immutable" -q`

Expected: PASS.

- [ ] **Step 7: Проверить типы и сделать commit**

Run: `python -m compileall -q tools/parsergen/src/parsergen`

```powershell
git add tools/parsergen/src/parsergen/direct_render_analysis.py tools/parsergen/tests/test_direct_render_analysis.py tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
git commit -m "feat(parsergen): analyze direct Python rendering"
```

### Task 2: Классифицировать безопасный tail loop и production-local continuation

**Files:**
- Modify: `tools/parsergen/src/parsergen/direct_render_analysis.py`
- Modify: `tools/parsergen/tests/test_direct_render_analysis.py`

**Interfaces:**
- Consumes: `IrSite`, liveness и recursive production graph из Task 1.
- Produces: `RecursiveCallSite.kind`, равный `safe_tail_loop` или `local_continuation`, и минимальный `ContinuationLayout`.

- [ ] **Step 1: Написать failing classification matrix**

```python
@pytest.mark.parametrize(
    ("grammar", "expected"),
    [
        ("<S> ::= ITEM <S> | ПУСТО", "safe_tail_loop"),
        ("<S> ::= @Link Value = ITEM Rest = <S> | @End STOP", "local_continuation"),
    ],
)
def test_classifies_direct_self_recursion(grammar: str, expected: str) -> None:
    analysis = analyze_direct_render(_build_ir(grammar))
    assert analysis.recursive_calls[0].kind == expected


def test_open_constructor_prevents_tail_loop() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @Node Value = ITEM <S> | @End STOP")
    )
    assert all(site.kind != "safe_tail_loop" for site in analysis.recursive_calls)
```

Добавить отрицательные случаи для active wrap, left fold, collection receiver, pending freeze, mutual recursion и self-call с живым результатом после call.

- [ ] **Step 2: Запустить RED**

Run: `python -m pytest tools/parsergen/tests/test_direct_render_analysis.py -k "tail or continuation or recursive" -q`

Expected: FAIL, потому что `RecursiveCallSite` и `ContinuationLayout` ещё не реализованы.

- [ ] **Step 3: Реализовать exact analysis records**

```python
RecursiveKind = Literal["safe_tail_loop", "local_continuation"]


@dataclass(frozen=True, slots=True)
class ContinuationSlot:
    kind: Literal[
        "operation_result", "span_start", "builder_field",
        "wrap_seed", "fold_accumulator", "collection_accumulator",
    ]
    index: int | None


@dataclass(frozen=True, slots=True)
class ContinuationLayout:
    slots: tuple[ContinuationSlot, ...]


@dataclass(frozen=True, slots=True)
class RecursiveCallSite:
    site: IrSite
    kind: RecursiveKind
    layout: ContinuationLayout | None
```

`safe_tail_loop` разрешён только для direct self-call, после которого отсутствуют operations, implicit freeze, active constructor/span, wrap/fold/accumulator, pending scoped effect и живые locals. `local_continuation` разрешён только для direct right recursion внутри одной production; layout содержит лишь operation results, start offset, builder fields, wrap seed и fold/collection accumulators, действительно используемые обратным завершением. Generic receiver/_deliver state в analysis или runtime не вводится. Mutual-recursive SCC не преобразуются.

- [ ] **Step 4: Запустить classification suite**

Run: `python -m pytest tools/parsergen/tests/test_direct_render_analysis.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/parsergen/src/parsergen/direct_render_analysis.py tools/parsergen/tests/test_direct_render_analysis.py
git commit -m "feat(parsergen): classify direct recursion"
```

### Task 3: Сгенерировать прямой runtime skeleton и базовые semantic operations

**Files:**
- Create: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Create: `tools/parsergen/tests/test_python_direct_rendering.py`
- Modify: `tools/parsergen/src/parsergen/python_semantic_codegen.py:81-101`

**Interfaces:**
- Consumes: `AstNodeSchema`, `DirectRenderAnalysis`, optimized `ParserIr`.
- Produces: `render_direct_python_module(source, parser_ir, entrypoints, schema, analysis) -> str`.

- [ ] **Step 1: Написать RED-тест private differential seam**

```python
def _shape(value: object) -> object:
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple((field.name, _shape(getattr(value, field.name))) for field in fields(value)),
        )
    if isinstance(value, tuple):
        return tuple(_shape(item) for item in value)
    return value


def _execute(module_text: str, tokens: list[Token]) -> tuple[dict[str, object], object]:
    namespace: dict[str, object] = {}
    exec(compile(module_text, "<semantic-parser>", "exec"), namespace)
    result = namespace["GeneratedParser"]().parse(tokens, "start")
    return namespace, result


def _generated_pair(grammar: str, *, k: int = 1):
    parsed = parse_grammar(grammar, "direct-runtime-test.grammar")
    assert parsed.diagnostics == () and parsed.grammar is not None
    assert parsed.source_grammar is not None and parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == () and resolved.grammar is not None
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        compute_analysis(resolved.grammar, k, ("S",)),
        entrypoint_productions=("S",),
    )
    vm = generate_python_semantic_parser(
        parsed.source_grammar, parser_ir, {"start": "S"}
    )
    direct = _generate_direct_python_semantic_parser(
        parsed.source_grammar, parser_ir, {"start": "S"}
    )
    return vm, direct


def test_direct_module_compiles_and_preserves_runtime_shape() -> None:
    vm, direct = _generated_pair("<S> ::= ITEM")
    vm_namespace, vm_result = _execute(vm.module_text, [Token("ITEM")])
    direct_namespace, direct_result = _execute(direct.module_text, [Token("ITEM")])
    assert direct_result == vm_result == "ITEM"
    assert direct_namespace["GeneratedParser"]().parse([Token("ITEM")], "start") == "ITEM"
```

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k runtime_shape -q`

Expected: FAIL с отсутствующим `_generate_direct_python_semantic_parser`.

- [ ] **Step 2: Реализовать private seam, focused renderer и fixed runtime prelude**

В `python_semantic_codegen.py` добавить private seam, но публичный generator до Task 11 оставлять на VM:

```python
def _generate_direct_python_semantic_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> GeneratedPythonSemanticParser:
    _validate_entrypoints(parser_ir, entrypoints)
    schema = _SchemaBuilder(parser_ir).build()
    analysis = analyze_direct_render(parser_ir)
    return GeneratedPythonSemanticParser(
        render_direct_python_module(source, parser_ir, entrypoints, schema, analysis),
        schema,
    )
```

`python_direct_codegen.py` владеет только именованием и rendering; schema discovery остаётся в facade.

```python
PYTHON_SEMANTIC_BACKEND_ID = "python-semantic-direct-v1"


class _DirectPythonRenderer:
    def __init__(self, source, parser_ir, entrypoints, schema, analysis) -> None:
        self.source = source
        self.parser_ir = parser_ir
        self.entrypoints = dict(entrypoints)
        self.schema = schema
        self.analysis = analysis
        self.production_names = {
            item.name: f"_p_{index:04d}"
            for index, item in enumerate(parser_ir.productions)
        }

    def render(self) -> str:
        return "\n\n".join((self._render_prelude(), self._render_productions(), self._render_parser())) + "\n"


def render_direct_python_module(source, parser_ir, entrypoints, schema, analysis) -> str:
    return _DirectPythonRenderer(source, parser_ir, entrypoints, schema, analysis).render()
```

Чтобы не создать circular import, `python_direct_codegen.py` импортирует `AstNodeSchema` только внутри `if TYPE_CHECKING:`; в runtime annotations используются благодаря `from __future__ import annotations`, а schema objects только читаются.

Generated `GeneratedParser.parse()` материализует любой iterable один раз в tuple, сбрасывает cursor, вызывает функцию entrypoint и проверяет `$` full consumption. Production получает parser через `self`, фиксирует `start = self._offset()`, возвращает semantic value и не использует generic frames.

- [ ] **Step 3: Реализовать cursor и terminal-like operations**

Использовать следующие direct forms:

| `ParserIr` operation | Generated action |
|---|---|
| `ParseSymbol(NonterminalCall)` | `value_i = self._p_N()` |
| `ParseSymbol(Terminal/Lexeme/IdentifierRef/Constant)` | `value_i = self._consume(expected, capture)` |
| `DiscardSymbol(NonterminalCall)` | вызвать `_p_N()` и отбросить результат |
| `DiscardSymbol(terminal-like)` | `self._consume(expected, False)` |
| `ConsumeKnownSymbol` | один consume без повторного decision |
| `ResolvedRegion` | inline nested sequence with its exact `result_index` |
| `UndefinedValue`/`ReturnConstant` | existing canonical constant mapping: `Истина→True`, `Ложь→False`, `Неопределено→None`, иначе строка |

- [ ] **Step 4: Сравнить terminal/call matrix со старым VM**

Проверить equality для transparent production, discarded terminal, discarded nonterminal, multiple entrypoints, identifier/lexeme/terminal и canonical constants. Exact AST/spans относятся к Task 4, exact errors — к Task 5.

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k "core or terminal or input" -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/src/parsergen/python_semantic_codegen.py tools/parsergen/tests/test_python_direct_rendering.py
git commit -m "feat(parsergen): render direct Python productions"
```

### Task 4: Рендерить constructors, bindings и freeze через locals

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`

**Interfaces:**
- Consumes: existing `AstNodeSchema` objects и direct sequence renderer Task 3.
- Produces: direct constructor state без generic builder dict и exact immutable AST nodes.

- [ ] **Step 1: Написать RED binding matrix**

Один fixture обязан одновременно проверить `ConstructNode`, `BindScalar`, `AppendCollection`, `ExtendCollection`, `ConcatScalar`, `IncrementScalar`, `AssignConstant`, root `items` и freeze span. `_shape(direct_result) == _shape(vm_result)` является oracle; дополнительно generated source не содержит `builder.values` и `_Builder`.

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k bindings -q`

Expected: FAIL на первом binding operation.

- [ ] **Step 2: Рендерить schema fields как обычные Python locals**

Для `@Node Title = ... Items += ... Joined ~= ... Count ++= ...` generated alternative имеет форму:

```python
node_title = None
node_items = []
node_joined = ""
node_count = 0
node_title = value_0
node_items.append(value_1)
node_joined += value_2
node_count += 1
result = Node(node_title, tuple(node_items), node_joined, node_count, SourceSpan(start, self._end_offset(start)))
```

Имена locals выделяются renderer deterministically по schema order. `AssignConstant` использует тот же `_constant()` compile-time mapping, `ExtendCollection` вызывает `extend`, root collection использует field `items`. `AST_CLASSES`/`NODE_DEFAULTS` остаются read-only reflection metadata и не участвуют в freeze.

- [ ] **Step 3: Проверить nested regions и несовместимые schema bindings**

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_python_semantic_codegen.py -k "bindings or schema or region or frozen" -q`

Expected: PASS, включая существующие deterministic schema errors.

- [ ] **Step 4: Commit**

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/tests/test_python_direct_rendering.py
git commit -m "feat(parsergen): render direct AST bindings"
```

### Task 5: Рендерить canonical DAG, diagnostics и path facts

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`

**Interfaces:**
- Consumes: `DecisionRenderFacts.node_indegrees` и exact `CanonicalDecision`/`BranchIr.path_facts` из исходного IR.
- Produces: structured `if` для tree DAG и один state block для shared DAG.

- [ ] **Step 1: Написать exact error/DAG RED matrix**

```python
def _error_shape(parser: object, tokens: list[Token]) -> tuple[object, ...]:
    with pytest.raises(Exception) as caught:
        parser.parse(tokens, "start")
    error = caught.value
    return (
        type(error).__name__, error.args, error.position, error.actual, error.expected,
    )


@pytest.mark.parametrize(
    ("grammar", "tokens", "k"),
    [
        ("<S> ::= ITEM", [Token("BAD")], 1),
        ("<S> ::= ITEM", [], 1),
        ("<S> ::= ITEM", [Token("ITEM"), Token("ITEM")], 1),
        ("<S> ::= 'a' 'b' | 'a' 'c'", [Token("a"), Token("x")], 2),
        ("<S> ::= 'a' 'b' | 'c'", [Token("a"), Token("x")], 1),
    ],
)
def test_direct_errors_equal_vm_without_normalization(grammar, tokens, k) -> None:
    vm_parser, direct_parser = _parser_pair(grammar, k=k)
    assert _error_shape(direct_parser, tokens) == _error_shape(vm_parser, tokens)
```

`_parser_pair()` возвращает два parser instances:

```python
def _parser_pair(grammar: str, *, k: int = 1) -> tuple[object, object]:
    vm, direct = _generated_pair(grammar, k=k)
    vm_namespace = _execute_without_parse(vm.module_text)
    direct_namespace = _execute_without_parse(direct.module_text)
    return vm_namespace["GeneratedParser"](), direct_namespace["GeneratedParser"]()


def _execute_without_parse(module_text: str) -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(compile(module_text, "<semantic-parser>", "exec"), namespace)
    return namespace
```

`_execute_without_parse()` не запускает parser. Дополнительные tests используют `#Name ::= ID` для identifier mismatch и вызывают `parse(tokens, "missing")` для exact unknown-entrypoint `ValueError`. Optional/repeat exits проверяются как successful control paths в Task 6. Shared fixture задаёт `CanonicalDecisionDag(root=0)` с edges `0→1`, `0→2`, `1→3`, `2→3`: node 3 имеет in-degree 2 и рендерится единожды. Отдельная optimized grammar fixture из `ParserIrSpecializationTests.PATH_FACTS_GRAMMAR` содержит две branches с одинаковым outcome и разными `path_facts`.

- [ ] **Step 2: Запустить RED**

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k "decision or error or path_facts" -q`

Expected: FAIL на первом ещё не поддержанном control operation.

- [ ] **Step 3: Реализовать decision rendering**

Для tree DAG рендерить nested `if/elif`; `LookaheadDecision.offset` читает token type либо `$`. Для shared node создать один local state loop:

```python
decision_state = ROOT_INDEX
while True:
    if decision_state == 0:
        if self._type_at(OFFSET) in TOKEN_TYPES:
            decision_state = TARGET
            continue
        raise self._syntax_error(EXPECTED)
    if decision_state == COMMIT:
        outcome = (PRODUCTION, ALTERNATIVE)
        break
```

Не сливать branches только по outcome. `ImmediateError` использует точный `node.expected`; `ExitDecision` возвращает exit outcome без consume. Выбор semantic branch после outcome выполняется отдельной ordered проверкой path facts в Step 4.

- [ ] **Step 4: Реализовать branch selection по path facts**

Decision renderer возвращает outcome; затем generated branches проверяются в исходном `BranchIr` order. Branch подходит, когда outcome совпал и `path_facts is None` либо каждый `(offset, predicate.token_types)` совпал с текущим lookahead. Это exact direct equivalent текущего VM `_select_branch()`; dictionary lookup только по outcome запрещён.

- [ ] **Step 5: Запустить focused diagnostics tests**

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_python_semantic_codegen.py -k "decision or dag or path_facts or error" -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/tests/test_python_direct_rendering.py
git commit -m "feat(parsergen): render direct semantic control flow"
```

### Task 6: Рендерить dispatch, optional и repeat

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`

**Interfaces:**
- Consumes: exact decision/outcome/path-fact selection Task 5.
- Produces: direct `Dispatch`, `DispatchValue`, `ParseBranchValue`, `OptionalBranch` и iterative `RepeatLoop`.

- [ ] **Step 1: Написать RED control-flow matrix**

Сравнить `_shape()` с VM для двух-way dispatch, value dispatch, optional present/exit, repeat empty/one/5,000 и nested parse-branch result index. Counting token fixture доказывает единственный consume/capture.

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k "dispatch or optional or repeat" -q`

Expected: FAIL на unsupported control operation.

- [ ] **Step 2: Реализовать direct control flow**

- `Dispatch`/`DispatchValue`: decision один раз, branch selection Task 5, затем inline sequence/value.
- `ParseBranchValue`: inline nested sequence и exact `result_index`.
- `OptionalBranch`: exit выполняет `exit_operations`, present — выбранную branch.
- `RepeatLoop`: ordinary `while`, decision перед каждой итерацией, exit завершает loop; после branch проверять продвижение cursor тем же deterministic error, что VM.

- [ ] **Step 3: Проверить 5,000 repeat и parser reuse**

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_python_semantic_codegen.py -k "dispatch or optional or repeat or reuse" -q`

Expected: PASS без изменения recursion limit.

- [ ] **Step 4: Commit**

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/tests/test_python_direct_rendering.py
git commit -m "feat(parsergen): render direct semantic branches"
```

### Task 7: Рендерить wraps и left fold

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`

**Interfaces:**
- Consumes: direct branch/value renderer Task 6.
- Produces: `WrapValue`, `WrapOptional` и iterative `LeftFold` с exact accumulator/spans.

- [ ] **Step 1: Написать RED wrap/fold matrix**

Проверить required/optional/prepend wraps, absent optional identity, multi-constructor wrapper schema и 2,000-operator left-associative AST против VM structural shape.

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k "wrap or left_fold" -q`

Expected: FAIL на unsupported wrap/fold.

- [ ] **Step 2: Реализовать wraps и fold**

`WrapValue` сохраняет seed local, разбирает bound value и freeze wrapper с исходным wrapper span; prepend создаёт tuple с seed первым. `WrapOptional` возвращает seed при exit. `LeftFold` разбирает base один раз, хранит `fold_accumulator` local и выполняет recursive decision в `while`, подставляя `FoldLeftValue` без recursive Python call.

- [ ] **Step 3: Прогнать focused tests и commit**

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_python_semantic_codegen.py -k "wrap or left_fold" -q`

Expected: PASS.

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/tests/test_python_direct_rendering.py
git commit -m "feat(parsergen): render direct wraps and folds"
```

### Task 8: Рендерить безопасную self-tail recursion как loop

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`
- Modify: `tools/parsergen/tests/test_python_semantic_codegen.py:330-340`

**Interfaces:**
- Consumes: `RecursiveCallSite(kind="safe_tail_loop")` из Task 2.
- Produces: iterative generated code для syntax-only self-tail recursion.

- [ ] **Step 1: Перевести существующий 5,000 syntax-only test на direct seam**

Grammar `<S> ::= ITEM <Tail>` / `<Tail> ::= ITEM <Tail> | ПУСТО` разбирает 5,000 `ITEM`, возвращает `None`, не меняет `sys.getrecursionlimit()` и generated source не содержит recursive call в tail site.

- [ ] **Step 2: Запустить RED**

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k safe_tail -q`

Expected: FAIL с `RecursionError`.

- [ ] **Step 3: Рендерить безопасный self-tail call как while**

Production с `safe_tail_loop` получает внешний `while True`; self-call site присваивает новые parameters/locals, сбрасывает iteration start и выполняет `continue`. Discarded result сам по себе не даёт разрешение: renderer доверяет только exact site из analysis.

- [ ] **Step 4: Проверить отрицательный constructor case**

Grammar `<S> ::= @Node Value = ITEM Rest = <S> | @End STOP` не классифицируется как safe tail. Generated renderer не применяет tail transform к неизвестному site.

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k safe_tail -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_python_semantic_codegen.py
git commit -m "feat(parsergen): iterate safe direct tail calls"
```

### Task 9: Рендерить value-carrying right recursion через local continuation

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`

**Interfaces:**
- Consumes: `RecursiveCallSite(kind="local_continuation")` и `ContinuationLayout` из Task 2.
- Produces: production-local continuation stack без generic VM receiver/tasks.

- [ ] **Step 1: Написать RED 5,000 linked-node test с реальными offsets**

```python
def _direct_parser(grammar: str) -> object:
    _, direct = _generated_pair(grammar)
    namespace = _execute_without_parse(direct.module_text)
    return namespace["GeneratedParser"]()


def test_value_carrying_right_recursion_builds_5000_linked_nodes() -> None:
    parser = _direct_parser("<S> ::= @Link Value = ITEM Rest = <S> | @End STOP")
    tokens = [Token("ITEM", start=index, end=index + 1) for index in range(5_000)]
    tokens.append(Token("STOP", start=5_000, end=5_001))
    node = parser.parse(tokens, "start")
    count = 0
    while type(node).__name__ == "Link":
        assert node.span.start == count
        count += 1
        node = node.Rest
    assert count == 5_000
    assert type(node).__name__ == "End"
```

- [ ] **Step 2: Запустить RED**

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k value_carrying_right_recursion -q`

Expected: FAIL с `RecursionError`.

- [ ] **Step 3: Реализовать production-local continuation**

Для production с `local_continuation` создать локальный `continuations = []`. Перед self-call append tuple ровно по `ContinuationLayout`; продолжить разбор следующего звена в том же production loop. После base result generated production-local unwind block выполняет:

```python
while continuations:
    saved = continuations.pop()
    result = finish_site_0(saved, result)
return result
```

`finish_site_0` генерируется внутри той же production из исходного `ParserIr`: восстанавливает только declared layout slots, bind рекурсивного result, выполняет оставшиеся semantic actions и freeze. Он не принимает generic receiver и не интерпретирует operations.

- [ ] **Step 4: Проверить freeze/span/error order**

В differential test временно подменить VM/direct AST class recording factory и сравнить последовательность `(constructor, span)`; injected freeze failure должен возникнуть на одном и том же node. После Task 11 эти fixtures остаются самостоятельными exact assertions, VM import удаляется.

Run: `python -m pytest tools/parsergen/tests/test_python_direct_rendering.py -k "tail or continuation or right_recursion or linked or freeze" -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_python_semantic_codegen.py
git commit -m "feat(parsergen): iterate value-carrying recursion"
```

### Task 10: Сохранить scoped nearest-owner semantics

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/tests/test_scoped_append_python_runtime.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`

**Interfaces:**
- Consumes: `DirectRenderAnalysis.mutable_owner_types` и исходные `AppendNearestOwner` operations.
- Produces: typed owner stacks и deferred append queue в generated parser; optimizer остаётся без изменений.

- [ ] **Step 1: Зафиксировать optimizer barrier и написать nested-effect RED test**

Run: `python -m pytest tools/parsergen/tests/test_scoped_append_parser_ir.py -q`

Expected: PASS до изменений.

Добавить direct fixture, где nested production делает scoped append до и после effect внешней production; ожидаемый порядок определяется `(source_order, enqueue_sequence)`.

- [ ] **Step 2: Перевести fault injection с VM metadata на direct symbols**

Freeze error инъецируется заменой прямого generated class symbol `Owner`; append error — заменой owner-state collection на объект, чей `append()` бросает `RuntimeError`. Не мутировать `AST_CLASSES`/`NODE_DEFAULTS`, потому что direct execution их не читает.

- [ ] **Step 3: Реализовать owner state и deferred queue**

Для каждого типа из `mutable_owner_types` generated parser содержит отдельный stack активных builders. `AppendNearestOwner`:

```python
owner = owner_stack[-1] if owner_stack else None
payload = evaluate_once()
if owner is not None:
    self._enqueue_sequence += 1
    owner.pending.append((source_order, self._enqueue_sequence, property_name, payload))
```

Перед freeze pending сортируются по первым двум полям и применяются; owner снимается со stack до outward delivery. Общий `finally` в `parse()` очищает все owner stacks, pending queues и `_enqueue_sequence`, в том числе после syntax/freeze/append error. Missing owner — no-op, payload result сохраняется.

- [ ] **Step 4: Прогнать scoped parity**

Run: `python -m pytest tools/parsergen/tests/test_scoped_append_python_runtime.py tools/parsergen/tests/test_scoped_append_backend_fences.py tools/parsergen/tests/test_scoped_append_parser_ir.py -q`

Expected: PASS для shadowing, FIFO, repeat taps, wraps, missing owner и parser reuse.

- [ ] **Step 5: Commit**

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/tests/test_scoped_append_python_runtime.py tools/parsergen/tests/test_python_direct_rendering.py
git commit -m "feat(parsergen): preserve scoped append in direct target"
```

### Task 11: Добавить backend/marker seams и переключить public facade

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/src/parsergen/python_semantic_codegen.py`
- Modify: `tools/parsergen/tests/test_python_semantic_codegen.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`
- Modify: `tools/parsergen/tests/test_separated_semantics_legacy.py`

**Interfaces:**
- Consumes: полностью функциональный direct renderer Tasks 3-10.
- Produces: единственный production direct target с backend ID и двумя stable consumer sections.

- [ ] **Step 1: Написать artifact-shape tests**

```python
FORBIDDEN = (
    "PRODUCTIONS =", "DECISIONS =", "class _Frame", "_run_sequence",
    "_run_operation", "_deliver", "_start_call",
)


def test_generated_module_is_direct_and_has_stable_consumer_seams() -> None:
    text = _generate("<S> ::= @Node Value = ITEM")[2].module_text
    assert 'PARSERGEN_BACKEND_ID = "python-semantic-direct-v1"' in text
    assert text.count("# <parsergen:source-span>") == 1
    assert text.count("# </parsergen:source-span>") == 1
    assert text.count("# <parsergen:artifact-metadata>") == 1
    assert text.count("# </parsergen:artifact-metadata>") == 1
    assert all(symbol not in text for symbol in FORBIDDEN)
    assert "import parsergen" not in text
```

Обновить legacy test: frozen остаются dataclass shapes и `GeneratedParser.parse(tokens, entrypoint)`, но старый VM byte SHA больше не является совместимостью и заменяется assert backend ID/direct symbols.

- [ ] **Step 2: Добавить markers в generated prelude**

Generated fragment должен быть ровно:

```python
PARSERGEN_BACKEND_ID = "python-semantic-direct-v1"

# <parsergen:artifact-metadata>
# </parsergen:artifact-metadata>

# <parsergen:source-span>
@dataclass(frozen=True, slots=True)
class SourceSpan:
    start: int
    end: int
# </parsergen:source-span>
```

- [ ] **Step 3: Переключить facade и удалить VM**

`generate_python_semantic_parser()` вызывает `_generate_direct_python_semantic_parser()`. Удалить `_SemanticGenerator`, serializers decisions/operations, `_RUNTIME_TEMPLATE`, `_SCOPED_RUNTIME_TEMPLATE`, `_Builder`, `_Frame` и task dispatcher text. Private differential seam можно оставить только как маленький alias facade→direct; test oracle больше не импортируется.

- [ ] **Step 4: Проверить standalone import и hash determinism**

Subprocess сохраняет `module_text` во временный каталог, запускается с пустым `PYTHONPATH`, импортирует его и разбирает token fixture. Второй subprocess с `PYTHONHASHSEED=1/3` должен вернуть одинаковый SHA-256 generated bytes.

Run: `python -m pytest tools/parsergen/tests/test_python_semantic_codegen.py tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_separated_semantics_legacy.py -q`

Expected: PASS; grep generated source не находит VM symbols.

- [ ] **Step 5: Commit**

```powershell
git add tools/parsergen/src/parsergen/python_direct_codegen.py tools/parsergen/src/parsergen/python_semantic_codegen.py tools/parsergen/tests/test_python_semantic_codegen.py tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_separated_semantics_legacy.py
git commit -m "feat(parsergen): switch Python semantics to direct code"
```

### Task 12: Документация, полная регрессия и parsergen structural evidence

**Files:**
- Modify: `docs/architecture/parser-generator.md:753-789`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`

**Interfaces:**
- Consumes: финальный direct target.
- Produces: проверенный parsergen commit, готовый к независимому review и merge до consumer-интеграции.

- [ ] **Step 1: Обновить архитектурную документацию**

Описать pipeline `optimized ParserIr -> DirectRenderAnalysis -> direct renderer`, production-local continuation, stable markers и то, что scoped optimizer barrier пока сохраняется. Удалить описание `while tasks:` VM.

- [ ] **Step 2: Добавить только structural complexity fences**

Generated module для shared-DAG fixture должен содержать каждый shared state block один раз, а размер series из DAG fixtures должен расти линейно по числу уникальных nodes, не по числу paths. Реальные gates `<=60 calls/token`, direct `<=4x` frozen VM, cold/warm p95 и full BSL profile остаются обязательными в связанном Onec Runtime plan, где frozen VM привязан к точному git ref и SHA; синтетический pytest не выдаётся за performance acceptance.

- [ ] **Step 3: Запустить полный parsergen suite**

Run: `python -m pytest tools/parsergen/tests -q -p no:cacheprovider`

Expected: PASS.

- [ ] **Step 4: Проверить compile и repository generation без записи**

```powershell
python -m compileall -q tools/parsergen/src/parsergen
$env:PYTHONPATH = (Resolve-Path 'tools/parsergen/src')
python -m parsergen validate --config parsergen.toml
python -m parsergen generate --config parsergen.toml --check
```

Expected: exit code 0 для всех команд.

- [ ] **Step 5: Повторно проверить raw hashes и нулевой BSL diff**

Run: `python -m pytest tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py -q`

```powershell
$artifacts = @(
  'QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl',
  'QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt',
  'QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt'
)
git diff --exit-code -- $artifacts
```

Expected: test PASS и пустой diff.

- [ ] **Step 6: Commit docs/tests и запросить независимое review**

```powershell
git add docs/architecture/parser-generator.md tools/parsergen/tests/test_python_direct_rendering.py
git commit -m "docs(parsergen): document direct Python target"
```

На review передать spec, этот plan, `git diff` всей ветки, результаты full suite, raw hashes, call/token и generated-size fences. Parsergen PR не включает runtime benchmark и не заявляет общий hot-reload `<2.5 с`.
