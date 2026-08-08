import unittest

from parsergen.grammar_parser import parse_grammar, parse_source_grammar
from parsergen.lowering import (
    LoweredConstructKind,
    lower_source_grammar,
)
from parsergen.model import Lexeme, NonterminalCall
from parsergen.resolver import resolve_grammar


def _lower(source: str):
    parsed = parse_source_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    return parsed.grammar, lower_source_grammar(parsed.grammar)


class EbnfLoweringTests(unittest.TestCase):
    def test_star_lowers_group_body_to_recursion_and_epsilon(self) -> None:
        _, lowered = _lower("<S> ::= 'a' (',' 'a')*")

        self.assertEqual(lowered.diagnostics, ())
        self.assertEqual(len(lowered.grammar.productions), 2)
        public, synthetic = lowered.grammar.productions
        self.assertEqual(public.name, "S")
        call = public.alternatives[0].syntax_symbols[1]
        self.assertIsInstance(call, NonterminalCall)
        assert isinstance(call, NonterminalCall)
        self.assertEqual(
            call.name,
            "__parsergen_ebnf__p0_a0_n1_star",
        )
        self.assertEqual(synthetic.name, call.name)
        self.assertEqual(len(synthetic.alternatives), 2)
        recursive = synthetic.alternatives[0].syntax_symbols
        self.assertEqual(
            [item.text for item in recursive[:2]],
            [",", "a"],
        )
        self.assertIsInstance(recursive[2], NonterminalCall)
        self.assertEqual(recursive[2].name, synthetic.name)
        self.assertEqual(synthetic.alternatives[1].syntax_symbols, ())

        construct = lowered.constructs[0]
        self.assertIs(construct.kind, LoweredConstructKind.STAR)
        self.assertEqual(construct.production, synthetic.name)
        self.assertIsNone(construct.tail_production)
        self.assertEqual(construct.source_span.start.column, 13)
        self.assertEqual(construct.operator_span.start.column, 22)
        self.assertEqual(
            lowered.alternative_origins[(synthetic.name, 1)],
            construct.operator_span,
        )

    def test_optional_lowers_each_group_branch_and_exit(self) -> None:
        _, lowered = _lower("<S> ::= (a | b)?")

        construct = lowered.constructs[0]
        self.assertIs(construct.kind, LoweredConstructKind.OPTIONAL)
        production = next(
            item
            for item in lowered.grammar.productions
            if item.name == construct.production
        )
        self.assertEqual(len(production.alternatives), 3)
        self.assertEqual(
            [
                alternative.syntax_symbols[0].token_type
                for alternative in production.alternatives[:2]
            ],
            ["a", "b"],
        )
        self.assertEqual(production.alternatives[2].syntax_symbols, ())

    def test_plus_lowers_to_mandatory_head_and_repeat_tail(self) -> None:
        _, lowered = _lower("<S> ::= 'a'+")

        construct = lowered.constructs[0]
        self.assertIs(construct.kind, LoweredConstructKind.PLUS)
        self.assertEqual(
            construct.production,
            "__parsergen_ebnf__p0_a0_n0_plus",
        )
        self.assertEqual(
            construct.tail_production,
            "__parsergen_ebnf__p0_a0_n0_plus_tail",
        )
        head = next(
            item
            for item in lowered.grammar.productions
            if item.name == construct.production
        )
        tail = next(
            item
            for item in lowered.grammar.productions
            if item.name == construct.tail_production
        )
        self.assertEqual(len(head.alternatives), 1)
        self.assertEqual(
            [type(item) for item in head.alternatives[0].syntax_symbols],
            [Lexeme, NonterminalCall],
        )
        self.assertEqual(
            head.alternatives[0].syntax_symbols[1].name,
            tail.name,
        )
        self.assertEqual(len(tail.alternatives), 2)
        self.assertEqual(tail.alternatives[1].syntax_symbols, ())

    def test_standalone_group_lowers_to_synthetic_choice(self) -> None:
        _, lowered = _lower("<S> ::= (a | b) c")

        group = lowered.constructs[0]
        self.assertIs(group.kind, LoweredConstructKind.GROUP)
        public = lowered.grammar.productions[0]
        self.assertEqual(
            public.alternatives[0].syntax_symbols[0].name,
            group.production,
        )
        synthetic = next(
            item
            for item in lowered.grammar.productions
            if item.name == group.production
        )
        self.assertEqual(
            [alt.syntax_symbols[0].token_type for alt in synthetic.alternatives],
            ["a", "b"],
        )

    def test_nested_names_and_order_are_deterministic(self) -> None:
        source = "<S> ::= (a+)*"
        _, first = _lower(source)
        _, second = _lower(source)

        self.assertEqual(first, second)
        self.assertEqual(
            [item.production for item in first.constructs],
            [
                "__parsergen_ebnf__p0_a0_n0_g0_n0_plus",
                "__parsergen_ebnf__p0_a0_n0_star",
            ],
        )
        self.assertEqual(
            [item.name for item in first.grammar.productions],
            [
                "S",
                "__parsergen_ebnf__p0_a0_n0_g0_n0_plus",
                "__parsergen_ebnf__p0_a0_n0_g0_n0_plus_tail",
                "__parsergen_ebnf__p0_a0_n0_star",
            ],
        )

    def test_synthetic_productions_propagate_owner_parameters(self) -> None:
        _, lowered = _lower(
            "<S>(Owner) ::= <A>(Owner)*\n<A>(Owner) ::= TOKEN"
        )

        public = lowered.grammar.productions[0]
        synthetic = next(
            item
            for item in lowered.grammar.productions
            if item.name == lowered.constructs[0].production
        )
        call = public.alternatives[0].syntax_symbols[0]
        self.assertEqual(call.arguments, ("Owner",))
        self.assertEqual(synthetic.parameters, ("Owner",))
        recursive = synthetic.alternatives[0].syntax_symbols[-1]
        self.assertEqual(recursive.arguments, ("Owner",))

    def test_bnf_lowering_is_identity_without_synthetic_constructs(self) -> None:
        source = "<S>(Owner) ::= {Value = 1} 'a' <A>(Owner)\n<A>(Owner) ::= ПУСТО"
        legacy = parse_grammar(source)
        source_result = parse_source_grammar(source)
        assert source_result.grammar is not None
        lowered = lower_source_grammar(source_result.grammar)

        self.assertEqual(lowered.diagnostics, ())
        self.assertEqual(lowered.constructs, ())
        self.assertEqual(lowered.grammar, legacy.grammar)

    def test_parse_facade_returns_lowered_cfg_and_origin_sidecar(self) -> None:
        result = parse_grammar("<S> ::= 'a' (',' 'a')*")

        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        self.assertIsNotNone(result.source_grammar)
        self.assertIsNotNone(result.lowering)
        assert result.grammar is not None
        self.assertEqual(len(result.grammar.productions), 2)

    def test_resolver_handles_calls_inside_lowered_repeat(self) -> None:
        _, lowered = _lower("<S> ::= <A>*\n<A> ::= a")

        resolved = resolve_grammar(lowered.grammar)

        self.assertEqual(resolved.diagnostics, ())
        self.assertIsNotNone(resolved.grammar)

    def test_unknown_call_inside_repeat_keeps_source_span(self) -> None:
        _, lowered = _lower("<S> ::= <Missing>*")

        resolved = resolve_grammar(lowered.grammar)

        self.assertEqual(len(resolved.diagnostics), 1)
        self.assertEqual(resolved.diagnostics[0].span.start.column, 9)

    def test_direct_lowering_reports_invalid_source_construct(self) -> None:
        parsed = parse_source_grammar("<S> ::= <N>*\n<N> ::= ПУСТО")
        assert parsed.grammar is not None

        lowered = lower_source_grammar(parsed.grammar)

        self.assertEqual(
            [item.code for item in lowered.diagnostics],
            ["EBNF201"],
        )


if __name__ == "__main__":
    unittest.main()
