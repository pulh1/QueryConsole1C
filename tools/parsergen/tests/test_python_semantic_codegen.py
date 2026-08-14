from __future__ import annotations

from dataclasses import dataclass, FrozenInstanceError, replace
import os
from pathlib import Path
import subprocess
import sys

import pytest

from parsergen import generate_python_semantic_parser as public_generate
from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar


@dataclass(frozen=True)
class Token:
    type: str
    text: str = ""
    start: int = 0
    end: int = 0
    value: object | None = None


def _generate(source: str):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )
    generated = generate_python_semantic_parser(
        parsed.source_grammar,
        parser_ir,
        {"start": "S"},
    )
    namespace: dict[str, object] = {}
    exec(compile(generated.module_text, "<generated-semantic-parser>", "exec"), namespace)
    return parsed, parser_ir, generated, namespace


def test_generates_distinct_frozen_ast_classes_and_schema() -> None:
    assert public_generate is generate_python_semantic_parser
    _, _, generated, namespace = _generate(
        "#Name ::= ID\n"
        "<S> ::= @Module Title = #Name Items += <Item> "
        "(',' Items += <Item>)* Count ++= MARK Joined ~= #Name "
        "Enabled := Истина\n"
        "<Item> ::= @Item Value = #Name"
    )

    module_class = namespace["Module"]
    item_class = namespace["Item"]
    span_class = namespace["SourceSpan"]
    assert module_class is not item_class
    assert namespace["AST_CLASSES"] == {"Module": module_class, "Item": item_class}
    assert [item.name for item in generated.ast_schema] == ["Module", "Item"]
    assert [(field.name, field.category) for field in generated.ast_schema[0].fields] == [
        ("Title", "scalar"),
        ("Items", "collection"),
        ("Count", "increment"),
        ("Joined", "concat"),
        ("Enabled", "scalar"),
    ]

    span = span_class(0, 4)
    item = item_class("value", span)
    node = module_class("title", (item,), 1, "tail", True, span)
    assert node.Items == (item,)
    assert node.span == span
    assert not hasattr(node, "node_type")
    with pytest.raises(FrozenInstanceError):
        node.Title = "changed"


def test_generation_is_deterministic_and_rejects_incompatible_ir() -> None:
    parsed, parser_ir, first, _ = _generate("<S> ::= @Node Value = ITEM")
    second = generate_python_semantic_parser(
        parsed.source_grammar,
        parser_ir,
        {"start": "S"},
    )
    assert first == second

    other, _, _, _ = _generate("<S> ::= @Other Value = ITEM")
    assert other.source_grammar is not None
    with pytest.raises(ValueError, match="source grammar"):
        generate_python_semantic_parser(
            other.source_grammar,
            parser_ir,
            {"start": "S"},
        )


def test_schema_errors_are_deterministic_for_multi_constructor_wrap() -> None:
    script = """
from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar

source = (
    "<S> ::= <Seed> Child => <Wrapper>?\\n"
    "<Seed> ::= @Seed Value = SEED\\n"
    "<Wrapper> ::= @Zulu Child += Z | @Alpha Child += A"
)
parsed = parse_grammar(source, "grammar.txt")
resolved = resolve_grammar(parsed.grammar)
analysis = compute_analysis(resolved.grammar, 1, ("S",))
parser_ir = build_parser_ir(
    parsed.source_grammar,
    parsed.lowering,
    resolved.grammar,
    analysis,
    entrypoint_productions=("S",),
)
try:
    generate_python_semantic_parser(
        parsed.source_grammar,
        parser_ir,
        {"start": "S"},
    )
except ValueError as error:
    print(error)
"""
    outputs = []
    for seed in (1, 3):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = str(seed)
        environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
        completed = subprocess.run(
            [sys.executable, "-c", script],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        outputs.append(completed.stdout.strip())

    assert outputs == [
        "field Alpha.Child has incompatible binding categories",
        "field Alpha.Child has incompatible binding categories",
    ]


def test_malformed_ir_reports_unknown_value_production() -> None:
    parsed, parser_ir, _, _ = _generate(
        "<S> ::= <Seed> Child => <Wrapper>\n"
        "<Seed> ::= @Seed Value = SEED\n"
        "<Wrapper> ::= @Wrapper WRAP"
    )
    production = parser_ir.productions[0]
    alternative = production.alternatives[0]
    wrap = alternative.operations[0]
    missing_value = replace(
        wrap.value,
        symbol=replace(wrap.value.symbol, name="Missing"),
    )
    malformed = replace(
        parser_ir,
        productions=(
            replace(
                production,
                alternatives=(
                    replace(
                        alternative,
                        operations=(replace(wrap, value=missing_value),),
                    ),
                ),
            ),
            *parser_ir.productions[1:],
        ),
    )

    with pytest.raises(ValueError, match="unknown production 'Missing'"):
        generate_python_semantic_parser(
            parsed.source_grammar,
            malformed,
            {"start": "S"},
        )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("<S> ::= @GeneratedParser Value = ITEM", "reserved"),
        ("<S> ::= @ENTRYPOINTS Value = ITEM", "reserved"),
        ("<S> ::= @PRODUCTIONS Value = ITEM", "reserved"),
        ("<S> ::= @DECISIONS Value = ITEM", "reserved"),
        ("<S> ::= @NODE_DEFAULTS Value = ITEM", "reserved"),
        ("<S> ::= @_Builder Value = ITEM", "reserved"),
        ("<S> ::= @_Frame Value = ITEM", "reserved"),
        ("<S> ::= @Node span = ITEM", "reserved"),
        ("<S> ::= @Node items = ITEM", "reserved"),
    ],
)
def test_rejects_reserved_generated_names(source: str, message: str) -> None:
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )

    with pytest.raises(ValueError, match=message):
        generate_python_semantic_parser(
            parsed.source_grammar,
            parser_ir,
            {"start": "S"},
        )


def test_parses_constructor_bindings_constants_and_input_span() -> None:
    _, _, _, namespace = _generate(
        "#Name ::= ID\n"
        "<S> ::= @Assignment Name = #Name '=' Number = &NUMBER "
        "Enabled := Истина"
    )
    parser = namespace["GeneratedParser"]()

    node = parser.parse(
        [
            Token("ID", "Total", 0, 5),
            Token("=", "=", 6, 7),
            Token("NUMBER", "42", 8, 10, 42),
        ],
        "start",
    )

    assert type(node) is namespace["Assignment"]
    assert node.Name == "Total"
    assert node.Number == 42
    assert node.Enabled is True
    assert node.span == namespace["SourceSpan"](0, 10)


def test_child_span_ends_at_consumed_token_not_next_token_start() -> None:
    _, _, _, namespace = _generate(
        "#Name ::= ID\n"
        "<S> ::= @Assignment Target = <Target> '=' Value = <Target>\n"
        "<Target> ::= @Target Name = #Name"
    )

    node = namespace["GeneratedParser"]().parse(
        [
            Token("ID", "Result", 0, 6),
            Token("=", "=", 17, 18),
            Token("ID", "Value", 26, 31),
        ],
        "start",
    )

    assert node.Target.span == namespace["SourceSpan"](0, 6)
    assert node.Value.span == namespace["SourceSpan"](26, 31)
    assert node.span == namespace["SourceSpan"](0, 31)


def test_transparent_nonterminal_returns_child_ast() -> None:
    _, _, _, namespace = _generate(
        "#Name ::= ID\n<S> ::= <Item>\n<Item> ::= @Item Value = #Name"
    )

    node = namespace["GeneratedParser"]().parse(
        [Token("ID", "value", 4, 9)],
        "start",
    )

    assert type(node) is namespace["Item"]
    assert node.Value == "value"
    assert node.span == namespace["SourceSpan"](4, 9)


def test_generated_semantic_parser_reports_syntax_error_and_full_consumption() -> None:
    _, _, _, namespace = _generate("<S> ::= @Node Value = ITEM")
    parser = namespace["GeneratedParser"]()
    error_type = namespace["GeneratedParseError"]

    with pytest.raises(error_type) as caught:
        parser.parse([Token("OTHER", "secret", 7, 13)], "start")
    assert caught.value.position == 0
    assert caught.value.actual == "OTHER"
    assert caught.value.expected == ("ITEM",)
    assert "secret" not in str(caught.value)

    with pytest.raises(error_type) as caught:
        parser.parse([Token("ITEM", "ok"), Token("ITEM", "extra")], "start")
    assert caught.value.position == 1
    assert caught.value.expected == ("$",)


def test_semantic_parser_trampolines_direct_right_recursion() -> None:
    _, _, _, namespace = _generate(
        "<S> ::= ITEM <Tail>\n<Tail> ::= ITEM <Tail> | ПУСТО"
    )
    parser = namespace["GeneratedParser"]()
    original_limit = sys.getrecursionlimit()

    assert parser.parse([Token("ITEM") for _ in range(5_000)], "start") is None
    assert sys.getrecursionlimit() == original_limit


def test_executes_dispatch_optional_repeat_concat_and_increment() -> None:
    _, _, _, namespace = _generate(
        "#Name ::= ID\n"
        "<S> ::= @List Choice = (A | B) Maybe = FLAG? "
        "Items += ITEM (',' Items += ITEM)* "
        "Path ~= #Name (Path ~= '.' Path ~= #Name)* "
        "(Count ++= MARK)*"
    )
    parser = namespace["GeneratedParser"]()

    node = parser.parse(
        [
            Token("B"),
            Token("ITEM", "first"),
            Token(","),
            Token("ITEM", "second"),
            Token("ID", "Root"),
            Token(".", "."),
            Token("ID", "Leaf"),
            Token("MARK"),
            Token("MARK"),
        ],
        "start",
    )

    assert node.Choice == "B"
    assert node.Maybe is None
    assert node.Items == ("ITEM", "ITEM")
    assert node.Path == "Root.Leaf"
    assert node.Count == 2


def test_optional_present_and_long_repeat_are_iterative() -> None:
    _, _, _, namespace = _generate(
        "<S> ::= @List Maybe = FLAG? Items += ITEM (',' Items += ITEM)*"
    )
    parser = namespace["GeneratedParser"]()
    tokens = [Token("FLAG"), Token("ITEM")]
    tokens.extend(
        token
        for _ in range(4_999)
        for token in (Token(","), Token("ITEM"))
    )
    original_limit = sys.getrecursionlimit()

    node = parser.parse(tokens, "start")

    assert node.Maybe == "FLAG"
    assert len(node.Items) == 5_000
    assert sys.getrecursionlimit() == original_limit


def test_required_and_optional_wrap_return_frozen_wrapper_nodes() -> None:
    _, _, _, required_namespace = _generate(
        "<S> ::= <Seed> Child => <Wrapper>\n"
        "<Seed> ::= @Seed Value = SEED\n"
        "<Wrapper> ::= @Wrapper WRAP"
    )
    required = required_namespace["GeneratedParser"]().parse(
        [Token("SEED", start=0, end=4), Token("WRAP", start=5, end=9)],
        "start",
    )
    assert type(required) is required_namespace["Wrapper"]
    assert type(required.Child) is required_namespace["Seed"]
    assert required.Child.Value == "SEED"

    _, _, _, optional_namespace = _generate(
        "<S> ::= <Seed> Child => <Wrapper>?\n"
        "<Seed> ::= @Seed Value = SEED\n"
        "<Wrapper> ::= @Wrapper WRAP"
    )
    parser = optional_namespace["GeneratedParser"]()
    seed = parser.parse([Token("SEED", start=0, end=4)], "start")
    wrapped = parser.parse(
        [Token("SEED", start=0, end=4), Token("WRAP", start=5, end=9)],
        "start",
    )
    assert type(seed) is optional_namespace["Seed"]
    assert type(wrapped) is optional_namespace["Wrapper"]
    assert type(wrapped.Child) is optional_namespace["Seed"]
    assert wrapped.span == optional_namespace["SourceSpan"](5, 9)


def test_direct_left_recursion_builds_left_associative_ast_iteratively() -> None:
    _, _, _, namespace = _generate(
        "<S> ::= <Expr>\n"
        "<Expr> ::= @Binary Left = <Expr> Operator = '+' Right = <Term> | <Term>\n"
        "<Term> ::= @Term Value = ITEM"
    )
    parser = namespace["GeneratedParser"]()
    tokens = [Token("ITEM", start=0, end=1)]
    tokens.extend(
        token
        for index in range(1, 2_000)
        for token in (
            Token("+", start=index * 2 - 1, end=index * 2),
            Token("ITEM", start=index * 2, end=index * 2 + 1),
        )
    )
    original_limit = sys.getrecursionlimit()

    node = parser.parse(tokens, "start")

    assert type(node) is namespace["Binary"]
    assert type(node.Left) is namespace["Binary"]
    assert type(node.Right) is namespace["Term"]
    assert node.span == namespace["SourceSpan"](0, 3_999)
    assert sys.getrecursionlimit() == original_limit


def test_root_collection_extend_and_prepend_wrap_use_immutable_tuples() -> None:
    _, _, _, extend_namespace = _generate(
        "<S> ::= @Node Items *= <Values>\n"
        "<Values> ::= @Values += ITEM (',' += ITEM)*"
    )
    extended = extend_namespace["GeneratedParser"]().parse(
        [Token("ITEM"), Token(","), Token("ITEM")],
        "start",
    )
    assert extended.Items == ("ITEM", "ITEM")

    _, _, _, wrap_namespace = _generate(
        "<S> ::= <Base> Elements +=> <Postfix>?\n"
        "<Base> ::= @Base Value = BASE\n"
        "<Postfix> ::= @Postfix POSTFIX"
    )
    wrapped = wrap_namespace["GeneratedParser"]().parse(
        [Token("BASE"), Token("POSTFIX")],
        "start",
    )
    assert type(wrapped) is wrap_namespace["Postfix"]
    assert len(wrapped.Elements) == 1
    assert type(wrapped.Elements[0]) is wrap_namespace["Base"]
