import pytest

from parsergen.diagnostics import SourcePosition, SourceSpan
from parsergen.model import Terminal
from parsergen.semantic_profile_binding import bind_semantic_profile
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.source_model import SourceScopedValue
from parsergen.syntax_grammar_parser import parse_syntax_grammar


def _bind(syntax_source: str, profile_source: str):
    syntax = parse_syntax_grammar(syntax_source, "syntax.grammar")
    profile = parse_semantic_profile(profile_source, "worker.semantic")
    assert syntax.diagnostics == ()
    assert syntax.grammar is not None
    assert profile.diagnostics == ()
    assert profile.profile is not None
    return bind_semantic_profile(syntax.grammar, profile.profile)


def _original_codes(result) -> list[str]:
    return [
        item.details["original_code"]
        for item in result.diagnostics
        if item.code == "SPB207"
    ]


def test_rejects_unknown_owner_constructor() -> None:
    result = _bind(
        "<S> ::= [root] item: ITEM",
        "profile worker\n<S>[root] {\n^Missing.Items += item\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["SCOP200"]


def test_rejects_scoped_collection_conflicting_with_owner_scalar_field() -> None:
    result = _bind(
        "<Owner> ::= [owner] value: ITEM\n<S> ::= [root] item: ITEM",
        "profile worker\n"
        "<Owner>[owner] {\n@Owner\nItems = value\n}\n"
        "<S>[root] {\n^Owner.Items += item\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["SCOP201"]
    diagnostic = next(item for item in result.diagnostics if item.code == "SPB207")
    assert any(
        item.message == "conflicting scalar field is declared here"
        and item.span.path == "worker.semantic"
        and item.span.start.line == 4
        for item in diagnostic.related
    )


@pytest.mark.parametrize("target", ("<OwnerDef>", "<Choice>"))
def test_rejects_scoped_collection_conflicting_with_wrap_scalar(
    target: str,
) -> None:
    result = _bind(
        f"<S> ::= [root] seed: <Seed> child: {target}\n"
        "<Seed> ::= [seed] item: SEED\n"
        "<OwnerDef> ::= [owner] item: OWNER\n"
        "<Choice> ::= [owner_choice] item: OWNER | [other_choice] item: OTHER",
        "profile worker\n"
        "<S>[root] {\nChild => child\n^Owner.Child += seed\n}\n"
        "<Seed>[seed] {\n@Seed\n-= item\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= item\n}\n"
        "<Choice>[owner_choice] {\n@Owner\n-= item\n}\n"
        "<Choice>[other_choice] {\n@Other\n-= item\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["SCOP201"]
    diagnostic = next(item for item in result.diagnostics if item.code == "SPB207")
    assert any(
        item.message == "conflicting scalar field is declared here"
        and item.span.path == "worker.semantic"
        and item.span.start.line == 3
        for item in diagnostic.related
    )


def test_scoped_collection_accepts_wrap_prepend_collection_target() -> None:
    result = _bind(
        "<S> ::= [root] seed: <Seed> child: <OwnerDef>\n"
        "<Seed> ::= [seed] item: SEED\n"
        "<OwnerDef> ::= [owner] item: OWNER",
        "profile worker\n"
        "<S>[root] {\nChildren +=> child\n^Owner.Children += seed\n}\n"
        "<Seed>[seed] {\n@Seed\n-= item\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= item\n}\n",
    )

    assert result.diagnostics == ()
    assert result.source_grammar is not None


@pytest.mark.parametrize("anchor", ("(A B)", "(A B)?", "(A B)*", "(A B)+"))
def test_rejects_scoped_anchor_branch_without_one_capturable_value(
    anchor: str,
) -> None:
    result = _bind(
        f"<S> ::= [root] value: {anchor}\n"
        "<OwnerDef> ::= [owner] value: OWNER",
        "profile worker\n"
        "<S>[root] {\n^Owner.Items += value\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= value\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["SCOP205"]
    diagnostic = next(item for item in result.diagnostics if item.code == "SPB207")
    assert diagnostic.span.path == "worker.semantic"
    assert diagnostic.span.start.line == 3


def test_rejects_scoped_anchor_with_nested_multiple_results() -> None:
    result = _bind(
        "<S> ::= [root] value: ((<A> <B> | C))\n"
        "<A> ::= A\n"
        "<B> ::= B\n"
        "<OwnerDef> ::= [owner] value: OWNER",
        "profile worker\n"
        "<S>[root] {\n^Owner.Items += value\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= value\n}\n",
    )

    assert result.source_grammar is None
    assert "SCOP205" in _original_codes(result)


@pytest.mark.parametrize(
    "anchor",
    (
        "([word] token: 'word')",
        "([word] token: 'word')+",
    ),
)
def test_scoped_anchor_accepts_propertyless_semantic_constant_result(
    anchor: str,
) -> None:
    result = _bind(
        f"<S> ::= [root] value: {anchor}",
        "profile worker\n"
        "<S>[root] {\n@Owner\n^Owner.Items += value\n}\n"
        "<S>[word] {\n-= token\n:= Kinds.Word\n}\n",
    )

    assert result.diagnostics == ()
    assert result.source_grammar is not None


def test_group_constant_and_following_result_reports_bind206_before_ir() -> None:
    result = _bind(
        "#Result ::= RESULT\n"
        "<S> ::= [root] ([word] 'word') returned: #Result",
        "profile worker\n"
        "<S>[root] {\n}\n"
        "<S>[word] {\n:= Kinds.Word\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["BIND206"]


def test_nested_group_with_multiple_results_reports_bind206_before_ir() -> None:
    result = _bind(
        "<S> ::= [root] (<A> <B> | C) item: ITEM\n"
        "<A> ::= A\n"
        "<B> ::= B\n"
        "<OwnerDef> ::= [owner] token: OWNER",
        "profile worker\n"
        "<S>[root] {\n^Owner.Items += item\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= token\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["BIND206"]


def test_scoped_repeat_cannot_intervene_before_returned_child() -> None:
    result = _bind(
        "<S> ::= [root] seed: <Seed> values: ITEM* child: <Child>\n"
        "<Seed> ::= [seed] token: SEED\n"
        "<Child> ::= [child] token: CHILD\n"
        "<OwnerDef> ::= [owner] token: OWNER",
        "profile worker\n"
        "<S>[root] {\n^Owner.Items += values\nChildField => child\n}\n"
        "<Seed>[seed] {\n@Seed\n-= token\n}\n"
        "<Child>[child] {\n@Child\n-= token\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= token\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["BIND210"]


@pytest.mark.parametrize(
    ("anchor", "support"),
    (
        ("<A>*", "<A> ::= A\n"),
        ("(<A> | TOKEN)*", "<A> ::= A\n"),
        ("((<A> <B> | C))*", "<A> ::= A\n<B> ::= B\n"),
    ),
)
def test_unbound_semantic_repeat_reports_bind206_before_ir(
    anchor: str,
    support: str,
) -> None:
    result = _bind(
        f"<S> ::= [root] many: {anchor} item: ITEM\n"
        f"{support}"
        "<OwnerDef> ::= [owner] token: OWNER",
        "profile worker\n"
        "<S>[root] {\n^Owner.Items += item\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= token\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["BIND206"]


@pytest.mark.parametrize(
    ("owner", "expected_codes"),
    (("Owner", ()), ("Other", ("SCOP201",))),
)
def test_wrap_constructor_inference_follows_only_returned_nonterminal(
    owner: str,
    expected_codes: tuple[str, ...],
) -> None:
    result = _bind(
        "<S> ::= [root] seed: <Seed> child: <Transparent>\n"
        "<Seed> ::= [seed] token: SEED\n"
        "<Transparent> ::= [transparent] discarded: <OwnerDef> "
        "returned: <OtherDef>\n"
        "<OwnerDef> ::= [owner] token: OWNER\n"
        "<OtherDef> ::= [other] token: OTHER",
        "profile worker\n"
        f"<S>[root] {{\nChild => child\n^{owner}.Child += seed\n}}\n"
        "<Seed>[seed] {\n@Seed\n-= token\n}\n"
        "<Transparent>[transparent] {\n-= discarded\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= token\n}\n"
        "<OtherDef>[other] {\n@Other\n-= token\n}\n",
    )

    assert tuple(_original_codes(result)) == expected_codes
    assert (result.source_grammar is not None) == (not expected_codes)


@pytest.mark.parametrize(
    "anchor",
    ("((<Child>))", "((<Child>)?)"),
)
def test_scoped_anchor_accepts_nested_transparent_result(anchor: str) -> None:
    result = _bind(
        f"<S> ::= [root] value: {anchor}\n"
        "<Child> ::= [child] token: CHILD",
        "profile worker\n"
        "<S>[root] {\n@Owner\n^Owner.Items += value\n}\n"
        "<Child>[child] {\n@Child\n-= token\n}\n",
    )

    assert result.diagnostics == ()
    assert result.source_grammar is not None


@pytest.mark.parametrize("returned", ("(<OwnerDef>)", "<OwnerDef>?"))
def test_wrap_constructor_inference_follows_nested_transparent_result(
    returned: str,
) -> None:
    result = _bind(
        "<S> ::= [root] seed: <Seed> child: <Transparent>\n"
        "<Seed> ::= [seed] token: SEED\n"
        f"<Transparent> ::= [transparent] {returned}\n"
        "<OwnerDef> ::= [owner] token: OWNER",
        "profile worker\n"
        "<S>[root] {\nChild => child\n^Owner.Child += seed\n}\n"
        "<Seed>[seed] {\n@Seed\n-= token\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= token\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["SCOP201"]


@pytest.mark.parametrize("quantifier", ("*", "+"))
def test_wrap_constructor_inference_ignores_scoped_repeat_side_effect(
    quantifier: str,
) -> None:
    result = _bind(
        "<S> ::= [root] seed: <Seed> child: <Transparent>\n"
        "<Seed> ::= [seed] token: SEED\n"
        f"<Transparent> ::= [transparent] marker: MARK owners: <OwnerDef>{quantifier} "
        "returned: <OtherDef>\n"
        "<OwnerDef> ::= [owner] token: OWNER\n"
        "<OtherDef> ::= [other] token: OTHER\n"
        "<SinkDef> ::= [sink] token: SINK",
        "profile worker\n"
        "<S>[root] {\nChild => child\n^Owner.Child += seed\n}\n"
        "<Seed>[seed] {\n@Seed\n-= token\n}\n"
        "<Transparent>[transparent] {\n-= marker\n^Sink.Items += owners\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= token\n}\n"
        "<OtherDef>[other] {\n@Other\n-= token\n}\n"
        "<SinkDef>[sink] {\n@Sink\n-= token\n}\n",
    )

    assert result.diagnostics == ()
    assert result.source_grammar is not None


def test_current_field_appends_after_a_definite_scalar_write() -> None:
    result = _bind(
        "<S> ::= [root] value: ITEM",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "Value = value\n"
        "^Owner.Items += $Value\n"
        "}\n",
    )

    assert result.diagnostics == ()
    assert result.source_grammar is not None
    effect = result.source_grammar.productions[0].alternatives[0].body.items[-1]
    assert isinstance(effect, SourceScopedValue)
    assert effect.value is None
    assert effect.current_field == "Value"


def test_concat_and_increment_are_definite_scalar_writes() -> None:
    for operator in ("~=", "++="):
        result = _bind(
            "<S> ::= [root] value: ITEM",
            "profile worker\n"
            "<S>[root] {\n"
            "@Owner\n"
            f"Value {operator} value\n"
            "^Owner.Items += $Value\n"
            "}\n",
        )

        assert result.diagnostics == ()


def test_current_field_requires_an_active_builder_and_definite_write() -> None:
    cases = (
        (
            "<S> ::= [root] value: ITEM\n<Owner> ::= [owner] token: OWNER",
            "profile worker\n"
            "<S>[root] {\n^Owner.Items += $Value\n}\n"
            "<Owner>[owner] {\n@Owner\n-= token\n}\n",
            "SCOP202",
        ),
        (
            "<S> ::= [root] value: ITEM",
            "profile worker\n<S>[root] {\n@Owner\n^Owner.Items += $Value\n}\n",
            "SCOP203",
        ),
    )

    for syntax_source, profile_source, expected in cases:
        result = _bind(syntax_source, profile_source)

        assert result.source_grammar is None
        assert _original_codes(result) == [expected]


def test_group_intersects_definite_writes_but_optional_and_repeat_do_not() -> None:
    accepted = _bind(
        "<S> ::= [root] ([left] LEFT | [right] RIGHT)",
        "profile worker\n"
        "<S>[root] {\n@Owner\n^Owner.Items += $Value\n}\n"
        "<S>[left] {\nValue := Истина\n}\n"
        "<S>[right] {\nValue := Ложь\n}\n",
    )
    assert accepted.diagnostics == ()

    rejected_sources = (
        "<S> ::= [root] ([present] ITEM)?",
        "<S> ::= [root] ([present] ITEM)*",
    )
    for syntax_source in rejected_sources:
        result = _bind(
            syntax_source,
            "profile worker\n"
            "<S>[root] {\n@Owner\n^Owner.Items += $Value\n}\n"
            "<S>[present] {\nValue := Истина\n}\n",
        )

        assert result.source_grammar is None
        assert _original_codes(result) == ["SCOP203"]


def test_nonterminal_call_does_not_export_current_builder_writes() -> None:
    result = _bind(
        "<S> ::= [root] child: <Child>\n<Child> ::= [child] value: ITEM",
        "profile worker\n"
        "<S>[root] {\n@Owner\n-= child\n^Owner.Items += $Value\n}\n"
        "<Child>[child] {\n@Child\nValue = value\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["SCOP203"]


def test_scoped_append_is_allowed_in_lr_base_and_rejected_in_recursive_suffix() -> None:
    syntax = (
        "<Expr> ::= [recursive] left: <Expr> plus: '+' right: ITEM "
        "| [base] item: ITEM"
    )
    base = _bind(
        syntax,
        "profile worker\n"
        "<Expr>[recursive] {\n@Binary\nLeft = left\n-= plus\nRight = right\n}\n"
        "<Expr>[base] {\n@Owner\nValue = item\n^Owner.Items += item\n}\n",
    )
    assert base.diagnostics == ()

    recursive = _bind(
        syntax,
        "profile worker\n"
        "<Expr>[recursive] {\n@Binary\nLeft = left\n-= plus\nRight = right\n"
        "^Owner.Items += right\n}\n"
        "<Expr>[base] {\n@Owner\nValue = item\n}\n",
    )
    assert recursive.source_grammar is None
    assert _original_codes(recursive) == ["SCOP204"]


def test_rejects_scoped_tap_on_direct_lr_self_reference() -> None:
    result = _bind(
        "<Expr> ::= [recursive] left: <Expr> plus: '+' right: ITEM "
        "| [base] item: ITEM",
        "profile worker\n"
        "<Expr>[recursive] {\n"
        "@Binary\n"
        "Left = left\n"
        "^Owner.Items += left\n"
        "-= plus\n"
        "Right = right\n"
        "}\n"
        "<Expr>[base] {\n@Owner\nValue = item\n}\n",
    )

    assert result.source_grammar is None
    assert _original_codes(result) == ["SCOP204"]


def test_source_scoped_value_requires_exactly_one_payload_kind() -> None:
    position = SourcePosition(1, 1, 0)
    span = SourceSpan("profile.semantic", position, position)
    value = Terminal("ITEM", span)

    with pytest.raises(ValueError, match="exactly one"):
        SourceScopedValue(
            "Owner",
            "Items",
            None,
            None,
            source_order=0,
            span=span,
        )
    with pytest.raises(ValueError, match="exactly one"):
        SourceScopedValue(
            "Owner",
            "Items",
            value,
            "Field",
            source_order=0,
            span=span,
        )
