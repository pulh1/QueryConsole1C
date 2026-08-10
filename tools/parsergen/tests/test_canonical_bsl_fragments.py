import unittest

from parsergen.analysis import compute_analysis
import parsergen.canonical_bsl_codegen as canonical_bsl_codegen
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.resolver import resolve_grammar


def _projected(source: str, names: tuple[str, ...]):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolution = resolve_grammar(parsed.grammar)
    assert resolution.diagnostics == ()
    assert resolution.grammar is not None
    analysis = compute_analysis(resolution.grammar, 1, ("S",))
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolution.grammar,
        analysis,
        production_names=names,
    )
    return parsed.source_grammar, parser_ir


class CanonicalBslFragmentTests(unittest.TestCase):
    def test_renders_only_projected_functions_with_explicit_abi(self) -> None:
        source, parser_ir = _projected(
            "<S> ::= <Expr> {Legacy = ТекущийЭлемент}\n"
            "<Expr> ::= @НовыйБинарный Левая = <Expr> "
            "Оператор = '+' Правая = <Term> | <Term>\n"
            "<Term> ::= @НовыйТерм Значение = ITEM",
            ("Expr",),
        )

        generated = canonical_bsl_codegen.generate_canonical_functions(
            source,
            parser_ir,
            abi_parameters=("Родитель", "ЛевыйЭлемент"),
        )

        self.assertIn(
            "Функция НеТерминалExpr(Родитель = Неопределено, "
            "ЛевыйЭлемент = Неопределено)",
            generated.module_fragment,
        )
        self.assertEqual(generated.module_fragment.count("Пока "), 1)
        self.assertNotIn("Функция НеТерминалS", generated.module_fragment)
        self.assertNotIn("Функция НеТерминалTerm", generated.module_fragment)
        self.assertNotIn("// <parsergen:", generated.module_fragment)
        self.assertEqual(generated.constructor_names, ("НовыйБинарный",))

    def test_rejects_duplicate_abi_parameter(self) -> None:
        source, parser_ir = _projected("<S> ::= ITEM", ("S",))

        with self.assertRaisesRegex(ValueError, "duplicate ABI parameter"):
            canonical_bsl_codegen.generate_canonical_functions(
                source,
                parser_ir,
                abi_parameters=("Контекст", "контекст"),
            )

    def test_rejects_abi_parameter_colliding_with_declared_parameter(self) -> None:
        source, parser_ir = _projected("<S>(Context) ::= ITEM", ("S",))

        with self.assertRaisesRegex(ValueError, "collides with declared parameter"):
            canonical_bsl_codegen.generate_canonical_functions(
                source,
                parser_ir,
                abi_parameters=("context",),
            )

    def test_rejects_decision_token_generated_local_collisions(self) -> None:
        source, parser_ir = _projected(
            "<S>(ТокенРешения0) ::= ITEM",
            ("S",),
        )
        with self.assertRaisesRegex(ValueError, "collides with generated local"):
            canonical_bsl_codegen.generate_canonical_functions(
                source,
                parser_ir,
            )

        source, parser_ir = _projected("<S> ::= ITEM", ("S",))
        with self.assertRaisesRegex(ValueError, "collides with generated local"):
            canonical_bsl_codegen.generate_canonical_functions(
                source,
                parser_ir,
                abi_parameters=("ТокенРешения1",),
            )

    def test_rejects_call_prefix_with_wrong_abi_arity(self) -> None:
        source, parser_ir = _projected("<S> ::= ITEM", ("S",))

        with self.assertRaisesRegex(ValueError, "must match ABI parameter"):
            canonical_bsl_codegen.generate_canonical_functions(
                source,
                parser_ir,
                abi_parameters=("Родитель", "ЛевыйЭлемент"),
                call_argument_prefix=("Неопределено",),
            )


if __name__ == "__main__":
    unittest.main()
