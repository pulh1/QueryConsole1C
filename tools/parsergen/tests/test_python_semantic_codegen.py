from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar


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
