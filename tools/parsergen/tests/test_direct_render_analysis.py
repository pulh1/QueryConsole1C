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

from parsergen.direct_render_analysis import (
    ContinuationLayout,
    ContinuationSlot,
    IrSite,
    RecursiveCallSite,
    analyze_direct_render,
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


@pytest.mark.parametrize(
    ("grammar", "expected"),
    [
        ("<S> ::= ITEM <S> | ПУСТО", "safe_tail_loop"),
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

    assert analysis.recursive_calls[0].kind == expected


def test_local_continuation_has_only_live_builder_state() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @Link Value = ITEM Rest = <S> | @End STOP")
    )

    assert analysis.recursive_calls[0].site == IrSite(
        "S",
        0,
        (("operation", 2), ("value", 0)),
    )
    assert analysis.recursive_calls[0].layout == ContinuationLayout(
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

    assert analysis.recursive_calls == (
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

    assert all(site.kind != "safe_tail_loop" for site in analysis.recursive_calls)
    assert analysis.recursive_calls[0].kind == "local_continuation"


def test_active_wrap_prevents_tail_loop_and_preserves_its_seed() -> None:
    analysis = analyze_direct_render(
        _build_ir(
            "<S> ::= <Leaf> Next => <S> | @End STOP\n"
            "<Leaf> ::= @Leaf ITEM"
        )
    )

    assert analysis.recursive_calls[0].kind == "local_continuation"
    assert analysis.recursive_calls[0].layout == ContinuationLayout(
        (ContinuationSlot("wrap_seed", 0),)
    )


def test_collection_receiver_prevents_tail_loop_and_preserves_accumulator() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @List Items += ITEM <S> | @End STOP")
    )

    assert analysis.recursive_calls[0].kind == "local_continuation"
    assert analysis.recursive_calls[0].layout == ContinuationLayout(
        (
            ContinuationSlot("span_start", 0),
            ContinuationSlot("collection_accumulator", 1),
        )
    )


def test_pending_constructor_freeze_prevents_tail_loop() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @Node Value = ITEM <S> | @End STOP")
    )

    assert analysis.recursive_calls[0].layout == ContinuationLayout(
        (
            ContinuationSlot("span_start", 0),
            ContinuationSlot("builder_field", 1),
        )
    )


def test_pending_scoped_effect_prevents_recursion_transformation() -> None:
    analysis = analyze_direct_render(
        _build_bound_ir(
            "#Value ::= ITEM\n"
            "<S> ::= [root] value: #Value <S> | STOP",
            "profile worker\n"
            "<S>[root] {\n"
            "@Owner\n"
            "^Owner.Items += value\n"
            "}\n",
        )
    )

    assert analysis.recursive_calls == ()


@pytest.mark.parametrize(
    ("syntax_source", "profile_source", "production", "trail"),
    (
        (
            "#Item ::= ITEM\n"
            "<S> ::= [root] elements: <Elements>\n"
            "<Elements> ::= [elements] ([item] item: #Item rest: <Elements>)?",
            "profile worker\n"
            "<S>[root] {\n@Owner\n-= elements\n}\n"
            "<Elements>[item] {\n"
            "^Owner.Items += item\n-= item\n-= rest\n}\n",
            "Elements",
            (
                ("operation", 0),
                ("branch", 0),
                ("operation", 1),
            ),
        ),
        (
            "#Item ::= ITEM\n"
            "<S> ::= [root] body: <Block>\n"
            "<Block> ::= [block] ([first] first: <Statement> "
            "([rest] separator: SEP rest: <Block>)?)?\n"
            "<Statement> ::= [statement] value: #Item | "
            "[nested] discard: AGAIN nested: <Block> discard_2: END",
            "profile worker\n"
            "<S>[root] {\n@Owner\n-= body\n}\n"
            "<Block>[first] {\n-= first\n}\n"
            "<Block>[rest] {\n-= separator\n-= rest\n}\n"
            "<Statement>[statement] {\n"
            "^Owner.Items += value\n-= value\n}\n"
            "<Statement>[nested] {\n"
            "-= discard\n-= nested\n-= discard_2\n}\n",
            "Block",
            (
                ("operation", 0),
                ("branch", 0),
                ("operation", 1),
                ("branch", 0),
                ("operation", 1),
            ),
        ),
    ),
    ids=("direct-scoped-effect", "transitive-scoped-effect"),
)
def test_resultless_discarded_tail_preserves_scoped_effects_iteratively(
    syntax_source: str,
    profile_source: str,
    production: str,
    trail: tuple[tuple[str, int], ...],
) -> None:
    analysis = analyze_direct_render(_build_bound_ir(syntax_source, profile_source))

    assert RecursiveCallSite(
        IrSite(production, 0, trail),
        "safe_tail_loop",
        None,
    ) in analysis.recursive_calls


def test_left_fold_is_not_classified_as_direct_recursion() -> None:
    analysis = analyze_direct_render(
        _build_ir("<S> ::= @Node Left = <S> Right = ITEM | @Leaf ITEM")
    )

    assert analysis.recursive_calls == ()


def test_direct_self_tail_is_transformed_without_classifying_mutual_edges() -> None:
    analysis = analyze_direct_render(
        _build_ir(
            "<S> ::= ITEM <S> | <A>\n"
            "<A> ::= STOP <S> | END"
        )
    )

    assert analysis.recursive_calls == (
        RecursiveCallSite(
            IrSite("S", 0, (("operation", 1),)),
            "safe_tail_loop",
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

    assert analysis.recursive_calls == (
        RecursiveCallSite(
            IrSite("S", 0, (("operation", 2), ("value", 0))),
            "local_continuation",
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
        for item in analysis.sequence_liveness
        if item.site == IrSite("S", 0, ())
    )
    assert sequence.live_after == (frozenset({0}), frozenset({0}))
    assert analysis.recursive_calls[0].kind == "local_continuation"
    assert analysis.recursive_calls[0].layout == ContinuationLayout(
        (ContinuationSlot("operation_result", 0),)
    )
