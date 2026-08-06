from dataclasses import FrozenInstanceError
import unittest

from parsergen.diagnostics import (
    Diagnostic,
    DiagnosticBag,
    RelatedLocation,
    Severity,
    SourcePosition,
    SourceSpan,
)
from parsergen.model import Action, Alternative, Grammar, Production, Terminal


def span(line: int, column: int = 1) -> SourceSpan:
    start = SourcePosition(line=line, column=column, offset=line * 100 + column)
    end = SourcePosition(
        line=line,
        column=column + 1,
        offset=line * 100 + column + 1,
    )
    return SourceSpan(path="grammar.txt", start=start, end=end)


class ModelTests(unittest.TestCase):
    def test_model_is_immutable_and_preserves_action_boundary(self) -> None:
        production = Production(
            name="S",
            parameters=(),
            alternatives=(
                Alternative(
                    index=1,
                    elements=(
                        Action("x = 1", boundary=0, span=span(1)),
                        Terminal("a", span(1)),
                    ),
                    span=span(1),
                ),
            ),
            order=0,
            span=span(1),
        )
        grammar = Grammar(
            productions=(production,), identifier_definitions=(), path="grammar.txt"
        )

        self.assertEqual(grammar.productions[0].alternatives[0].elements[0].boundary, 0)
        with self.assertRaises(FrozenInstanceError):
            production.name = "Changed"  # type: ignore[misc]

    def test_diagnostic_bag_sorts_and_detects_errors(self) -> None:
        warning = Diagnostic("VAL001", Severity.WARNING, "unreachable", span(5))
        error = Diagnostic(
            "RES001",
            Severity.ERROR,
            "unknown",
            span(2),
            related=(RelatedLocation("used here", span(4)),),
            details={"symbol": "Missing"},
        )
        bag = DiagnosticBag((warning, error))

        self.assertTrue(bag.has_errors)
        self.assertEqual([item.code for item in bag.sorted()], ["RES001", "VAL001"])

