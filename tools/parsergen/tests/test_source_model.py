from dataclasses import FrozenInstanceError
import unittest

from parsergen.diagnostics import SourcePosition, SourceSpan
from parsergen.model import Lexeme
from parsergen.source_model import (
    QuantifierKind,
    SourceRepeat,
    SourceSequence,
)


class SourceModelTests(unittest.TestCase):
    def test_structural_nodes_are_immutable(self) -> None:
        span = SourceSpan(
            "grammar.txt",
            SourcePosition(1, 1, 0),
            SourcePosition(1, 3, 2),
        )
        body = SourceSequence((Lexeme("a", span),), span)
        repeat = SourceRepeat(
            body,
            QuantifierKind.ZERO_OR_MORE,
            span,
            span,
        )

        with self.assertRaises(FrozenInstanceError):
            repeat.kind = QuantifierKind.ONE_OR_MORE  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
