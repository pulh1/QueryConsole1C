import unittest

from parsergen.grammar_parser import parse_grammar, parse_source_grammar
from parsergen.source_validation import validate_source_grammar


def _validate(source: str):
    parsed = parse_source_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    return validate_source_grammar(parsed.grammar)


class SourceValidationTests(unittest.TestCase):
    def test_computes_facts_for_productive_consuming_recursion(self) -> None:
        report = _validate("<S> ::= <A>*\n<A> ::= a <A> | a")

        self.assertEqual(report.diagnostics, ())
        facts = report.production_facts["A"]
        self.assertTrue(facts.productive)
        self.assertFalse(facts.nullable)
        self.assertEqual(facts.min_consumed_tokens, 1)

    def test_rejects_direct_and_transitively_nullable_repeat_body(self) -> None:
        cases = (
            ("<S> ::= <N>*\n<N> ::= ПУСТО", 12),
            ("<S> ::= <N>+\n<N> ::= <E>\n<E> ::= ПУСТО", 12),
        )
        for source, column in cases:
            with self.subTest(source=source):
                report = _validate(source)
                self.assertEqual(
                    [item.code for item in report.diagnostics],
                    ["EBNF201"],
                )
                self.assertEqual(report.diagnostics[0].span.start.column, column)
                self.assertNotIn(
                    "__parsergen_ebnf__",
                    report.diagnostics[0].message,
                )

    def test_rejects_nonproductive_repeat_body(self) -> None:
        report = _validate("<S> ::= <N>*\n<N> ::= <M>\n<M> ::= <N>")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["EBNF200"],
        )

    def test_does_not_mask_unknown_nonterminal_with_progress_error(self) -> None:
        report = _validate("<S> ::= <Missing>*")

        self.assertEqual(report.diagnostics, ())

    def test_rejects_repeat_over_nested_optional(self) -> None:
        report = _validate("<S> ::= (a?)*")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["EBNF201"],
        )

    def test_rejects_nullable_optional_body(self) -> None:
        report = _validate("<S> ::= (<N>)?\n<N> ::= ПУСТО | a")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["EBNF202"],
        )

    def test_accepts_nonnullable_optional_body(self) -> None:
        report = _validate("<S> ::= (<N>)?\n<N> ::= a | b")

        self.assertEqual(report.diagnostics, ())

    def test_rejects_action_nested_in_ebnf_group(self) -> None:
        report = _validate("<S> ::= (a {Value = 1})?")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["EBNF204"],
        )
        self.assertEqual(report.diagnostics[0].span.start.column, 12)

    def test_reports_progress_and_action_errors_for_action_only_repeat(self) -> None:
        report = _validate("<S> ::= ({Value = 1})*")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["EBNF204", "EBNF201"],
        )

    def test_rejects_reserved_synthetic_production_prefix_case_insensitively(
        self,
    ) -> None:
        report = _validate("<__ParserGen_EBNF__User> ::= a")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["GR005"],
        )

    def test_parse_facade_exposes_source_validation_before_lowering_error(
        self,
    ) -> None:
        result = parse_grammar("<S> ::= <N>*\n<N> ::= ПУСТО")

        self.assertEqual(
            [item.code for item in result.diagnostics],
            ["EBNF201"],
        )
        self.assertIsNone(result.grammar)
        self.assertIsNotNone(result.source_grammar)

    def test_binding_does_not_hide_nullable_repeat_body(self) -> None:
        parsed = parse_source_grammar(
            "<S> ::= @НовыйУзел Элементы += <N>*\n<N> ::= ПУСТО"
        )
        assert parsed.grammar is not None

        report = validate_source_grammar(parsed.grammar)

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["EBNF201"],
        )


if __name__ == "__main__":
    unittest.main()
