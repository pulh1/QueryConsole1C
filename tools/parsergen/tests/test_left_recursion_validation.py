import unittest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar, parse_source_grammar
from parsergen.left_recursion import classify_direct_left_recursion
from parsergen.resolver import resolve_grammar
from parsergen.source_model import BindingMode
from parsergen.source_validation import validate_source_grammar
from parsergen.validation import validate_grammar


def _source(text: str):
    parsed = parse_source_grammar(text, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    return parsed.grammar


def _validate(text: str):
    return validate_source_grammar(_source(text))


class DirectLeftRecursionClassificationTests(unittest.TestCase):
    def test_classifies_base_and_multiple_recursive_alternatives(self) -> None:
        grammar = _source(
            "<Expr> ::= <Expr> '+' <Term> | <Expr> '-' <Term> | <Term>\n"
            "<Term> ::= ITEM"
        )

        recursion = classify_direct_left_recursion(grammar)["Expr"]

        self.assertEqual(recursion.base_alternatives, (2,))
        self.assertEqual(
            tuple(item.alternative for item in recursion.recursive_alternatives),
            (0, 1),
        )
        self.assertEqual(
            tuple(
                item.self_reference.item_index
                for item in recursion.recursive_alternatives
            ),
            (0, 0),
        )
        self.assertTrue(
            all(
                item.self_reference.property is None
                for item in recursion.recursive_alternatives
            )
        )

    def test_unwraps_scalar_self_binding_after_constructor(self) -> None:
        grammar = _source(
            "<Expr> ::= @НовыйБинарный Левый = <Expr> "
            "Оператор = '+' Правый = <Term> | <Term>\n"
            "<Term> ::= ITEM"
        )

        recursion = classify_direct_left_recursion(grammar)["Expr"]
        reference = recursion.recursive_alternatives[0].self_reference

        self.assertEqual(reference.item_index, 1)
        self.assertEqual(reference.call.name, "Expr")
        self.assertEqual(reference.property, "Левый")
        self.assertIs(reference.binding_mode, BindingMode.SCALAR)

    def test_preserves_parameterized_self_call(self) -> None:
        grammar = _source("<A>(P) ::= <A>(P) x | y")

        reference = classify_direct_left_recursion(grammar)[
            "A"
        ].recursive_alternatives[0].self_reference

        self.assertEqual(reference.call.arguments, ("P",))


class DirectLeftRecursionValidationTests(unittest.TestCase):
    def test_parse_facade_keeps_formal_lr_errors_for_validation_stage(self) -> None:
        parsed = parse_grammar("<A> ::= <A>", "grammar.txt")

        self.assertEqual(parsed.diagnostics, ())
        self.assertIsNotNone(parsed.grammar)
        self.assertIsNotNone(parsed.lowering)
        assert parsed.grammar is not None
        assert parsed.lowering is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(resolution.grammar, 1, ("A",))
        report = validate_grammar(
            parsed.grammar,
            resolution.grammar,
            analysis,
            {"Parse": "A"},
            lowering=parsed.lowering,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["VAL200", "LR200", "LR201", "VAL202"],
        )

    def test_accepts_productive_recognition_and_semantic_forms(self) -> None:
        cases = (
            (
                "<Expr> ::= <Expr> '+' <Term> | <Expr> '-' <Term> | <Term>\n"
                "<Term> ::= ITEM"
            ),
            (
                "<Expr> ::= @НовыйБинарный Левый = <Expr> "
                "Оператор = '+' Правый = <Term> | <Term>\n"
                "<Term> ::= ITEM"
            ),
            "<A>(P) ::= <A>(P) x | y",
        )
        for source in cases:
            with self.subTest(source=source):
                report = _validate(source)
                self.assertEqual(report.diagnostics, ())
                self.assertIn(
                    source.split(">", 1)[0][1:].split("(", 1)[0],
                    report.left_recursions,
                )

    def test_rejects_missing_base_alternative(self) -> None:
        report = _validate("<A> ::= <A> x")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["LR200"],
        )
        self.assertEqual(report.diagnostics[0].span.start.column, 9)

    def test_rejects_empty_nullable_and_nonproductive_suffix(self) -> None:
        cases = (
            ("<A> ::= <A> | x", 9),
            ("<A> ::= <A> <N> | x\n<N> ::= ПУСТО", 9),
            (
                "<A> ::= <A> <N> | x\n<N> ::= <M>\n<M> ::= <N>",
                9,
            ),
        )
        for source, column in cases:
            with self.subTest(source=source):
                report = _validate(source)
                recursion_errors = [
                    item for item in report.diagnostics if item.code == "LR201"
                ]
                self.assertEqual(len(recursion_errors), 1)
                self.assertEqual(
                    recursion_errors[0].span.start.column,
                    column,
                )
                self.assertNotIn(
                    "__parsergen_",
                    recursion_errors[0].message,
                )

    def test_rejects_changed_recursive_arguments(self) -> None:
        report = _validate("<A>(P) ::= <A>(Q) x | y")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["LR202"],
        )
        self.assertEqual(
            report.diagnostics[0].details,
            {
                "production": "A",
                "expected_arguments": ("P",),
                "actual_arguments": ("Q",),
            },
        )

    def test_rejects_missing_or_inconsistent_semantic_left_binding(self) -> None:
        cases = (
            (
                "<A> ::= @НовыйA <A> x | <B>\n<B> ::= ITEM",
                17,
            ),
            (
                "<A> ::= @НовыйA Левый = <A> x | <A> y | <B>\n"
                "<B> ::= ITEM",
                33,
            ),
            (
                "<A> ::= @НовыйA Левые += <A> x | <B>\n<B> ::= ITEM",
                17,
            ),
        )
        for source, column in cases:
            with self.subTest(source=source):
                report = _validate(source)
                semantic_errors = [
                    item for item in report.diagnostics if item.code == "LR203"
                ]
                self.assertEqual(len(semantic_errors), 1)
                self.assertEqual(
                    semantic_errors[0].span.start.column,
                    column,
                )

    def test_requires_semantic_base_to_return_one_value(self) -> None:
        report = _validate(
            "<A> ::= @НовыйA Левый = <A> Оператор = '+' Правый = <T> | ITEM\n"
            "<T> ::= ITEM"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["LR203"],
        )
        self.assertEqual(report.diagnostics[0].span.start.line, 1)

    def test_rejects_arbitrary_action_in_direct_lr_production(self) -> None:
        report = _validate("<A> ::= <A> x {Значение = 1} | y")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["LR204"],
        )
        self.assertEqual(report.diagnostics[0].span.start.column, 15)


if __name__ == "__main__":
    unittest.main()
