from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from parsergen.analysis import AnalysisResult, compute_analysis
from parsergen.canonical_select import (
    AlternativeOutcome,
    CanonicalDecisionSource,
    CanonicalOutcome,
    ExitOutcome,
    TokenSetPredicate,
    build_canonical_decision_source,
    canonical_matcher_definitions,
)
from parsergen.grammar_parser import parse_grammar
from parsergen.resolver import resolve_grammar


def _analysis(source: str, k: int = 1) -> AnalysisResult:
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.grammar is not None, parsed.diagnostics
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.grammar is not None, resolved.diagnostics
    return compute_analysis(resolved.grammar, k, ("S",))


def _accepts(
    source: CanonicalDecisionSource,
    outcome: CanonicalOutcome,
    word: tuple[str, ...],
) -> bool:
    language = next(
        item.language for item in source.languages if item.outcome == outcome
    )
    states = {language.root}
    for token in word:
        states = {
            edge.target
            for state in states
            for edge in language.nodes[state].edges
            if token in edge.predicate.token_types
        }
    return any(language.nodes[state].accepting for state in states)


class CanonicalSelectTests(unittest.TestCase):
    def test_source_keeps_identifier_matcher_as_exact_token_set(self) -> None:
        analysis = _analysis("#ID_X ::= ID | ГДЕ\n<S> ::= #ID_X | END")
        compressed = analysis._compressed
        assert compressed is not None

        with patch(
            "parsergen.analysis.build_canonical_decision_artifact",
            side_effect=AssertionError("row materialization is forbidden"),
        ):
            source = build_canonical_decision_source(analysis, "S")

        predicates = {
            edge.predicate.token_types
            for outcome_language in source.languages
            for node in outcome_language.language.nodes
            for edge in node.edges
        }
        self.assertIn(("ID", "ГДЕ"), predicates)
        self.assertIn(("END",), predicates)
        self.assertEqual(compressed.stats["public_select_expansions"], 0)
        self.assertEqual(compressed.stats["artifact_matcher_rows"], 0)

    def test_equal_token_sets_ignore_matcher_provenance(self) -> None:
        source = build_canonical_decision_source(
            _analysis("#ID_X ::= A\n<S> ::= #ID_X | A"),
            "S",
        )
        predicates = [
            edge.predicate
            for outcome_language in source.languages
            for node in outcome_language.language.nodes
            for edge in node.edges
        ]

        self.assertGreaterEqual(predicates.count(TokenSetPredicate(("A",))), 2)
        self.assertEqual(len(set(predicates)), 1)

    def test_short_select_continues_through_follow_and_preserves_end(self) -> None:
        source = build_canonical_decision_source(
            _analysis("<S> ::= <A>\n<A> ::= X | ПУСТО", k=2),
            "A",
        )

        self.assertTrue(
            _accepts(source, AlternativeOutcome("A", 1), ("X", "$"))
        )
        self.assertTrue(_accepts(source, AlternativeOutcome("A", 2), ("$",)))

    def test_source_and_predicates_are_immutable_and_validated(self) -> None:
        source = build_canonical_decision_source(_analysis("<S> ::= A"), "S")

        with self.assertRaises(FrozenInstanceError):
            source.production = "Other"  # type: ignore[misc]
        for token_types in ((), ("B", "A"), ("A", "A")):
            with self.subTest(token_types=token_types):
                with self.assertRaisesRegex(
                    ValueError,
                    "token predicate must be sorted, unique, and non-empty",
                ):
                    TokenSetPredicate(token_types)

    def test_exit_alternative_must_exist_exactly_once(self) -> None:
        analysis = _analysis("<S> ::= A | ПУСТО")

        source = build_canonical_decision_source(
            analysis,
            "S",
            exit_alternative=2,
        )
        self.assertEqual(
            tuple(item.outcome for item in source.languages),
            (AlternativeOutcome("S", 1), ExitOutcome("S", 2)),
        )
        with self.assertRaisesRegex(
            ValueError,
            "exit alternative must exist exactly once",
        ):
            build_canonical_decision_source(
                analysis,
                "S",
                exit_alternative=3,
            )

    def test_matcher_definitions_are_exported_without_decision_rows(self) -> None:
        analysis = _analysis("#ID_X ::= ID | ГДЕ\n<S> ::= #ID_X")
        compressed = analysis._compressed
        assert compressed is not None

        definitions = canonical_matcher_definitions(analysis)

        self.assertEqual(
            [(item.label, item.token_types) for item in definitions],
            [("ID_X", ("ID", "ГДЕ")), ("$", ("$",))],
        )
        self.assertEqual(compressed.stats["artifact_matcher_rows"], 0)


if __name__ == "__main__":
    unittest.main()
