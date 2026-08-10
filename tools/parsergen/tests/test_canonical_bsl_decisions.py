import unittest

from parsergen.canonical_bsl_decisions import CanonicalDecisionRenderer
from parsergen.decision_dag import CommitAlternative
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
        render_leaf=lambda leaf, facts, indent: [
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

    def test_named_set_candidate_uses_cached_token_and_exact_class(self) -> None:
        parser_ir = _build_ir(
            "#ID_Large ::= A | B | C | D | E | F | G | H | I\n"
            "<S> ::= #ID_Large | END"
        )
        production = next(
            item for item in parser_ir.productions if item.name == "S"
        )
        assert production.decision is not None
        token_types = tuple("ABCDEFGHI")
        renderer = CanonicalDecisionRenderer(
            parser_ir.matcher_definitions,
            named_predicates={token_types: "ID_Large"},
        )
        rendered = "\n".join(
            renderer.render(
                production.decision,
                indent="",
                token_prefix="ТокенРешения",
                render_leaf=lambda leaf, facts, indent: [f"{indent}// leaf"],
            )
        )

        self.assertIn(
            'ТокенПринадлежитКлассу(ТокенРешения0, "ID_Large")',
            rendered,
        )
        helper_call = next(
            line for line in rendered.splitlines()
            if "ТокенПринадлежитКлассу" in line
        )
        self.assertNotIn("ТипТокенаПросмотра", helper_call)

    def test_renderer_passes_exact_facts_for_direct_and_two_token_paths(
        self,
    ) -> None:
        parser_ir = _build_ir("<S> ::= A X | A Y | B Z", 2)
        production = next(
            item for item in parser_ir.productions if item.name == "S"
        )
        assert production.decision is not None
        observed: dict[
            int,
            tuple[tuple[int, tuple[str, ...]], ...],
        ] = {}

        def render_leaf(leaf, facts, indent: str) -> list[str]:
            if isinstance(leaf, CommitAlternative):
                observed[leaf.outcome.alternative] = tuple(
                    (fact.offset, fact.predicate.token_types)
                    for fact in facts
                )
            return [f"{indent}// leaf"]

        CanonicalDecisionRenderer(parser_ir.matcher_definitions).render(
            production.decision,
            indent="",
            token_prefix="ТокенРешения",
            render_leaf=render_leaf,
        )

        self.assertEqual(
            observed,
            {
                1: ((0, ("A",)), (1, ("X",))),
                2: ((0, ("A",)), (1, ("Y",))),
                3: ((0, ("B",)),),
            },
        )


if __name__ == "__main__":
    unittest.main()
