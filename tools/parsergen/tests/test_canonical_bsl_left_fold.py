import re
import unittest

from tests.test_canonical_bsl_codegen import _build, _function


class CanonicalBslLeftFoldTests(unittest.TestCase):
    def test_renders_recognition_left_fold_as_single_loop(self) -> None:
        generated = _build(
            "<Expr> ::= <Expr> '+' <Term> | <Term>\n"
            "<Term> ::= ITEM",
            entrypoints={"Parse": "Expr"},
        )
        function = _function(generated.module_text, "НеТерминалExpr")

        self.assertEqual(function.count("Пока "), 1)
        self.assertEqual(function.count("НеТерминалExpr("), 0)
        self.assertNotIn(
            "Функция НеТерминал__parsergen_ebnf__",
            generated.module_text,
        )
        self.assertLess(
            function.index("НеТерминалTerm()"),
            function.index("Пока "),
        )
        before_loop, loop_body = function.split("Пока ", 1)
        accumulator_match = re.search(
            r"(?m)^\s*(Значение\d+) = Значение\d+;\r?$",
            before_loop,
        )
        assert accumulator_match is not None
        self.assertNotIn(
            f"{accumulator_match.group(1)} = ",
            loop_body.split("КонецЦикла;", 1)[0],
        )
        self.assertIn("Если Не ", function)
        self.assertIn("ВызватьИсключениеСинтаксическаяОшибка", function)

    def test_semantic_fold_binds_left_then_replaces_accumulator(self) -> None:
        generated = _build(
            "<Expr> ::= @НовыйБинарный Левый = <Expr> "
            "Оператор = '+' Правый = <Term> | <Term>\n"
            "<Term> ::= @НовыйТерм Значение = ITEM",
            entrypoints={"Parse": "Expr"},
        )
        function = _function(generated.module_text, "НеТерминалExpr")

        self.assertEqual(
            function.count(
                "ЭлементыМоделиЗапроса.НовыйБинарный(ТекущийТокен)"
            ),
            1,
        )
        base_call = function.index("НеТерминалTerm()")
        loop = function.index("Пока ")
        constructor = function.index(
            "ЭлементыМоделиЗапроса.НовыйБинарный(ТекущийТокен)"
        )
        left_binding = function.index("ЭтотУзел.Левый = ", constructor)
        operator_parse = function.index('Лексема("+")', left_binding)
        right_parse = function.index("НеТерминалTerm()", operator_parse)
        replace_accumulator = function.index(" = ЭтотУзел;", right_parse)

        self.assertLess(base_call, loop)
        self.assertLess(loop, constructor)
        self.assertLess(constructor, left_binding)
        self.assertLess(left_binding, operator_parse)
        self.assertLess(operator_parse, right_parse)
        self.assertLess(right_parse, replace_accumulator)
        self.assertEqual(
            generated.constructor_names,
            ("НовыйБинарный", "НовыйТерм"),
        )

    def test_multiple_recursive_operators_use_disjoint_inner_dispatch(self) -> None:
        function = _function(
            _build(
                "<Expr> ::= <Expr> '+' <Term> | "
                "<Expr> '-' <Term> | <Term>\n"
                "<Term> ::= ITEM",
                entrypoints={"Parse": "Expr"},
            ).module_text,
            "НеТерминалExpr",
        )
        loop = function.split("Пока ", 1)[1].split("КонецЦикла;", 1)[0]

        self.assertIn('Если (ТипТокенаПросмотра(0) = "+") Тогда', loop)
        self.assertIn(
            'ИначеЕсли (ТипТокенаПросмотра(0) = "-") Тогда',
            loop,
        )
        self.assertIn("Иначе", loop)
        self.assertIn("ВызватьИсключениеСинтаксическаяОшибка", loop)

    def test_separate_productions_preserve_precedence_and_parentheses(self) -> None:
        module = _build(
            "<Expr> ::= <Expr> '+' <Term> | <Term>\n"
            "<Term> ::= <Term> '*' <Factor> | <Factor>\n"
            "<Factor> ::= '(' <Expr> ')' | ATOM",
            entrypoints={"Parse": "Expr"},
        ).module_text
        expression = _function(module, "НеТерминалExpr")
        term = _function(module, "НеТерминалTerm")
        factor = _function(module, "НеТерминалFactor")

        self.assertEqual(expression.count("Пока "), 1)
        self.assertIn("НеТерминалTerm()", expression)
        self.assertNotIn("НеТерминалExpr()", expression)
        self.assertEqual(term.count("Пока "), 1)
        self.assertIn("НеТерминалFactor()", term)
        self.assertNotIn("НеТерминалTerm()", term)
        self.assertIn("НеТерминалExpr()", factor)

    def test_base_dispatch_rejects_token_outside_canonical_select(self) -> None:
        function = _function(
            _build(
                "<Expr> ::= <Expr> '+' ITEM | A | B",
                entrypoints={"Parse": "Expr"},
            ).module_text,
            "НеТерминалExpr",
        )
        before_loop = function.split("Пока ", 1)[0]

        self.assertIn('Если (ТипТокенаПросмотра(0) = "A") Тогда', before_loop)
        self.assertIn(
            'ИначеЕсли (ТипТокенаПросмотра(0) = "B") Тогда',
            before_loop,
        )
        self.assertIn("Иначе", before_loop)
        self.assertIn("ВызватьИсключениеСинтаксическаяОшибка", before_loop)


if __name__ == "__main__":
    unittest.main()
