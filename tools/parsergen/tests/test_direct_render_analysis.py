from dataclasses import FrozenInstanceError, fields, is_dataclass, replace

import pytest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import (
    BranchIr,
    CanonicalDecision,
    Operation,
    ParserIr,
    ProductionIr,
    build_parser_ir,
)
from parsergen.resolver import resolve_grammar
from parsergen.decision_dag import (
    CanonicalDecisionDag,
    CommitAlternative,
    DecisionEdge,
    LookaheadDecision,
)
from parsergen.canonical_select import AlternativeOutcome, TokenSetPredicate

from parsergen.direct_render_analysis import analyze_direct_render
from parsergen.recursion_plan import (
    ContinuationLayout,
    ContinuationSlot,
    IrSite,
    RecursiveCallSite,
    ResultFlowFact,
    analyze_recursion_plan,
)


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
    assert first.recursion_plan.sequence_liveness[0].site == IrSite("S", 0, ())
    with pytest.raises(FrozenInstanceError):
        first.recursion_plan = first.recursion_plan
    _assert_contains_no_execution_ir(first)


# Mutation caught: leave recursion eligibility in DirectRenderAnalysis rather
# than exposing the target-neutral plan built over the same ParserIr.
def test_analysis_exposes_the_shared_recursion_plan() -> None:
    parser_ir = _build_ir("<S> ::= ITEM <S> | STOP")

    analysis = analyze_direct_render(parser_ir)

    assert analysis.recursion_plan == analyze_recursion_plan(
        parser_ir.source_grammar,
        parser_ir,
    )


def test_sequence_liveness_retains_its_result_after_it_is_produced() -> None:
    parser_ir = _build_ir("<S> ::= &Number")

    analysis = analyze_direct_render(parser_ir)
    sequence = analysis.recursion_plan.sequence_liveness[0]
    result_index = parser_ir.productions[0].alternatives[0].result_index

    assert result_index is not None
    assert sequence.live_after[result_index] == frozenset({result_index})


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


@pytest.mark.parametrize(
    ("grammar", "expected"),
    [
        ("<S> ::= ITEM <S> | ПУСТО", "tail_loop"),
        (
            "<S> ::= @Link Value = ITEM Rest = <S> | @End STOP",
            "local_continuation",
        ),
    ],
)
def test_classifies_direct_self_recursion(
    grammar: str,
    expected: str,
) -> None:
    analysis = analyze_direct_render(_build_ir(grammar))

    assert analysis.recursion_plan.sites[0].kind == expected


def test_local_continuation_has_only_live_builder_state() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @Link Value = ITEM Rest = <S> | @End STOP")
    )

    assert analysis.recursion_plan.sites[0].site == IrSite(
        "S",
        0,
        (("operation", 2), ("value", 0)),
    )
    assert analysis.recursion_plan.sites[0].layout == ContinuationLayout(
        (
            ContinuationSlot("span_start", 0),
            ContinuationSlot("builder_field", 1),
        )
    )


def test_optional_branch_self_calls_have_path_specific_local_continuations() -> None:
    analysis = analyze_direct_render(
        _build_ir(
            "<S> ::= @Node ("
            "A Item = ITEM Rest = <S> | "
            "B First = ITEM (SEP Rest = <S>)?"
            ")? | @End STOP"
        )
    )

    assert analysis.recursion_plan.sites == (
        RecursiveCallSite(
            IrSite(
                "S",
                0,
                (
                    ("operation", 1),
                    ("branch", 0),
                    ("operation", 2),
                    ("value", 0),
                ),
            ),
            "local_continuation",
            False,
            ContinuationLayout(
                (
                    ContinuationSlot("span_start", 0),
                    ContinuationSlot("builder_field", None, "Item"),
                )
            ),
        ),
        RecursiveCallSite(
            IrSite(
                "S",
                0,
                (
                    ("operation", 1),
                    ("branch", 1),
                    ("operation", 2),
                    ("branch", 0),
                    ("operation", 1),
                    ("value", 0),
                ),
            ),
            "local_continuation",
            False,
            ContinuationLayout(
                (
                    ContinuationSlot("span_start", 0),
                    ContinuationSlot("builder_field", None, "First"),
                )
            ),
        ),
    )


def test_open_constructor_prevents_tail_loop() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @Node Value = ITEM <S> | @End STOP")
    )

    assert all(
        site.kind != "tail_loop" for site in analysis.recursion_plan.sites
    )
    assert analysis.recursion_plan.sites[0].kind == "local_continuation"


def test_active_wrap_prevents_tail_loop_and_preserves_its_seed() -> None:
    analysis = analyze_direct_render(
        _build_ir(
            "<S> ::= <Leaf> Next => <S> | @End STOP\n"
            "<Leaf> ::= @Leaf ITEM"
        )
    )

    assert analysis.recursion_plan.sites[0].kind == "local_continuation"
    assert analysis.recursion_plan.sites[0].layout == ContinuationLayout(
        (ContinuationSlot("wrap_seed", 0),)
    )


def test_collection_receiver_prevents_tail_loop_and_preserves_accumulator() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @List Items += ITEM <S> | @End STOP")
    )

    assert analysis.recursion_plan.sites[0].kind == "local_continuation"
    assert analysis.recursion_plan.sites[0].layout == ContinuationLayout(
        (
            ContinuationSlot("span_start", 0),
            ContinuationSlot("collection_accumulator", 1),
        )
    )


def test_pending_constructor_freeze_prevents_tail_loop() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @Node Value = ITEM <S> | @End STOP")
    )

    assert analysis.recursion_plan.sites[0].layout == ContinuationLayout(
        (
            ContinuationSlot("span_start", 0),
            ContinuationSlot("builder_field", 1),
        )
    )


def test_left_fold_is_not_classified_as_direct_recursion() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @Node Left = <S> Right = ITEM | @Leaf ITEM")
    )

    assert analysis.recursion_plan.sites == ()


def test_direct_self_tail_is_transformed_without_classifying_mutual_edges() -> None:
    analysis = analyze_direct_render(
        _build_ir(
            "<S> ::= ITEM <S> | <A>\n"
            "<A> ::= STOP <S> | END"
        )
    )

    assert analysis.recursion_plan.sites == (
        RecursiveCallSite(
            IrSite("S", 0, (("operation", 1),)),
            "tail_loop",
            True,
            None,
        ),
    )


def test_local_self_continuation_remains_safe_inside_a_mutual_component() -> None:
    analysis = analyze_direct_render(
        _build_ir(
            "<S> ::= @Link Value = ITEM Rest = <S> | <A>\n"
            "<A> ::= AGAIN <S> | @End STOP"
        )
    )

    assert analysis.recursion_plan.sites == (
        RecursiveCallSite(
            IrSite("S", 0, (("operation", 2), ("value", 0))),
            "local_continuation",
            False,
            ContinuationLayout(
                (
                    ContinuationSlot("span_start", 0),
                    ContinuationSlot("builder_field", 1),
                )
            ),
        ),
    )


def test_final_direct_self_call_preserves_a_live_prior_result() -> None:
    parser_ir = _build_ir(
        "<S> ::= <A> -= <S> | STOP\n"
        "<A> ::= ITEM"
    )
    production = parser_ir.productions[0]
    alternative = production.alternatives[0]
    parser_ir = replace(
        parser_ir,
        productions=(
            replace(
                production,
                alternatives=(
                    replace(alternative, result_index=0),
                    *production.alternatives[1:],
                ),
            ),
            *parser_ir.productions[1:],
        ),
    )

    analysis = analyze_direct_render(parser_ir)

    sequence = next(
        item
        for item in analysis.recursion_plan.sequence_liveness
        if item.site == IrSite("S", 0, ())
    )
    assert sequence.live_after == (frozenset({0}), frozenset({0}))
    assert analysis.recursion_plan.sites[0].kind == "local_continuation"
    assert analysis.recursion_plan.sites[0].layout == ContinuationLayout(
        (ContinuationSlot("operation_result", 0),)
    )


def test_direct_discarded_self_call_requires_unchanged_result_flow() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= 'a' -= <S> | @End STOP")
    )

    assert analysis.recursion_plan.result_flow == (
        ResultFlowFact(IrSite("S", 0, (("operation", 1),)), False),
    )
    assert analysis.recursion_plan.sites == ()
