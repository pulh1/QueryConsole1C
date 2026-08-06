from collections.abc import Mapping

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.resolver import ResolvedGrammar, resolve_grammar
from parsergen.validation import ValidationReport, validate_grammar


def resolved(text: str) -> ResolvedGrammar:
    parsed = parse_grammar(text)
    assert parsed.grammar is not None
    assert parsed.diagnostics == ()
    result = resolve_grammar(parsed.grammar)
    assert result.grammar is not None
    assert result.diagnostics == ()
    return result.grammar


def compiled(
    text: str,
    k: int,
    entrypoints: Mapping[str, str],
):
    parsed = parse_grammar(text)
    assert parsed.grammar is not None
    assert parsed.diagnostics == ()
    resolution = resolve_grammar(parsed.grammar)
    assert resolution.grammar is not None
    assert resolution.diagnostics == ()
    analysis = compute_analysis(
        resolution.grammar,
        k,
        tuple(entrypoints.values()),
    )
    report = validate_grammar(
        parsed.grammar,
        resolution.grammar,
        analysis,
        entrypoints,
    )
    assert not report.has_errors, report.diagnostics
    return parsed.grammar, resolution.grammar, analysis


def validate_text(
    text: str,
    entrypoints: Mapping[str, str],
    k: int,
) -> ValidationReport:
    parsed = parse_grammar(text)
    if parsed.grammar is None:
        raise AssertionError("parser did not return a grammar")
    resolution = resolve_grammar(parsed.grammar)
    analysis = None
    if resolution.grammar is not None:
        valid_starts = tuple(
            name
            for name in entrypoints.values()
            if name in resolution.grammar.productions
        )
        if not valid_starts and resolution.grammar.production_order:
            valid_starts = (resolution.grammar.production_order[0],)
        analysis = compute_analysis(resolution.grammar, k, valid_starts)
    return validate_grammar(
        parsed.grammar,
        resolution.grammar,
        analysis,
        entrypoints,
        (*parsed.diagnostics, *resolution.diagnostics),
    )

