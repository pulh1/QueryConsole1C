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
