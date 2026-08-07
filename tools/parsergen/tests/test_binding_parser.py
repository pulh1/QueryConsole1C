import unittest

from parsergen.grammar_parser import parse_source_grammar
from parsergen.model import Constant, IdentifierRef, NonterminalCall, Terminal
from parsergen.source_model import (
    BindingMode,
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
    SourceGroup,
    SourceOptional,
    SourceRepeat,
)


class BindingParserTests(unittest.TestCase):
    def test_parses_constructor_and_scalar_nonterminal_binding(self) -> None:
        result = parse_source_grammar(
            "<S> ::= @НовыйУзел Значение=<A>\n<A> ::= a",
            "grammar.txt",
        )

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        items = result.grammar.productions[0].alternatives[0].body.items
        self.assertEqual([type(item) for item in items], [SourceConstructor, SourceBinding])
        constructor, binding = items
        self.assertEqual(constructor.name, "НовыйУзел")
        self.assertEqual(constructor.span.start.column, 9)
        self.assertEqual(binding.property, "Значение")
        self.assertIs(binding.mode, BindingMode.SCALAR)
        self.assertIsInstance(binding.value, NonterminalCall)
        self.assertEqual(binding.operator_span.start.column, 28)

    def test_scalar_binding_may_wrap_optional_value(self) -> None:
        result = parse_source_grammar(
            "<S> ::= @НовыйУзел Значение = <A>?\n<A> ::= a"
        )

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        binding = result.grammar.productions[0].alternatives[0].body.items[1]
        self.assertIsInstance(binding, SourceBinding)
        self.assertIsInstance(binding.value, SourceOptional)

    def test_parses_collection_binding_inside_separator_repeat(self) -> None:
        result = parse_source_grammar(
            "<List> ::= @НовыйСписок Элементы += <Item> "
            "(',' Элементы += <Item>)*\n<Item> ::= ITEM"
        )

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        items = result.grammar.productions[0].alternatives[0].body.items
        first = items[1]
        self.assertIsInstance(first, SourceBinding)
        self.assertIs(first.mode, BindingMode.APPEND)
        repeat = items[2]
        self.assertIsInstance(repeat, SourceRepeat)
        assert isinstance(repeat, SourceRepeat)
        self.assertIsInstance(repeat.body, SourceGroup)
        assert isinstance(repeat.body, SourceGroup)
        repeated = repeat.body.alternatives[0].body.items[1]
        self.assertIsInstance(repeated, SourceBinding)
        self.assertIs(repeated.mode, BindingMode.APPEND)
        self.assertEqual(repeated.property, "Элементы")

    def test_binding_captures_terminal_identifier_and_constant_tokens(self) -> None:
        result = parse_source_grammar(
            "<S> ::= @НовыйУзел "
            "КлючевоеСлово = KEY "
            "Имя = #ID_Name "
            "Число = &Number"
        )

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        bindings = result.grammar.productions[0].alternatives[0].body.items[1:]
        self.assertEqual(
            [type(item.value) for item in bindings],
            [Terminal, IdentifierRef, Constant],
        )

    def test_parses_boolean_and_dotted_constant_bindings(self) -> None:
        result = parse_source_grammar(
            "<S> ::= @НовыйУзел Флаг := Истина Тип := Типы.Все"
        )

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        constants = result.grammar.productions[0].alternatives[0].body.items[1:]
        self.assertEqual(
            [type(item) for item in constants],
            [SourceConstantBinding, SourceConstantBinding],
        )
        self.assertEqual([item.value for item in constants], ["Истина", "Типы.Все"])

    def test_quoted_and_action_content_protects_binding_markers(self) -> None:
        result = parse_source_grammar(
            '<S> ::= {Text = "@Node X += Y Z := Q"} '
            "'@' '=' '+=' ':='"
        )

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        items = result.grammar.productions[0].alternatives[0].body.items
        self.assertEqual(len(items), 5)

    def test_reports_malformed_constructor_and_binding_syntax(self) -> None:
        cases = (
            "<S> ::= @",
            "<S> ::= = <A>",
            "<S> ::= Значение =",
            "<S> ::= Значение *= <A>",
            "<S> ::= Значение :=",
        )
        for source in cases:
            with self.subTest(source=source):
                result = parse_source_grammar(source)
                self.assertEqual(
                    [item.code for item in result.diagnostics],
                    ["GP010"],
                )

if __name__ == "__main__":
    unittest.main()
