from __future__ import annotations

from dataclasses import dataclass

import pytest

from parsergen.analysis import compute_analysis
from parsergen.lowering import lower_source_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar
from parsergen.semantic_profile_binding import bind_semantic_profile
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.syntax_grammar_parser import parse_syntax_grammar


@dataclass(frozen=True)
class Token:
    type: str
    text: str = ""
    start: int = 0
    end: int = 0


def _generate(
    syntax_text: str,
    profile_text: str,
    entrypoints: dict[str, str] | None = None,
):
    entries = entrypoints or {"start": "S"}
    syntax = parse_syntax_grammar(syntax_text, "syntax.grammar")
    profile = parse_semantic_profile(profile_text, "worker.semantic")
    assert syntax.diagnostics == ()
    assert syntax.grammar is not None
    assert profile.diagnostics == ()
    assert profile.profile is not None
    bound = bind_semantic_profile(syntax.grammar, profile.profile)
    assert bound.diagnostics == ()
    assert bound.source_grammar is not None
    lowering = lower_source_grammar(bound.source_grammar)
    assert lowering.diagnostics == ()
    resolved = resolve_grammar(lowering.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, tuple(entries.values()))
    parser_ir = build_parser_ir(
        bound.source_grammar,
        lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=tuple(entries.values()),
    )
    generated = generate_python_semantic_parser(
        bound.source_grammar,
        parser_ir,
        entries,
    )
    namespace: dict[str, object] = {}
    exec(compile(generated.module_text, "<generated-scoped-parser>", "exec"), namespace)
    return generated, namespace


def _owner_runtime():
    return _generate(
        "#Name ::= ID\n"
        "<S> ::= [root] head: #Name child: <Child> tail: #Name\n"
        "<Child> ::= [child] own: #Name leaf: <Leaf>\n"
        "<Leaf> ::= [leaf] value: #Name",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "Name = head\n"
        "^Owner.Items += tail\n"
        "^Owner.Items += child\n"
        "^Owner.Items += $Name\n"
        "}\n"
        "<Child>[child] {\n"
        "@Owner\n"
        "Name = own\n"
        "Leaf = leaf\n"
        "}\n"
        "<Leaf>[leaf] {\n"
        "@Leaf\n"
        "Value = value\n"
        "^Owner.Items += value\n"
        "}\n",
        {"start": "S", "leaf": "Leaf"},
    )


def _tokens():
    return [
        Token("ID", "outer", 0, 5),
        Token("ID", "inner", 6, 11),
        Token("ID", "leaf", 12, 16),
        Token("ID", "tail", 17, 21),
    ]


def test_nearest_owner_shadowing_order_and_close_before_delivery() -> None:
    generated, namespace = _owner_runtime()

    result = namespace["GeneratedParser"]().parse(_tokens(), "start")

    assert "append_nearest" in generated.module_text
    assert type(result) is namespace["Owner"]
    assert result.Name == "outer"
    assert result.Items[0] == "tail"
    child = result.Items[1]
    assert type(child) is namespace["Owner"]
    assert child.Name == "inner"
    assert child.Items == ("leaf",)
    assert result.Items[2] == "outer"
    assert type(child.Leaf) is namespace["Leaf"]


def test_missing_owner_is_noop_and_preserves_the_payload_result() -> None:
    _, namespace = _owner_runtime()

    result = namespace["GeneratedParser"]().parse(
        [Token("ID", "standalone", 3, 13)],
        "leaf",
    )

    assert type(result) is namespace["Leaf"]
    assert result.Value == "standalone"


class CountingToken:
    type = "ID"
    start = 0
    end = 1

    def __init__(self, text: str) -> None:
        self._text = text
        self.reads = 0

    @property
    def text(self) -> str:
        self.reads += 1
        return self._text


def test_repeat_tap_captures_once_and_same_order_executions_are_fifo() -> None:
    _, namespace = _generate(
        "#Name ::= ID\n<S> ::= [root] many: #Name+\n<OwnerDef> ::= [owner] item: ITEM",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "Values += many\n"
        "^Owner.Items += many\n"
        "}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= item\n}\n",
    )
    tokens = [CountingToken("first"), CountingToken("second"), CountingToken("third")]

    result = namespace["GeneratedParser"]().parse(tokens, "start")

    assert result.Values == ("first", "second", "third")
    assert result.Items == ("first", "second", "third")
    assert [token.reads for token in tokens] == [1, 1, 1]


@pytest.mark.parametrize("quantifier", ("+", "*"))
def test_scoped_repeat_is_resultless_and_taps_every_item(
    quantifier: str,
) -> None:
    _, namespace = _generate(
        "#Item ::= ITEM\n"
        "#Result ::= RESULT\n"
        "<S> ::= [root] child: <Transparent>\n"
        f"<Transparent> ::= [transparent] marker: MARK values: #Item{quantifier} "
        "returned: #Result",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "Child = child\n"
        "}\n"
        "<Transparent>[transparent] {\n"
        "-= marker\n"
        "^Owner.Items += values\n"
        "}\n",
    )

    result = namespace["GeneratedParser"]().parse(
        [
            Token("MARK"),
            Token("ITEM", "first"),
            Token("ITEM", "second"),
            Token("RESULT", "actual"),
        ],
        "start",
    )

    assert result.Child == "actual"
    assert result.Items == ("first", "second")


@pytest.mark.parametrize("error_kind", ("syntax", "freeze", "append"))
def test_runtime_state_is_cleared_and_parser_reusable_after_errors(error_kind: str) -> None:
    _, namespace = _owner_runtime()
    parser = namespace["GeneratedParser"]()
    owner_class = namespace["AST_CLASSES"]["Owner"]
    owner_defaults = namespace["NODE_DEFAULTS"]["Owner"]

    if error_kind == "syntax":
        failing_tokens = [Token("BAD")]
        expected_error = namespace["GeneratedParseError"]
    elif error_kind == "freeze":
        namespace["AST_CLASSES"]["Owner"] = lambda *args: (_ for _ in ()).throw(
            RuntimeError("freeze failed")
        )
        failing_tokens = _tokens()
        expected_error = RuntimeError
    else:
        namespace["NODE_DEFAULTS"]["Owner"] = tuple(
            (field, "scalar" if field == "Items" else category)
            for field, category in owner_defaults
        )
        failing_tokens = _tokens()
        expected_error = AttributeError

    with pytest.raises(expected_error):
        parser.parse(failing_tokens, "start")

    assert parser._owner_stacks == {}
    assert parser._pending_scoped_appends == {}
    assert parser._enqueue_sequence == 0
    namespace["AST_CLASSES"]["Owner"] = owner_class
    namespace["NODE_DEFAULTS"]["Owner"] = owner_defaults
    assert parser.parse(_tokens(), "start").Name == "outer"
