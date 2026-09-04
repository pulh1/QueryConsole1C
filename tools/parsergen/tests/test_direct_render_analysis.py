from dataclasses import FrozenInstanceError, fields, is_dataclass, replace

import pytest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.lowering import lower_source_grammar
from parsergen.parser_ir import (
    BranchIr,
    CanonicalDecision,
    Operation,
    ParserIr,
    ProductionIr,
    build_parser_ir,
)
from parsergen.resolver import resolve_grammar
from parsergen.semantic_profile_binding import bind_semantic_profile
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.syntax_grammar_parser import parse_syntax_grammar
from parsergen.decision_dag import (
    CanonicalDecisionDag,
    CommitAlternative,
    DecisionEdge,
    LookaheadDecision,
)
from parsergen.canonical_select import AlternativeOutcome, TokenSetPredicate

from parsergen.direct_render_analysis import IrSite, analyze_direct_render


def _build_ir(source: str, *, k: int = 1) -> ParserIr:
    parsed = parse_grammar(source, "direct-test.grammar")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, k, ("S",))
    return build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )


def _build_bound_ir(syntax_source: str, profile_source: str) -> ParserIr:
    syntax = parse_syntax_grammar(syntax_source, "direct-test.grammar")
    profile = parse_semantic_profile(profile_source, "direct-test.semantic")
    assert syntax.diagnostics == ()
    assert syntax.grammar is not None
    assert profile.diagnostics == ()
    assert profile.profile is not None
    bound = bind_semantic_profile(syntax.grammar, profile.profile)
    assert bound.diagnostics == ()
    assert bound.source_grammar is not None
    lowering = lower_source_grammar(bound.source_grammar)
    assert lowering.diagnostics == ()
    resolved = resolve_grammar(lowering.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    return build_parser_ir(
        bound.source_grammar,
        lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )


def _assert_contains_no_execution_ir(value: object) -> None:
    assert not isinstance(
        value,
        Operation | BranchIr | ProductionIr | CanonicalDecision,
    )
    if is_dataclass(value):
        for field in fields(value):
            _assert_contains_no_execution_ir(getattr(value, field.name))
    elif isinstance(value, (tuple, frozenset)):
        for item in value:
            _assert_contains_no_execution_ir(item)


def test_analysis_uses_stable_ir_sites_and_is_immutable() -> None:
    parser_ir = _build_ir("<S> ::= @Node Value = ITEM")

    first = analyze_direct_render(parser_ir)
    second = analyze_direct_render(parser_ir)

    assert first == second
    assert first.sequence_liveness[0].site == IrSite("S", 0, ())
    with pytest.raises(FrozenInstanceError):
        first.sequence_liveness = ()
    _assert_contains_no_execution_ir(first)


def test_sequence_liveness_retains_its_result_after_it_is_produced() -> None:
    parser_ir = _build_ir("<S> ::= &Number")

    analysis = analyze_direct_render(parser_ir)
    sequence = analysis.sequence_liveness[0]
    result_index = parser_ir.productions[0].alternatives[0].result_index

    assert result_index is not None
    assert sequence.live_after[result_index] == frozenset({result_index})


def test_analysis_discovers_owner_types_in_nested_scoped_values() -> None:
    parser_ir = _build_bound_ir(
        "#Value ::= ID\n"
        "#Other ::= NAME\n"
        "<S> ::= [root] value: (#Value | #Other)",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "^Owner.Items += value\n"
        "}\n",
    )

    analysis = analyze_direct_render(parser_ir)

    assert analysis.mutable_owner_types == frozenset({"Owner"})
    assert analysis.decisions[0].site == IrSite(
        "S",
        0,
        (("operation", 1), ("value", 0)),
    )


def test_decision_indegrees_follow_dag_edges() -> None:
    parser_ir = _build_ir("<S> ::= A | B")
    original = parser_ir.productions[0]
    assert original.decision is not None
    dag = CanonicalDecisionDag(
        "S",
        2,
        0,
        (
            LookaheadDecision(
                0,
                ("A", "B"),
                (
                    DecisionEdge(TokenSetPredicate(("A",)), 1),
                    DecisionEdge(TokenSetPredicate(("B",)), 2),
                ),
            ),
            LookaheadDecision(
                1,
                ("C", "D"),
                (
                    DecisionEdge(TokenSetPredicate(("C",)), 2),
                    DecisionEdge(TokenSetPredicate(("D",)), 3),
                ),
            ),
            CommitAlternative(AlternativeOutcome("S", 1)),
            CommitAlternative(AlternativeOutcome("S", 2)),
        ),
        {},
    )
    decision = CanonicalDecision(original.decision.source, dag)
    parser_ir = replace(
        parser_ir,
        productions=(replace(original, decision=decision),),
    )

    analysis = analyze_direct_render(parser_ir)

    assert analysis.decisions[0].node_indegrees == (0, 1, 2, 1)
