import unittest

from tests.test_canonical_bsl_codegen import _build, _function


class CanonicalBslEbnfTests(unittest.TestCase):
    def test_star_is_one_loop_with_canonical_exit_validation(self) -> None:
        function = _function(
            _build("<S> ::= ITEM*").module_text,
            "НеТерминалS",
        )

        self.assertEqual(function.count("Пока "), 1)
        self.assertIn(
            'Пока (ТипТокенаПросмотра(0) = "ITEM") Цикл',
            function,
        )
        self.assertIn('Значение1 = Терминал("ITEM");', function)
        self.assertIn("Если Не (ТипТокенаПросмотра(0) = Неопределено) Тогда", function)
        self.assertNotIn("НеТерминал__parsergen_ebnf__", function)

    def test_plus_parses_first_item_and_then_uses_one_loop(self) -> None:
        function = _function(
            _build("<S> ::= ITEM+").module_text,
            "НеТерминалS",
        )

        self.assertEqual(function.count("Пока "), 1)
        self.assertEqual(function.count('Терминал("ITEM")'), 2)
        self.assertLess(
            function.index('Терминал("ITEM")'),
            function.index("Пока "),
        )

    def test_separator_repeat_keeps_separator_inside_loop(self) -> None:
        function = _function(
            _build("<S> ::= ITEM (',' ITEM)* END", k=2).module_text,
            "НеТерминалS",
        )

        loop = function.split("Пока ", 1)[1].split("КонецЦикла;", 1)[0]
        self.assertIn('Лексема(",")', loop)
        self.assertIn('Терминал("ITEM")', loop)
        self.assertLess(loop.index('Лексема(",")'), loop.index('Терминал("ITEM")'))

    def test_optional_has_explicit_consume_exit_and_error_paths(self) -> None:
        function = _function(
            _build("<S> ::= HEAD? END").module_text,
            "НеТерминалS",
        )

        self.assertIn('Если (ТипТокенаПросмотра(0) = "HEAD") Тогда', function)
        self.assertIn('ИначеЕсли (ТипТокенаПросмотра(0) = "END") Тогда', function)
        self.assertIn("Иначе", function)
        self.assertIn('ВызватьИсключениеСинтаксическаяОшибка("S")', function)

    def test_repeat_with_multiple_branches_dispatches_inside_loop(self) -> None:
        function = _function(
            _build("<S> ::= (A | B)* END").module_text,
            "НеТерминалS",
        )

        self.assertIn(
            'Пока ((ТипТокенаПросмотра(0) = "A") Или '
            '(ТипТокенаПросмотра(0) = "B")) Цикл',
            function,
        )
        loop = function.split("Пока ", 1)[1].split("КонецЦикла;", 1)[0]
        self.assertIn('Если (ТипТокенаПросмотра(0) = "A") Тогда', loop)
        self.assertIn('ИначеЕсли (ТипТокенаПросмотра(0) = "B") Тогда', loop)

    def test_nested_optional_repeat_and_k3_remain_iterative(self) -> None:
        module = _build(
            "<S> ::= ((A | B)? C)* END",
            k=3,
        ).module_text
        function = _function(module, "НеТерминалS")

        self.assertEqual(function.count("Пока "), 1)
        self.assertIn("ТипТокенаПросмотра(2)", function)
        self.assertNotIn("__parsergen_ebnf__", module)
        self.assertNotIn("НомерВариантаПродукции", module)
        self.assertEqual(module.count("Функция НеТерминалS("), 1)


if __name__ == "__main__":
    unittest.main()
