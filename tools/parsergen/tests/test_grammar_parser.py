import unittest

from parsergen.grammar_parser import parse_grammar
from parsergen.model import Action, Constant, IdentifierRef, Lexeme, NonterminalCall, Terminal
from tests.grammar_cases import SYMBOL_CASES


class GrammarParserTests(unittest.TestCase):
    def test_parse_extended_alternative_with_parameters_and_actions(self) -> None:
        result = parse_grammar(
            """
            #ID_Name ::= ID | ГДЕ
            <S>(Owner) ::= {ЭтотУзел = НовыйУзел} 'x' <A>(Owner, "a,b")
                           {ЭтотУзел.Value = ТекущийЭлемент} #ID_Name &Number WORD
            <A>(Owner, Value) ::= ПУСТО
            """,
            "grammar.txt",
        )

        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        self.assertEqual(result.grammar.identifier_definitions[0].token_types, ("ID", "ГДЕ"))
        elements = result.grammar.productions[0].alternatives[0].elements
        self.assertEqual(
            [type(item) for item in elements],
            [Action, Lexeme, NonterminalCall, Action, IdentifierRef, Constant, Terminal],
        )
        call = elements[2]
        self.assertIsInstance(call, NonterminalCall)
        assert isinstance(call, NonterminalCall)
        self.assertEqual(call.arguments, ("Owner", '"a,b"'))
        self.assertEqual(elements[0].boundary, 0)
        self.assertEqual(elements[3].boundary, 2)

    def test_comments_and_delimiters_inside_action_do_not_split_grammar(self) -> None:
        result = parse_grammar(
            '<S> ::= {Text = "a;b=c"; // action comment\n'
            " Value = Call(1, 2)} '<|>' | ПУСТО"
        )
        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        self.assertEqual(len(result.grammar.productions[0].alternatives), 2)

    def test_closing_brace_inside_action_comment_is_not_an_action_delimiter(self) -> None:
        result = parse_grammar('<S> ::= { // }\n Value = 1} a')
        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        elements = result.grammar.productions[0].alternatives[0].elements
        self.assertEqual([type(item) for item in elements], [Action, Terminal])
        self.assertEqual(elements[1].token_type, "a")

    def test_slashes_inside_call_arguments_are_not_a_grammar_comment(self) -> None:
        result = parse_grammar('<S> ::= <A>("//")')
        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        call = result.grammar.productions[0].alternatives[0].elements[0]
        self.assertIsInstance(call, NonterminalCall)
        assert isinstance(call, NonterminalCall)
        self.assertEqual(call.arguments, ('"//"',))

    def test_argument_strings_protect_every_delimiter(self) -> None:
        arguments = ('")"', '"("', '"<"', '">"', '"}"', '"a"")"')
        for argument in arguments:
            with self.subTest(argument=argument):
                result = parse_grammar(f"<S> ::= <A>({argument})")
                self.assertEqual(result.diagnostics, ())
                assert result.grammar is not None
                call = result.grammar.productions[0].alternatives[0].elements[0]
                self.assertIsInstance(call, NonterminalCall)
                assert isinstance(call, NonterminalCall)
                self.assertEqual(call.arguments, (argument,))

    def test_action_comments_protect_delimiters_until_newline(self) -> None:
        comments = ('unmatched "', "unmatched '", "} | still comment")
        for comment in comments:
            with self.subTest(comment=comment):
                result = parse_grammar(f"<S> ::= {{ // {comment}\n Value=1}} a | b")
                self.assertEqual(result.diagnostics, ())
                assert result.grammar is not None
                self.assertEqual(len(result.grammar.productions[0].alternatives), 2)

    def test_depth_zero_comments_do_not_make_declarations(self) -> None:
        cases = (
            ("// comment\n<S> ::= a", 1),
            ("// comment", 0),
            ("\n // comment\n\n", 0),
        )
        for source, production_count in cases:
            with self.subTest(source=source):
                result = parse_grammar(source)
                self.assertEqual(result.diagnostics, ())
                assert result.grammar is not None
                self.assertEqual(len(result.grammar.productions), production_count)

    def test_alternative_spans_start_in_the_body_not_matching_header_text(self) -> None:
        result = parse_grammar("<S>(S) ::= S")
        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        terminal = result.grammar.productions[0].alternatives[0].elements[0]
        self.assertIsInstance(terminal, Terminal)
        self.assertEqual((terminal.span.start.line, terminal.span.start.column, terminal.span.start.offset), (1, 12, 11))

    def test_empty_alternative_span_starts_after_its_separator(self) -> None:
        result = parse_grammar("<S> ::= a |")
        self.assertEqual([item.code for item in result.diagnostics], ["GP007"])
        diagnostic = result.diagnostics[0]
        self.assertEqual(
            (diagnostic.span.start.line, diagnostic.span.start.column, diagnostic.span.start.offset),
            (1, 12, 11),
        )

    def test_multiline_body_continues_previous_declaration(self) -> None:
        result = parse_grammar("<S> ::= a <A>\n <B>\n<A> ::= ПУСТО\n<B> ::= b")
        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        symbols = result.grammar.productions[0].alternatives[0].syntax_symbols
        self.assertEqual(
            [symbol.name for symbol in symbols if isinstance(symbol, NonterminalCall)],
            ["A", "B"],
        )

    def test_adjacent_terminal_lexeme_and_nonterminal_are_separate_symbols(
        self,
    ) -> None:
        result = parse_grammar(
            "<S> ::= СУММА'('<Выражение>')'\n<Выражение> ::= ID"
        )

        self.assertEqual(result.diagnostics, ())
        assert result.grammar is not None
        elements = result.grammar.productions[0].alternatives[0].elements
        self.assertEqual(
            [type(element) for element in elements],
            [Terminal, Lexeme, NonterminalCall, Lexeme],
        )
        self.assertEqual(elements[0].token_type, "СУММА")
        self.assertEqual(elements[1].text, "(")
        self.assertEqual(elements[2].name, "Выражение")
        self.assertEqual(elements[3].text, ")")

    def test_repeated_declaration_may_omit_or_later_supply_formals(self) -> None:
        cases = (
            ("<S>(Owner) ::= a\n<S> ::= b", ("Owner",)),
            ("<S> ::= a\n<S>(Owner) ::= b", ("Owner",)),
        )
        for source, expected_parameters in cases:
            with self.subTest(source=source):
                result = parse_grammar(source)
                self.assertEqual(result.diagnostics, ())
                assert result.grammar is not None
                production = result.grammar.productions[0]
                self.assertEqual(production.parameters, expected_parameters)
                self.assertEqual(len(production.alternatives), 2)

    def test_reports_all_unclosed_constructs_with_locations(self) -> None:
        result = parse_grammar("<A> ::= 'x\n<B> ::= {x = 1\n<C> ::= <D")
        self.assertEqual([item.code for item in result.diagnostics], ["GP002", "GP003", "GP004"])
        self.assertEqual([item.span.start.line for item in result.diagnostics], [1, 2, 3])

    def test_rejects_epsilon_mixed_with_symbol_but_allows_action(self) -> None:
        invalid = parse_grammar("<S> ::= ПУСТО a")
        valid = parse_grammar("<S> ::= {x = 1} ПУСТО")
        self.assertEqual([item.code for item in invalid.diagnostics], ["GR004"])
        self.assertEqual(valid.diagnostics, ())

    def test_symbol_and_declaration_corner_cases(self) -> None:
        for name, source, expected_kind, expected in SYMBOL_CASES:
            with self.subTest(name=name):
                result = parse_grammar(source)
                if expected_kind == "diagnostic":
                    self.assertEqual([item.code for item in result.diagnostics], [expected])
                else:
                    self.assertEqual(result.diagnostics, ())
                    self.assertIsNotNone(result.grammar)
                    assert result.grammar is not None
                    element = result.grammar.productions[0].alternatives[0].elements[0]
                    self.assertEqual(type(element).__name__, expected)


if __name__ == "__main__":
    unittest.main()

