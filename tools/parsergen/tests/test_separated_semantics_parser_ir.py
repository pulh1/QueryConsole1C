from collections.abc import Mapping
from dataclasses import fields, is_dataclass

from parsergen.analysis import compute_analysis
from parsergen.canonical_select import build_canonical_decision_source
from parsergen.diagnostics import SourceSpan
from parsergen.grammar_parser import parse_source_grammar
from parsergen.lowering import (
    BindingOriginKind,
    LoweredConstructKind,
    LoweredLeftRecursion,
    lower_source_grammar,
)
from parsergen.parser_ir import (
    AppendCollection,
    BindScalar,
    ConstructNode,
    DiscardSymbol,
    Dispatch,
    LeftFold,
    ParseBranchValue,
    ParseSymbol,
    RepeatLoop,
    ReturnConstant,
    build_parser_ir,
)
from parsergen.resolver import resolve_grammar
from parsergen.semantic_profile_binding import bind_semantic_profile
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.syntax_grammar_parser import parse_syntax_grammar


def _semantic_shape(value: object) -> object:
    if isinstance(value, SourceSpan):
        return "<span>"
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple(
                (field.name, _semantic_shape(getattr(value, field.name)))
                for field in fields(value)
            ),
        )
    if isinstance(value, tuple):
        return tuple(_semantic_shape(item) for item in value)
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (key, _semantic_shape(item))
                for key, item in value.items()
            )
        )
    return value


def _combined(source: str):
    result = parse_source_grammar(source, "syntax.grammar")
    assert result.diagnostics == ()
    assert result.grammar is not None
    return result.grammar


def _separated(syntax_source: str, profile_source: str):
    syntax = parse_syntax_grammar(syntax_source, "syntax.grammar")
    profile = parse_semantic_profile(profile_source, "profile.semantic")
    assert syntax.diagnostics == ()
    assert syntax.grammar is not None
    assert profile.diagnostics == ()
    assert profile.profile is not None
    result = bind_semantic_profile(syntax.grammar, profile.profile)
    assert result.diagnostics == ()
    assert result.source_grammar is not None
    return result.source_grammar


def _compile(source_grammar, starts: tuple[str, ...]):
    lowering = lower_source_grammar(source_grammar)
    assert lowering.diagnostics == ()
    resolution = resolve_grammar(lowering.grammar)
    assert resolution.diagnostics == ()
    assert resolution.grammar is not None
    analysis = compute_analysis(resolution.grammar, 1, starts)
    parser_ir = build_parser_ir(
        source_grammar,
        lowering,
        resolution.grammar,
        analysis,
        entrypoint_productions=starts,
    )
    return lowering, resolution.grammar, analysis, parser_ir


def test_all_binding_modes_match_the_equivalent_combined_parser_ir() -> None:
    syntax_source = (
        "#Name ::= ID\n"
        "<S> ::= [main] name: #Name maybe: <OptionalValue>? "
        "repeated: <RepeatedValue>* more: <Atoms> separator: ',' "
        "count: BANG junk: JUNK\n"
        "<OptionalValue> ::= [optional] value: OPT\n"
        "<RepeatedValue> ::= [repeated] value: REP\n"
        "<Atoms> ::= [atoms] value: MORE\n"
        "<Atom> ::= [atom] value: ITEM\n"
        "<Wrapped> ::= [wrapped] seed: <Atom> child: <Atom>\n"
        "<Prepended> ::= [prepended] seed: <Atom> child: <Atom>?"
    )
    profile_source = """profile full
<S>[main] {
@Root
Name = name
Maybe = maybe
Items += repeated
More *= more
Text ~= separator
Count ++= count
-= junk
Enabled := Истина
}
<OptionalValue>[optional] {
@OptionalValue
Value = value
}
<RepeatedValue>[repeated] {
@RepeatedValue
Value = value
}
<Atoms>[atoms] {
@Values
+= value
}
<Atom>[atom] {
@Atom
Value = value
}
<Wrapped>[wrapped] {
Child => child
}
<Prepended>[prepended] {
Children +=> child
}
"""
    combined_source = (
        "#Name ::= ID\n"
        "<S> ::= @Root Name = #Name Maybe = <OptionalValue>? "
        "Items += <RepeatedValue>* More *= <Atoms> Text ~= ',' "
        "Count ++= BANG -= JUNK Enabled := Истина\n"
        "<OptionalValue> ::= @OptionalValue Value = OPT\n"
        "<RepeatedValue> ::= @RepeatedValue Value = REP\n"
        "<Atoms> ::= @Values += MORE\n"
        "<Atom> ::= @Atom Value = ITEM\n"
        "<Wrapped> ::= <Atom> Child => <Atom>\n"
        "<Prepended> ::= <Atom> Children +=> <Atom>?"
    )
    separated = _separated(syntax_source, profile_source)
    combined = _combined(combined_source)

    assert _semantic_shape(separated) == _semantic_shape(combined)
    starts = ("S", "Wrapped", "Prepended")
    separated_lowering, _, _, separated_ir = _compile(separated, starts)
    combined_lowering, _, _, combined_ir = _compile(combined, starts)
    assert _semantic_shape(separated_lowering) == _semantic_shape(combined_lowering)
    assert _semantic_shape(separated_ir) == _semantic_shape(combined_ir)
    assert {binding.kind for binding in separated_lowering.bindings} >= {
        BindingOriginKind.CONSTRUCTOR,
        BindingOriginKind.SCALAR,
        BindingOriginKind.APPEND,
        BindingOriginKind.EXTEND,
        BindingOriginKind.CONCAT,
        BindingOriginKind.INCREMENT,
        BindingOriginKind.WRAP,
        BindingOriginKind.WRAP_PREPEND,
        BindingOriginKind.DISCARD,
        BindingOriginKind.CONSTANT,
    }


def test_named_repeated_group_alternatives_preserve_ebnf_results() -> None:
    separated = _separated(
        "<S> ::= [root] values: "
        "([word] token: 'word' | [number] token: 'number')+",
        """profile full
<S>[root] {
@List
Values += values
}
<S>[word] {
-= token
:= Kinds.Word
}
<S>[number] {
-= token
:= Kinds.Number
}
""",
    )
    combined = _combined(
        "<S> ::= @List Values += "
        "(-= 'word' := Kinds.Word | -= 'number' := Kinds.Number)+"
    )

    separated_lowering, _, _, separated_ir = _compile(separated, ("S",))
    combined_lowering, _, _, combined_ir = _compile(combined, ("S",))
    assert _semantic_shape(separated_lowering) == _semantic_shape(combined_lowering)
    assert _semantic_shape(separated_ir) == _semantic_shape(combined_ir)
    assert [construct.kind for construct in separated_lowering.constructs] == [
        LoweredConstructKind.PLUS
    ]
    construct = separated_lowering.constructs[0]
    assert construct.production == "__parsergen_ebnf__p0_a0_n1_plus"
    assert construct.tail_production == "__parsergen_ebnf__p0_a0_n1_plus_tail"
    assert [
        (production.name, len(production.alternatives))
        for production in separated_lowering.grammar.productions
    ] == [
        ("S", 1),
        (construct.production, 2),
        (construct.tail_production, 3),
    ]

    operations = separated_ir.productions[0].alternatives[0].operations
    dispatch = next(item for item in operations if isinstance(item, Dispatch))
    repeat = next(item for item in operations if isinstance(item, RepeatLoop))
    appends = [
        branch.operations[0]
        for branch in (*dispatch.branches, *repeat.branches)
    ]
    assert all(isinstance(item, AppendCollection) for item in appends)
    values = [item.value for item in appends]
    assert all(isinstance(value, ParseBranchValue) for value in values)
    assert [value.result_index for value in values] == [1, 1, 1, 1]
    assert all(
        [type(operation) for operation in value.operations]
        == [DiscardSymbol, ReturnConstant]
        for value in values
    )


def test_named_direct_left_recursion_preserves_left_fold_semantics() -> None:
    separated = _separated(
        "<S> ::= [start] expr: <Expr>\n"
        "<Expr> ::= [recursive] left: <Expr> plus: '+' right: <Term> "
        "| [base] term: <Term>\n"
        "<Term> ::= [term] value: ITEM",
        """profile full
<Expr>[recursive] {
@Binary
Left = left
Operator = plus
Right = right
}
<Term>[term] {
@Term
Value = value
}
""",
    )
    combined = _combined(
        "<S> ::= <Expr>\n"
        "<Expr> ::= @Binary Left = <Expr> Operator = '+' Right = <Term> "
        "| <Term>\n"
        "<Term> ::= @Term Value = ITEM"
    )

    separated_lowering, _, _, separated_ir = _compile(separated, ("S",))
    combined_lowering, _, _, combined_ir = _compile(combined, ("S",))
    assert _semantic_shape(separated_lowering) == _semantic_shape(combined_lowering)
    assert _semantic_shape(separated_ir) == _semantic_shape(combined_ir)
    assert len(separated_lowering.left_recursions) == 1
    recursion = separated_lowering.left_recursions[0]
    assert isinstance(recursion, LoweredLeftRecursion)
    assert (
        recursion.production,
        recursion.base_alternatives,
        recursion.recursive_alternatives,
    ) == ("Expr", (1,), (0,))

    expression = next(
        production
        for production in separated_ir.productions
        if production.name == "Expr"
    )
    alternative = expression.alternatives[0]
    assert alternative.result_index == 0
    fold = alternative.operations[0]
    assert isinstance(fold, LeftFold)
    assert fold.base_branches[0].result_index == 0
    assert [
        type(operation)
        for operation in fold.recursive_branches[0].operations
    ] == [ConstructNode, BindScalar, BindScalar, BindScalar]


def test_profiles_preserve_grammar_analysis_and_canonical_decisions() -> None:
    syntax_source = (
        "<S> ::= [root] child: <Wrapper>\n"
        "<Wrapper> ::= [wrapper] value: <Value>\n"
        "<Value> ::= [word] token: 'word' | [number] token: 'number'"
    )
    full = _separated(
        syntax_source,
        """profile full
<S>[root] {
@Root
Child = child
}
<Wrapper>[wrapper] {
@Wrapper
Value = value
}
<Value>[word] {
@Word
Text = token
}
<Value>[number] {
@Number
Text = token
}
""",
    )
    compact = _separated(syntax_source, "profile compact\n")

    full_lowering, full_resolved, full_analysis, full_ir = _compile(full, ("S",))
    compact_lowering, compact_resolved, compact_analysis, compact_ir = _compile(
        compact,
        ("S",),
    )
    assert _semantic_shape(full_lowering.grammar) == _semantic_shape(
        compact_lowering.grammar
    )
    assert _semantic_shape(full_resolved) == _semantic_shape(compact_resolved)
    assert full_analysis.nullable == compact_analysis.nullable
    assert _semantic_shape(full_analysis.first) == _semantic_shape(
        compact_analysis.first
    )
    assert _semantic_shape(full_analysis.follow) == _semantic_shape(
        compact_analysis.follow
    )
    assert _semantic_shape(full_analysis.select) == _semantic_shape(
        compact_analysis.select
    )
    assert _semantic_shape(
        build_canonical_decision_source(full_analysis, "Value")
    ) == _semantic_shape(
        build_canonical_decision_source(compact_analysis, "Value")
    )

    assert [production.name for production in full_ir.productions] == [
        "S",
        "Wrapper",
        "Value",
    ]
    assert [production.name for production in compact_ir.productions] == [
        "S",
        "Value",
    ]
    assert full_ir.matcher_definitions == compact_ir.matcher_definitions
    assert full_ir.lookahead == compact_ir.lookahead == 1
    assert full_ir.entrypoint_productions == compact_ir.entrypoint_productions
    full_value = next(
        production for production in full_ir.productions if production.name == "Value"
    )
    compact_value = next(
        production
        for production in compact_ir.productions
        if production.name == "Value"
    )
    assert _semantic_shape(full_value.decision) == _semantic_shape(
        compact_value.decision
    )
    assert [
        type(operation)
        for operation in full_ir.productions[0].alternatives[0].operations
    ] == [ConstructNode, BindScalar]
    compact_start = compact_ir.productions[0].alternatives[0]
    assert compact_start.result_index == 0
    assert [type(operation) for operation in compact_start.operations] == [
        ParseSymbol
    ]
    assert compact_start.operations[0].symbol.name == "Value"
