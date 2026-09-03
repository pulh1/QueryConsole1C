from dataclasses import replace

import pytest

from parsergen.analysis import compute_analysis
from parsergen.canonical_bsl_codegen import generate_canonical_parser
from parsergen.grammar_parser import parse_grammar
from parsergen.hybrid_bsl_codegen import generate_hybrid_parser
from parsergen.parser_ir import AppendNearestOwner, build_parser_ir
from parsergen.resolver import resolve_grammar
from parsergen.source_model import SourceScopedValue


def _parts():
    parsed = parse_grammar("<S> ::= @Owner Items += ITEM", "legacy.grammar")
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
    return parsed, resolved.grammar, analysis, parser_ir


def _source_only_variant(source, parser_ir):
    production = source.productions[0]
    alternative = production.alternatives[0]
    constructor, binding = alternative.body.items
    scoped = SourceScopedValue(
        "Owner", "Items", binding.value, None, binding.span, 0
    )
    body = replace(alternative.body, items=(constructor, replace(binding, value=scoped)))
    changed_source = replace(
        source,
        productions=(
            replace(production, alternatives=(replace(alternative, body=body),)),
        ),
    )
    return changed_source, replace(parser_ir, source_grammar=changed_source)


def _ir_only_variant(source, parser_ir):
    production = parser_ir.productions[0]
    alternative = production.alternatives[0]
    constructor, append = alternative.operations
    scoped = AppendNearestOwner(
        "Owner", "Items", append.value, None, 0, append.source_span
    )
    changed = replace(
        parser_ir,
        productions=(
            replace(
                production,
                alternatives=(
                    replace(
                        alternative,
                        operations=(constructor, replace(append, value=scoped)),
                    ),
                ),
            ),
        ),
    )
    return source, changed


@pytest.mark.parametrize("variant", (_source_only_variant, _ir_only_variant))
def test_canonical_bsl_rejects_scoped_source_or_live_ir_before_entrypoints(variant) -> None:
    parsed, _, _, parser_ir = _parts()
    source, changed_ir = variant(parsed.source_grammar, parser_ir)

    with pytest.raises(ValueError, match="scoped append.*canonical BSL"):
        generate_canonical_parser(source, changed_ir, {})


@pytest.mark.parametrize("variant", (_source_only_variant, _ir_only_variant))
def test_hybrid_bsl_rejects_scoped_source_or_live_ir_before_routing(variant) -> None:
    parsed, resolved, analysis, parser_ir = _parts()
    source, changed_ir = variant(parsed.source_grammar, parser_ir)

    with pytest.raises(ValueError, match="scoped append.*hybrid BSL"):
        generate_hybrid_parser(
            source,
            parsed.lowering,
            parsed.grammar,
            resolved,
            analysis,
            changed_ir,
            canonical_productions=(),
            entrypoints={"Разобрать": "S"},
        )


def test_combined_grammar_rejects_leading_scoped_append_with_gp010() -> None:
    result = parse_grammar("<S> ::= ^Owner.Items += ITEM", "combined.grammar")

    assert [item.code for item in result.diagnostics] == ["GP010"]
    diagnostic = result.diagnostics[0]
    assert diagnostic.span.start.column == 9
    assert "scoped append" in diagnostic.message
