import itertools
import re
import unittest

from parsergen.analysis import CanonicalDecisionRow, MatcherDefinition
from parsergen.canonical_bsl_conditions import CanonicalConditionRenderer
from parsergen.parser_ir import CanonicalDecision


def _decision(
    rows: tuple[CanonicalDecisionRow, ...],
    definitions: tuple[MatcherDefinition, ...],
) -> CanonicalDecision:
    return CanonicalDecision("Choice", rows, definitions)


def _matching_alternatives(
    decision: CanonicalDecision,
    word: tuple[str | None, ...],
) -> set[int]:
    definitions = {
        item.label: frozenset(item.token_types)
        for item in decision.matcher_definitions
    }
    matched = set()
    for row in decision.rows:
        if all(
            (
                word[index] is None
                if matcher == "$"
                else word[index] in definitions[matcher]
            )
            for index, matcher in enumerate(row.matchers)
        ):
            matched.add(row.alternative)
    return matched


def _condition_matches(
    condition: str,
    word: tuple[str | None, ...],
) -> bool:
    expression = re.sub(
        r"ТипТокенаПросмотра\((\d+)\)",
        lambda match: f"word[{match.group(1)}]",
        condition,
    )
    expression = expression.replace("Неопределено", "None")
    expression = expression.replace(" = ", " == ")
    expression = expression.replace(" И ", " and ")
    expression = expression.replace(" Или ", " or ")
    return bool(
        eval(
            expression,
            {"__builtins__": {}},
            {"word": word},
        )
    )


class CanonicalBslConditionTests(unittest.TestCase):
    def test_renders_single_token_condition(self) -> None:
        definitions = (MatcherDefinition("A", ("a",)),)
        decision = _decision(
            (CanonicalDecisionRow("Choice", 1, ("A",)),),
            definitions,
        )

        rendered = CanonicalConditionRenderer(
            definitions
        ).for_alternative(decision, 1)

        self.assertEqual(
            rendered,
            '(ТипТокенаПросмотра(0) = "a")',
        )

    def test_keeps_identifier_matcher_factorized(self) -> None:
        definitions = (MatcherDefinition("ID_Name", ("ID", "WORD")),)
        decision = _decision(
            (CanonicalDecisionRow("Choice", 1, ("ID_Name",)),),
            definitions,
        )

        rendered = CanonicalConditionRenderer(
            definitions
        ).for_alternative(decision, 1)

        self.assertEqual(
            rendered,
            '(ТипТокенаПросмотра(0) = "ID" Или '
            'ТипТокенаПросмотра(0) = "WORD")',
        )

    def test_renders_k3_conjunction_and_short_prefix_rows(self) -> None:
        definitions = (
            MatcherDefinition("A", ("a",)),
            MatcherDefinition("B", ("b",)),
            MatcherDefinition("C", ("c",)),
        )
        decision = _decision(
            (
                CanonicalDecisionRow("Choice", 1, ("A", "B", "C")),
                CanonicalDecisionRow("Choice", 1, ("A", "C")),
            ),
            definitions,
        )

        rendered = CanonicalConditionRenderer(
            definitions
        ).for_alternative(decision, 1)

        self.assertEqual(
            rendered,
            '(ТипТокенаПросмотра(0) = "a" И '
            '((ТипТокенаПросмотра(1) = "b" И '
            '(ТипТокенаПросмотра(2) = "c")) Или '
            'ТипТокенаПросмотра(1) = "c"))',
        )

    def test_factors_common_prefix_and_equal_suffixes(self) -> None:
        definitions = (
            MatcherDefinition("A", ("a",)),
            MatcherDefinition("B", ("b",)),
            MatcherDefinition("C", ("c",)),
            MatcherDefinition("D", ("d",)),
        )
        decision = _decision(
            (
                CanonicalDecisionRow("Choice", 1, ("A", "B")),
                CanonicalDecisionRow("Choice", 1, ("A", "C")),
                CanonicalDecisionRow("Choice", 1, ("A", "D")),
            ),
            definitions,
        )

        rendered = CanonicalConditionRenderer(
            definitions
        ).for_alternative(decision, 1)

        self.assertEqual(
            rendered,
            '(ТипТокенаПросмотра(0) = "a" И '
            '(ТипТокенаПросмотра(1) = "b" Или '
            'ТипТокенаПросмотра(1) = "c" Или '
            'ТипТокенаПросмотра(1) = "d"))',
        )
        self.assertEqual(rendered.count("ТипТокенаПросмотра(0)"), 1)

    def test_factorization_preserves_union_of_canonical_rows(self) -> None:
        definitions = (
            MatcherDefinition("A", ("a",)),
            MatcherDefinition("B", ("b",)),
            MatcherDefinition("C", ("c",)),
            MatcherDefinition("ID", ("ID", "WORD")),
            MatcherDefinition("$", ("$",)),
        )
        decision = _decision(
            (
                CanonicalDecisionRow("Choice", 1, ("A", "B", "C")),
                CanonicalDecisionRow("Choice", 1, ("A", "C")),
                CanonicalDecisionRow("Choice", 1, ("ID", "$")),
            ),
            definitions,
        )

        rendered = CanonicalConditionRenderer(
            definitions
        ).for_alternative(decision, 1)

        alphabet = ("a", "b", "c", "ID", "WORD", "other", None)
        for word in itertools.product(alphabet, repeat=3):
            with self.subTest(word=word):
                expected = bool(_matching_alternatives(decision, word))
                self.assertEqual(
                    _condition_matches(rendered, word),
                    expected,
                )

    def test_renders_eof_as_undefined_lookahead(self) -> None:
        definitions = (MatcherDefinition("$", ("$",)),)
        decision = _decision(
            (CanonicalDecisionRow("Choice", 2, ("$",)),),
            definitions,
        )

        rendered = CanonicalConditionRenderer(
            definitions
        ).for_alternative(decision, 2)

        self.assertEqual(
            rendered,
            "(ТипТокенаПросмотра(0) = Неопределено)",
        )

    def test_combines_requested_alternatives_without_precedence(self) -> None:
        definitions = (
            MatcherDefinition("A", ("a",)),
            MatcherDefinition("B", ("b",)),
        )
        decision = _decision(
            (
                CanonicalDecisionRow("Choice", 1, ("A",)),
                CanonicalDecisionRow("Choice", 2, ("B",)),
            ),
            definitions,
        )

        rendered = CanonicalConditionRenderer(
            definitions
        ).for_alternatives(decision, (1, 2))

        self.assertEqual(
            rendered,
            '(ТипТокенаПросмотра(0) = "a" Или '
            'ТипТокенаПросмотра(0) = "b")',
        )
        for word in itertools.product(("a", "b", "c", None), repeat=1):
            self.assertLessEqual(len(_matching_alternatives(decision, word)), 1)

    def test_unique_first_prefix_commits_disjoint_alternative(self) -> None:
        definitions = (
            MatcherDefinition("A", ("a",)),
            MatcherDefinition("B", ("b",)),
            MatcherDefinition("X", ("x",)),
            MatcherDefinition("Y", ("y",)),
        )
        decision = _decision(
            (
                CanonicalDecisionRow("Choice", 1, ("A", "X")),
                CanonicalDecisionRow("Choice", 2, ("B", "Y")),
            ),
            definitions,
        )

        renderer = CanonicalConditionRenderer(definitions)

        self.assertEqual(
            renderer.for_alternative_with_unique_first(decision, 1),
            '(ТипТокенаПросмотра(0) = "a")',
        )
        self.assertEqual(
            renderer.for_alternative_with_unique_first(decision, 2),
            '(ТипТокенаПросмотра(0) = "b")',
        )

    def test_shared_concrete_first_token_still_requires_full_select(self) -> None:
        definitions = (
            MatcherDefinition("ID", ("ID", "WORD")),
            MatcherDefinition("WORD", ("WORD",)),
            MatcherDefinition("X", ("x",)),
            MatcherDefinition("Y", ("y",)),
        )
        decision = _decision(
            (
                CanonicalDecisionRow("Choice", 1, ("ID", "X")),
                CanonicalDecisionRow("Choice", 2, ("WORD", "Y")),
            ),
            definitions,
        )

        renderer = CanonicalConditionRenderer(definitions)
        first = renderer.for_alternative_with_unique_first(decision, 1)
        second = renderer.for_alternative_with_unique_first(decision, 2)

        self.assertIn('ТипТокенаПросмотра(0) = "ID"', first)
        self.assertIn('ТипТокенаПросмотра(1) = "x"', first)
        self.assertIn('ТипТокенаПросмотра(1) = "y"', second)
        for word in itertools.product(("ID", "WORD", "x", "y"), repeat=2):
            self.assertLessEqual(
                int(_condition_matches(first, word))
                + int(_condition_matches(second, word)),
                1,
            )

    def test_rejects_incomplete_or_malformed_canonical_artifact(self) -> None:
        cases = (
            (
                (MatcherDefinition("A", ("a",)),),
                (CanonicalDecisionRow("Choice", 1, ("Missing",)),),
                1,
                "unknown matcher",
            ),
            (
                (MatcherDefinition("A", ()),),
                (CanonicalDecisionRow("Choice", 1, ("A",)),),
                1,
                "empty token set",
            ),
            (
                (MatcherDefinition("$", ("EOF",)),),
                (CanonicalDecisionRow("Choice", 1, ("$",)),),
                1,
                "reserved EOF matcher",
            ),
            (
                (MatcherDefinition("A", ("a",)),),
                (CanonicalDecisionRow("Choice", 1, ("A",)),),
                2,
                "has no canonical rows",
            ),
        )
        for definitions, rows, alternative, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    CanonicalConditionRenderer(
                        definitions
                    ).for_alternative(
                        _decision(rows, definitions),
                        alternative,
                    )


if __name__ == "__main__":
    unittest.main()
