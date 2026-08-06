import unittest

from parsergen.grammar_parser import parse_grammar
from parsergen.resolver import ResolvedToken, resolve_grammar


def resolve(text: str):
    parsed = parse_grammar(text)
    assert parsed.grammar is not None
    return resolve_grammar(parsed.grammar)


class ResolverTests(unittest.TestCase):
    def test_private_diagnostic_annotations_are_resolvable(self) -> None:
        from typing import get_type_hints

        from parsergen import resolver

        hints = get_type_hints(resolver._diagnostic)

        self.assertIs(hints["return"], resolver.Diagnostic)

    def test_resolves_identifier_class_to_concrete_token_types(self) -> None:
        result = resolve("#ID_Name ::= ID | ГДЕ\n<S> ::= #ID_Name | ГДЕ")

        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        first = result.grammar.productions["S"][0].symbols[0]
        self.assertIsInstance(first, ResolvedToken)
        assert isinstance(first, ResolvedToken)
        self.assertEqual(first.token_types, frozenset({"ID", "ГДЕ"}))

    def test_reports_unknown_references_and_too_many_arguments_together(self) -> None:
        result = resolve("<S> ::= <Missing> #ID_Missing <A>(1, 2)\n<A>(X) ::= a")

        self.assertEqual(
            [item.code for item in result.diagnostics],
            ["RES001", "RES002", "GR003"],
        )

    def test_reports_empty_identifier_definition(self) -> None:
        result = resolve("#ID_X ::= ")

        self.assertEqual([item.code for item in result.diagnostics], ["RES003"])

    def test_merges_identical_identifier_definitions(self) -> None:
        result = resolve("#ID_X ::= ID | ГДЕ\n#ID_X ::= ID | ГДЕ\n<S> ::= #ID_X")

        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        self.assertEqual(
            result.grammar.identifier_tokens["ID_X"],
            frozenset({"ID", "ГДЕ"}),
        )
        token = result.grammar.productions["S"][0].symbols[0]
        self.assertIsInstance(token, ResolvedToken)
        assert isinstance(token, ResolvedToken)
        self.assertEqual(token.token_types, frozenset({"ID", "ГДЕ"}))

    def test_merges_additive_identifier_definitions_in_first_seen_order(self) -> None:
        result = resolve(
            "#ID_X ::= ID | ГДЕ\n"
            "#ID_X ::= ГДЕ | WORD\n"
            "#ID_X ::= ID\n"
            "<S> ::= #ID_X"
        )

        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        self.assertEqual(
            result.grammar.identifier_tokens["ID_X"],
            frozenset({"ID", "ГДЕ", "WORD"}),
        )
        token = result.grammar.productions["S"][0].symbols[0]
        self.assertIsInstance(token, ResolvedToken)
        assert isinstance(token, ResolvedToken)
        self.assertEqual(token.token_types, frozenset({"ID", "ГДЕ", "WORD"}))

    def test_indexes_nonterminal_occurrences_without_actions(self) -> None:
        result = resolve("<S> ::= {Before()} <A> {Between()} <A> {After()}\n<A> ::= a")

        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        assert result.grammar is not None
        self.assertEqual(result.grammar.occurrences, {"A": (("S", 0, 0), ("S", 0, 1))})

    def test_allows_fewer_arguments_than_formals(self) -> None:
        result = resolve("<S> ::= <A>()\n<A>(X, Y) ::= a")

        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)

    def test_rejects_reserved_end_token_from_every_token_source(self) -> None:
        cases = (
            ("terminal", "<S> ::= $"),
            ("lexeme", "<S> ::= '$'"),
            ("constant", "<S> ::= &$"),
            ("identifier definition", "#ID_X ::= $\n<S> ::= #ID_X"),
            ("identifier name", "#$ ::= ID\n<S> ::= #$"),
        )

        for name, text in cases:
            with self.subTest(name=name):
                result = resolve(text)
                self.assertIsNone(result.grammar)
                self.assertEqual(
                    [item.code for item in result.diagnostics],
                    ["RES004"],
                )
                self.assertIn("reserved", result.diagnostics[0].message)


if __name__ == "__main__":
    unittest.main()
