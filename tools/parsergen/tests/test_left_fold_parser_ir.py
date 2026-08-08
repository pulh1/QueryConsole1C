from dataclasses import replace
import unittest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import (
    BindScalar,
    ConstructNode,
    FoldLeftValue,
    LeftFold,
    ParseSymbol,
    build_parser_ir,
)
from parsergen.resolver import resolve_grammar


def _parts(source: str, k: int = 1):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    assert parsed.grammar is not None
    resolution = resolve_grammar(parsed.grammar)
    assert resolution.diagnostics == ()
    assert resolution.grammar is not None
    analysis = compute_analysis(resolution.grammar, k, ("Expr",))
    return parsed, resolution.grammar, analysis


def _build(source: str, k: int = 1):
    parsed, resolved, analysis = _parts(source, k)
    return build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved,
        analysis,
    )


def _expr_fold(parser_ir) -> LeftFold:
    production = next(
        item for item in parser_ir.productions if item.name == "Expr"
    )
    assert len(production.alternatives) == 1
    operation = production.alternatives[0].operations[0]
    assert isinstance(operation, LeftFold)
    return operation


class LeftFoldParserIrTests(unittest.TestCase):
    def test_builds_recognition_left_fold_without_runtime_self_call(self) -> None:
        parser_ir = _build(
            "<Expr> ::= <Expr> '+' <Term> | <Term>\n"
            "<Term> ::= ITEM"
        )

        fold = _expr_fold(parser_ir)
        self.assertIsNone(fold.base_decision)
        self.assertEqual(len(fold.base_branches), 1)
        self.assertEqual(fold.base_branches[0].alternative, 1)
        self.assertEqual(fold.base_branches[0].result_index, 0)
        self.assertEqual(len(fold.recursive_branches), 1)
        recursive = fold.recursive_branches[0]
        self.assertEqual(recursive.alternative, 1)
        self.assertFalse(
            any(
                isinstance(operation, ParseSymbol)
                and getattr(operation.symbol, "name", None) == "Expr"
                for operation in recursive.operations
            )
        )
        self.assertEqual(fold.exit_alternative, 2)
        self.assertIn("left_fold_tail", fold.recursive_decision.production)
        self.assertNotIn(
            fold.recursive_decision.production,
            [item.name for item in parser_ir.productions],
        )

    def test_replaces_scalar_self_binding_with_fold_left_value(self) -> None:
        fold = _expr_fold(
            _build(
                "<Expr> ::= @НовыйБинарный Левый = <Expr> "
                "Оператор = '+' Правый = <Term> | <Term>\n"
                "<Term> ::= ITEM"
            )
        )

        operations = fold.recursive_branches[0].operations
        self.assertEqual(
            [type(item) for item in operations],
            [ConstructNode, BindScalar, BindScalar, BindScalar],
        )
        left = operations[1]
        assert isinstance(left, BindScalar)
        self.assertEqual(left.property, "Левый")
        self.assertIsInstance(left.value, FoldLeftValue)
        operator = operations[2]
        right = operations[3]
        assert isinstance(operator, BindScalar)
        assert isinstance(right, BindScalar)
        self.assertEqual(operator.property, "Оператор")
        self.assertEqual(right.property, "Правый")

    def test_keeps_separate_base_and_recursive_decisions(self) -> None:
        fold = _expr_fold(
            _build(
                "<Expr> ::= <Expr> '+' <Term> | <Expr> '-' <Term> | A | B\n"
                "<Term> ::= ITEM"
            )
        )

        self.assertIsNotNone(fold.base_decision)
        assert fold.base_decision is not None
        self.assertEqual(fold.base_decision.production, "Expr")
        self.assertEqual(
            tuple(branch.alternative for branch in fold.base_branches),
            (1, 2),
        )
        self.assertEqual(
            tuple(branch.alternative for branch in fold.recursive_branches),
            (1, 2),
        )
        self.assertEqual(fold.exit_alternative, 3)

    def test_recognition_only_terminal_base_may_have_no_semantic_result(
        self,
    ) -> None:
        fold = _expr_fold(_build("<Expr> ::= <Expr> '+' ITEM | BASE"))

        self.assertIsNone(fold.base_branches[0].result_index)
        self.assertIsNone(fold.recursive_branches[0].result_index)

    def test_rejects_semantic_fold_with_valueless_base(self) -> None:
        parsed, resolved, analysis = _parts(
            "<Expr> ::= @НовыйБинарный Левый = <Expr> "
            "Оператор = '+' Правый = <Term> | BASE\n"
            "<Term> ::= ITEM"
        )

        with self.assertRaisesRegex(ValueError, "validation errors"):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved,
                analysis,
            )

    def test_rejects_forged_left_recursion_sidecar(self) -> None:
        parsed, resolved, analysis = _parts(
            "<Expr> ::= <Expr> '+' <Term> | <Term>\n"
            "<Term> ::= ITEM"
        )
        forged = replace(parsed.lowering, left_recursions=())

        with self.assertRaisesRegex(ValueError, "source grammar"):
            build_parser_ir(
                parsed.source_grammar,
                forged,
                resolved,
                analysis,
            )

    def test_rejects_overlapping_recursive_select(self) -> None:
        parsed, resolved, analysis = _parts(
            "<Expr> ::= <Expr> x y | <Expr> x z | BASE",
            k=1,
        )

        with self.assertRaisesRegex(ValueError, "overlapping canonical SELECT"):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved,
                analysis,
            )


if __name__ == "__main__":
    unittest.main()
