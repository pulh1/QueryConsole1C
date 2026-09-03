from __future__ import annotations

from dataclasses import fields, replace
from unittest.mock import patch

import pytest

import parsergen.parser_ir as parser_ir_module
from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar, parse_source_grammar
from parsergen.lowering import lower_source_grammar
from parsergen.model import IdentifierRef, Lexeme, Terminal
from parsergen.parser_ir import (
    BindScalar,
    DispatchValue,
    LeftFold,
    OptionalBranch,
    ParseSymbol,
    RepeatLoop,
    ResolvedRegion,
    WrapOptional,
    build_parser_ir,
)
from parsergen.parser_ir_optimization import optimize_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar
from parsergen.semantic_profile_binding import bind_semantic_profile
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.syntax_grammar_parser import parse_syntax_grammar


AppendNearestOwner = getattr(
    parser_ir_module,
    "AppendNearestOwner",
    type(None),
)


def _bound_source(syntax_source: str, profile_source: str):
    syntax = parse_syntax_grammar(syntax_source, "syntax.grammar")
    profile = parse_semantic_profile(profile_source, "worker.semantic")
    assert syntax.diagnostics == ()
    assert syntax.grammar is not None
    assert profile.diagnostics == ()
    assert profile.profile is not None
    bound = bind_semantic_profile(syntax.grammar, profile.profile)
    assert bound.diagnostics == ()
    assert bound.source_grammar is not None
    return bound.source_grammar


def _build(
    syntax_source: str,
    profile_source: str,
    *,
    optimize: bool = True,
):
    source = _bound_source(syntax_source, profile_source)
    lowering = lower_source_grammar(source)
    assert lowering.diagnostics == ()
    resolution = resolve_grammar(lowering.grammar)
    assert resolution.diagnostics == ()
    assert resolution.grammar is not None
    analysis = compute_analysis(resolution.grammar, 1, ("S",))
    if optimize:
        return build_parser_ir(
            source,
            lowering,
            resolution.grammar,
            analysis,
            entrypoint_productions=("S",),
        )
    with patch(
        "parsergen.parser_ir_optimization.optimize_parser_ir",
        side_effect=lambda parser_ir: parser_ir,
    ):
        return build_parser_ir(
            source,
            lowering,
            resolution.grammar,
            analysis,
            entrypoint_productions=("S",),
        )


def _production(parser_ir, name: str):
    return next(item for item in parser_ir.productions if item.name == name)


def test_scoped_taps_capture_once_and_carry_global_profile_order() -> None:
    parser_ir = _build(
        "#Value ::= ID\n"
        "<S> ::= [root] first: #Value second: #Value",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "First = first\n"
        "^Owner.Items += second\n"
        "^Owner.Items += first\n"
        "^Owner.Items += $First\n"
        "}\n",
        optimize=False,
    )

    alternative = _production(parser_ir, "S").alternatives[0]
    receiver = alternative.operations[1]
    second = alternative.operations[2]
    current = alternative.operations[3]
    assert isinstance(receiver, BindScalar)
    assert isinstance(receiver.value, AppendNearestOwner)
    first = receiver.value
    assert isinstance(second, AppendNearestOwner)
    assert isinstance(current, AppendNearestOwner)
    assert [first.source_order, second.source_order, current.source_order] == [1, 0, 2]
    assert [item.source_order for item in sorted(
        (first, second, current), key=lambda item: item.source_order
    )] == [0, 1, 2]
    assert isinstance(first.value, ParseSymbol)
    assert isinstance(second.value, ParseSymbol)
    assert current.value is None
    assert current.current_field == "First"
    assert sum(
        isinstance(item, ParseSymbol)
        for item in (first.value, second.value)
    ) == 2
    assert tuple(item.name for item in fields(AppendNearestOwner)) == (
        "owner",
        "property",
        "value",
        "current_field",
        "source_order",
        "source_span",
    )


def test_current_field_before_anchors_keeps_its_earlier_source_order() -> None:
    parser_ir = _build(
        "#Value ::= ID\n"
        "<S> ::= [root] first: #Value second: #Value",
        "profile worker\n"
        "<S>[root] {\n"
        "@Owner\n"
        "First = first\n"
        "^Owner.Items += $First\n"
        "^Owner.Items += second\n"
        "^Owner.Items += first\n"
        "}\n",
        optimize=False,
    )

    operations = _production(parser_ir, "S").alternatives[0].operations
    first = operations[1].value
    second = operations[2]
    current = operations[3]
    assert isinstance(first, AppendNearestOwner)
    assert isinstance(second, AppendNearestOwner)
    assert isinstance(current, AppendNearestOwner)
    assert [first.source_order, second.source_order, current.source_order] == [2, 1, 0]
    assert current.current_field == "First"


def test_scoped_tap_is_transparent_for_a_semantic_anchor() -> None:
    parser_ir = _build(
        "#Value ::= ID\n"
        "<S> ::= [root] value: #Value\n"
        "<OwnerDef> ::= [owner] value: VALUE",
        "profile worker\n"
        "<S>[root] {\n^Owner.Items += value\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= value\n}\n",
        optimize=False,
    )

    alternative = _production(parser_ir, "S").alternatives[0]
    tap = alternative.operations[0]
    assert isinstance(tap, AppendNearestOwner)
    assert isinstance(tap.value, ParseSymbol)
    assert isinstance(tap.value.symbol, IdentifierRef)
    assert alternative.result_index == 0


def test_transparent_semantic_group_keeps_one_capture_per_branch() -> None:
    parser_ir = _build(
        "<S> ::= [root] choice: (<A> | <B>)\n"
        "<A> ::= A\n"
        "<B> ::= B\n"
        "<OwnerDef> ::= [owner] value: VALUE",
        "profile worker\n"
        "<S>[root] {\n^Owner.Items += choice\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= value\n}\n",
        optimize=False,
    )

    alternative = _production(parser_ir, "S").alternatives[0]
    tap = alternative.operations[0]
    assert isinstance(tap, AppendNearestOwner)
    assert alternative.result_index == 0
    assert isinstance(tap.value, DispatchValue)
    assert len(tap.value.branches) == 2
    assert all(branch.value.result_index == 0 for branch in tap.value.branches)
    assert all(
        len(branch.value.operations) == 1
        and isinstance(branch.value.operations[0], ParseSymbol)
        for branch in tap.value.branches
    )


def test_same_anchor_multi_tap_fans_out_one_parsed_value() -> None:
    parser_ir = _build(
        "#Value ::= ID\n"
        "<S> ::= [root] value: #Value\n"
        "<OwnerDef> ::= [owner] value: VALUE",
        "profile worker\n"
        "<S>[root] {\n"
        "^Owner.First += value\n"
        "^Owner.Second += value\n"
        "}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= value\n}\n",
        optimize=False,
    )

    alternative = _production(parser_ir, "S").alternatives[0]
    outer = alternative.operations[0]
    assert isinstance(outer, AppendNearestOwner)
    inner = outer.value
    assert isinstance(inner, AppendNearestOwner)
    leaf = inner.value
    assert isinstance(leaf, ParseSymbol)
    assert (inner.property, inner.source_order) == ("First", 0)
    assert (outer.property, outer.source_order) == ("Second", 1)
    assert alternative.result_index == 0


def test_scoped_tap_keeps_discarded_punctuation_resultless() -> None:
    parser_ir = _build(
        "<S> ::= [root] comma: ','\n"
        "<OwnerDef> ::= [owner] value: VALUE",
        "profile worker\n"
        "<S>[root] {\n-= comma\n^Owner.Items += comma\n}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= value\n}\n",
        optimize=False,
    )

    alternative = _production(parser_ir, "S").alternatives[0]
    assert alternative.result_index is None
    assert len(alternative.operations) == 1
    region = alternative.operations[0]
    assert isinstance(region, ResolvedRegion)
    assert region.result_index is None
    assert len(region.operations) == 1
    tap = region.operations[0]
    assert isinstance(tap, AppendNearestOwner)
    assert isinstance(tap.value, ParseSymbol)
    assert isinstance(tap.value.symbol, Lexeme)


@pytest.mark.parametrize(
    ("anchor_source", "container_type", "payload_type"),
    (
        ("maybe: ITEM?", OptionalBranch, ParseSymbol),
        ("choice: (A | B)", AppendNearestOwner, DispatchValue),
        ("many: ITEM*", RepeatLoop, ParseSymbol),
    ),
)
def test_scoped_tap_preserves_ebnf_shape(
    anchor_source: str,
    container_type: type,
    payload_type: type,
) -> None:
    parser_ir = _build(
        f"<S> ::= [root] {anchor_source}\n"
        "<OwnerDef> ::= [owner] value: VALUE",
        "profile worker\n"
        "<S>[root] {\n^Owner.Items += "
        f"{anchor_source.split(':', 1)[0]}\n}}\n"
        "<OwnerDef>[owner] {\n@Owner\n-= value\n}\n",
        optimize=False,
    )

    operation = _production(parser_ir, "S").alternatives[0].operations[0]
    assert isinstance(operation, container_type)
    if isinstance(operation, OptionalBranch):
        tap = operation.branches[0].operations[0]
    elif isinstance(operation, RepeatLoop):
        tap = operation.branches[0].operations[0]
        assert operation.branches[0].result_index is None
    else:
        tap = operation
    assert isinstance(tap, AppendNearestOwner)
    assert isinstance(tap.value, payload_type)


def test_scoped_ir_is_an_optimizer_barrier_except_for_reachability() -> None:
    syntax = (
        "<S> ::= [root] child: <Wrapper>\n"
        "<Wrapper> ::= [forward] item: ITEM\n"
        "<Dead> ::= DEAD"
    )
    profile = (
        "profile worker\n"
        "<S>[root] {\n@Owner\nValue = child\n^Owner.Items += child\n}\n"
    )
    raw = _build(syntax, profile, optimize=False)
    optimized = optimize_parser_ir(raw)

    assert tuple(item.name for item in raw.productions) == ("S", "Wrapper", "Dead")
    assert tuple(item.name for item in optimized.productions) == ("S", "Wrapper")
    assert optimized.productions == raw.productions[:2]


def test_scoped_tap_is_preserved_in_direct_left_recursion_base() -> None:
    parser_ir = _build(
        "<S> ::= <Expr>\n"
        "<Expr> ::= [recursive] left: <Expr> PLUS right: ITEM "
        "| [base] item: ITEM",
        "profile worker\n"
        "<Expr>[base] {\n@Owner\n^Owner.Items += item\n}\n",
        optimize=False,
    )

    operation = _production(parser_ir, "Expr").alternatives[0].operations[0]
    assert isinstance(operation, LeftFold)
    assert any(
        isinstance(item, AppendNearestOwner)
        for branch in operation.base_branches
        for item in branch.operations
    )


def test_legacy_ir_still_uses_transforming_optimizer() -> None:
    source = "<S> ::= <Wrapper>\n<Wrapper> ::= ITEM\n<Dead> ::= DEAD"
    result = parse_grammar(source, "legacy.grammar")
    assert result.diagnostics == ()
    assert result.source_grammar is not None
    assert result.lowering is not None
    assert result.grammar is not None
    resolved = resolve_grammar(result.grammar)
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    optimized = build_parser_ir(
        result.source_grammar,
        result.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )

    assert tuple(item.name for item in optimized.productions) == ("S",)
    operation = optimized.productions[0].alternatives[0].operations[0]
    assert isinstance(operation, ParseSymbol)
    assert isinstance(operation.symbol, Terminal)


def test_scoped_tap_requires_exactly_one_value_source() -> None:
    from parsergen.diagnostics import SourcePosition, SourceSpan

    position = SourcePosition(1, 1, 0)
    span = SourceSpan("profile.semantic", position, position)
    value = ParseSymbol(Terminal("ITEM", span), span)

    with pytest.raises(ValueError, match="exactly one"):
        AppendNearestOwner("Owner", "Items", value, "Field", 0, span)
    with pytest.raises(ValueError, match="exactly one"):
        AppendNearestOwner("Owner", "Items", None, None, 0, span)


def test_unscoped_group_optional_wrap_keeps_legacy_ir_and_codegen() -> None:
    parsed = parse_source_grammar(
        "<S> ::= <Seed> Child => (<A> | <B>)?\n"
        "<Seed> ::= @Seed SEED\n"
        "<A> ::= @A A\n"
        "<B> ::= @B B",
        "legacy.grammar",
    )
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    lowering = replace(
        lower_source_grammar(parsed.grammar),
        diagnostics=(),
    )
    resolved = resolve_grammar(lowering.grammar)
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    with patch(
        "parsergen.parser_ir_optimization.optimize_parser_ir",
        side_effect=lambda parser_ir: parser_ir,
    ), patch(
        "parsergen.parser_ir.lower_source_grammar",
        return_value=lowering,
    ):
        parser_ir = build_parser_ir(
            parsed.grammar,
            lowering,
            resolved.grammar,
            analysis,
            entrypoint_productions=("S",),
        )

    wrapper = _production(parser_ir, "S").alternatives[0].operations[0]
    assert isinstance(wrapper, WrapOptional)
    assert all(
        isinstance(branch.operations[0], ParseSymbol)
        for branch in wrapper.branches
    )
    generated = generate_python_semantic_parser(
        parsed.grammar,
        parser_ir,
        {"start": "S"},
    )
    compile(generated.module_text, "<generated-legacy-parser>", "exec")
