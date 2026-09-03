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
