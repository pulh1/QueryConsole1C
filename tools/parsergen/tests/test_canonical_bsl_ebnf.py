import unittest

from tests.test_canonical_bsl_codegen import _build, _function


class CanonicalBslEbnfTests(unittest.TestCase):
    def test_star_uses_one_explicit_iteration_exit_error_decision(self) -> None:
        function = _function(
            _build("<S> ::= ITEM* END").module_text,
            "НеТерминалS",
        )

        self.assertIn("Пока Истина Цикл", function)
        self.assertIn("Прервать;", function)
        self.assertIn("ВызватьИсключениеСинтаксическаяОшибка", function)
        self.assertEqual(function.count("ТипТокенаПросмотра(0)"), 1)
        self.assertIn('Терминал("ITEM");', function)
        self.assertNotIn('= Терминал("ITEM");', function)
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

    def test_optional_rejects_token_outside_body_and_canonical_exit(self) -> None:
        function = _function(
            _build("<S> ::= HEAD? END").module_text,
            "НеТерминалS",
        )

        self.assertIn('ТокенРешения0 = "HEAD"', function)
        self.assertIn('ТокенРешения0 = "END"', function)
        self.assertIn(
            'ВызватьИсключениеСинтаксическаяОшибкаОжидаемыеТокены('
            '"""END"", ""HEAD""");',
            function,
        )
        self.assertIn('Терминал("END")', function)

    def test_repeat_with_multiple_branches_dispatches_inside_loop(self) -> None:
        function = _function(
            _build("<S> ::= (A | B)* END").module_text,
            "НеТерминалS",
        )

        self.assertIn("Пока Истина Цикл", function)
        loop = function.split("Пока ", 1)[1].split("КонецЦикла;", 1)[0]
        self.assertIn('ТокенРешения0 = "A"', loop)
        self.assertIn('ТокенРешения0 = "B"', loop)
        self.assertIn("Прервать;", loop)

    def test_immediate_error_reports_small_canonical_expected_union(self) -> None:
        two_tokens = _function(
            _build("<S> ::= ITEM* END").module_text,
            "НеТерминалS",
        )
        three_tokens_module = _build(
            "<S> ::= ITEM+ ELSE? END"
        ).module_text
        three_tokens = _function(three_tokens_module, "НеТерминалS")

        self.assertIn(
            'ВызватьИсключениеСинтаксическаяОшибкаОжидаемыеТокены('
            '"""END"", ""ITEM""");',
            two_tokens,
        )
        self.assertIn(
            'ВызватьИсключениеСинтаксическаяОшибкаОжидаемыеТокены('
            '"""ELSE"", ""END"", ""ITEM""");',
            three_tokens,
        )
        self.assertIn(
            "Процедура "
            "ВызватьИсключениеСинтаксическаяОшибкаОжидаемыеТокены(",
            three_tokens_module,
        )

    def test_nested_optional_repeat_and_k3_remain_iterative(self) -> None:
        module = _build(
            "<S> ::= ((A | B)? C)* END",
            k=3,
        ).module_text
        function = _function(module, "НеТерминалS")

        self.assertEqual(function.count("Пока "), 1)
        self.assertIn("КоличествоПросматриваемыхСимволов = 3;", module)
        self.assertNotIn("__parsergen_ebnf__", module)
        self.assertNotIn("НомерВариантаПродукции", module)
        self.assertEqual(module.count("Функция НеТерминалS("), 1)


if __name__ == "__main__":
    unittest.main()
