import unittest

from parsergen.grammar_parser import parse_source_grammar
from parsergen.model import Lexeme, NonterminalCall
from parsergen.source_model import (
    QuantifierKind,
    SourceGroup,
    SourceOptional,
    SourceRepeat,
)


class SourceGrammarParserTests(unittest.TestCase):
    def test_parses_separator_repeat_with_source_origins(self) -> None:
        result = parse_source_grammar("<S> ::= 'a' (',' 'a')*", "grammar.txt")

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        sequence = result.grammar.productions[0].alternatives[0].body
        self.assertEqual(len(sequence.items), 2)
        repeat = sequence.items[1]
        self.assertIsInstance(repeat, SourceRepeat)
        assert isinstance(repeat, SourceRepeat)
        self.assertIs(repeat.kind, QuantifierKind.ZERO_OR_MORE)
        self.assertIsInstance(repeat.body, SourceGroup)
        assert isinstance(repeat.body, SourceGroup)
        self.assertEqual(
            [item.text for item in repeat.body.alternatives[0].body.items],
            [",", "a"],
        )
        self.assertEqual(repeat.span.start.column, 13)
        self.assertEqual(repeat.span.end.column, 23)
        self.assertEqual(repeat.operator_span.start.column, 22)
        self.assertEqual(repeat.operator_span.end.column, 23)

    def test_parses_plus_and_optional_as_distinct_constructs(self) -> None:
        result = parse_source_grammar("<S> ::= <A>+ <B>?\n<A> ::= a\n<B> ::= b")

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        items = result.grammar.productions[0].alternatives[0].body.items
        self.assertIsInstance(items[0], SourceRepeat)
        self.assertIs(items[0].kind, QuantifierKind.ONE_OR_MORE)
        self.assertIsInstance(items[0].body, NonterminalCall)
        self.assertIsInstance(items[1], SourceOptional)
        self.assertIsInstance(items[1].body, NonterminalCall)

    def test_parses_group_alternatives_and_nested_group(self) -> None:
        result = parse_source_grammar("<S> ::= ((a | b) c)?")

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        optional = result.grammar.productions[0].alternatives[0].body.items[0]
        self.assertIsInstance(optional, SourceOptional)
        assert isinstance(optional, SourceOptional)
        outer = optional.body
        self.assertIsInstance(outer, SourceGroup)
        assert isinstance(outer, SourceGroup)
        inner = outer.alternatives[0].body.items[0]
        self.assertIsInstance(inner, SourceGroup)
        assert isinstance(inner, SourceGroup)
        self.assertEqual(len(inner.alternatives), 2)

    def test_quoted_operator_and_parenthesis_characters_remain_lexemes(self) -> None:
        result = parse_source_grammar("<S> ::= '*' '+' '?' '(' ')' '|'")

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        items = result.grammar.productions[0].alternatives[0].body.items
        self.assertEqual([type(item) for item in items], [Lexeme] * 6)
        self.assertEqual([item.text for item in items], ["*", "+", "?", "(", ")", "|"])

    def test_nonterminal_argument_parentheses_are_not_a_group(self) -> None:
        result = parse_source_grammar('<S> ::= <A>(Owner, "(x|y)")*\n<A>(Owner, Value) ::= a')

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        repeat = result.grammar.productions[0].alternatives[0].body.items[0]
        self.assertIsInstance(repeat, SourceRepeat)
        assert isinstance(repeat, SourceRepeat)
        self.assertIsInstance(repeat.body, NonterminalCall)
        assert isinstance(repeat.body, NonterminalCall)
        self.assertEqual(repeat.body.arguments, ("Owner", '"(x|y)"'))

    def test_actions_and_comments_protect_ebnf_delimiters(self) -> None:
        result = parse_source_grammar(
            '<S> ::= {Text = "(*) | ?"; // )* |\n Value = 1} a*'
        )

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        items = result.grammar.productions[0].alternatives[0].body.items
        self.assertEqual(len(items), 2)
        self.assertIsInstance(items[1], SourceRepeat)

    def test_reports_postfix_without_operand(self) -> None:
        for source in ("<S> ::= *", "<S> ::= + a", "<S> ::= ?"):
            with self.subTest(source=source):
                result = parse_source_grammar(source)
                self.assertEqual([item.code for item in result.diagnostics], ["GP008"])

    def test_reports_repeated_postfix(self) -> None:
        for source in ("<S> ::= a*?", "<S> ::= a**", "<S> ::= (a)+*"):
            with self.subTest(source=source):
                result = parse_source_grammar(source)
                self.assertEqual([item.code for item in result.diagnostics], ["EBNF203"])

    def test_reports_empty_group(self) -> None:
        result = parse_source_grammar("<S> ::= ()")

        self.assertEqual([item.code for item in result.diagnostics], ["GP009"])
        self.assertEqual(result.diagnostics[0].span.start.column, 9)

    def test_reports_empty_group_alternative(self) -> None:
        for source in ("<S> ::= (| a)", "<S> ::= (a |)"):
            with self.subTest(source=source):
                result = parse_source_grammar(source)
                self.assertEqual([item.code for item in result.diagnostics], ["GP007"])


if __name__ == "__main__":
    unittest.main()
