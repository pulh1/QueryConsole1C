from __future__ import annotations

from dataclasses import dataclass, FrozenInstanceError
import sys

import pytest

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


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("<S> ::= @GeneratedParser Value = ITEM", "reserved"),
        ("<S> ::= @Node span = ITEM", "reserved"),
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
