import parsergen


REMOVED = (
    "parse_syntax_grammar",
    "parse_semantic_profile",
    "bind_semantic_profile",
    "SemanticProfile",
    "AppendNearestOwner",
)


def test_public_module_does_not_export_removed_projection_api() -> None:
    assert all(not hasattr(parsergen, name) for name in REMOVED)
