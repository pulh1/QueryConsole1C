from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace

import pytest

from parsergen.analysis import compute_analysis
from parsergen.canonical_select import AlternativeOutcome, TokenSetPredicate
from parsergen.decision_dag import (
    CanonicalDecisionDag,
    CommitAlternative,
    DecisionEdge,
    LookaheadDecision,
)
from parsergen.grammar_parser import parse_grammar
from parsergen.direct_render_analysis import analyze_direct_render
from parsergen.parser_ir import (
    AssignConstant,
    CanonicalDecision,
    OptionalBranch,
    RepeatLoop,
    ResolvedRegion,
    UndefinedValue,
    WrapOptional,
    build_parser_ir,
)
from parsergen.python_direct_codegen import _DirectPythonRenderer
from parsergen.python_semantic_codegen import (
    _generate_direct_python_semantic_parser,
    generate_python_semantic_parser,
)
from parsergen.resolver import resolve_grammar


@dataclass(frozen=True)
class Token:
    type: str
    text: str = ""
    start: int = 0
    end: int = 0
    value: object | None = None


class CountingToken:
    def __init__(self, value: object) -> None:
        self.type = "NUMBER"
        self.text = str(value)
        self.start = 0
        self.end = 0
        self._value = value
        self.value_reads = 0

    @property
    def value(self) -> object:
        self.value_reads += 1
        return self._value


class ProgressProbeToken:
    def __init__(self) -> None:
        self.text = ""
        self.start = 0
        self.end = 0
        self._type_reads = 0

    @property
    def type(self) -> str:
        self._type_reads += 1
        return "A" if self._type_reads <= 2 else "$"


def _shape(value: object) -> object:
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple((field.name, _shape(getattr(value, field.name))) for field in fields(value)),
        )
    if isinstance(value, tuple):
        return tuple(_shape(item) for item in value)
    return value


def _execute(
    module_text: str,
    tokens: list[Token],
    entrypoint: str = "start",
) -> tuple[dict[str, object], object]:
    namespace: dict[str, object] = {}
    exec(compile(module_text, "<semantic-parser>", "exec"), namespace)
    result = namespace["GeneratedParser"]().parse(tokens, entrypoint)
    return namespace, result


def _execute_without_parse(module_text: str) -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(compile(module_text, "<semantic-parser>", "exec"), namespace)
    return namespace


def _generated_pair(
    grammar: str,
    *,
    k: int = 1,
    entrypoints: dict[str, str] | None = None,
):
    parsed = parse_grammar(grammar, "direct-runtime-test.grammar")
    assert parsed.diagnostics == () and parsed.grammar is not None
    assert parsed.source_grammar is not None and parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == () and resolved.grammar is not None
    mapping = {"start": "S"} if entrypoints is None else entrypoints
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        compute_analysis(resolved.grammar, k, tuple(mapping.values())),
        entrypoint_productions=tuple(mapping.values()),
    )
    vm = generate_python_semantic_parser(parsed.source_grammar, parser_ir, mapping)
    direct = _generate_direct_python_semantic_parser(
        parsed.source_grammar,
        parser_ir,
        mapping,
    )
    return vm, direct, parser_ir, parsed.source_grammar


def _parser_pair(grammar: str, *, k: int = 1) -> tuple[object, object]:
    vm, direct, _, _ = _generated_pair(grammar, k=k)
    vm_namespace = _execute_without_parse(vm.module_text)
    direct_namespace = _execute_without_parse(direct.module_text)
    return vm_namespace["GeneratedParser"](), direct_namespace["GeneratedParser"]()


def _error_shape(parser: object, tokens: list[Token]) -> tuple[object, ...]:
    with pytest.raises(Exception) as caught:
        parser.parse(tokens, "start")
    error = caught.value
    return (
        type(error).__name__,
        error.args,
        error.position,
        error.actual,
        error.expected,
    )


def test_direct_module_compiles_and_preserves_runtime_shape() -> None:
    vm, direct, _, _ = _generated_pair("<S> ::= ITEM")
    vm_namespace, vm_result = _execute(vm.module_text, [Token("ITEM")])
    direct_namespace, direct_result = _execute(direct.module_text, [Token("ITEM")])

    assert _shape(direct_result) == _shape(vm_result) is None
    assert direct_namespace["GeneratedParser"]().parse([Token("ITEM")], "start") is None
    assert vm_namespace["GeneratedParser"]().parse([Token("ITEM")], "start") is None


def test_direct_captured_terminal_matches_vm() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= ITEM")
    production = parser_ir.productions[0]
    captured_ir = replace(
        parser_ir,
        productions=(
            replace(
                production,
                alternatives=(replace(production.alternatives[0], result_index=0),),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, captured_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, captured_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [Token("ITEM")])
    _, direct_result = _execute(direct.module_text, [Token("ITEM")])
    assert _shape(direct_result) == _shape(vm_result) == "ITEM"


@pytest.mark.parametrize(
    ("grammar", "tokens", "expected"),
    [
        ("<S> ::= ITEM -= JUNK", [Token("ITEM"), Token("JUNK")], None),
        (
            "<S> ::= ITEM -= <Discarded>\n<Discarded> ::= JUNK",
            [Token("ITEM"), Token("JUNK")],
            None,
        ),
        ("#Name ::= ID\n<S> ::= #Name", [Token("ID", "Name")], "Name"),
        ("<S> ::= '+'", [Token("+")], None),
        ("<S> ::= &NUMBER", [Token("NUMBER", "42", value=42)], 42),
        ("<S> ::= &NUMBER", [Token("NUMBER", "42")], "42"),
    ],
    ids=(
        "discarded-terminal",
        "discarded-nonterminal",
        "identifier",
        "lexeme",
        "constant-value",
        "constant-text-fallback",
    ),
)
def test_direct_core_terminal_operations_match_vm(
    grammar: str,
    tokens: list[Token],
    expected: object,
) -> None:
    vm, direct, _, _ = _generated_pair(grammar)
    _, vm_result = _execute(vm.module_text, tokens)
    _, direct_result = _execute(direct.module_text, tokens)

    assert _shape(direct_result) == _shape(vm_result) == expected


@pytest.mark.parametrize(
    ("constant", "expected"),
    [("Истина", True), ("Ложь", False), ("Неопределено", None), ("Kinds.Value", "Kinds.Value")],
)
def test_direct_canonical_return_constants_match_vm(
    constant: str,
    expected: object,
) -> None:
    vm, direct, _, _ = _generated_pair(f"<S> ::= := {constant}")
    _, vm_result = _execute(vm.module_text, [])
    _, direct_result = _execute(direct.module_text, [])

    assert _shape(direct_result) == _shape(vm_result) == expected


def test_direct_undefined_value_matches_vm() -> None:
    vm, direct, parser_ir, source = _generated_pair("<S> ::= := Неопределено")
    alternative = parser_ir.productions[0].alternatives[0]
    undefined = UndefinedValue("Неопределено", alternative.operations[0].source_span)
    undefined_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(replace(alternative, operations=(undefined,)),),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, undefined_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, undefined_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [])
    _, direct_result = _execute(direct.module_text, [])
    assert _shape(direct_result) == _shape(vm_result) is None


def test_direct_parser_reuses_iterable_input_and_checks_full_consumption() -> None:
    _, direct, _, _ = _generated_pair("<S> ::= ITEM")
    namespace: dict[str, object] = {}
    exec(compile(direct.module_text, "<semantic-parser>", "exec"), namespace)
    parser = namespace["GeneratedParser"]()

    assert parser.parse(iter([Token("ITEM")]), "start") is None
    assert parser.parse([Token("ITEM")], "start") is None
    with pytest.raises(namespace["GeneratedParseError"]) as caught:
        parser.parse([Token("ITEM"), Token("ITEM")], "start")
    assert caught.value.position == 1
    assert caught.value.actual == "ITEM"
    assert caught.value.expected == ("$",)


@pytest.mark.parametrize(
    ("grammar", "tokens", "k"),
    [
        ("<S> ::= ITEM", [Token("BAD")], 1),
        ("<S> ::= ITEM", [], 1),
        ("<S> ::= ITEM", [Token("ITEM"), Token("ITEM")], 1),
        ("<S> ::= 'a' 'b' | 'a' 'c'", [Token("a"), Token("x")], 2),
        ("<S> ::= 'a' 'b' | 'c'", [Token("a"), Token("x")], 1),
    ],
    ids=("bad", "eof", "trailing", "k2", "committed"),
)
def test_direct_errors_equal_vm_without_normalization(
    grammar: str,
    tokens: list[Token],
    k: int,
) -> None:
    vm_parser, direct_parser = _parser_pair(grammar, k=k)

    assert _error_shape(direct_parser, tokens) == _error_shape(vm_parser, tokens)


def test_direct_identifier_mismatch_error_equals_vm_without_normalization() -> None:
    vm_parser, direct_parser = _parser_pair("#Name ::= ID\n<S> ::= #Name")

    assert _error_shape(direct_parser, [Token("BAD")]) == _error_shape(
        vm_parser,
        [Token("BAD")],
    )


def test_direct_unknown_entrypoint_error_equals_vm_without_normalization() -> None:
    vm_parser, direct_parser = _parser_pair("<S> ::= ITEM")

    with pytest.raises(Exception) as vm_caught:
        vm_parser.parse([], "missing")
    with pytest.raises(Exception) as direct_caught:
        direct_parser.parse([], "missing")

    assert (
        type(direct_caught.value).__name__,
        direct_caught.value.args,
    ) == (
        type(vm_caught.value).__name__,
        vm_caught.value.args,
    )


def test_direct_shared_decision_dag_renders_the_shared_node_once() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= A | B")
    original = parser_ir.productions[0]
    assert original.decision is not None
    dag = CanonicalDecisionDag(
        "S",
        2,
        0,
        (
            LookaheadDecision(
                0,
                ("A", "B"),
                (
                    DecisionEdge(TokenSetPredicate(("A",)), 1),
                    DecisionEdge(TokenSetPredicate(("B",)), 2),
                ),
            ),
            LookaheadDecision(
                1,
                ("C",),
                (DecisionEdge(TokenSetPredicate(("C",)), 3),),
            ),
            LookaheadDecision(
                1,
                ("D",),
                (DecisionEdge(TokenSetPredicate(("D",)), 3),),
            ),
            CommitAlternative(AlternativeOutcome("S", 1)),
        ),
        {},
    )
    decision = CanonicalDecision(original.decision.source, dag)
    shared_ir = replace(
        parser_ir,
        productions=(replace(original, decision=decision),),
    )

    direct = _generate_direct_python_semantic_parser(source, shared_ir, {"start": "S"})

    assert direct.module_text.count("decision_state == 3") == 1


def test_direct_path_facts_select_in_original_branch_order() -> None:
    grammar = (
        "<S> ::= <Base> Child => <Choice>?\n"
        "<Base> ::= @NewBase BASE\n"
        "<Choice> ::= @NewBetween (NOT Inverted := Истина)? BETWEEN <Tail>\n"
        "<Choice> ::= @NewIn (NOT Inverted := Истина)? IN <Tail>\n"
        "<Tail> ::= VALUE"
    )
    parsed = parse_grammar(grammar, "path-facts.grammar")
    assert parsed.diagnostics == () and parsed.grammar is not None
    assert parsed.source_grammar is not None and parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == () and resolved.grammar is not None
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        compute_analysis(resolved.grammar, 2, ("S",)),
        entrypoint_productions=("S",),
    )
    wrapper = parser_ir.productions[0].alternatives[0].operations[0]
    assert isinstance(wrapper, WrapOptional)
    outcome = AlternativeOutcome("Choice", 1)
    outcome_key = (outcome.production, outcome.alternative)
    specialized = tuple(
        branch for branch in wrapper.branches if branch.outcome == outcome
    )
    assert len(specialized) == 2
    renderer = _DirectPythonRenderer(
        parsed.source_grammar,
        parser_ir,
        {"start": "S"},
        (),
        analyze_direct_render(parser_ir),
    )

    lines = renderer._render_branch_selection(
        wrapper.branches,
        "outcome",
        "    ",
        lambda branch, indent: [f"{indent}return {wrapper.branches.index(branch)!r}"],
    )
    namespace: dict[str, object] = {}
    exec(
        compile(
            "def select(self, outcome):\n" + "\n".join(lines),
            "<path-facts-selector>",
            "exec",
        ),
        namespace,
    )

    class Probe:
        def __init__(self, token_types: tuple[str, ...]) -> None:
            self.token_types = token_types

        def _type_at(self, offset: int) -> str:
            return self.token_types[offset] if offset < len(self.token_types) else "$"

    select = namespace["select"]
    between_index = wrapper.branches.index(specialized[0])
    not_between_index = wrapper.branches.index(specialized[1])
    assert select(Probe(("BETWEEN",)), outcome_key) == between_index
    assert select(Probe(("NOT", "BETWEEN")), outcome_key) == not_between_index

    generic_first = replace(specialized[0], path_facts=None)
    ordered_lines = renderer._render_branch_selection(
        (generic_first, specialized[0]),
        "outcome",
        "    ",
        lambda branch, indent: [
            f"{indent}return {'generic' if branch is generic_first else 'specialized'!r}"
        ],
    )
    ordered_namespace: dict[str, object] = {}
    exec(
        compile(
            "def select_ordered(self, outcome):\n" + "\n".join(ordered_lines),
            "<ordered-path-facts-selector>",
            "exec",
        ),
        ordered_namespace,
    )
    assert ordered_namespace["select_ordered"](
        Probe(("BETWEEN",)), outcome_key
    ) == "generic"


def test_direct_parser_supports_multiple_entrypoints() -> None:
    vm, direct, _, _ = _generated_pair(
        "<S> ::= ITEM\n<A> ::= OTHER",
        entrypoints={"start": "S", "other": "A"},
    )
    _, vm_result = _execute(vm.module_text, [Token("OTHER")], "other")
    namespace, direct_result = _execute(direct.module_text, [Token("OTHER")], "other")

    assert _shape(direct_result) == _shape(vm_result) is None
    assert namespace["GeneratedParser"]().parse([Token("ITEM")], "start") is None


def test_direct_constructor_bindings_match_vm_and_freeze_schema_order() -> None:
    vm, direct, _, _ = _generated_pair(
        "#Name ::= ID\n"
        "<S> ::= @Node Title = #Name Items += ITEM Joined ~= #Name "
        "Count ++= MARK Enabled := Истина Values *= <Values>\n"
        "<Values> ::= @Values += ITEM += ITEM"
    )
    tokens = [
        Token("ID", "Title", 0, 5),
        Token("ITEM", start=6, end=10),
        Token("ID", "Tail", 11, 15),
        Token("MARK", start=16, end=17),
        Token("ITEM", start=18, end=22),
        Token("ITEM", start=23, end=27),
    ]

    _, vm_result = _execute(vm.module_text, tokens)
    direct_namespace, direct_result = _execute(direct.module_text, tokens)

    assert _shape(direct_result) == _shape(vm_result)
    assert direct_result.span == direct_namespace["SourceSpan"](0, 27)
    assert direct_result.Values == ("ITEM", "ITEM")
    assert "builder.values" not in direct.module_text
    assert "_Builder" not in direct.module_text
    assert "AST_CLASSES[" not in direct.module_text
    assert "NODE_DEFAULTS[" not in direct.module_text

    direct_namespace["AST_CLASSES"] = {}
    direct_namespace["NODE_DEFAULTS"] = {}
    result_with_mutated_reflection = direct_namespace["GeneratedParser"]().parse(
        tokens,
        "start",
    )
    assert _shape(result_with_mutated_reflection) == _shape(vm_result)


def test_direct_bindings_in_nested_region_match_vm() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= @Node Title = ITEM")
    alternative = parser_ir.productions[0].alternatives[0]
    construct, binding = alternative.operations
    nested_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(
                    replace(
                        alternative,
                        operations=(
                            construct,
                            ResolvedRegion((binding,), None, binding.source_span),
                        ),
                    ),
                ),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, nested_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, nested_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [Token("ITEM", start=3, end=7)])
    direct_namespace, direct_result = _execute(
        direct.module_text,
        [Token("ITEM", start=3, end=7)],
    )

    assert _shape(direct_result) == _shape(vm_result)
    assert direct_result.span == direct_namespace["SourceSpan"](3, 7)


def test_direct_nested_region_constructor_preserves_outer_bindings() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= @Node First = FIRST")
    alternative = parser_ir.productions[0].alternatives[0]
    construct, outer_binding = alternative.operations
    inner_binding = replace(
        outer_binding,
        value=replace(
            outer_binding.value,
            symbol=replace(outer_binding.value.symbol, token_type="SECOND"),
        ),
    )
    nested_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(
                    replace(
                        alternative,
                        operations=(
                            construct,
                            outer_binding,
                            ResolvedRegion(
                                (construct, inner_binding),
                                None,
                                inner_binding.source_span,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, nested_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, nested_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [Token("FIRST"), Token("SECOND")])
    _, direct_result = _execute(direct.module_text, [Token("FIRST"), Token("SECOND")])

    assert vm_result.First == "FIRST"
    assert _shape(direct_result) == _shape(vm_result)


def test_direct_constructor_locals_are_unique_across_constructor_field_pairs() -> None:
    _, _, parser_ir, source = _generated_pair(
        "<S> ::= @A_B C = FIRST -= <Inner>\n<Inner> ::= @A B_C = SECOND"
    )
    outer_alternative = parser_ir.productions[0].alternatives[0]
    inner_alternative = parser_ir.productions[1].alternatives[0]
    outer_construct, outer_binding, _ = outer_alternative.operations
    inner_construct, inner_binding = inner_alternative.operations
    nested_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(
                    replace(
                        outer_alternative,
                        operations=(
                            outer_construct,
                            outer_binding,
                            ResolvedRegion(
                                (inner_construct, inner_binding),
                                None,
                                inner_binding.source_span,
                            ),
                        ),
                    ),
                ),
            ),
            parser_ir.productions[1],
        ),
    )
    vm = generate_python_semantic_parser(source, nested_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, nested_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [Token("FIRST"), Token("SECOND")])
    _, direct_result = _execute(direct.module_text, [Token("FIRST"), Token("SECOND")])

    assert vm_result.C == "FIRST"
    assert _shape(direct_result) == _shape(vm_result)


@pytest.mark.parametrize(
    ("grammar", "tokens"),
    [
        ("<S> ::= (A | B)", [Token("B")]),
        ("<S> ::= @Node Item = (A | B)", [Token("B")]),
    ],
    ids=("two-way-dispatch", "value-dispatch-nested-branch-result"),
)
def test_direct_dispatches_match_vm(
    grammar: str,
    tokens: list[Token],
) -> None:
    vm, direct, _, _ = _generated_pair(grammar)

    _, vm_result = _execute(vm.module_text, tokens)
    _, direct_result = _execute(direct.module_text, tokens)

    assert _shape(direct_result) == _shape(vm_result)


@pytest.mark.parametrize(
    "tokens",
    ([Token("A")], []),
    ids=("present", "exit"),
)
def test_direct_optional_branch_and_exit_operations_match_vm(tokens: list[Token]) -> None:
    grammar = "<S> ::= @Node Item = (A | B)?"
    vm, direct, _, _ = _generated_pair(grammar)

    _, vm_result = _execute(vm.module_text, tokens)
    _, direct_result = _execute(direct.module_text, tokens)

    assert _shape(direct_result) == _shape(vm_result)


def test_direct_optional_exit_operations_preserve_order() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= @Node Flag := Ложь Item = A?")
    alternative = parser_ir.productions[0].alternatives[0]
    optional = alternative.operations[2]
    assert isinstance(optional, OptionalBranch)
    exit_operations = (
        AssignConstant("Flag", "Истина", optional.source_span),
        AssignConstant("Flag", "Ложь", optional.source_span),
    )
    specialized_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(
                    replace(
                        alternative,
                        operations=(
                            alternative.operations[0],
                            alternative.operations[1],
                            replace(optional, exit_operations=exit_operations),
                        ),
                    ),
                ),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, specialized_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, specialized_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [])
    _, direct_result = _execute(direct.module_text, [])

    assert vm_result.Flag is False
    assert _shape(direct_result) == _shape(vm_result)


def test_direct_parse_branch_value_uses_its_nested_result_index() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= @Node Item = (A | B)")
    alternative = parser_ir.productions[0].alternatives[0]
    binding = alternative.operations[1]
    dispatch = binding.value
    branch_value = dispatch.branches[0].value
    first = branch_value.operations[0]
    second = replace(first, symbol=replace(first.symbol, token_type="C"))
    specialized_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(
                    replace(
                        alternative,
                        operations=(
                            alternative.operations[0],
                            replace(
                                binding,
                                value=replace(
                                    dispatch,
                                    branches=(
                                        replace(
                                            dispatch.branches[0],
                                            value=replace(
                                                branch_value,
                                                operations=(first, second),
                                                result_index=1,
                                            ),
                                        ),
                                        dispatch.branches[1],
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, specialized_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, specialized_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [Token("A"), Token("C")])
    _, direct_result = _execute(direct.module_text, [Token("A"), Token("C")])

    assert vm_result.Item == "C"
    assert _shape(direct_result) == _shape(vm_result)


@pytest.mark.parametrize(
    "values",
    ([], [1]),
    ids=("empty", "one"),
)
def test_direct_repeat_matches_vm(values: list[int]) -> None:
    grammar = "<S> ::= @Node Items += &NUMBER*"
    vm, direct, _, _ = _generated_pair(grammar)
    tokens = [Token("NUMBER", str(value), value=value) for value in values]

    _, vm_result = _execute(vm.module_text, tokens)
    _, direct_result = _execute(direct.module_text, tokens)

    assert _shape(direct_result) == _shape(vm_result)


def test_direct_repeat_captures_each_counting_token_once() -> None:
    grammar = "<S> ::= @Node Items += &NUMBER*"
    vm, direct, _, _ = _generated_pair(grammar)
    vm_token = CountingToken(42)
    direct_token = CountingToken(42)

    _, vm_result = _execute(vm.module_text, [vm_token])
    _, direct_result = _execute(direct.module_text, [direct_token])

    assert _shape(direct_result) == _shape(vm_result)
    assert vm_token.value_reads == direct_token.value_reads == 1


def test_direct_repeat_handles_5000_items_and_parser_reuse() -> None:
    _, direct, _, _ = _generated_pair("<S> ::= @Node Items += &NUMBER*")
    namespace = _execute_without_parse(direct.module_text)
    parser = namespace["GeneratedParser"]()
    tokens = [Token("NUMBER", str(index), value=index) for index in range(5_000)]

    result = parser.parse(tokens, "start")
    reused_result = parser.parse([Token("NUMBER", "9", value=9)], "start")

    assert result.Items == tuple(range(5_000))
    assert reused_result.Items == (9,)


def test_direct_repeat_rejects_a_nonadvancing_malformed_ir_branch() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= A*")
    alternative = parser_ir.productions[0].alternatives[0]
    repeat = alternative.operations[0]
    assert isinstance(repeat, RepeatLoop)
    nonadvancing = replace(
        repeat,
        branches=(
            replace(
                repeat.branches[0],
                operations=(UndefinedValue("Неопределено", repeat.source_span),),
            ),
        ),
    )
    malformed_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(replace(alternative, operations=(nonadvancing,)),),
            ),
        ),
    )
    direct = _generate_direct_python_semantic_parser(source, malformed_ir, {"start": "S"})
    parser = _execute_without_parse(direct.module_text)["GeneratedParser"]()

    with pytest.raises(RuntimeError, match="^repeat branch did not advance parser cursor$"):
        parser.parse([ProgressProbeToken()], "start")
