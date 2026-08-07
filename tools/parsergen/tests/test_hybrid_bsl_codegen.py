import importlib
import unittest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.resolver import resolve_grammar


def _parts(source: str, canonical_names: tuple[str, ...]):
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
        production_names=canonical_names,
    )
    return parsed, resolution.grammar, analysis, parser_ir


def _function(module: str, name: str) -> str:
    return module.split(f"Функция {name}", 1)[1].split(
        "КонецФункции",
        1,
    )[0]


def _generate(*args, **kwargs):
    module = importlib.import_module("parsergen.hybrid_bsl_codegen")
    return module.generate_hybrid_parser(*args, **kwargs)


class HybridBslCodegenTests(unittest.TestCase):
    def test_links_legacy_canonical_legacy_calls_and_isolates_matcher_rows(
        self,
    ) -> None:
        parsed, resolved, analysis, parser_ir = _parts(
            "<S> ::= <Expr> {ЭтотУзел = ТекущийЭлемент}\n"
            "<Expr> ::= @НовыйБинарный Левая = <Expr> "
            "Оператор = '+' Правая = <Term> | <Term>\n"
            "<Term> ::= {ЭтотУзел = НовыйТерм} ITEM | "
            "{ЭтотУзел = НовыйТерм} NUMBER",
            ("Expr",),
        )

        generated = _generate(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolved,
            analysis,
            parser_ir,
            canonical_productions=("Expr",),
            entrypoints={"Разобрать": "S"},
        )

        module = generated.module_text
        expression = _function(module, "НеТерминалExpr")
        start = _function(module, "НеТерминалS")
        self.assertEqual(module.count("Функция НеТерминалExpr("), 1)
        self.assertIn("Функция НеТерминалTerm(", module)
        self.assertIn("НеТерминалExpr(ЭтотУзел, ТекущийЭлемент)", start)
        self.assertIn("НеТерминалTerm()", expression)
        self.assertEqual(expression.count("Пока "), 1)
        self.assertNotIn("НомерВариантаПродукции", expression)
        self.assertNotIn("Функция НеТерминал__parsergen_ebnf__", module)
        self.assertIn("Функция ТипТокенаПросмотра(Смещение)", module)

        production_column = next(
            index
            for index, column in enumerate(generated.select_table.columns)
            if column.name == "Продукция"
        )
        matcher_productions = {
            row[production_column]
            for row in generated.select_table.rows
        }
        self.assertIn("Term", matcher_productions)
        self.assertNotIn("Expr", matcher_productions)
        self.assertFalse(
            any(
                str(name).startswith("__parsergen_ebnf__")
                for name in matcher_productions
            )
        )
        self.assertEqual(
            generated.constructor_names,
            ("НовыйТерм", "НовыйБинарный"),
        )

    def test_rejects_canonical_ownership_different_from_parser_ir(self) -> None:
        parsed, resolved, analysis, parser_ir = _parts(
            "<S> ::= <Expr>\n<Expr> ::= ITEM",
            ("Expr",),
        )

        with self.assertRaisesRegex(ValueError, "does not match Parser IR"):
            _generate(
                parsed.source_grammar,
                parsed.lowering,
                parsed.grammar,
                resolved,
                analysis,
                parser_ir,
                canonical_productions=("S",),
                entrypoints={"Разобрать": "S"},
            )

    def test_rejects_synthetic_construct_owned_by_legacy_island(self) -> None:
        parsed, resolved, analysis, parser_ir = _parts(
            "<S> ::= <Expr> <Legacy>\n"
            "<Expr> ::= ITEM\n"
            "<Legacy> ::= tail*",
            ("Expr",),
        )

        with self.assertRaisesRegex(ValueError, "legacy island.*synthetic"):
            _generate(
                parsed.source_grammar,
                parsed.lowering,
                parsed.grammar,
                resolved,
                analysis,
                parser_ir,
                canonical_productions=("Expr",),
                entrypoints={"Разобрать": "S"},
            )


if __name__ == "__main__":
    unittest.main()
