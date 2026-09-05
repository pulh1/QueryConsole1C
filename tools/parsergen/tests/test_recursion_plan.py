from dataclasses import fields, is_dataclass, replace

import pytest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import (
    BranchIr,
    CanonicalDecision,
    Operation,
    ParserIr,
    ProductionIr,
    ReturnConstant,
    build_parser_ir,
)
from parsergen.recursion_plan import (
    ContinuationLayout,
    ContinuationSlot,
    IrSite,
    analyze_recursion_plan,
)
from parsergen.resolver import resolve_grammar
from parsergen.source_model import SourceGrammar


def _build(source: str) -> tuple[SourceGrammar, ParserIr]:
    parsed = parse_grammar(source, "recursion-plan.grammar")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    return parsed.source_grammar, build_parser_ir(
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


# Mutation caught: classify every final self-call as tail_loop, losing the
# continuation's constant suffix or transforming a discarded-result call.
def test_plan_classifies_safe_tail_continuation_and_unsafe_discard() -> None:
    tail_source, tail_ir = _build("<S> ::= ITEM <S> | STOP")
    continuation_source, continuation_ir = _build(
        "<S> ::= @Link Value = ITEM Rest = <S> Kind := Истина | @End STOP"
    )
    discard_source, discard_ir = _build("<S> ::= 'a' -= <S> | @End STOP")

    tail = analyze_recursion_plan(tail_source, tail_ir)
    continuation = analyze_recursion_plan(
        continuation_source,
        continuation_ir,
    )
    discard = analyze_recursion_plan(discard_source, discard_ir)

    assert tail.sites[0].site == IrSite("S", 0, (("operation", 1),))
    assert tail.sites[0].kind == "tail_loop"
    assert tail.sites[0].layout is None
    assert continuation.sites[0].kind == "local_continuation"
    assert continuation.sites[0].layout == ContinuationLayout(
        (
            ContinuationSlot("span_start", 0),
            ContinuationSlot("builder_field", 1),
        ),
        suffix_indices=(3,),
    )
    assert discard.sites == ()
    _assert_contains_no_execution_ir(tail)
    _assert_contains_no_execution_ir(continuation)
    _assert_contains_no_execution_ir(discard)


# Mutation caught: infer iteration progress from the recursive call's
# syntactic position, even after the source-linked IR prefix stops consuming.
def test_plan_rejects_tail_site_without_proven_ir_progress() -> None:
    source, parser_ir = _build("<S> ::= ITEM <S> | STOP")
    production = parser_ir.productions[0]
    alternative = production.alternatives[0]
    first = alternative.operations[0]
    assert hasattr(first, "source_span")
    no_progress_ir = replace(
        parser_ir,
        productions=(
            replace(
                production,
                alternatives=(
                    replace(
                        alternative,
                        operations=(
                            ReturnConstant("unchanged", first.source_span),
                            *alternative.operations[1:],
                        ),
                    ),
                    *production.alternatives[1:],
                ),
            ),
        ),
    )

    plan = analyze_recursion_plan(source, no_progress_ir)

    assert plan.sites == ()


# Mutation caught: treat a LeftFold recurrence as a local continuation even
# though it has its own accumulator and iteration semantics.
def test_plan_never_emits_a_fold_accumulator_continuation_slot() -> None:
    source, parser_ir = _build(
        "<S> ::= @Node Left = <S> Right = ITEM | @Leaf ITEM"
    )

    plan = analyze_recursion_plan(source, parser_ir)

    assert plan.sites == ()


# Mutation caught: replace calls with iteration while dropping evaluation of
# actual arguments or the default-parameter reset of an omitted argument.
@pytest.mark.parametrize("grammar", [
    "<S>(Context) ::= ITEM <S>(Context.Next()) | STOP",
    "<S>(Context) ::= @Link Value = ITEM Rest = <S>(Context.Next()) | @End STOP",
    "<S>(Context) ::= ITEM <S>(Context) | STOP",
    "<S>(Context) ::= ITEM <S> | STOP",
    "<S>(First, Second) ::= ITEM <S>(Second, First) | STOP",
    "<S>(Context) ::= (ITEM <S>(Context.Next()))?",
])
def test_plan_keeps_parameter_state_changes_recursive(grammar: str) -> None:
    source, parser_ir = _build(grammar)

    assert analyze_recursion_plan(source, parser_ir).sites == ()


# Mutation caught: snapshot a completed prefix wrapper's seed a second time,
# or remove the seed needed to finish a genuinely suspended WrapValue.
@pytest.mark.parametrize("grammar, trail, slots", [
    (
        "<S> ::= <Leaf> Next => <Wrapped> -= <S> | @End STOP\n"
        "<Leaf> ::= @Leaf ITEM\n<Wrapped> ::= @Wrapped WRAP",
        (("operation", 1),),
        (ContinuationSlot("operation_result", 0),),
    ),
    (
        "<S> ::= <Leaf> Next => <S> | @End STOP\n<Leaf> ::= @Leaf ITEM",
        (("operation", 0), ("value", 0)),
        (ContinuationSlot("wrap_seed", 0),),
    ),
])
def test_wrap_layout_saves_only_state_needed_after_recursion(
    grammar: str, trail: tuple, slots: tuple[ContinuationSlot, ...],
) -> None:
    source, parser_ir = _build(grammar)

    plan = analyze_recursion_plan(source, parser_ir)

    assert len(plan.sites) == 1
    call = plan.sites[0]
    assert call.site == IrSite("S", 0, trail)
    assert call.kind == "local_continuation"
    assert call.layout == ContinuationLayout(slots)
