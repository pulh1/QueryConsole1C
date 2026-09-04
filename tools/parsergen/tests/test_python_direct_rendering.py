from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
import sys

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
from parsergen.python_semantic_codegen import generate_python_semantic_parser
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


def _generate(
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
    direct = generate_python_semantic_parser(
        parsed.source_grammar,
        parser_ir,
        mapping,
    )
    return direct, parser_ir, parsed.source_grammar


def test_direct_module_compiles_and_preserves_runtime_shape() -> None:
    direct, _, _ = _generate("<S> ::= ITEM")
    direct_namespace, direct_result = _execute(direct.module_text, [Token("ITEM")])

    assert _shape(direct_result) is None
    assert direct_namespace["GeneratedParser"]().parse([Token("ITEM")], "start") is None


def test_direct_captured_terminal_is_exact() -> None:
    _, parser_ir, source = _generate("<S> ::= ITEM")
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
    direct = generate_python_semantic_parser(source, captured_ir, {"start": "S"})

    _, direct_result = _execute(direct.module_text, [Token("ITEM")])
    assert _shape(direct_result) == "ITEM"


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
def test_direct_core_terminal_operations_are_exact(
    grammar: str,
    tokens: list[Token],
    expected: object,
) -> None:
    direct, _, _ = _generate(grammar)
    _, direct_result = _execute(direct.module_text, tokens)

    assert _shape(direct_result) == expected


@pytest.mark.parametrize(
    ("constant", "expected"),
    [("Истина", True), ("Ложь", False), ("Неопределено", None), ("Kinds.Value", "Kinds.Value")],
)
def test_direct_canonical_return_constants_are_exact(
    constant: str,
    expected: object,
) -> None:
    direct, _, _ = _generate(f"<S> ::= := {constant}")
    _, direct_result = _execute(direct.module_text, [])

    assert _shape(direct_result) == expected


def test_direct_undefined_value_is_exact() -> None:
    _, parser_ir, source = _generate("<S> ::= := Неопределено")
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
    direct = generate_python_semantic_parser(source, undefined_ir, {"start": "S"})

    _, direct_result = _execute(direct.module_text, [])
    assert _shape(direct_result) is None


def test_direct_parser_reuses_iterable_input_and_checks_full_consumption() -> None:
    direct, _, _ = _generate("<S> ::= ITEM")
    namespace: dict[str, object] = {}
    exec(compile(direct.module_text, "<semantic-parser>", "exec"), namespace)
    parser = namespace["GeneratedParser"]()

    assert parser.parse(iter([Token("ITEM")]), "start") is None
    assert parser.parse([Token("ITEM")], "start") is None
    with pytest.raises(namespace["GeneratedParseError"]) as caught:
        parser.parse([Token("ITEM"), Token("ITEM")], "start")
    assert type(caught.value) is namespace["GeneratedParseError"]
    assert caught.value.position == 1
    assert caught.value.actual == "ITEM"
    assert caught.value.expected == ("$",)
    assert caught.value.args == ("unexpected 'ITEM' at token 1; expected ('$',)",)
    assert str(caught.value) == "unexpected 'ITEM' at token 1; expected ('$',)"


@pytest.mark.parametrize(
    ("grammar", "tokens", "k", "expected"),
    [
        ("<S> ::= ITEM", [Token("BAD")], 1, (0, "BAD", ("ITEM",))),
        ("<S> ::= ITEM", [], 1, (0, "$", ("ITEM",))),
        ("<S> ::= ITEM", [Token("ITEM"), Token("ITEM")], 1, (1, "ITEM", ("$",))),
        ("<S> ::= 'a' 'b' | 'a' 'c'", [Token("a"), Token("x")], 2, (0, "a", ("b", "c"))),
        ("<S> ::= 'a' 'b' | 'c'", [Token("a"), Token("x")], 1, (1, "x", ("b",))),
    ],
    ids=("bad", "eof", "trailing", "k2", "committed"),
)
def test_direct_errors_are_exact(
    grammar: str,
    tokens: list[Token],
    k: int,
    expected: tuple[int, str, tuple[str, ...]],
) -> None:
    direct, _, _ = _generate(grammar, k=k)
    namespace = _execute_without_parse(direct.module_text)
    error_type = namespace["GeneratedParseError"]
    parser = namespace["GeneratedParser"]()

    with pytest.raises(error_type) as caught:
        parser.parse(tokens, "start")
    position, actual, expected_tokens = expected
    assert type(caught.value) is error_type
    assert caught.value.args == (
        f"unexpected {actual!r} at token {position}; expected {expected_tokens!r}",
    )
    assert str(caught.value) == caught.value.args[0]
    assert (caught.value.position, caught.value.actual, caught.value.expected) == expected


def test_direct_identifier_mismatch_error_is_exact() -> None:
    direct, _, _ = _generate("#Name ::= ID\n<S> ::= #Name")
    namespace = _execute_without_parse(direct.module_text)
    error_type = namespace["GeneratedParseError"]
    parser = namespace["GeneratedParser"]()

    with pytest.raises(error_type) as caught:
        parser.parse([Token("BAD")], "start")
    assert type(caught.value) is error_type
    assert caught.value.args == ("unexpected 'BAD' at token 0; expected ('ID',)",)
    assert str(caught.value) == "unexpected 'BAD' at token 0; expected ('ID',)"
    assert (caught.value.position, caught.value.actual, caught.value.expected) == (
        0,
        "BAD",
        ("ID",),
    )


def test_direct_unknown_entrypoint_error_is_exact() -> None:
    direct, _, _ = _generate("<S> ::= ITEM")
    parser = _execute_without_parse(direct.module_text)["GeneratedParser"]()

    with pytest.raises(ValueError) as caught:
        parser.parse([], "missing")
    assert type(caught.value) is ValueError
    assert caught.value.args == ("unknown entrypoint 'missing'",)
    assert str(caught.value) == "unknown entrypoint 'missing'"


def test_direct_shared_decision_dag_renders_the_shared_node_once() -> None:
    _, parser_ir, source = _generate("<S> ::= A | B")
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

    direct = generate_python_semantic_parser(source, shared_ir, {"start": "S"})

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
    direct, _, _ = _generate(
        "<S> ::= ITEM\n<A> ::= OTHER",
        entrypoints={"start": "S", "other": "A"},
    )
    namespace, direct_result = _execute(direct.module_text, [Token("OTHER")], "other")

    assert _shape(direct_result) is None
    assert namespace["GeneratedParser"]().parse([Token("ITEM")], "start") is None


def test_direct_constructor_bindings_are_complete_and_field_ordered() -> None:
    direct, _, _ = _generate(
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

    direct_namespace, direct_result = _execute(direct.module_text, tokens)

    assert type(direct_result) is direct_namespace["Node"]
    assert tuple(field.name for field in fields(direct_result)) == (
        "Title",
        "Items",
        "Joined",
        "Count",
        "Enabled",
        "Values",
        "span",
    )
    assert (
        direct_result.Title,
        direct_result.Items,
        direct_result.Joined,
        direct_result.Count,
        direct_result.Enabled,
        direct_result.Values,
        direct_result.span,
    ) == (
        "Title",
        ("ITEM",),
        "Tail",
        1,
        True,
        ("ITEM", "ITEM"),
        direct_namespace["SourceSpan"](0, 27),
    )
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
    assert _shape(result_with_mutated_reflection) == _shape(direct_result)


def test_direct_bindings_in_nested_region_are_complete() -> None:
    _, parser_ir, source = _generate("<S> ::= @Node Title = ITEM")
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
    direct = generate_python_semantic_parser(source, nested_ir, {"start": "S"})

    direct_namespace, direct_result = _execute(
        direct.module_text,
        [Token("ITEM", start=3, end=7)],
    )

    assert type(direct_result) is direct_namespace["Node"]
    assert tuple(field.name for field in fields(direct_result)) == ("Title", "span")
    assert (direct_result.Title, direct_result.span) == (
        "ITEM",
        direct_namespace["SourceSpan"](3, 7),
    )


def test_direct_nested_region_constructor_preserves_outer_bindings() -> None:
    _, parser_ir, source = _generate("<S> ::= @Node First = FIRST")
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
    direct = generate_python_semantic_parser(source, nested_ir, {"start": "S"})

    _, direct_result = _execute(direct.module_text, [Token("FIRST"), Token("SECOND")])

    assert direct_result.First == "FIRST"


def test_direct_constructor_locals_are_unique_across_constructor_field_pairs() -> None:
    _, parser_ir, source = _generate(
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
    direct = generate_python_semantic_parser(source, nested_ir, {"start": "S"})

    _, direct_result = _execute(direct.module_text, [Token("FIRST"), Token("SECOND")])

    assert direct_result.C == "FIRST"


@pytest.mark.parametrize(
    ("grammar", "tokens", "expected"),
    [
        ("<S> ::= (A | B)", [Token("B")], None),
        ("<S> ::= @Node Item = (A | B)", [Token("B")], "B"),
    ],
    ids=("two-way-dispatch", "value-dispatch-nested-branch-result"),
)
def test_direct_dispatches_are_exact(
    grammar: str,
    tokens: list[Token],
    expected: object,
) -> None:
    direct, _, _ = _generate(grammar)

    _, direct_result = _execute(direct.module_text, tokens)

    if expected is None:
        assert direct_result is None
    else:
        assert direct_result.Item == expected


@pytest.mark.parametrize(
    ("tokens", "expected"),
    (([Token("A")], "A"), ([], None)),
    ids=("present", "exit"),
)
def test_direct_optional_branch_and_exit_operations_are_exact(
    tokens: list[Token],
    expected: str | None,
) -> None:
    grammar = "<S> ::= @Node Item = (A | B)?"
    direct, _, _ = _generate(grammar)

    _, direct_result = _execute(direct.module_text, tokens)

    assert direct_result.Item == expected


def test_direct_optional_exit_operations_preserve_order() -> None:
    _, parser_ir, source = _generate("<S> ::= @Node Flag := Ложь Item = A?")
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
    direct = generate_python_semantic_parser(source, specialized_ir, {"start": "S"})

    _, direct_result = _execute(direct.module_text, [])

    assert direct_result.Flag is False


def test_direct_parse_branch_value_uses_its_nested_result_index() -> None:
    _, parser_ir, source = _generate("<S> ::= @Node Item = (A | B)")
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
    direct = generate_python_semantic_parser(source, specialized_ir, {"start": "S"})

    _, direct_result = _execute(direct.module_text, [Token("A"), Token("C")])

    assert direct_result.Item == "C"


@pytest.mark.parametrize(
    "values",
    ([], [1]),
    ids=("empty", "one"),
)
def test_direct_repeat_is_exact(values: list[int]) -> None:
    grammar = "<S> ::= @Node Items += &NUMBER*"
    direct, _, _ = _generate(grammar)
    tokens = [Token("NUMBER", str(value), value=value) for value in values]

    _, direct_result = _execute(direct.module_text, tokens)

    assert direct_result.Items == tuple(values)


def test_direct_repeat_captures_each_counting_token_once() -> None:
    grammar = "<S> ::= @Node Items += &NUMBER*"
    direct, _, _ = _generate(grammar)
    direct_token = CountingToken(42)

    _, direct_result = _execute(direct.module_text, [direct_token])

    assert direct_token.value_reads == 1


def test_direct_repeat_handles_5000_items_and_parser_reuse() -> None:
    direct, _, _ = _generate("<S> ::= @Node Items += &NUMBER*")
    namespace = _execute_without_parse(direct.module_text)
    parser = namespace["GeneratedParser"]()
    tokens = [Token("NUMBER", str(index), value=index) for index in range(5_000)]

    result = parser.parse(tokens, "start")
    reused_result = parser.parse([Token("NUMBER", "9", value=9)], "start")

    assert result.Items == tuple(range(5_000))
    assert reused_result.Items == (9,)


def test_direct_repeat_rejects_a_nonadvancing_malformed_ir_branch() -> None:
    _, parser_ir, source = _generate("<S> ::= A*")
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
    direct = generate_python_semantic_parser(source, malformed_ir, {"start": "S"})
    parser = _execute_without_parse(direct.module_text)["GeneratedParser"]()

    with pytest.raises(RuntimeError, match="^repeat branch did not advance parser cursor$"):
        parser.parse([ProgressProbeToken()], "start")


def test_direct_safe_tail_recursion_parses_5000_items_without_recursive_call() -> None:
    direct, parser_ir, _ = _generate(
        "<S> ::= ITEM <Tail>\n<Tail> ::= ITEM <Tail> | ПУСТО"
    )
    namespace = _execute_without_parse(direct.module_text)
    parser = namespace["GeneratedParser"]()
    tail_production = next(item for item in parser_ir.productions if item.name == "Tail")
    tail_method = f"_p_{parser_ir.productions.index(tail_production):04d}"
    generated_tail = direct.module_text.split(f"    def {tail_method}(self):", 1)[1]
    original_limit = sys.getrecursionlimit()

    assert parser.parse([Token("ITEM") for _ in range(5_000)], "start") is None
    assert sys.getrecursionlimit() == original_limit
    assert f"self.{tail_method}()" not in generated_tail


def test_direct_constructor_recursion_is_not_rendered_as_a_tail_loop() -> None:
    direct, parser_ir, _ = _generate(
        "<S> ::= @Node Value = ITEM <S> | @End STOP"
    )
    analysis = analyze_direct_render(parser_ir)
    method = "_p_0000"
    generated_production = direct.module_text.split(f"    def {method}(self):", 1)[1]

    assert analysis.recursive_calls[0].kind == "local_continuation"
    assert "continuations = []" in generated_production
    assert "def finish_site_0(saved, result):" in generated_production
    assert f"self.{method}()" not in generated_production


def test_value_carrying_right_recursion_builds_5000_linked_nodes() -> None:
    direct, _, _ = _generate(
        "<S> ::= @Link Value = ITEM Rest = <S> | @End STOP"
    )
    parser = _execute_without_parse(direct.module_text)["GeneratedParser"]()
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


def _record_constructor_calls(
    namespace: dict[str, object],
    name: str,
    calls: list[tuple[str, tuple[int, int]]],
    *,
    fail_on: int | None = None,
) -> None:
    original = namespace[name]

    def factory(*values: object) -> object:
        span = values[-1]
        calls.append((name, (span.start, span.end)))
        if fail_on is not None and len(calls) == fail_on:
            raise RuntimeError("injected freeze failure")
        return original(*values)

    namespace[name] = factory


def test_value_carrying_right_recursion_preserves_freeze_and_span_order() -> None:
    direct, _, _ = _generate(
        "<S> ::= @Link Value = ITEM Rest = <S> | @End STOP"
    )
    tokens = [Token("ITEM", start=index, end=index + 1) for index in range(3)]
    tokens.append(Token("STOP", start=3, end=4))
    direct_namespace = _execute_without_parse(direct.module_text)
    direct_calls: list[tuple[str, tuple[int, int]]] = []
    _record_constructor_calls(direct_namespace, "Link", direct_calls)
    _record_constructor_calls(direct_namespace, "End", direct_calls)

    direct_namespace["GeneratedParser"]().parse(tokens, "start")

    assert direct_calls == [
        ("End", (3, 4)),
        ("Link", (2, 4)),
        ("Link", (1, 4)),
        ("Link", (0, 4)),
    ]


def test_value_carrying_right_recursion_raises_on_the_same_freeze_node() -> None:
    direct, _, _ = _generate(
        "<S> ::= @Link Value = ITEM Rest = <S> | @End STOP"
    )
    tokens = [Token("ITEM", start=index, end=index + 1) for index in range(3)]
    tokens.append(Token("STOP", start=3, end=4))
    direct_namespace = _execute_without_parse(direct.module_text)
    direct_calls: list[tuple[str, tuple[int, int]]] = []
    _record_constructor_calls(direct_namespace, "Link", direct_calls, fail_on=3)
    _record_constructor_calls(direct_namespace, "End", direct_calls, fail_on=3)

    with pytest.raises(RuntimeError, match="^injected freeze failure$"):
        direct_namespace["GeneratedParser"]().parse(tokens, "start")

    assert direct_calls == [
        ("End", (3, 4)),
        ("Link", (2, 4)),
        ("Link", (1, 4)),
    ]


def test_multiple_local_continuation_sites_unwind_lifo_without_single_site_tag_stack() -> None:
    single_site, _, _ = _generate(
        "<S> ::= @Link Value = ITEM Rest = <S> | @End STOP"
    )
    direct, _, _ = _generate(
        "<S> ::= @ItemA Value = A Rest = <S> | "
        "@ItemB Value = B Rest = <S> | @End STOP"
    )
    tokens = [
        Token("A", start=0, end=1),
        Token("B", start=1, end=2),
        Token("A", start=2, end=3),
        Token("STOP", start=3, end=4),
    ]

    _, direct_result = _execute(direct.module_text, tokens)

    assert [
        type(item).__name__
        for item in (
            direct_result,
            direct_result.Rest,
            direct_result.Rest.Rest,
            direct_result.Rest.Rest.Rest,
        )
    ] == ["ItemA", "ItemB", "ItemA", "End"]
    assert "continuation_sites = []" in direct.module_text
    assert "continuation_sites = []" not in single_site.module_text


def test_wrap_value_local_continuation_saves_its_seed_before_recursing() -> None:
    grammar = "<S> ::= <Leaf> Next => <S> | @End STOP\n<Leaf> ::= @Leaf ITEM"
    direct, _, _ = _generate(grammar)
    tokens = [Token("ITEM", start=0, end=4), Token("STOP", start=5, end=9)]

    direct_namespace, direct_result = _execute(direct.module_text, tokens)

    assert type(direct_result) is direct_namespace["End"]
    assert tuple(field.name for field in fields(direct_result)) == ("Next", "span")
    assert type(direct_result.Next) is direct_namespace["Leaf"]
    assert tuple(field.name for field in fields(direct_result.Next)) == ("span",)
    assert (direct_result.Next.span, direct_result.span) == (
        direct_namespace["SourceSpan"](0, 4),
        direct_namespace["SourceSpan"](5, 9),
    )


def test_prepend_wrap_value_local_continuation_preserves_items_and_seed() -> None:
    grammar = "<S> ::= <Leaf> Items +=> <S> | @End STOP\n<Leaf> ::= @Leaf ITEM"
    direct, _, _ = _generate(grammar)
    tokens = [Token("ITEM", start=0, end=4), Token("STOP", start=5, end=9)]

    namespace, direct_result = _execute(direct.module_text, tokens)

    assert type(direct_result) is namespace["End"]
    assert tuple(field.name for field in fields(direct_result)) == ("Items", "span")
    assert len(direct_result.Items) == 1
    assert type(direct_result.Items[0]) is namespace["Leaf"]
    assert direct_result.Items[0].span == namespace["SourceSpan"](0, 4)
    assert direct_result.span == namespace["SourceSpan"](5, 9)


def test_direct_tail_transform_matches_the_exact_safe_analysis_site() -> None:
    direct, parser_ir, _ = _generate(
        "<S> ::= ITEM <S> | @Node Value = MARK <S> | @End STOP"
    )
    analysis = analyze_direct_render(parser_ir)
    generated_production = direct.module_text.split("    def _p_0000(self):", 1)[1]

    assert {
        (call.site.alternative, call.kind) for call in analysis.recursive_calls
    } == {
        (0, "safe_tail_loop"),
        (1, "local_continuation"),
    }
    assert "        while True:" in generated_production
    assert "continuations = []" in generated_production
    assert "self._p_0000()" not in generated_production


@pytest.mark.parametrize(
    ("grammar", "tokens", "property_name"),
    (
        (
            "<S> ::= <Seed> Type => <Wrapper>\n"
            "<Seed> ::= @Seed SEED\n"
            "<Wrapper> ::= @Wrapper WRAPPER",
            [Token("SEED", start=0, end=4), Token("WRAPPER", start=5, end=12)], "Type",
        ),
        (
            "<S> ::= <Seed> Type => <Wrapper>?\n"
            "<Seed> ::= @Seed SEED\n"
            "<Wrapper> ::= @Wrapper WRAPPER",
            [Token("SEED", start=0, end=4), Token("WRAPPER", start=5, end=12)], "Type",
        ),
        (
            "<S> ::= <Seed> Items +=> <Wrapper>\n"
            "<Seed> ::= @Seed SEED\n"
            "<Wrapper> ::= @Wrapper WRAPPER",
            [Token("SEED", start=0, end=4), Token("WRAPPER", start=5, end=12)], "Items",
        ),
    ),
    ids=("required", "optional-present", "prepend"),
)
def test_direct_wrap_values_preserve_property_and_seed(
    grammar: str,
    tokens: list[Token],
    property_name: str,
) -> None:
    direct, _, _ = _generate(grammar)

    direct_namespace, direct_result = _execute(direct.module_text, tokens)

    assert type(direct_result) is direct_namespace["Wrapper"]
    assert tuple(field.name for field in fields(direct_result)) == (
        property_name,
        "span",
    )
    seed = getattr(direct_result, property_name)
    if property_name == "Items":
        assert len(seed) == 1
        seed = seed[0]
    assert type(seed) is direct_namespace["Seed"]
    assert (seed.span, direct_result.span) == (
        direct_namespace["SourceSpan"](0, 4),
        direct_namespace["SourceSpan"](5, 12),
    )


def test_direct_optional_wrap_exit_returns_the_seed_identity() -> None:
    grammar = (
        "<S> ::= <Seed> Type => <Wrapper>?\n"
        "<Seed> ::= @Seed SEED\n"
        "<Wrapper> ::= @Wrapper WRAPPER"
    )
    direct, _, _ = _generate(grammar)

    direct_namespace, direct_result = _execute(
        direct.module_text,
        [Token("SEED", start=3, end=7)],
    )

    assert type(direct_result) is direct_namespace["Seed"]
    assert tuple(field.name for field in fields(direct_result)) == ("span",)
    assert direct_result.span == direct_namespace["SourceSpan"](3, 7)


@pytest.mark.parametrize(
    ("token_type", "constructor"),
    (("FIRST", "First"), ("SECOND", "Second")),
)
def test_direct_wrap_preserves_a_multi_constructor_wrapper_schema(
    token_type: str,
    constructor: str,
) -> None:
    grammar = (
        "<S> ::= <Seed> Type => <Wrapper>\n"
        "<Seed> ::= @Seed Value = SEED\n"
        "<Wrapper> ::= @First FIRST | @Second SECOND"
    )
    direct, _, _ = _generate(grammar)
    tokens = [Token("SEED", start=0, end=4), Token(token_type, start=5, end=11)]

    namespace, direct_result = _execute(direct.module_text, tokens)

    assert type(direct_result) is namespace[constructor]
    assert tuple(field.name for field in fields(direct_result)) == ("Type", "span")
    assert type(direct_result.Type) is namespace["Seed"]
    assert tuple(field.name for field in fields(direct_result.Type)) == ("Value", "span")
    assert direct_result.Type.Value == "SEED"
    assert (direct_result.Type.span, direct_result.span) == (
        namespace["SourceSpan"](0, 4),
        namespace["SourceSpan"](5, 11),
    )


def test_direct_left_fold_is_iterative_and_exact_for_2000_operators() -> None:
    grammar = (
        "<S> ::= <Expr>\n"
        "<Expr> ::= @Binary Left = <Expr> Operator = '+' Right = <Term> | <Term>\n"
        "<Term> ::= @Term Value = ITEM"
    )
    direct, _, _ = _generate(grammar)
    tokens = [Token("ITEM", start=0, end=1)]
    for index in range(2_000):
        offset = 1 + index * 2
        tokens.extend(
            (Token("+", start=offset, end=offset + 1), Token("ITEM", start=offset + 1, end=offset + 2))
        )

    direct_namespace = _execute_without_parse(direct.module_text)
    direct_result = direct_namespace["GeneratedParser"]().parse(tokens, "start")

    def fold_spine(value: object) -> tuple[object, ...]:
        items = []
        while type(value).__name__ == "Binary":
            items.append(
                (
                    value.span.start,
                    value.span.end,
                    value.Operator,
                    type(value.Right).__name__,
                    value.Right.Value,
                )
            )
            value = value.Left
        return tuple(items), type(value).__name__, value.Value

    spine, root_type, root_value = fold_spine(direct_result)
    assert len(spine) == 2_000
    assert spine[0] == (0, 4_001, "+", "Term", "ITEM")
    assert spine[-1] == (0, 3, "+", "Term", "ITEM")
    assert (root_type, root_value) == ("Term", "ITEM")
    assert "fold_accumulator" in direct.module_text
