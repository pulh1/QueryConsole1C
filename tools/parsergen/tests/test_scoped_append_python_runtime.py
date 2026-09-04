from __future__ import annotations

from dataclasses import dataclass

import pytest

from parsergen.analysis import compute_analysis
from parsergen.lowering import lower_source_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.python_semantic_codegen import _generate_direct_python_semantic_parser
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
    generated = _generate_direct_python_semantic_parser(
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

    assert "_owner_stack_owner" in generated.module_text
    assert type(result) is namespace["Owner"]
    assert result.Name == "outer"
    assert result.Items[0] == "tail"
    child = result.Items[1]
    assert type(child) is namespace["Owner"]
    assert child.Name == "inner"
    assert child.Items == ("leaf",)
    assert result.Items[2] == "outer"
    assert type(child.Leaf) is namespace["Leaf"]


def test_nested_scoped_effects_are_sorted_by_source_then_enqueue() -> None:
    _, namespace = _generate(
        "#Name ::= ID\n"
        "<S> ::= [root] before: <Before> after: <After> outer: #Name\n"
        "<Before> ::= [before] value: #Name\n"
        "<After> ::= [after] value: #Name",
        "profile worker\n"
        "<Before>[before] {\n"
        "^Owner.Items += value\n"
        "}\n"
        "<S>[root] {\n"
        "@Owner\n"
        "Name = outer\n"
        "^Owner.Items += outer\n"
        "}\n"
        "<After>[after] {\n"
        "^Owner.Items += value\n"
        "}\n",
    )

    result = namespace["GeneratedParser"]().parse(
        [
            Token("ID", "before", 0, 6),
            Token("ID", "after", 7, 12),
            Token("ID", "outer", 13, 18),
        ],
        "start",
    )

    assert result.Name == "outer"
    assert result.Items == ("before", "outer", "after")


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
        f"<Transparent> ::= [transparent] values: #Item{quantifier} "
        "returned: #Result",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "Child = child\n"
        "}\n"
        "<Transparent>[transparent] {\n"
        "^Owner.Items += values\n"
        "}\n",
    )

    result = namespace["GeneratedParser"]().parse(
        [
            Token("ITEM", "first"),
            Token("ITEM", "second"),
            Token("RESULT", "actual"),
        ],
        "start",
    )

    assert result.Child == "actual"
    assert result.Items == ("first", "second")


@pytest.mark.parametrize(
    ("operator", "optional", "property_name"),
    (
        ("ChildField =>", "", "ChildField"),
        ("ChildField =>", "?", "ChildField"),
        ("Children +=>", "", "Children"),
    ),
)
def test_scoped_wrap_receiver_contributes_target_schema(
    operator: str,
    optional: str,
    property_name: str,
) -> None:
    _, namespace = _generate(
        "<S> ::= [root] seed: <Seed> "
        f"child: <Child>{optional}\n"
        "<Seed> ::= [seed] token: SEED\n"
        "<Child> ::= [child] token: CHILD\n"
        "<OwnerDef> ::= [owner] token: OWNER",
        "profile worker\n"
        "<S>[root] {\n"
        f"{operator} child\n"
        "^Owner.Items += child\n"
        "}\n"
        "<Seed>[seed] {\n@Seed\n-= token\n}\n"
        "<Child>[child] {\n@Child\n-= token\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= token\n}\n",
    )

    result = namespace["GeneratedParser"]().parse(
        [Token("SEED", "seed"), Token("CHILD", "child")],
        "start",
    )

    assert type(result) is namespace["Child"]
    wrapped = getattr(result, property_name)
    if operator == "Children +=>":
        assert len(wrapped) == 1
        wrapped = wrapped[0]
    assert type(wrapped) is namespace["Seed"]


def test_scoped_group_payload_contributes_active_builder_schema() -> None:
    _, namespace = _generate(
        "#Value ::= VALUE\n"
        "<S> ::= [root] grouped: ([group] value: #Value child: <Child>)\n"
        "<Child> ::= [child] token: CHILD",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "^Owner.Items += grouped\n"
        "}\n"
        "<S>[group] {\nField = value\n}\n"
        "<Child>[child] {\n@Child\n-= token\n}\n",
    )

    result = namespace["GeneratedParser"]().parse(
        [Token("VALUE", "kept"), Token("CHILD")],
        "start",
    )

    assert result.Field == "kept"
    assert len(result.Items) == 1
    assert type(result.Items[0]) is namespace["Child"]


def test_scoped_append_reuses_propertyless_root_collection() -> None:
    _, namespace = _generate(
        "#Name ::= ID\n<S> ::= [root] first: #Name second: #Name",
        "profile worker\n"
        "<S>[root] {\n"
        "@List\n"
        "+= first\n"
        "^List.items += second\n"
        "}\n",
    )

    result = namespace["GeneratedParser"]().parse(
        [Token("ID", "first"), Token("ID", "second")],
        "start",
    )

    assert result.items == ("first", "second")


@pytest.mark.parametrize("error_kind", ("syntax", "freeze", "append"))
def test_runtime_state_is_cleared_and_parser_reusable_after_errors(error_kind: str) -> None:
    _, namespace = _owner_runtime()
    parser = namespace["GeneratedParser"]()
    owner_class = namespace["Owner"]
    owner_state = namespace["_OwnerState_Owner"]

    if error_kind == "syntax":
        failing_tokens = [Token("BAD")]
        expected_error = namespace["GeneratedParseError"]
    elif error_kind == "freeze":
        namespace["Owner"] = lambda *args: (_ for _ in ()).throw(
            RuntimeError("freeze failed")
        )
        failing_tokens = _tokens()
        expected_error = RuntimeError
    else:
        class RaisingAppendList:
            def append(self, payload: object) -> None:
                raise RuntimeError("append failed")

        namespace["_OwnerState_Owner"] = lambda *collections: owner_state(
            RaisingAppendList()
        )
        failing_tokens = _tokens()
        expected_error = RuntimeError

    with pytest.raises(expected_error):
        parser.parse(failing_tokens, "start")

    assert parser._owner_stack_owner == []
    assert parser._enqueue_sequence == 0
    namespace["Owner"] = owner_class
    namespace["_OwnerState_Owner"] = owner_state
    assert parser.parse(_tokens(), "start").Name == "outer"
