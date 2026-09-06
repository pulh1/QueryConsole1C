"""Bound repeated work with counters, never wall-clock timing assertions."""

from dataclasses import replace
from unittest.mock import patch

import pytest

from parsergen.analysis import compute_analysis
from parsergen.canonical_bsl_codegen import generate_canonical_parser
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.recursion_plan import analyze_recursion_plan
from parsergen.resolver import resolve_grammar


def _build(grammar):
    parsed = parse_grammar(grammar)
    assert parsed.diagnostics == ()
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    entries = {f"parse{i}": production.name for i, production in enumerate(parsed.source_grammar.productions)}
    analysis = compute_analysis(resolved.grammar, 1, tuple(entries.values()))
    parser_ir = build_parser_ir(
        parsed.source_grammar, parsed.lowering, resolved.grammar, analysis,
        entrypoint_productions=tuple(entries.values()),
    )
    return parsed.source_grammar, parser_ir, entries


def test_nonrecursive_sequence_does_not_copy_quadratic_suffixes() -> None:
    # Mutation caught: materialize every remaining suffix before finding a call.
    class CountedSequence(tuple):
        copied_items = 0

        def __getitem__(self, key):
            result = super().__getitem__(key)
            if isinstance(key, slice):
                self.copied_items += len(result)
            return result

    count = 128
    source, parser_ir, _ = _build("<S> ::= " + " ".join(["ITEM"] * count))
    production = parser_ir.productions[0]
    alternative = production.alternatives[0]
    operations = CountedSequence(alternative.operations)
    parser_ir = replace(parser_ir, productions=(replace(
        production, alternatives=(replace(alternative, operations=operations),),
    ),))

    plan = analyze_recursion_plan(source, parser_ir)

    assert plan.sites == ()
    assert operations.copied_items <= 4 * count


@pytest.mark.parametrize("target, generate", [
    ("parsergen.direct_render_analysis", generate_python_semantic_parser),
    ("parsergen.canonical_bsl_codegen", generate_canonical_parser),
])
def test_renderer_does_not_compare_every_site_with_every_production(target, generate) -> None:
    # Mutation caught: filter the complete site list for each production.
    # Instrument equality on otherwise ordinary production-name strings; the
    # real planner and renderer still supply every decision and output byte.
    class CountedName(str):
        comparisons = 0
        __hash__ = str.__hash__

        def __eq__(self, other):
            type(self).comparisons += 1
            return super().__eq__(other)

    count = 40
    source, parser_ir, entries = _build("\n".join(
        f"<P{i}> ::= ITEM <P{i}> | STOP" for i in range(count)
    ))
    expected = generate(source, parser_ir, entries).module_text
    plan = analyze_recursion_plan(source, parser_ir)
    assert len(plan.sites) == count
    plan = replace(plan, sites=tuple(
        replace(call, site=replace(call.site, production=CountedName(call.site.production)))
        for call in plan.sites
    ))

    with patch(f"{target}.analyze_recursion_plan", return_value=plan):
        generated = generate(source, parser_ir, entries)

    assert generated.module_text == expected
    assert CountedName.comparisons <= 10 * count
