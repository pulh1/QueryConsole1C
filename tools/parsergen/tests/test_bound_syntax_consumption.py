"""Inlining a value-less child must retain its token consumption."""

import pytest

from parsergen.canonical_bsl_codegen import generate_canonical_parser
from parsergen.parser_ir_optimization import optimize_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from tests.test_parser_ir_optimization import _build_raw, _function
from tests.test_python_semantic_codegen import Token


@pytest.mark.parametrize("child", [
    "<Child> ::= ITEM",
    "<Child> ::= <Middle>\n<Middle> ::= <Leaf>\n<Leaf> ::= ITEM",
])
@pytest.mark.parametrize("optimized", [False, True])
def test_bound_syntax_child_consumes_and_keeps_absent_result(child, optimized):
    parser_ir = _build_raw("<S> ::= @Node Value = <Child>\n" + child)
    if optimized:
        parser_ir = optimize_parser_ir(parser_ir)
    generated = generate_python_semantic_parser(
        parser_ir.source_grammar, parser_ir, {"start": "S"},
    )
    namespace = {}
    exec(compile(generated.module_text, "<bound-syntax>", "exec"), namespace)
    parser = namespace["GeneratedParser"]()
    result = parser.parse([Token("ITEM", start=4, end=11)], "start")
    assert result.Value is None
    assert (result.span.start, result.span.end) == (4, 11)
    for tokens, wanted in [
        ([], (0, "$", ("ITEM",))),
        ([Token("OTHER")], (0, "OTHER", ("ITEM",))),
        ([Token("ITEM"), Token("OTHER")], (1, "OTHER", ("$",))),
    ]:
        with pytest.raises(namespace["GeneratedParseError"]) as raised:
            parser.parse(tokens, "start")
        error = raised.value
        assert (error.position, error.actual, error.expected) == wanted


@pytest.mark.parametrize("child", [
    "<Child> ::= ITEM",
    "<Child> ::= <Middle>\n<Middle> ::= <Leaf>\n<Leaf> ::= ITEM",
])
def test_bsl_inlined_syntax_child_consumes_between_constructor_and_assignment(child):
    parser_ir = optimize_parser_ir(_build_raw("<S> ::= @Node Value = <Child>\n" + child))
    module = generate_canonical_parser(
        parser_ir.source_grammar, parser_ir, {"start": "S"},
    ).module_text
    function = _function(module, "S")
    assert function.index("Node(ТекущийТокен)") < function.index('Терминал("ITEM");')
    assert function.index('Терминал("ITEM");') < function.index("ЭтотУзел.Value = Неопределено;")
    assert "Возврат РезультатПродукции;" in function
