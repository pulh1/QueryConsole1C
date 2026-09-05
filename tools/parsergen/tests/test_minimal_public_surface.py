import importlib.util

import pytest

import parsergen
from parsergen.config import ParsergenConfig, load_config


REMOVED = (
    "parse_syntax_grammar",
    "parse_semantic_profile",
    "bind_semantic_profile",
    "SemanticBindingResult",
    "SemanticProfile",
    "SemanticProfileParseResult",
    "SyntaxGrammar",
    "SyntaxParseResult",
    "AppendNearestOwner",
)

REMOVED_MODULES = (
    "parsergen.bsl_codegen",
    "parsergen.semantic_actions",
    "parsergen.hybrid_bsl_codegen",
)


def test_public_module_does_not_export_removed_projection_api() -> None:
    assert all(not hasattr(parsergen, name) for name in REMOVED)


def test_public_surface_has_no_legacy_bsl_or_migration_path(tmp_path) -> None:
    config = tmp_path / "parsergen.toml"
    config.write_text(
        'grammar = "grammar.txt"\n'
        'target = "Parser"\n'
        "lookahead = 1\n"
        "[migration]\n"
        'canonical_productions = ["S"]\n'
        "[entrypoints]\n"
        '"parse" = "S"\n',
        encoding="utf-8",
    )

    assert all(importlib.util.find_spec(name) is None for name in REMOVED_MODULES)
    assert not hasattr(ParsergenConfig, "canonical_productions")
    with pytest.raises(ValueError, match="unexpected top-level configuration keys: 'migration'"):
        load_config(config)
