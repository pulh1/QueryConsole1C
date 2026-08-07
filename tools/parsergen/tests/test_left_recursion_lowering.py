import unittest

from parsergen.grammar_parser import parse_grammar, parse_source_grammar
from parsergen.lowering import lower_source_grammar
from parsergen.model import Lexeme, NonterminalCall, Terminal


def _lower(source: str):
    parsed = parse_source_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    return lower_source_grammar(parsed.grammar)


class DirectLeftRecursionLoweringTests(unittest.TestCase):
    def test_lowers_base_and_recursive_rows_to_public_head_and_tail(self) -> None:
        lowered = _lower(
            "<A>(P) ::= <A>(P) '+' <T>(P) | "
            "<A>(P) '-' <T>(P) | <T>(P)\n"
            "<T>(P) ::= ITEM"
        )

        self.assertEqual(lowered.diagnostics, ())
        self.assertEqual(len(lowered.left_recursions), 1)
        origin = lowered.left_recursions[0]
        self.assertEqual(origin.production, "A")
        self.assertEqual(origin.base_alternatives, (2,))
        self.assertEqual(origin.recursive_alternatives, (0, 1))
        self.assertEqual(
            origin.tail_production,
            "__parsergen_ebnf__p0_left_fold_tail",
        )

        public = lowered.grammar.productions[0]
        self.assertEqual(public.name, "A")
        self.assertEqual(public.parameters, ("P",))
        self.assertEqual(len(public.alternatives), 1)
        base_symbols = public.alternatives[0].syntax_symbols
        self.assertEqual(
            [item.name for item in base_symbols],
            ["T", origin.tail_production],
        )
        self.assertEqual(base_symbols[0].arguments, ("P",))
        self.assertEqual(base_symbols[1].arguments, ("P",))

        tail = next(
            item
            for item in lowered.grammar.productions
            if item.name == origin.tail_production
        )
        self.assertEqual(tail.parameters, ("P",))
        self.assertEqual(len(tail.alternatives), 3)
        for alternative, operator in zip(tail.alternatives[:2], ("+", "-")):
            symbols = alternative.syntax_symbols
            self.assertEqual(
                [type(item) for item in symbols],
                [Lexeme, NonterminalCall, NonterminalCall],
            )
            self.assertEqual(symbols[0].text, operator)
            self.assertEqual(symbols[1].name, "T")
            self.assertEqual(symbols[2].name, tail.name)
            self.assertNotIn("A", [item.name for item in symbols[1:]])
        self.assertEqual(tail.alternatives[2].syntax_symbols, ())

    def test_preserves_source_origins_for_reindexed_rows(self) -> None:
        parsed = parse_source_grammar(
            "<A> ::= <A> '+' ITEM | BASE | <A> '-' ITEM",
            "grammar.txt",
        )
        assert parsed.grammar is not None
        source = parsed.grammar.productions[0]

        lowered = lower_source_grammar(parsed.grammar)
        origin = lowered.left_recursions[0]

        self.assertEqual(
            lowered.alternative_origins[("A", 0)],
            source.alternatives[1].span,
        )
        self.assertEqual(
            lowered.alternative_origins[(origin.tail_production, 0)],
            source.alternatives[0].span,
        )
        self.assertEqual(
            lowered.alternative_origins[(origin.tail_production, 1)],
            source.alternatives[2].span,
        )

    def test_semantic_directives_remain_origins_but_not_cfg_symbols(self) -> None:
        lowered = _lower(
            "<Expr> ::= @НовыйБинарный Левый = <Expr> "
            "Оператор = '+' Правый = <Term> | <Term>\n"
            "<Term> ::= ITEM"
        )
        origin = lowered.left_recursions[0]
        tail = next(
            item
            for item in lowered.grammar.productions
            if item.name == origin.tail_production
        )

        self.assertEqual(
            [type(item) for item in tail.alternatives[0].syntax_symbols],
            [Lexeme, NonterminalCall, NonterminalCall],
        )
        self.assertEqual(
            [item.kind.value for item in lowered.bindings[:4]],
            ["constructor", "scalar", "scalar", "scalar"],
        )
        self.assertEqual(lowered.bindings[1].property, "Левый")

    def test_invalid_direct_cycle_is_not_transformed_for_low_level_analysis(
        self,
    ) -> None:
        lowered = _lower("<A> ::= <A>")

        self.assertEqual(lowered.left_recursions, ())
        production = lowered.grammar.productions[0]
        self.assertEqual(len(production.alternatives), 1)
        self.assertIsInstance(
            production.alternatives[0].syntax_symbols[0],
            NonterminalCall,
        )

    def test_parse_facade_exposes_lowered_direct_lr(self) -> None:
        parsed = parse_grammar("<A> ::= <A> '+' ITEM | BASE")

        self.assertEqual(parsed.diagnostics, ())
        assert parsed.lowering is not None
        self.assertEqual(len(parsed.lowering.left_recursions), 1)
        assert parsed.grammar is not None
        self.assertIsInstance(
            parsed.grammar.productions[0].alternatives[0].syntax_symbols[0],
            Terminal,
        )


if __name__ == "__main__":
    unittest.main()
