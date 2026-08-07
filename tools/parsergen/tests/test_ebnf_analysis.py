import unittest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.lowering import LoweredConstructKind
from parsergen.resolver import resolve_grammar


def _analyze(source: str, k: int):
    parsed = parse_grammar(source)
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, k, ("S",))
    return parsed, resolved.grammar, analysis


def _assert_mapped_analysis_equal(
    testcase: unittest.TestCase,
    actual,
    expected,
    mapping: dict[str, str],
) -> None:
    _, actual_grammar, actual_analysis = actual
    _, expected_grammar, expected_analysis = expected
    for actual_name, expected_name in mapping.items():
        testcase.assertEqual(
            actual_name in actual_analysis.nullable,
            expected_name in expected_analysis.nullable,
        )
        testcase.assertEqual(
            actual_analysis.first[actual_name],
            expected_analysis.first[expected_name],
        )
        testcase.assertEqual(
            actual_analysis.follow[actual_name],
            expected_analysis.follow[expected_name],
        )
        actual_alternatives = actual_grammar.productions[actual_name]
        expected_alternatives = expected_grammar.productions[expected_name]
        testcase.assertEqual(
            len(actual_alternatives),
            len(expected_alternatives),
        )
        for number in range(1, len(actual_alternatives) + 1):
            testcase.assertEqual(
                actual_analysis.select[(actual_name, number)],
                expected_analysis.select[(expected_name, number)],
            )


class EbnfAnalysisEquivalenceTests(unittest.TestCase):
    def test_separator_star_matches_handwritten_bnf_at_k_1_to_3(self) -> None:
        ebnf = "<S> ::= start (',' item)* end"
        bnf = (
            "<S> ::= start <Tail> end\n"
            "<Tail> ::= ',' item <Tail> | ПУСТО"
        )
        for k in (1, 2, 3):
            with self.subTest(k=k):
                actual = _analyze(ebnf, k)
                expected = _analyze(bnf, k)
                construct = actual[0].lowering.constructs[0]
                _assert_mapped_analysis_equal(
                    self,
                    actual,
                    expected,
                    {"S": "S", construct.production: "Tail"},
                )

    def test_plus_at_eof_matches_handwritten_head_and_tail(self) -> None:
        ebnf = "<S> ::= 'a'+"
        bnf = (
            "<S> ::= <Head>\n"
            "<Head> ::= 'a' <Tail>\n"
            "<Tail> ::= 'a' <Tail> | ПУСТО"
        )
        for k in (1, 2, 3):
            with self.subTest(k=k):
                actual = _analyze(ebnf, k)
                expected = _analyze(bnf, k)
                construct = actual[0].lowering.constructs[0]
                _assert_mapped_analysis_equal(
                    self,
                    actual,
                    expected,
                    {
                        "S": "S",
                        construct.production: "Head",
                        construct.tail_production: "Tail",
                    },
                )

    def test_optional_group_at_eof_matches_handwritten_bnf(self) -> None:
        ebnf = "<S> ::= (a | b)?"
        bnf = "<S> ::= <Optional>\n<Optional> ::= a | b | ПУСТО"
        for k in (1, 2, 3):
            with self.subTest(k=k):
                actual = _analyze(ebnf, k)
                expected = _analyze(bnf, k)
                construct = actual[0].lowering.constructs[0]
                _assert_mapped_analysis_equal(
                    self,
                    actual,
                    expected,
                    {"S": "S", construct.production: "Optional"},
                )

    def test_nested_optional_repeat_matches_handwritten_bnf(self) -> None:
        ebnf = "<S> ::= start ((a | b)? c)* end"
        bnf = (
            "<S> ::= start <Outer> end\n"
            "<Outer> ::= <Optional> c <Outer> | ПУСТО\n"
            "<Optional> ::= a | b | ПУСТО"
        )
        for k in (1, 2, 3):
            with self.subTest(k=k):
                actual = _analyze(ebnf, k)
                expected = _analyze(bnf, k)
                constructs = actual[0].lowering.constructs
                optional = next(
                    item
                    for item in constructs
                    if item.kind is LoweredConstructKind.OPTIONAL
                )
                repeat = next(
                    item
                    for item in constructs
                    if item.kind is LoweredConstructKind.STAR
                )
                _assert_mapped_analysis_equal(
                    self,
                    actual,
                    expected,
                    {
                        "S": "S",
                        repeat.production: "Outer",
                        optional.production: "Optional",
                    },
                )


if __name__ == "__main__":
    unittest.main()
