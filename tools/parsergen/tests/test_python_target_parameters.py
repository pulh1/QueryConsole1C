"""The Python target must reject call state it cannot evaluate or preserve."""

from dataclasses import replace

import pytest

from parsergen import generate_python_semantic_parser
from parsergen.analysis import compute_analysis
from parsergen.canonical_bsl_codegen import generate_canonical_parser
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.resolver import resolve_grammar
from parsergen.validation import validate_grammar


@pytest.mark.parametrize("grammar, actuals_only", [
    ("<S>(Context) ::= @Node ITEM", False),
    ("<S> ::= <Child>(Context.Next())\n<Child>(Context) ::= ITEM", True),
    ("<S> ::= @Node Value = <Child>(Context.Next())\n"
     "<Child>(Context) ::= @Child ITEM", False),  # Independent review repro.
    ("<S> ::= (<Child>(Context.Next()) | OTHER)\n<Child>(Context) ::= ITEM", True),
    ("<S> ::= @Node Value = (<Child>(Context.Next()) | OTHER)\n<Child>(Context) ::= ITEM", True),
    ("<S> ::= @Node Values += (<Child>(Context.Next()) OTHER?)*\n<Child>(Context) ::= ITEM", True),
    ("<S> ::= @Node Value = <Child>(Context.Next())?\n<Child>(Context) ::= ITEM", True),
    ("<S> ::= ITEM\n<Unused>(Context) ::= OTHER", False),
    ("<S> ::= ITEM\n<Unused> ::= <Child>(Context.Next())\n<Child>(Context) ::= OTHER", True),
    # The capability error must precede Python AST schema validation.
    ("<S>(Context) ::= @GeneratedParser ITEM", False),
])
def test_python_rejects_formal_parameters_or_actual_arguments(
    grammar: str, actuals_only: bool,
) -> None:
    parsed = parse_grammar(grammar, "python-parameters.grammar")
    assert parsed.diagnostics == ()
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    report = validate_grammar(
        parsed.grammar, resolved.grammar, analysis, {"start": "S"},
        lowering=parsed.lowering, source_grammar=parsed.source_grammar,
    )
    assert not report.has_errors
    parser_ir = build_parser_ir(
        parsed.source_grammar, parsed.lowering, resolved.grammar, analysis,
        entrypoint_productions=("S",),
    )
    source = parsed.source_grammar
    if actuals_only:
        # Normal arity validation requires formals for actuals (GR003). Remove
        # them from the input fixture to exercise the independent actual-call
        # capability check, without masking it behind the formals check.
        source = replace(source, productions=tuple(
            replace(item, parameters=()) for item in source.productions
        ))
        parser_ir = replace(
            parser_ir, source_grammar=source,
            productions=tuple(replace(item, parameters=()) for item in parser_ir.productions),
        )

    # Mutation caught: silently drop any source call state at Python generation,
    # including calls nested in bindings/EBNF or eliminated from optimized IR.
    with pytest.raises(ValueError) as raised:
        generate_python_semantic_parser(source, parser_ir, {"start": "S"})
    assert str(raised.value) == (
        "Python target does not support production parameters or nonterminal call arguments"
    )


def test_bsl_keeps_formals_and_argument_expression_from_python_repro() -> None:
    parsed = parse_grammar(
        "<S> ::= @Node Value = <Child>(Context.Next())\n"
        "<Child>(Context) ::= @Child ITEM"
    )
    resolved = resolve_grammar(parsed.grammar)
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    parser_ir = build_parser_ir(
        parsed.source_grammar, parsed.lowering, resolved.grammar, analysis,
        entrypoint_productions=("S",),
    )

    generated = generate_canonical_parser(parsed.source_grammar, parser_ir, {"start": "S"})

    assert "Функция НеТерминалChild(Context = Неопределено)" in generated.module_text
    assert "НеТерминалChild(Context.Next())" in generated.module_text
