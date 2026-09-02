from parsergen.semantic_profile_binding import bind_semantic_profile
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.source_model import (
    SourceBinding,
    SourceConstructor,
    SourceGroup,
    SourceOptional,
    SourceRepeat,
)
from parsergen.syntax_grammar_parser import parse_syntax_grammar


def _bind(syntax_source: str, profile_source: str):
    syntax_result = parse_syntax_grammar(syntax_source, "syntax.grammar")
    profile_result = parse_semantic_profile(profile_source, "worker.semantic")
    assert syntax_result.diagnostics == ()
    assert syntax_result.grammar is not None
    assert profile_result.diagnostics == ()
    assert profile_result.profile is not None
    return (
        syntax_result.grammar,
        bind_semantic_profile(syntax_result.grammar, profile_result.profile),
    )


def _diagnostic(syntax_source: str, profile_source: str, code: str):
    _, result = _bind(syntax_source, profile_source)
    assert result.source_grammar is None
    matches = [item for item in result.diagnostics if item.code == code]
    assert len(matches) == 1
    diagnostic = matches[0]
    assert diagnostic.span.path == "worker.semantic"
    return diagnostic


def _syntax_related(diagnostic):
    related = [
        item for item in diagnostic.related if item.span.path == "syntax.grammar"
    ]
    assert related
    return related


def test_binds_profile_to_an_ordinary_source_grammar() -> None:
    syntax = parse_syntax_grammar(
        "#Name ::= ID\n<S> ::= [simple] name: #Name '=' value: &NUMBER",
        "syntax.grammar",
    ).grammar
    profile = parse_semantic_profile(
        "profile worker\n<S>[simple] {\n@Assignment\nName = name\nValue = value\nEnabled := Истина\n}",
        "worker.semantic",
    ).profile
    assert syntax is not None and profile is not None
    original_items = syntax.source_grammar.productions[0].alternatives[0].body.items

    result = bind_semantic_profile(syntax, profile)

    assert result.diagnostics == ()
    assert result.source_grammar is not None
    rendered_items = result.source_grammar.productions[0].alternatives[0].body.items
    assert type(rendered_items[0]).__name__ == "SourceConstructor"
    assert type(rendered_items[1]).__name__ == "SourceBinding"
    assert type(rendered_items[-1]).__name__ == "SourceConstantBinding"
    assert isinstance(rendered_items[0], SourceConstructor)
    assert isinstance(rendered_items[1], SourceBinding)
    assert rendered_items[0].span.path == "worker.semantic"
    assert rendered_items[1].span.path == "worker.semantic"
    assert rendered_items[1].value.span == original_items[0].span
    assert syntax.source_grammar.productions[0].alternatives[0].body.items == original_items
    assert not any(isinstance(item, SourceBinding) for item in original_items)


def test_recursively_rebuilds_groups_optionals_and_repeats() -> None:
    syntax_source = (
        "<S> ::= [root] optional: ([present] inner: ITEM)? "
        "repeated: ([element] item: ITEM)*"
    )
    profile_source = """profile worker
<S>[root] {
    -= optional
    -= repeated
}
<S>[present] {
    -= inner
}
<S>[element] {
    -= item
}
"""

    syntax, result = _bind(syntax_source, profile_source)

    assert result.diagnostics == ()
    assert result.source_grammar is not None
    items = result.source_grammar.productions[0].alternatives[0].body.items
    assert isinstance(items[0], SourceBinding)
    assert isinstance(items[0].value, SourceOptional)
    assert isinstance(items[0].value.body, SourceGroup)
    assert isinstance(
        items[0].value.body.alternatives[0].body.items[0],
        SourceBinding,
    )
    assert isinstance(items[1], SourceBinding)
    assert isinstance(items[1].value, SourceRepeat)
    assert isinstance(items[1].value.body, SourceGroup)
    assert isinstance(
        items[1].value.body.alternatives[0].body.items[0],
        SourceBinding,
    )
    original_items = syntax.source_grammar.productions[0].alternatives[0].body.items
    assert isinstance(original_items[0], SourceOptional)
    assert isinstance(original_items[1], SourceRepeat)


def test_reports_unknown_production_as_spb200() -> None:
    diagnostic = _diagnostic(
        "<S> ::= [only] value: ITEM",
        "profile worker\n<Missing> {\n}\n",
        "SPB200",
    )

    assert diagnostic.span.start.line == 2
    assert _syntax_related(diagnostic)[0].span.start.line == 1


def test_reports_unknown_alternative_as_spb201() -> None:
    diagnostic = _diagnostic(
        "<S> ::= [only] value: ITEM",
        "profile worker\n<S>[missing] {\n}\n",
        "SPB201",
    )

    assert diagnostic.span.start.line == 2
    assert _syntax_related(diagnostic)[0].span.start.line == 1


def test_reports_ambiguous_unnamed_alternative_as_spb202() -> None:
    diagnostic = _diagnostic(
        "<S> ::= [first] one: A | [second] two: B",
        "profile worker\n<S> {\n}\n",
        "SPB202",
    )

    assert diagnostic.span.start.line == 2
    assert len(_syntax_related(diagnostic)) == 2


def test_reports_missing_anchor_as_spb203() -> None:
    diagnostic = _diagnostic(
        "<S> ::= [only] value: ITEM",
        "profile worker\n<S>[only] {\nName = missing\n}\n",
        "SPB203",
    )

    assert diagnostic.span.start.line == 3
    assert _syntax_related(diagnostic)[0].span.start.offset == 8


def test_reports_wrong_scope_anchor_as_spb204() -> None:
    syntax_source = "<S> ::= [first] one: A | [second] two: B"
    diagnostic = _diagnostic(
        syntax_source,
        "profile worker\n<S>[first] {\nName = two\n}\n",
        "SPB204",
    )

    assert diagnostic.span.start.line == 3
    assert any(
        item.span.start.offset == syntax_source.index("two:")
        for item in _syntax_related(diagnostic)
    )


def test_reports_duplicate_profile_selector_as_spb205() -> None:
    diagnostic = _diagnostic(
        "<S> ::= [only] value: ITEM",
        "profile worker\n<S>[only] {\n}\n<S>[only] {\n}\n",
        "SPB205",
    )

    assert diagnostic.span.start.line == 4
    assert _syntax_related(diagnostic)[0].span.start.offset == 8
    assert any(item.span.start.line == 2 for item in diagnostic.related)


def test_reports_incompatible_anchor_reuse_as_spb206() -> None:
    syntax_source = "<S> ::= [only] value: ITEM"
    diagnostic = _diagnostic(
        syntax_source,
        "profile worker\n<S>[only] {\nLeft = value\nRight += value\n}\n",
        "SPB206",
    )

    assert diagnostic.span.start.line == 4
    assert _syntax_related(diagnostic)[0].span.start.offset == syntax_source.index(
        "value:"
    )
    assert any(item.span.start.line == 3 for item in diagnostic.related)


def test_converts_binding_validator_rejection_to_spb207() -> None:
    diagnostic = _diagnostic(
        "<S> ::= [only] value: ITEM",
        "profile worker\n<S>[only] {\nName = value\n}\n",
        "SPB207",
    )

    assert diagnostic.span.start.line == 3
    assert diagnostic.related[0].message.startswith("BIND201:")
    assert diagnostic.related[0].span.path == "worker.semantic"
    assert _syntax_related(diagnostic)[0].span.start.offset == 8


def test_converts_source_validator_rejection_to_spb207() -> None:
    syntax_source = "<S> ::= [root] value: <N>*\n<N> ::= ПУСТО"
    diagnostic = _diagnostic(
        syntax_source,
        "profile worker\n<S>[root] {\n-= value\n}\n",
        "SPB207",
    )

    assert diagnostic.span.start.line == 2
    assert diagnostic.related[0].message.startswith("EBNF201:")
    assert diagnostic.related[0].span.start.offset == syntax_source.index("*")
    assert _syntax_related(diagnostic)


def test_spb207_provenance_does_not_depend_on_distinct_paths() -> None:
    syntax_source = "<S> ::= [root] value: <N>*\n<N> ::= ПУСТО"
    syntax = parse_syntax_grammar(syntax_source).grammar
    profile = parse_semantic_profile(
        "profile worker\n<S>[root] {\n-= value\n}\n"
    ).profile
    assert syntax is not None and profile is not None
    assert syntax.path == profile.path == "<memory>"

    result = bind_semantic_profile(syntax, profile)

    assert result.source_grammar is None
    diagnostic = next(item for item in result.diagnostics if item.code == "SPB207")
    assert diagnostic.span is profile.alternatives[0].span
    assert diagnostic.related[0].message.startswith("EBNF201:")
    assert any(
        item.span is syntax.alternatives[0].span
        for item in diagnostic.related
    )


def test_maps_unprofiled_validator_error_to_the_same_production_profile() -> None:
    _, result = _bind(
        "#Item ::= ID\n"
        "<A> ::= [only_a] value: #Item\n"
        "<B> ::= [bound] first: #Item | [unbound] left: #Item right: #Item",
        "profile worker\n"
        "<A>[only_a] {\n-= value\n}\n"
        "<B>[bound] {\n-= first\n}\n",
    )

    assert result.source_grammar is None
    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == "SPB207"
        and item.related[0].message.startswith("BIND206:")
    )
    assert diagnostic.span.path == "worker.semantic"
    assert diagnostic.span.start.line == 5
    assert diagnostic.related[0].span.path == "syntax.grammar"
