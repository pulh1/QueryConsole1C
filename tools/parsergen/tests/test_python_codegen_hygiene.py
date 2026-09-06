"""Source names must not replace generated dependencies or resolved token sets."""

import pytest

from tests.test_python_semantic_codegen import Token, _generate


def test_ast_named_dataclass_does_not_replace_later_class_decorator():
    namespace = _generate("<S> ::= @dataclass Value = <Child>\n<Child> ::= @Child ITEM")[3]
    node = namespace["GeneratedParser"]().parse([Token("ITEM")], "start")
    assert type(node.Value) is namespace["Child"]


@pytest.mark.parametrize("definitions", [
    "#ID_X ::= A\n#ID_X ::= B",
    "#ID_X ::= B\n#ID_X ::= A\n#ID_X ::= B",
    "#Alias ::= A | B\n#ID_X ::= A\n#ID_X ::= B",
])
def test_repeated_identifier_definitions_preserve_union_and_error_set(definitions):
    _, _, _, namespace = _generate(definitions + "\n<S> ::= @Node Value = #ID_X")
    parser = namespace["GeneratedParser"]()
    for token_type in ("A", "B"):
        result = parser.parse([Token(token_type, "name", 2, 6)], "start")
        assert result.Value == "name"
        assert (result.span.start, result.span.end) == (2, 6)
    for tokens, actual in (([], "$"), ([Token("OTHER")], "OTHER")):
        with pytest.raises(namespace["GeneratedParseError"]) as raised:
            parser.parse(tokens, "start")
        assert (raised.value.position, raised.value.actual, raised.value.expected) == (
            0, actual, ("A", "B"),
        )


@pytest.mark.parametrize("name", [
    "tuple", "dataclass", "ValueError", "replace", "len", "getattr",
    "RuntimeError", "super", "object", "start", "outcome", "node_0_items",
    "_parsergen_builtins", "_parsergen_dataclasses",
])
def test_ast_names_cannot_shadow_python_dependencies_or_constructor_calls(name):
    _, _, generated, namespace = _generate(
        f"<S> ::= <Seed> Inner => <Wrapper>\n"
        "<Seed> ::= @Seed Items += &VALUE\n"
        f"<Wrapper> ::= @{name} WRAP"
    )
    parser = namespace["GeneratedParser"]()
    result = parser.parse([Token("VALUE", "v", 2, 5, "value"), Token("WRAP", start=7, end=11)], "start")
    assert type(result) is namespace["AST_CLASSES"][name]
    assert result.Inner.Items == ("value",)
    assert (result.Inner.span.start, result.Inner.span.end) == (2, 5)
    assert (result.span.start, result.span.end) == (7, 11)
    with pytest.raises(namespace["GeneratedParseError"]) as raised:
        parser.parse([], "start")
    assert isinstance(raised.value, ValueError)
    assert (raised.value.position, raised.value.actual, raised.value.expected) == (0, "$", ("VALUE",))
    with pytest.raises(ValueError, match="unknown entrypoint"):
        parser.parse([], "unknown")
    assert generated.module_text == _generate(
        f"<S> ::= <Seed> Inner => <Wrapper>\n"
        "<Seed> ::= @Seed Items += &VALUE\n"
        f"<Wrapper> ::= @{name} WRAP"
    )[2].module_text
