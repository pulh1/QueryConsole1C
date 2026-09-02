from parsergen.syntax_grammar_parser import parse_syntax_grammar


def test_parses_named_alternative_and_anchors_without_changing_symbols() -> None:
    source = (
        "#Name ::= ID\n"
        "<S> ::= [simple] target: #Name '=' value: &NUMBER"
    )
    result = parse_syntax_grammar(source, "syntax.grammar")

    assert result.diagnostics == ()
    assert result.grammar is not None
    assert result.grammar.source_sha256 == (
        "395836e0a59e8e91f5101414c411a94156e54baf5c053faeb4e3b9f5dda32688"
    )
    assert [(item.production, item.name) for item in result.grammar.alternatives] == [
        ("S", "simple")
    ]
    assert [item.name for item in result.grammar.anchors] == ["target", "value"]
    production = result.grammar.source_grammar.productions[0]
    assert production.alternatives[0].body.items[0].span.start.offset == source.index(
        "#Name", source.index("<S>")
    )
    assert production.alternatives[0].body.items[1].span.start.offset == source.index("'='")


def test_addresses_anchors_inside_named_group_alternatives() -> None:
    result = parse_syntax_grammar(
        "<S> ::= [root] head: ITEM ([tail] comma: ',' item: ITEM)*",
        "syntax.grammar",
    )

    assert result.diagnostics == ()
    assert result.grammar is not None
    assert {(anchor.address.alternative, anchor.name) for anchor in result.grammar.anchors} == {
        ("root", "head"),
        ("tail", "comma"),
        ("tail", "item"),
    }


def test_rejects_duplicate_labels_anchors_and_combined_actions() -> None:
    result = parse_syntax_grammar(
        "<S> ::= [same] value: A value: B | [same] other: B @Node",
        "syntax.grammar",
    )

    assert {item.code for item in result.diagnostics} == {
        "SGP101",
        "SGP102",
        "SGP103",
    }
    assert result.grammar is None


def test_rejects_a_label_that_is_not_at_an_alternative_start() -> None:
    result = parse_syntax_grammar("<S> ::= A [bad] (B)", "syntax.grammar")

    assert [item.code for item in result.diagnostics] == ["SGP104"]
    assert result.grammar is None


def test_does_not_scan_identifier_declarations_with_whitespace() -> None:
    result = parse_syntax_grammar(
        "<S> ::= [root] item: ITEM\n"
        "# Name ::= [TOK]\n"
        "<T> ::= [next] second: ITEM",
        "syntax.grammar",
    )

    assert result.diagnostics == ()
    assert result.grammar is not None
    assert [item.token_types for item in result.grammar.source_grammar.identifier_definitions] == [
        ("[TOK]",)
    ]
    assert [(item.production, item.name) for item in result.grammar.alternatives] == [
        ("S", "root"),
        ("T", "next"),
    ]


def test_addresses_anchors_in_direct_left_recursion() -> None:
    result = parse_syntax_grammar(
        "<S> ::= [base] head: ITEM | "
        "[recursive] left: <S> separator: ',' tail: ITEM",
        "syntax.grammar",
    )

    assert result.diagnostics == ()
    assert result.grammar is not None
    assert {(anchor.address.alternative, anchor.name) for anchor in result.grammar.anchors} == {
        ("base", "head"),
        ("recursive", "left"),
        ("recursive", "separator"),
        ("recursive", "tail"),
    }


def test_fails_closed_when_an_anchor_target_cannot_be_resolved() -> None:
    result = parse_syntax_grammar(
        "<S> ::= [root] missing: ПУСТО",
        "syntax.grammar",
    )

    assert [item.code for item in result.diagnostics] == ["SGP104"]
    assert result.grammar is None
