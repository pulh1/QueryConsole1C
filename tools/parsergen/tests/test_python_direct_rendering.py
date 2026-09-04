from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace

import pytest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import ResolvedRegion, UndefinedValue, build_parser_ir
from parsergen.python_semantic_codegen import (
    _generate_direct_python_semantic_parser,
    generate_python_semantic_parser,
)
from parsergen.resolver import resolve_grammar


@dataclass(frozen=True)
class Token:
    type: str
    text: str = ""
    start: int = 0
    end: int = 0
    value: object | None = None


def _shape(value: object) -> object:
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple((field.name, _shape(getattr(value, field.name))) for field in fields(value)),
        )
    if isinstance(value, tuple):
        return tuple(_shape(item) for item in value)
    return value


def _execute(
    module_text: str,
    tokens: list[Token],
    entrypoint: str = "start",
) -> tuple[dict[str, object], object]:
    namespace: dict[str, object] = {}
    exec(compile(module_text, "<semantic-parser>", "exec"), namespace)
    result = namespace["GeneratedParser"]().parse(tokens, entrypoint)
    return namespace, result


def _generated_pair(
    grammar: str,
    *,
    k: int = 1,
    entrypoints: dict[str, str] | None = None,
):
    parsed = parse_grammar(grammar, "direct-runtime-test.grammar")
    assert parsed.diagnostics == () and parsed.grammar is not None
    assert parsed.source_grammar is not None and parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == () and resolved.grammar is not None
    mapping = {"start": "S"} if entrypoints is None else entrypoints
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        compute_analysis(resolved.grammar, k, tuple(mapping.values())),
        entrypoint_productions=tuple(mapping.values()),
    )
    vm = generate_python_semantic_parser(parsed.source_grammar, parser_ir, mapping)
    direct = _generate_direct_python_semantic_parser(
        parsed.source_grammar,
        parser_ir,
        mapping,
    )
    return vm, direct, parser_ir, parsed.source_grammar


def test_direct_module_compiles_and_preserves_runtime_shape() -> None:
    vm, direct, _, _ = _generated_pair("<S> ::= ITEM")
    vm_namespace, vm_result = _execute(vm.module_text, [Token("ITEM")])
    direct_namespace, direct_result = _execute(direct.module_text, [Token("ITEM")])

    assert _shape(direct_result) == _shape(vm_result) is None
    assert direct_namespace["GeneratedParser"]().parse([Token("ITEM")], "start") is None
    assert vm_namespace["GeneratedParser"]().parse([Token("ITEM")], "start") is None


def test_direct_captured_terminal_matches_vm() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= ITEM")
    production = parser_ir.productions[0]
    captured_ir = replace(
        parser_ir,
        productions=(
            replace(
                production,
                alternatives=(replace(production.alternatives[0], result_index=0),),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, captured_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, captured_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [Token("ITEM")])
    _, direct_result = _execute(direct.module_text, [Token("ITEM")])
    assert _shape(direct_result) == _shape(vm_result) == "ITEM"


@pytest.mark.parametrize(
    ("grammar", "tokens", "expected"),
    [
        ("<S> ::= ITEM -= JUNK", [Token("ITEM"), Token("JUNK")], None),
        (
            "<S> ::= ITEM -= <Discarded>\n<Discarded> ::= JUNK",
            [Token("ITEM"), Token("JUNK")],
            None,
        ),
        ("#Name ::= ID\n<S> ::= #Name", [Token("ID", "Name")], "Name"),
        ("<S> ::= '+'", [Token("+")], None),
        ("<S> ::= &NUMBER", [Token("NUMBER", "42", value=42)], 42),
        ("<S> ::= &NUMBER", [Token("NUMBER", "42")], "42"),
    ],
    ids=(
        "discarded-terminal",
        "discarded-nonterminal",
        "identifier",
        "lexeme",
        "constant-value",
        "constant-text-fallback",
    ),
)
def test_direct_core_terminal_operations_match_vm(
    grammar: str,
    tokens: list[Token],
    expected: object,
) -> None:
    vm, direct, _, _ = _generated_pair(grammar)
    _, vm_result = _execute(vm.module_text, tokens)
    _, direct_result = _execute(direct.module_text, tokens)

    assert _shape(direct_result) == _shape(vm_result) == expected


@pytest.mark.parametrize(
    ("constant", "expected"),
    [("Истина", True), ("Ложь", False), ("Неопределено", None), ("Kinds.Value", "Kinds.Value")],
)
def test_direct_canonical_return_constants_match_vm(
    constant: str,
    expected: object,
) -> None:
    vm, direct, _, _ = _generated_pair(f"<S> ::= := {constant}")
    _, vm_result = _execute(vm.module_text, [])
    _, direct_result = _execute(direct.module_text, [])

    assert _shape(direct_result) == _shape(vm_result) == expected


def test_direct_undefined_value_matches_vm() -> None:
    vm, direct, parser_ir, source = _generated_pair("<S> ::= := Неопределено")
    alternative = parser_ir.productions[0].alternatives[0]
    undefined = UndefinedValue("Неопределено", alternative.operations[0].source_span)
    undefined_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(replace(alternative, operations=(undefined,)),),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, undefined_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, undefined_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [])
    _, direct_result = _execute(direct.module_text, [])
    assert _shape(direct_result) == _shape(vm_result) is None


def test_direct_parser_reuses_iterable_input_and_checks_full_consumption() -> None:
    _, direct, _, _ = _generated_pair("<S> ::= ITEM")
    namespace: dict[str, object] = {}
    exec(compile(direct.module_text, "<semantic-parser>", "exec"), namespace)
    parser = namespace["GeneratedParser"]()

    assert parser.parse(iter([Token("ITEM")]), "start") is None
    assert parser.parse([Token("ITEM")], "start") is None
    with pytest.raises(namespace["GeneratedParseError"]) as caught:
        parser.parse([Token("ITEM"), Token("ITEM")], "start")
    assert caught.value.position == 1
    assert caught.value.actual == "ITEM"
    assert caught.value.expected == ("$",)


def test_direct_parser_supports_multiple_entrypoints() -> None:
    vm, direct, _, _ = _generated_pair(
        "<S> ::= ITEM\n<A> ::= OTHER",
        entrypoints={"start": "S", "other": "A"},
    )
    _, vm_result = _execute(vm.module_text, [Token("OTHER")], "other")
    namespace, direct_result = _execute(direct.module_text, [Token("OTHER")], "other")

    assert _shape(direct_result) == _shape(vm_result) is None
    assert namespace["GeneratedParser"]().parse([Token("ITEM")], "start") is None


def test_direct_constructor_bindings_match_vm_and_freeze_schema_order() -> None:
    vm, direct, _, _ = _generated_pair(
        "#Name ::= ID\n"
        "<S> ::= @Node Title = #Name Items += ITEM Joined ~= #Name "
        "Count ++= MARK Enabled := Истина Values *= <Values>\n"
        "<Values> ::= @Values += ITEM += ITEM"
    )
    tokens = [
        Token("ID", "Title", 0, 5),
        Token("ITEM", start=6, end=10),
        Token("ID", "Tail", 11, 15),
        Token("MARK", start=16, end=17),
        Token("ITEM", start=18, end=22),
        Token("ITEM", start=23, end=27),
    ]

    _, vm_result = _execute(vm.module_text, tokens)
    direct_namespace, direct_result = _execute(direct.module_text, tokens)

    assert _shape(direct_result) == _shape(vm_result)
    assert direct_result.span == direct_namespace["SourceSpan"](0, 27)
    assert direct_result.Values == ("ITEM", "ITEM")
    assert "builder.values" not in direct.module_text
    assert "_Builder" not in direct.module_text
    assert "AST_CLASSES[" not in direct.module_text
    assert "NODE_DEFAULTS[" not in direct.module_text

    direct_namespace["AST_CLASSES"] = {}
    direct_namespace["NODE_DEFAULTS"] = {}
    result_with_mutated_reflection = direct_namespace["GeneratedParser"]().parse(
        tokens,
        "start",
    )
    assert _shape(result_with_mutated_reflection) == _shape(vm_result)


def test_direct_bindings_in_nested_region_match_vm() -> None:
    _, _, parser_ir, source = _generated_pair("<S> ::= @Node Title = ITEM")
    alternative = parser_ir.productions[0].alternatives[0]
    construct, binding = alternative.operations
    nested_ir = replace(
        parser_ir,
        productions=(
            replace(
                parser_ir.productions[0],
                alternatives=(
                    replace(
                        alternative,
                        operations=(
                            construct,
                            ResolvedRegion((binding,), None, binding.source_span),
                        ),
                    ),
                ),
            ),
        ),
    )
    vm = generate_python_semantic_parser(source, nested_ir, {"start": "S"})
    direct = _generate_direct_python_semantic_parser(source, nested_ir, {"start": "S"})

    _, vm_result = _execute(vm.module_text, [Token("ITEM", start=3, end=7)])
    direct_namespace, direct_result = _execute(
        direct.module_text,
        [Token("ITEM", start=3, end=7)],
    )

    assert _shape(direct_result) == _shape(vm_result)
    assert direct_result.span == direct_namespace["SourceSpan"](3, 7)
