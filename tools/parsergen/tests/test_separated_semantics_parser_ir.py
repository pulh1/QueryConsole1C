from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass, replace

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
    ParserIr,
    ParseBranchValue,
    ParseSymbol,
    RepeatLoop,
    ReturnConstant,
    build_parser_ir,
)
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar
from parsergen.semantic_profile_binding import bind_semantic_profile
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.syntax_grammar_parser import parse_syntax_grammar


@dataclass(frozen=True)
class _Token:
    type: str
    text: str = ""
    start: int = 0
    end: int = 0
    value: object | None = None


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


def _provenance_normalized_semantic_shape(value: object) -> object:
    if isinstance(value, SourceSpan):
        return "<span>"
    if is_dataclass(value):
        normalized_fields = []
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field.name == "path" and isinstance(field_value, str):
                normalized_value = "<source-path>"
            else:
                normalized_value = _provenance_normalized_semantic_shape(
                    field_value
                )
            normalized_fields.append((field.name, normalized_value))
        return type(value).__name__, tuple(normalized_fields)
    if isinstance(value, tuple):
        return tuple(
            _provenance_normalized_semantic_shape(item) for item in value
        )
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (
                    key,
                    _provenance_normalized_semantic_shape(item),
                )
                for key, item in value.items()
            )
        )
    return value


def _parser_ir_non_operation_shape(
    parser_ir: ParserIr,
    *,
    excluded_productions: frozenset[str] = frozenset(),
) -> object:
    lowered_source = lower_source_grammar(parser_ir.source_grammar)
    assert lowered_source.diagnostics == ()
    return (
        (
            "productions",
            tuple(
                (
                    "ProductionIr",
                    (
                        ("name", production.name),
                        ("parameters", production.parameters),
                        (
                            "alternatives",
                            tuple(
                                (
                                    "AlternativeIr",
                                    (
                                        ("index", alternative.index),
                                        ("result_index", alternative.result_index),
                                        (
                                            "source_span",
                                            _semantic_shape(alternative.source_span),
                                        ),
                                    ),
                                )
                                for alternative in production.alternatives
                            ),
                        ),
                        ("decision", _semantic_shape(production.decision)),
                        ("source_span", _semantic_shape(production.source_span)),
                    ),
                )
                for production in parser_ir.productions
                if production.name not in excluded_productions
            ),
        ),
        ("matcher_definitions", _semantic_shape(parser_ir.matcher_definitions)),
        ("lookahead", parser_ir.lookahead),
        ("source_grammar", _semantic_shape(lowered_source.grammar)),
        (
            "entrypoint_productions",
            tuple(sorted(parser_ir.entrypoint_productions)),
        ),
    )


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


def _runtime_shape(value: object) -> object:
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple(
                (field.name, _runtime_shape(getattr(value, field.name)))
                for field in fields(value)
            ),
        )
    if isinstance(value, tuple):
        return tuple(_runtime_shape(item) for item in value)
    return value


def test_different_paths_preserve_raw_provenance_but_not_semantic_identity() -> None:
    syntax_source = "#Name ::= ID\n<S> ::= [root] name: #Name"
    profile_source = (
        "profile worker\n"
        "<S>[root] {\n"
        "    @Named\n"
        "    Name = name\n"
        "}\n"
    )

    first_syntax = parse_syntax_grammar(syntax_source, "first.syntax")
    second_syntax = parse_syntax_grammar(syntax_source, "second.syntax")
    first_profile = parse_semantic_profile(profile_source, "first.semantic")
    second_profile = parse_semantic_profile(profile_source, "second.semantic")
    assert first_syntax.grammar is not None
    assert second_syntax.grammar is not None
    assert first_profile.profile is not None
    assert second_profile.profile is not None

    first_binding = bind_semantic_profile(
        first_syntax.grammar,
        first_profile.profile,
    )
    second_binding = bind_semantic_profile(
        second_syntax.grammar,
        second_profile.profile,
    )
    assert first_binding.source_grammar is not None
    assert second_binding.source_grammar is not None
    first_source = first_binding.source_grammar
    second_source = second_binding.source_grammar
    _, _, _, first_ir = _compile(first_source, ("S",))
    _, _, _, second_ir = _compile(second_source, ("S",))

    assert first_syntax.grammar.path == "first.syntax"
    assert second_syntax.grammar.path == "second.syntax"
    assert first_profile.profile.path == "first.semantic"
    assert second_profile.profile.path == "second.semantic"
    assert first_source.path == "first.syntax"
    assert second_source.path == "second.syntax"
    assert first_source != second_source
    assert first_ir != second_ir
    assert _provenance_normalized_semantic_shape(
        first_source
    ) == _provenance_normalized_semantic_shape(second_source)
    assert _provenance_normalized_semantic_shape(
        first_ir
    ) == _provenance_normalized_semantic_shape(second_ir)

    first_module = generate_python_semantic_parser(
        first_source,
        first_ir,
        {"start": "S"},
    ).module_text
    second_module = generate_python_semantic_parser(
        second_source,
        second_ir,
        {"start": "S"},
    ).module_text
    assert first_module == second_module


def test_generated_combined_and_separated_parsers_are_executable_equivalents() -> None:
    syntax_source = (
        "#Name ::= ID\n"
        "<S> ::= [root] name: #Name '=' value: &NUMBER items: ITEM+"
    )
    profile_source = """profile full
<S>[root] {
@Assignment
Name = name
Value = value
Items += items
Enabled := Истина
}
"""
    combined_source = (
        "#Name ::= ID\n"
        "<S> ::= @Assignment Name = #Name '=' Value = &NUMBER Items += ITEM+ "
        "Enabled := Истина"
    )
    _, _, _, separated_ir = _compile(
        _separated(syntax_source, profile_source),
        ("S",),
    )
    _, _, _, combined_ir = _compile(_combined(combined_source), ("S",))

    separated_module = generate_python_semantic_parser(
        separated_ir.source_grammar,
        separated_ir,
        {"start": "S"},
    ).module_text
    combined_module = generate_python_semantic_parser(
        combined_ir.source_grammar,
        combined_ir,
        {"start": "S"},
    ).module_text
    separated_namespace: dict[str, object] = {}
    combined_namespace: dict[str, object] = {}
    exec(compile(separated_module, "<separated-parser>", "exec"), separated_namespace)
    exec(compile(combined_module, "<combined-parser>", "exec"), combined_namespace)

    tokens = (
        _Token("ID", "Total", 0, 5),
        _Token("=", "=", 6, 7),
        _Token("NUMBER", "42", 8, 10, 42),
        _Token("ITEM", "first", 11, 16),
        _Token("ITEM", "second", 17, 23),
    )
    separated_parser = separated_namespace["GeneratedParser"]()
    combined_parser = combined_namespace["GeneratedParser"]()
    separated_result = separated_parser.parse(tokens, "start")
    combined_result = combined_parser.parse(tokens, "start")
    separated_shape = _runtime_shape(separated_result)
    combined_shape = _runtime_shape(combined_result)
    assert separated_shape == combined_shape
    assert ("Items", ("ITEM", "ITEM")) in separated_shape[1]
    assert ("Items", ("ITEM", "ITEM")) in combined_shape[1]

    bad_tokens = (_Token("OTHER", "secret", 7, 13),)
    separated_error_type = separated_namespace["GeneratedParseError"]
    combined_error_type = combined_namespace["GeneratedParseError"]
    try:
        separated_parser.parse(bad_tokens, "start")
    except separated_error_type as error:
        separated_error = error
    else:
        raise AssertionError("separated parser accepted invalid tokens")
    try:
        combined_parser.parse(bad_tokens, "start")
    except combined_error_type as error:
        combined_error = error
    else:
        raise AssertionError("combined parser accepted invalid tokens")
    assert (
        separated_error.position,
        separated_error.actual,
        separated_error.expected,
    ) == (
        combined_error.position,
        combined_error.actual,
        combined_error.expected,
    )


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
    compact = _separated(
        syntax_source,
        """profile compact
<S>[root] {
@Root
Child = child
}
""",
    )

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
    assert _parser_ir_non_operation_shape(
        full_ir,
        excluded_productions=frozenset({"Wrapper"}),
    ) == _parser_ir_non_operation_shape(compact_ir)
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
    full_start_production = full_ir.productions[0]
    compact_start_production = compact_ir.productions[0]
    full_start = full_start_production.alternatives[0]
    compact_start = compact_start_production.alternatives[0]
    assert full_start.result_index is compact_start.result_index is None
    assert [type(operation) for operation in full_start.operations] == [
        ConstructNode,
        BindScalar,
    ]
    assert [type(operation) for operation in compact_start.operations] == [
        ConstructNode,
        BindScalar,
    ]
    full_child = full_start.operations[1]
    compact_child = compact_start.operations[1]
    assert isinstance(full_child, BindScalar)
    assert isinstance(compact_child, BindScalar)
    assert isinstance(full_child.value, ParseSymbol)
    assert full_child.value.symbol.name == "Wrapper"
    assert isinstance(compact_child.value, ParseBranchValue)
    assert compact_child.value.result_index == 0
    assert len(compact_child.value.operations) == 1
    compact_child_operation = compact_child.value.operations[0]
    assert isinstance(compact_child_operation, ParseSymbol)
    assert compact_child_operation.symbol.name == "Value"
    assert all(
        [type(operation) for operation in alternative.operations]
        == [ConstructNode, BindScalar]
        for alternative in full_value.alternatives
    )
    assert all(
        [type(operation) for operation in alternative.operations]
        == [ParseSymbol]
        for alternative in compact_value.alternatives
    )

    compact_shape = _parser_ir_non_operation_shape(compact_ir)
    compact_start_alternative = compact_start_production.alternatives[0]
    structural_mutations = (
        replace(
            compact_ir,
            productions=(
                replace(compact_start_production, name="ChangedS"),
                *compact_ir.productions[1:],
            ),
        ),
        replace(
            compact_ir,
            productions=(
                replace(compact_start_production, parameters=("P",)),
                *compact_ir.productions[1:],
            ),
        ),
        replace(
            compact_ir,
            productions=(
                replace(compact_start_production, alternatives=()),
                *compact_ir.productions[1:],
            ),
        ),
        replace(
            compact_ir,
            productions=(
                replace(
                    compact_start_production,
                    alternatives=(
                        replace(compact_start_alternative, index=7),
                    ),
                ),
                *compact_ir.productions[1:],
            ),
        ),
        replace(
            compact_ir,
            productions=(
                replace(
                    compact_start_production,
                    alternatives=(
                        replace(compact_start_alternative, result_index=0),
                    ),
                ),
                *compact_ir.productions[1:],
            ),
        ),
        replace(
            compact_ir,
            productions=(
                replace(compact_start_production, decision=compact_value.decision),
                *compact_ir.productions[1:],
            ),
        ),
        replace(compact_ir, matcher_definitions=compact_ir.matcher_definitions[:-1]),
        replace(compact_ir, lookahead=2),
        replace(compact_ir, entrypoint_productions=frozenset({"Value"})),
        replace(
            compact_ir,
            source_grammar=replace(compact_ir.source_grammar, path="changed.grammar"),
        ),
    )
    assert all(
        _parser_ir_non_operation_shape(mutated) != compact_shape
        for mutated in structural_mutations
    )
    operation_only_mutation = replace(
        compact_ir,
        productions=(
            replace(
                compact_start_production,
                alternatives=(
                    replace(compact_start_alternative, operations=()),
                ),
            ),
            *compact_ir.productions[1:],
        ),
    )
    assert _parser_ir_non_operation_shape(operation_only_mutation) == compact_shape
    span_only_mutation = replace(
        compact_ir,
        productions=(
            replace(
                compact_start_production,
                source_span=compact_value.source_span,
                alternatives=(
                    replace(
                        compact_start_alternative,
                        source_span=compact_value.alternatives[0].source_span,
                    ),
                ),
            ),
            *compact_ir.productions[1:],
        ),
    )
    assert _parser_ir_non_operation_shape(span_only_mutation) == compact_shape
