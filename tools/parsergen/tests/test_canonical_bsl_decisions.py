import unittest

from parsergen.canonical_bsl_decisions import CanonicalDecisionRenderer
from tests.test_parser_ir import _build as _build_ir


def _render(grammar: str, k: int = 1) -> list[str]:
    parser_ir = _build_ir(grammar, k)
    production = next(
        item for item in parser_ir.productions if item.name == "S"
    )
    assert production.decision is not None
    renderer = CanonicalDecisionRenderer(parser_ir.matcher_definitions)
    return renderer.render(
        production.decision,
        indent="",
        token_prefix="ТокенРешения",
        render_leaf=lambda leaf, indent: [
            f"{indent}// {type(leaf).__name__}"
        ],
    )


class CanonicalBslDecisionTests(unittest.TestCase):
    def test_renderer_caches_first_token_and_nests_second_lookup(self) -> None:
        rendered = "\n".join(_render("<S> ::= A X | A Y | B Z", k=2))

        self.assertEqual(
            rendered.count("ТокенРешения0 = ТипТокенаПросмотра(0);"),
            1,
        )
        self.assertEqual(rendered.count("ТипТокенаПросмотра(1)"), 1)
        self.assertLess(
            rendered.index('ТокенРешения0 = "A"'),
            rendered.index("ТипТокенаПросмотра(1)"),
        )
        self.assertNotIn("DecisionNode", rendered)

    def test_renderer_emits_exact_identifier_token_set(self) -> None:
        rendered = "\n".join(
            _render("#ID_A ::= ID | WORD\n<S> ::= #ID_A | END")
        )

        self.assertIn('ТокенРешения0 = "ID"', rendered)
        self.assertIn('ТокенРешения0 = "WORD"', rendered)
        self.assertNotIn("ТипТокенаПросмотра(0) =", rendered)


if __name__ == "__main__":
    unittest.main()
