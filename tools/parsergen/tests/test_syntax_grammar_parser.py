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
