from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.source_model import BindingMode


def test_parses_constructor_anchor_bindings_and_constants() -> None:
    result = parse_semantic_profile(
        """profile worker
<S>[simple] {
    @Assignment
    Name = name
    Items += item
    Children *= children
    Path ~= part
    Count ++= mark
    Child => child
    Decorators +=> decorator
    += root_item
    -= ignored
    Enabled := Истина
    := Неопределено
}
""",
        "worker.semantic",
    )

    assert result.diagnostics == ()
    assert result.profile is not None
    alternative = result.profile.alternatives[0]
    assert alternative.constructor == "Assignment"
    assert [item.mode for item in alternative.anchor_bindings] == [
        BindingMode.SCALAR,
        BindingMode.APPEND,
        BindingMode.EXTEND,
        BindingMode.CONCAT,
        BindingMode.INCREMENT,
        BindingMode.WRAP,
        BindingMode.WRAP_PREPEND,
        BindingMode.APPEND,
        BindingMode.DISCARD,
    ]
    assert [(item.property, item.value) for item in alternative.constants] == [
        ("Enabled", "Истина"),
        (None, "Неопределено"),
    ]


def test_reports_sanitized_diagnostics_for_malformed_profiles() -> None:
    cases = (
        ("<Missing> {\n}\n", "missing.semantic", "SPP100", 1, 1, "Missing"),
        (
            "profile first\nprofile second\n",
            "duplicate.semantic",
            "SPP100",
            2,
            1,
            "second",
        ),
        (
            "profile valid\n<Broken {\n}\n",
            "selector.semantic",
            "SPP101",
            2,
            1,
            "Broken",
        ),
        (
            "profile valid\n<S>[choice]\n",
            "block.semantic",
            "SPP102",
            2,
            12,
            "choice",
        ),
        (
            "profile valid\n<S> {\n    @First\n    @Second\n}\n",
            "constructor.semantic",
            "SPP103",
            4,
            5,
            "Second",
        ),
        (
            "profile valid\n<S> {\n    { callback }\n}\n",
            "action.semantic",
            "SPP104",
            3,
            5,
            "callback",
        ),
        (
            "profile valid\n<S> {\n    Field +=\n}\n",
            "binding.semantic",
            "SPP105",
            3,
            11,
            "Field",
        ),
    )

    for source, path, code, line, column, source_literal in cases:
        result = parse_semantic_profile(source, path)

        diagnostic = next(item for item in result.diagnostics if item.code == code)
        assert diagnostic.span.path == path
        assert (diagnostic.span.start.line, diagnostic.span.start.column) == (line, column)
        assert source_literal not in diagnostic.message


def test_rejects_unterminated_and_extra_delimiter_alternative_selectors() -> None:
    for selector in ("<S>[broken {", "<S>[broken]] {"):
        result = parse_semantic_profile(
            f"profile worker\n{selector}\n",
            "selector.semantic",
        )

        assert [item.code for item in result.diagnostics] == ["SPP101"]


def test_rejects_constructor_after_discard_statement() -> None:
    result = parse_semantic_profile(
        "profile worker\n"
        "<S> {\n"
        "    -= ignored\n"
        "    @Node\n"
        "}\n",
        "late-constructor.semantic",
    )

    assert result.profile is None
    assert [
        (
            diagnostic.code,
            diagnostic.span.start.line,
            diagnostic.span.start.column,
            diagnostic.span.end.column,
        )
        for diagnostic in result.diagnostics
    ] == [("SPP103", 4, 5, 10)]


def test_parses_scoped_anchor_and_current_field_with_exact_spans() -> None:
    result = parse_semantic_profile(
        "profile worker\n"
        "<S> {\n"
        "    ^Owner.Collection += item\n"
        "    ^Owner.Collection += $CurrentField\n"
        "}\n",
        "worker.semantic",
    )

    assert result.diagnostics == ()
    assert result.profile is not None
    anchor, current_field = result.profile.scoped_appends
    assert (
        anchor.production,
        anchor.alternative,
        anchor.owner,
        anchor.property,
        anchor.anchor,
        anchor.current_field,
    ) == ("S", None, "Owner", "Collection", "item", None)
    assert (
        anchor.span.start.line,
        anchor.span.start.column,
        anchor.span.end.column,
        anchor.operator_span.start.column,
        anchor.operator_span.end.column,
    ) == (3, 5, 30, 23, 25)
    assert (
        current_field.anchor,
        current_field.current_field,
        current_field.span.start.line,
        current_field.span.start.column,
        current_field.span.end.column,
        current_field.operator_span.start.column,
        current_field.operator_span.end.column,
    ) == (None, "CurrentField", 4, 5, 39, 23, 25)


def test_rejects_malformed_or_trailing_scoped_append_input() -> None:
    cases = (
        "^Owner += item",
        "^Owner.Collection = item",
        "^Owner.Collection += $",
        "^Owner.Collection += item trailing",
    )

    for directive in cases:
        result = parse_semantic_profile(
            f"profile worker\n<S> {{\n    {directive}\n}}\n",
            "worker.semantic",
        )

        assert result.profile is None
        assert [item.code for item in result.diagnostics] == ["SPP105"]


def test_scoped_prefix_does_not_change_legacy_member_binding() -> None:
    result = parse_semantic_profile(
        "profile worker\n"
        "<S> {\n"
        "    Owner.Collection += legacy\n"
        "    ^Owner.Collection += scoped\n"
        "}\n",
        "worker.semantic",
    )

    assert result.diagnostics == ()
    assert result.profile is not None
    alternative = result.profile.alternatives[0]
    assert [(item.property, item.anchor) for item in alternative.anchor_bindings] == [
        ("Owner.Collection", "legacy")
    ]
    assert [item.anchor for item in result.profile.scoped_appends] == ["scoped"]
