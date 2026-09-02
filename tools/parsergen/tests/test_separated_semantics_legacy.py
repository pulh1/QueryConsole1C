from dataclasses import fields
import hashlib
from inspect import signature

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.lowering import LoweringResult
from parsergen.parser_ir import ParserIr, build_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar
from parsergen.source_model import SourceGrammar


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


def test_legacy_python_semantic_module_text_is_byte_identical() -> None:
    digest = hashlib.sha256(_legacy_module_text().encode("utf-8")).hexdigest()
    assert digest == "5aa204ccdaddb8dba6d07da5f861bb1716be03a83d50e5ff8cacdbf44abcf01c"
