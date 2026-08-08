import unittest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import (
    AppendCollection,
    AssignConstant,
    BindScalar,
    ConstructNode,
    ConcatScalar,
    Dispatch,
    DispatchValue,
    IncrementScalar,
    OptionalBranch,
    ParseBranchValue,
    ParseSymbol,
    RepeatLoop,
    ReturnConstant,
    UndefinedValue,
    build_parser_ir,
)
from parsergen.resolver import resolve_grammar


def _build(source: str, k: int = 1):
    parsed = parse_grammar(source, "grammar.txt")
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
    )


class BindingParserIrTests(unittest.TestCase):
    def test_constructor_scalar_and_constant_are_explicit_operations(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйУзел Значение = <A> Флаг := Истина\n"
            "<A> ::= ITEM"
        )

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual(
            [type(item) for item in operations],
            [ConstructNode, BindScalar, AssignConstant],
        )
        constructor, scalar, constant = operations
        self.assertEqual(constructor.constructor, "НовыйУзел")
        self.assertEqual(scalar.property, "Значение")
        self.assertIsInstance(scalar.value, ParseSymbol)
        self.assertEqual(scalar.value.symbol.name, "A")
        self.assertEqual(constant.property, "Флаг")
        self.assertEqual(constant.value, "Истина")

    def test_transparent_constant_is_explicit_semantic_result(self) -> None:
        parser_ir = _build("<S> ::= VALUE | := Неопределено")

        alternative = parser_ir.productions[0].alternatives[1]
        self.assertEqual(
            [type(item) for item in alternative.operations],
            [ReturnConstant],
        )
        self.assertEqual(alternative.result_index, 0)
        self.assertEqual(alternative.operations[0].value, "Неопределено")

    def test_optional_scalar_assigns_undefined_on_exit(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйУзел Значение = <A>?\n<A> ::= ITEM"
        )

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [ConstructNode, OptionalBranch])
        optional = operations[1]
        assert isinstance(optional, OptionalBranch)
        self.assertEqual(len(optional.branches), 1)
        present = optional.branches[0].operations
        self.assertEqual([type(item) for item in present], [BindScalar])
        self.assertIsInstance(present[0].value, ParseSymbol)
        self.assertEqual([type(item) for item in optional.exit_operations], [BindScalar])
        absent = optional.exit_operations[0]
        self.assertEqual(absent.property, "Значение")
        self.assertIsInstance(absent.value, UndefinedValue)
        self.assertEqual(absent.value.value, "Неопределено")

    def test_separator_repeat_appends_only_in_consuming_branch(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйСписок Элементы += <A> "
            "(',' Элементы += <A>)*\n<A> ::= ITEM"
        )

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual(
            [type(item) for item in operations],
            [ConstructNode, AppendCollection, RepeatLoop],
        )
        first = operations[1]
        self.assertIsInstance(first.value, ParseSymbol)
        loop = operations[2]
        assert isinstance(loop, RepeatLoop)
        self.assertEqual(
            [type(item) for item in loop.branches[0].operations],
            [ParseSymbol, AppendCollection],
        )
        append = loop.branches[0].operations[1]
        self.assertEqual(append.property, "Элементы")
        self.assertIsInstance(append.value, ParseSymbol)
        self.assertEqual(loop.exit_alternative, 2)

    def test_explicit_binding_makes_other_repeat_calls_syntax_only(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйСписок Элементы += <A> "
            "(';' Элементы += <A> <Extension>)*\n"
            "<A> ::= ITEM\n"
            "<Extension> ::= EXTRA | ПУСТО"
        )

        loop = parser_ir.productions[0].alternatives[0].operations[2]
        assert isinstance(loop, RepeatLoop)
        branch = loop.branches[0]
        self.assertIsNone(branch.result_index)
        self.assertEqual(
            [type(item) for item in branch.operations],
            [ParseSymbol, AppendCollection, ParseSymbol],
        )

    def test_root_collection_append_is_explicit_operation(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйСписок += <A> (',' += <A>)*\n<A> ::= ITEM"
        )

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual(
            [type(item) for item in operations],
            [ConstructNode, AppendCollection, RepeatLoop],
        )
        first = operations[1]
        self.assertIsNone(first.property)
        loop = operations[2]
        assert isinstance(loop, RepeatLoop)
        append = loop.branches[0].operations[1]
        self.assertIsInstance(append, AppendCollection)
        self.assertIsNone(append.property)

    def test_scalar_concat_is_explicit_inside_repeat(self) -> None:
        parser_ir = _build(
            "#ID_Name ::= ID\n"
            "<S> ::= @НовыйУзел Путь ~= #ID_Name "
            "(Путь ~= '.' Путь ~= #ID_Name)*"
        )

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual(
            [type(item) for item in operations],
            [ConstructNode, ConcatScalar, RepeatLoop],
        )
        first = operations[1]
        self.assertEqual(first.property, "Путь")
        self.assertIsInstance(first.value, ParseSymbol)
        loop = operations[2]
        assert isinstance(loop, RepeatLoop)
        self.assertEqual(
            [type(item) for item in loop.branches[0].operations],
            [ConcatScalar, ConcatScalar],
        )

    def test_scalar_increment_is_explicit_inside_repeat(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйУзел NOT (Количество ++= NOT)*"
        )

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual(
            [type(item) for item in operations],
            [ConstructNode, ParseSymbol, RepeatLoop],
        )
        loop = operations[2]
        assert isinstance(loop, RepeatLoop)
        increment = loop.branches[0].operations[0]
        self.assertIsInstance(increment, IncrementScalar)
        self.assertEqual(increment.property, "Количество")
        self.assertIsInstance(increment.value, ParseSymbol)

    def test_terminal_identifier_and_constant_capture_are_parse_values(self) -> None:
        parser_ir = _build(
            "#ID_Name ::= ID\n"
            "<S> ::= @НовыйУзел "
            "Ключ = KEY Имя = #ID_Name Число = &Number"
        )

        operations = parser_ir.productions[0].alternatives[0].operations
        bindings = [item for item in operations if isinstance(item, BindScalar)]
        self.assertEqual(len(bindings), 3)
        self.assertTrue(all(isinstance(item.value, ParseSymbol) for item in bindings))
        self.assertEqual(
            [type(item.value.symbol).__name__ for item in bindings],
            ["Terminal", "IdentifierRef", "Constant"],
        )

    def test_binding_wrapped_repeat_owns_append_in_loop_branch(self) -> None:
        parser_ir = _build("<S> ::= @НовыйСписок Элементы += ITEM*")

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [ConstructNode, RepeatLoop])
        loop = operations[1]
        assert isinstance(loop, RepeatLoop)
        self.assertEqual(
            [type(item) for item in loop.branches[0].operations],
            [AppendCollection],
        )
        self.assertIsInstance(loop.branches[0].operations[0].value, ParseSymbol)

    def test_binding_wrapped_plus_appends_first_and_then_loops(self) -> None:
        parser_ir = _build("<S> ::= @НовыйСписок Элементы += ITEM+")

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual(
            [type(item) for item in operations],
            [ConstructNode, AppendCollection, RepeatLoop],
        )
        self.assertIsInstance(operations[1].value, ParseSymbol)
        loop = operations[2]
        assert isinstance(loop, RepeatLoop)
        self.assertEqual(
            [type(item) for item in loop.branches[0].operations],
            [AppendCollection],
        )

    def test_grouped_optional_records_the_exact_branch_result(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйУзел Значение = (<A> | <B>)?\n"
            "<A> ::= A\n<B> ::= B"
        )

        optional = parser_ir.productions[0].alternatives[0].operations[1]
        assert isinstance(optional, OptionalBranch)
        self.assertEqual(len(optional.branches), 2)
        for branch in optional.branches:
            binding = branch.operations[0]
            self.assertIsInstance(binding, BindScalar)
            self.assertIsInstance(binding.value, ParseBranchValue)
            self.assertEqual(binding.value.result_index, 0)

    def test_scalar_group_dispatch_records_each_branch_result(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйУзел Значение = (<A> | <B>)\n"
            "<A> ::= A\n<B> ::= B"
        )

        binding = parser_ir.productions[0].alternatives[0].operations[1]
        self.assertIsInstance(binding, BindScalar)
        self.assertIsInstance(binding.value, DispatchValue)
        self.assertEqual(len(binding.value.branches), 2)
        self.assertEqual(
            [branch.value.result_index for branch in binding.value.branches],
            [0, 0],
        )

    def test_grouped_repeat_result_is_not_an_implicit_last_temporary(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйСписок "
            "Элементы += (',' <A>)*\n<A> ::= ITEM"
        )

        loop = parser_ir.productions[0].alternatives[0].operations[1]
        assert isinstance(loop, RepeatLoop)
        binding = loop.branches[0].operations[0]
        self.assertIsInstance(binding, AppendCollection)
        self.assertIsInstance(binding.value, ParseBranchValue)
        self.assertEqual(binding.value.result_index, 1)
        self.assertEqual(
            [type(item) for item in binding.value.operations],
            [ParseSymbol, ParseSymbol],
        )

    def test_explicit_group_binding_accepts_literal_branch_values(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйСписок Знаки += ('-' | '+')+"
        )

        operations = parser_ir.productions[0].alternatives[0].operations
        first = operations[1]
        self.assertIsInstance(first, Dispatch)
        assert isinstance(first, Dispatch)
        for branch in first.branches:
            append = branch.operations[0]
            self.assertIsInstance(append, AppendCollection)
            assert isinstance(append, AppendCollection)
            self.assertIsInstance(append.value, ParseBranchValue)
            assert isinstance(append.value, ParseBranchValue)
            self.assertEqual(append.value.result_index, 0)
            self.assertIsInstance(append.value.operations[0], ParseSymbol)


if __name__ == "__main__":
    unittest.main()
