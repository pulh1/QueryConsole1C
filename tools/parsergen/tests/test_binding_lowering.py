import unittest

from parsergen.grammar_parser import parse_grammar, parse_source_grammar
from parsergen.lowering import BindingOriginKind, lower_source_grammar
from parsergen.model import NonterminalCall
from parsergen.resolver import resolve_grammar


def _lower(source: str):
    parsed = parse_source_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    return lower_source_grammar(parsed.grammar)


class BindingLoweringTests(unittest.TestCase):
    def test_semantic_directives_do_not_enter_canonical_cfg(self) -> None:
        lowered = _lower(
            "<S> ::= @НовыйУзел Значение = <A> Флаг := Истина\n"
            "<A> ::= a"
        )

        self.assertEqual(lowered.diagnostics, ())
        symbols = lowered.grammar.productions[0].alternatives[0].syntax_symbols
        self.assertEqual(len(symbols), 1)
        self.assertIsInstance(symbols[0], NonterminalCall)
        self.assertEqual(symbols[0].name, "A")
        self.assertEqual(
            [item.kind for item in lowered.bindings],
            [
                BindingOriginKind.CONSTRUCTOR,
                BindingOriginKind.SCALAR,
                BindingOriginKind.CONSTANT,
            ],
        )
        self.assertEqual(lowered.bindings[0].value, "НовыйУзел")
        self.assertEqual(lowered.bindings[1].property, "Значение")
        self.assertEqual(lowered.bindings[2].value, "Истина")

    def test_append_inside_separator_repeat_preserves_only_parse_symbols(
        self,
    ) -> None:
        lowered = _lower(
            "<S> ::= @НовыйСписок Элементы += <A> "
            "(',' Элементы += <A>)*\n<A> ::= a"
        )

        repeat = lowered.constructs[0]
        synthetic = next(
            item
            for item in lowered.grammar.productions
            if item.name == repeat.production
        )
        recursive = synthetic.alternatives[0].syntax_symbols
        self.assertEqual(recursive[0].text, ",")
        self.assertEqual(recursive[1].name, "A")
        self.assertEqual(recursive[2].name, synthetic.name)
        appends = [
            item
            for item in lowered.bindings
            if item.kind is BindingOriginKind.APPEND
        ]
        self.assertEqual(len(appends), 2)
        self.assertEqual(
            [item.path for item in appends],
            ["p0_a0_n1", "p0_a0_n2_g0_n1"],
        )

    def test_binding_wrapped_optional_keeps_ebnf_lowering(self) -> None:
        lowered = _lower(
            "<S> ::= @НовыйУзел Значение = <A>?\n<A> ::= a"
        )

        self.assertEqual(len(lowered.constructs), 1)
        optional = lowered.constructs[0]
        production = next(
            item
            for item in lowered.grammar.productions
            if item.name == optional.production
        )
        self.assertEqual(len(production.alternatives), 2)
        self.assertEqual(production.alternatives[1].syntax_symbols, ())

    def test_discard_binding_is_explicit_in_lowering_metadata(self) -> None:
        lowered = _lower(
            "<S> ::= @НовыйУзел -= <A> (',' -= <A>)*\n<A> ::= a"
        )

        self.assertEqual(lowered.diagnostics, ())
        self.assertEqual(
            [
                item.kind
                for item in lowered.bindings
                if item.kind is BindingOriginKind.DISCARD
            ],
            [BindingOriginKind.DISCARD, BindingOriginKind.DISCARD],
        )

    def test_parse_facade_returns_bound_lowering_without_temporary_gate(self) -> None:
        result = parse_grammar(
            "<S> ::= @НовыйУзел Значение = <A>\n<A> ::= a"
        )

        self.assertEqual(result.diagnostics, ())
        self.assertIsNotNone(result.grammar)
        self.assertIsNotNone(result.lowering)
        assert result.grammar is not None
        resolved = resolve_grammar(result.grammar)
        self.assertEqual(resolved.diagnostics, ())

    def test_direct_lowering_reports_binding_validation_errors(self) -> None:
        lowered = _lower("<S> ::= Значение = a")

        self.assertEqual(
            [item.code for item in lowered.diagnostics],
            ["BIND201"],
        )


if __name__ == "__main__":
    unittest.main()
