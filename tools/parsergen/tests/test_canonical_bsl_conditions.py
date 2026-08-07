import itertools
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
            '((ТипТокенаПросмотра(0) = "ID" Или '
            'ТипТокенаПросмотра(0) = "WORD"))',
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
            '((ТипТокенаПросмотра(0) = "a" И '
            'ТипТокенаПросмотра(1) = "b" И '
            'ТипТокенаПросмотра(2) = "c") Или '
            '(ТипТокенаПросмотра(0) = "a" И '
            'ТипТокенаПросмотра(1) = "c"))',
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
            '((ТипТокенаПросмотра(0) = "a") Или '
            '(ТипТокенаПросмотра(0) = "b"))',
        )
        for word in itertools.product(("a", "b", "c", None), repeat=1):
            self.assertLessEqual(len(_matching_alternatives(decision, word)), 1)

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
