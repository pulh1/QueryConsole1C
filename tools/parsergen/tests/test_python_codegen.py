from __future__ import annotations

from dataclasses import dataclass

import pytest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import RepeatLoop, build_syntax_parser_ir
from parsergen.python_codegen import generate_python_parser
from parsergen.resolver import resolve_grammar


@dataclass(frozen=True)
class Token:
    type: str
    text: str = ""
    start: int = 0
    end: int = 0


def _generate(source: str, *, k: int = 1):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, k, ("S",))
    parser_ir = build_syntax_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )
    generated = generate_python_parser(
        parsed.source_grammar,
        parser_ir,
        {"start": "S"},
    )
    namespace: dict[str, object] = {}
    exec(compile(generated.module_text, "<generated-parser>", "exec"), namespace)
    return parser_ir, generated, namespace


def test_generates_dag_parser_and_repeat_loop_as_iterative_python() -> None:
    parser_ir, generated, namespace = _generate(
        "<S> ::= ITEM (',' ITEM)*"
    )

    assert any(
        isinstance(operation, RepeatLoop)
        for production in parser_ir.productions
        for alternative in production.alternatives
        for operation in alternative.operations
    )
    assert "while tasks:" in generated.module_text
    parser = namespace["GeneratedParser"]()
    parser.parse(
        [Token("ITEM"), *[token for _ in range(5_000) for token in (Token(","), Token("ITEM"))]],
        "start",
    )


def test_generated_parser_trampolines_direct_right_recursion() -> None:
    _, _, namespace = _generate("<S> ::= ITEM <S>?")
    parser = namespace["GeneratedParser"]()

    parser.parse([Token("ITEM") for _ in range(5_000)], "start")


def test_generated_parser_uses_k2_decision_dag() -> None:
    _, _, namespace = _generate(
        "<S> ::= 'a' 'b' | 'a' 'c'",
        k=2,
    )
    parser = namespace["GeneratedParser"]()

    parser.parse([Token("a"), Token("c")], "start")


def test_generated_parser_reports_position_actual_and_expected() -> None:
    _, _, namespace = _generate("<S> ::= ITEM ',' ITEM")
    parser = namespace["GeneratedParser"]()
    error_type = namespace["GeneratedParseError"]

    with pytest.raises(error_type) as caught:
        parser.parse([Token("ITEM"), Token(";")], "start")

    assert caught.value.position == 1
    assert caught.value.actual == ";"
    assert caught.value.expected == (",",)
