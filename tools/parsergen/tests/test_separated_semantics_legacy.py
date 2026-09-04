from dataclasses import fields
from inspect import signature

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.lowering import LoweringResult
from parsergen.parser_ir import ConstructNode, ParserIr, build_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar
from parsergen.separated_model import SemanticAlternative
from parsergen.source_model import SourceConstructor, SourceGrammar


LEGACY_SOURCE = (
    "#Name ::= ID\n"
    "<S> ::= @Assignment Name = #Name '=' Value = &NUMBER "
    "Enabled := Истина"
)


def test_separated_semantics_are_additive_public_api() -> None:
    import parsergen

    assert parsergen.__version__ == "0.2.0"
    assert callable(parsergen.parse_syntax_grammar)
    assert callable(parsergen.parse_semantic_profile)
    assert callable(parsergen.bind_semantic_profile)
    assert parsergen.SyntaxGrammar.__module__ == "parsergen.separated_model"
    assert parsergen.SemanticProfile.__module__ == "parsergen.separated_model"


def _legacy_module_text() -> str:
    parsed = parse_grammar(LEGACY_SOURCE, "legacy.grammar")
    assert parsed.diagnostics == ()
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    assert parsed.grammar is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )
    return generate_python_semantic_parser(
        parsed.source_grammar,
        parser_ir,
        {"start": "S"},
    ).module_text


def test_legacy_dataclass_shapes_and_parse_signature_are_frozen() -> None:
    assert tuple(item.name for item in fields(SemanticAlternative)) == (
        "production", "alternative", "constructor", "constructor_span",
        "anchor_bindings", "constants", "span",
    )
    assert tuple(item.name for item in fields(SourceConstructor)) == (
        "name", "span",
    )
    assert tuple(item.name for item in fields(ConstructNode)) == (
        "constructor", "source_span",
    )
    assert tuple(item.name for item in fields(SourceGrammar)) == (
        "productions", "identifier_definitions", "path"
    )
    assert tuple(item.name for item in fields(LoweringResult)) == (
        "grammar", "constructs", "production_origins", "alternative_origins",
        "diagnostics", "bindings", "left_recursions",
    )
    assert tuple(item.name for item in fields(ParserIr)) == (
        "productions", "matcher_definitions", "lookahead", "source_grammar",
        "entrypoint_productions",
    )
    assert str(signature(parse_grammar)) == (
        "(text: 'str', path: 'str' = '<memory>') -> 'ParseResult'"
    )


def test_legacy_python_semantic_module_uses_the_direct_backend() -> None:
    module_text = _legacy_module_text()
    namespace: dict[str, object] = {}
    exec(compile(module_text, "<legacy-generated-parser>", "exec"), namespace)

    assert str(signature(namespace["GeneratedParser"].parse)) == (
        "(self, tokens, entrypoint)"
    )
    assert 'PARSERGEN_BACKEND_ID = "python-semantic-direct-v1"' in module_text
    assert "PRODUCTIONS =" not in module_text
    assert "DECISIONS =" not in module_text
    assert "class _Frame" not in module_text
    assert "_run_sequence" not in module_text
