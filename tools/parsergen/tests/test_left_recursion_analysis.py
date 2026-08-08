import unittest

from parsergen.analysis import compute_analysis, find_select_conflicts
from parsergen.grammar_parser import parse_grammar
from parsergen.resolver import resolve_grammar
from parsergen.validation import validate_grammar


def _analyze(source: str, k: int, start: str = "A"):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.lowering is not None
    resolution = resolve_grammar(parsed.grammar)
    assert resolution.diagnostics == ()
    assert resolution.grammar is not None
    analysis = compute_analysis(resolution.grammar, k, (start,))
    return parsed, resolution.grammar, analysis


class DirectLeftRecursionAnalysisTests(unittest.TestCase):
    def test_productive_direct_lr_has_disjoint_base_suffix_and_exit(self) -> None:
        parsed, grammar, analysis = _analyze(
            "<A> ::= <A> '+' ITEM | <A> '-' ITEM | BASE",
            1,
        )

        self.assertEqual(find_select_conflicts(grammar, analysis), ())
        origin = parsed.lowering.left_recursions[0]
        self.assertEqual(analysis.select[("A", 1)], frozenset({("BASE",)}))
        self.assertEqual(
            analysis.select[(origin.tail_production, 1)],
            frozenset({("+",)}),
        )
        self.assertEqual(
            analysis.select[(origin.tail_production, 2)],
            frozenset({("-",)}),
        )
        self.assertEqual(
            analysis.select[(origin.tail_production, 3)],
            frozenset({("$",)}),
        )

    def test_recursive_conflict_disappears_at_sufficient_finite_k(self) -> None:
        source = "<A> ::= <A> x y | <A> x z | b"

        _, grammar_at_one, analysis_at_one = _analyze(source, 1)
        parsed, grammar_at_two, analysis_at_two = _analyze(source, 2)

        conflicts = find_select_conflicts(grammar_at_one, analysis_at_one)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].witness, ("x",))
        self.assertEqual(find_select_conflicts(grammar_at_two, analysis_at_two), ())
        tail = parsed.lowering.left_recursions[0].tail_production
        self.assertEqual(
            analysis_at_two.select[(tail, 1)],
            frozenset({("x", "y")}),
        )
        self.assertEqual(
            analysis_at_two.select[(tail, 2)],
            frozenset({("x", "z")}),
        )

    def test_suffix_exit_conflict_is_checked_at_configured_k(self) -> None:
        source = "<S> ::= <A> x\n<A> ::= <A> x y | b"

        _, grammar_at_one, analysis_at_one = _analyze(source, 1, "S")
        _, grammar_at_two, analysis_at_two = _analyze(source, 2, "S")

        self.assertEqual(len(find_select_conflicts(grammar_at_one, analysis_at_one)), 1)
        self.assertEqual(find_select_conflicts(grammar_at_two, analysis_at_two), ())

    def test_valid_direct_lr_no_longer_reports_val202(self) -> None:
        parsed, grammar, analysis = _analyze(
            "<A> ::= <A> '+' ITEM | BASE",
            1,
        )

        report = validate_grammar(
            parsed.grammar,
            grammar,
            analysis,
            {"Parse": "A"},
            lowering=parsed.lowering,
        )

        self.assertNotIn("VAL202", [item.code for item in report.diagnostics])
        self.assertFalse(report.has_errors)

    def test_indirect_and_nullable_prefix_lr_remain_unsupported(self) -> None:
        cases = (
            ("<A> ::= <B> | a\n<B> ::= <A> x | b", ("A", "B", "A")),
            ("<A> ::= <N> <A> x | a\n<N> ::= ПУСТО", ("A", "A")),
        )
        for source, path in cases:
            with self.subTest(source=source):
                parsed, grammar, analysis = _analyze(source, 2)
                report = validate_grammar(
                    parsed.grammar,
                    grammar,
                    analysis,
                    {"Parse": "A"},
                    lowering=parsed.lowering,
                )
                recursion = next(
                    item
                    for item in report.diagnostics
                    if item.code == "VAL202"
                )
                self.assertEqual(recursion.details["path"], path)


if __name__ == "__main__":
    unittest.main()
