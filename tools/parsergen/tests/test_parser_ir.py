import unittest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import (
    Dispatch,
    OptionalBranch,
    ParseSymbol,
    RepeatLoop,
    build_parser_ir,
)
from parsergen.resolver import resolve_grammar


def _build(source: str, k: int = 1):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, k, ("S",))
    return build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
    )


class ParserIrTests(unittest.TestCase):
    def test_separator_star_becomes_repeat_loop_without_synthetic_function(
        self,
    ) -> None:
        parser_ir = _build("<S> ::= 'a' (',' 'a')*")

        self.assertEqual(
            [production.name for production in parser_ir.productions],
            ["S"],
        )
        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [ParseSymbol, RepeatLoop])
        loop = operations[1]
        assert isinstance(loop, RepeatLoop)
        self.assertEqual(len(loop.branches), 1)
        self.assertEqual(
            [item.symbol.text for item in loop.branches[0].operations],
            [",", "a"],
        )
        self.assertTrue(loop.decision.production.startswith("__parsergen_ebnf__"))
        self.assertEqual(
            {row.alternative for row in loop.decision.rows},
            {1, 2},
        )
        self.assertFalse(
            any(
                production.name.startswith("__parsergen_ebnf__")
                for production in parser_ir.productions
            )
        )

    def test_plus_becomes_mandatory_parse_followed_by_repeat_loop(self) -> None:
        parser_ir = _build("<S> ::= 'a'+")

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [ParseSymbol, RepeatLoop])
        self.assertEqual(operations[0].symbol.text, "a")
        self.assertEqual(len(operations[1].branches), 1)

    def test_optional_becomes_optional_branch(self) -> None:
        parser_ir = _build("<S> ::= (a | b)?")

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [OptionalBranch])
        optional = operations[0]
        self.assertEqual(len(optional.branches), 2)
        self.assertEqual(
            [branch.operations[0].symbol.token_type for branch in optional.branches],
            ["a", "b"],
        )

    def test_standalone_group_becomes_canonical_dispatch(self) -> None:
        parser_ir = _build("<S> ::= (a | b) c")

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [Dispatch, ParseSymbol])
        self.assertEqual(len(operations[0].branches), 2)

    def test_canonical_decision_keeps_identifier_matcher_factorized(self) -> None:
        parser_ir = _build("#ID_A ::= ID | WORD\n<S> ::= #ID_A?")

        optional = parser_ir.productions[0].alternatives[0].operations[0]
        assert isinstance(optional, OptionalBranch)
        consuming = [
            row
            for row in optional.decision.rows
            if row.alternative == 1
        ]
        self.assertEqual(len(consuming), 1)
        matcher = next(
            definition
            for definition in optional.decision.matcher_definitions
            if definition.label == consuming[0].matchers[0]
        )
        self.assertEqual(matcher.token_types, ("ID", "WORD"))

    def test_conflicting_select_prevents_parser_ir_build(self) -> None:
        parsed = parse_grammar("<S> ::= 'a'* 'a'")
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        with self.assertRaisesRegex(ValueError, "overlapping canonical SELECT"):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved.grammar,
                analysis,
            )

    def test_source_action_requires_declarative_binding_before_ir_build(self) -> None:
        parsed = parse_grammar("<S> ::= {Value = 1} a")
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        with self.assertRaisesRegex(ValueError, "arbitrary source actions"):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved.grammar,
                analysis,
            )


if __name__ == "__main__":
    unittest.main()
