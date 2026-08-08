import unittest

from tests.test_canonical_bsl_codegen import _build, _function


class CanonicalBslBindingTests(unittest.TestCase):
    def test_reserved_keyword_is_valid_as_bound_member_name(self) -> None:
        function = _function(
            _build(
                "<S> ::= @НовыйУзел Иначе = VALUE"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn("ЭтотУзел.Иначе = Значение1;", function)

    def test_renders_constructor_scalar_and_constant_assignments(self) -> None:
        generated = _build(
            "#ID_Name ::= ID\n"
            "<S> ::= @НовыйУзел Значение = <A> "
            "Флаг := Истина Пустое := Null Тип := Типы.Все\n"
            "<A> ::= @НовыйДочерний Имя = #ID_Name"
        )

        function = _function(generated.module_text, "НеТерминалS")
        self.assertEqual(
            function.count(
                "ЭлементыМоделиЗапроса."
                "НовыйУзел(ТекущийТокен)"
            ),
            1,
        )
        self.assertIn("Значение1 = НеТерминалA();", function)
        self.assertIn("ЭтотУзел.Значение = Значение1;", function)
        self.assertIn("ЭтотУзел.Флаг = Истина;", function)
        self.assertIn("ЭтотУзел.Пустое = Null;", function)
        self.assertIn("ЭтотУзел.Тип = Типы.Все;", function)
        self.assertIn("РезультатПродукции = ЭтотУзел;", function)
        self.assertEqual(
            generated.constructor_names,
            ("НовыйУзел", "НовыйДочерний"),
        )

    def test_root_list_preserves_empty_slots_with_transparent_constant(self) -> None:
        function = _function(
            _build(
                "<S> ::= @НовыйСписок += (<A> | := Неопределено) "
                "(',' += (<A> | := Неопределено))* END\n"
                "<A> ::= ITEM",
                k=2,
            ).module_text,
            "НеТерминалS",
        )

        self.assertEqual(function.count("ЭтотУзел.Добавить("), 2)
        self.assertGreaterEqual(function.count("= Неопределено;"), 3)
        self.assertEqual(function.count("Пока "), 1)

    def test_optional_scalar_assigns_present_or_undefined(self) -> None:
        function = _function(
            _build(
                "<S> ::= @НовыйУзел Значение = HEAD? END"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn('Значение1 = Терминал("HEAD");', function)
        self.assertIn("ЭтотУзел.Значение = Значение1;", function)
        self.assertIn("ЭтотУзел.Значение = Неопределено;", function)

    def test_separator_repeat_appends_only_item_values(self) -> None:
        function = _function(
            _build(
                "<S> ::= @НовыйСписок Элементы += ITEM "
                "(',' Элементы += ITEM)* END",
                k=2,
            ).module_text,
            "НеТерминалS",
        )

        self.assertEqual(function.count("ЭтотУзел.Элементы.Добавить("), 2)
        loop = function.split("Пока ", 1)[1].split("КонецЦикла;", 1)[0]
        self.assertIn('Лексема(",");', loop)
        self.assertNotIn('= Лексема(",");', loop)
        self.assertIn('Значение2 = Терминал("ITEM");', loop)
        self.assertIn("ЭтотУзел.Элементы.Добавить(Значение2);", loop)

    def test_root_collection_binding_appends_to_constructed_value(self) -> None:
        function = _function(
            _build(
                "<S> ::= @НовыйСписок += ITEM (',' += ITEM)* END",
                k=2,
            ).module_text,
            "НеТерминалS",
        )

        self.assertEqual(function.count("ЭтотУзел.Добавить("), 2)
        self.assertNotIn("ЭтотУзел..Добавить(", function)

    def test_scalar_concat_accumulates_terminal_values_inside_loop(self) -> None:
        function = _function(
            _build(
                "#ID_Name ::= ID\n"
                "<S> ::= @НовыйУзел Путь ~= #ID_Name "
                "(Путь ~= '.' Путь ~= #ID_Name)* END",
                k=2,
            ).module_text,
            "НеТерминалS",
        )

        self.assertEqual(
            function.count("ЭтотУзел.Путь = ЭтотУзел.Путь +"),
            3,
        )
        loop = function.split("Пока ", 1)[1].split("КонецЦикла;", 1)[0]
        self.assertIn('= Лексема(".");', loop)
        self.assertIn('= Идентификатор("ID_Name");', loop)

    def test_scalar_increment_consumes_token_and_increments_inside_loop(self) -> None:
        function = _function(
            _build(
                "<S> ::= @НовыйУзел NOT (Количество ++= NOT)* END",
                k=2,
            ).module_text,
            "НеТерминалS",
        )

        loop = function.split("Пока ", 1)[1].split("КонецЦикла;", 1)[0]
        self.assertIn('Терминал("NOT");', loop)
        self.assertNotIn('= Терминал("NOT");', loop)
        self.assertIn(
            "ЭтотУзел.Количество = ЭтотУзел.Количество + 1;",
            loop,
        )

    def test_captures_terminal_identifier_and_constant_values(self) -> None:
        function = _function(
            _build(
                "#ID_Name ::= ID\n"
                "<S> ::= @НовыйУзел Ключ = KEY "
                "Имя = #ID_Name Число = &NUMBER"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn('Значение1 = Терминал("KEY");', function)
        self.assertIn('Значение2 = Идентификатор("ID_Name");', function)
        self.assertIn('Значение3 = Константа("NUMBER");', function)
        self.assertIn("ЭтотУзел.Ключ = Значение1;", function)
        self.assertIn("ЭтотУзел.Имя = Значение2;", function)
        self.assertIn("ЭтотУзел.Число = Значение3;", function)

    def test_grouped_value_dispatch_uses_recorded_branch_result(self) -> None:
        function = _function(
            _build(
                "<S> ::= @НовыйУзел Значение = (<A> | <B>)\n"
                "<A> ::= @НовыйA A\n<B> ::= @НовыйB B"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn('Если (ТипТокенаПросмотра(0) = "A") Тогда', function)
        self.assertIn('ИначеЕсли (ТипТокенаПросмотра(0) = "B") Тогда', function)
        self.assertIn("Значение1 = НеТерминалA();", function)
        self.assertIn("Значение2 = Значение1;", function)
        self.assertIn("Значение3 = НеТерминалB();", function)
        self.assertIn("Значение2 = Значение3;", function)
        self.assertIn("ЭтотУзел.Значение = Значение2;", function)

    def test_grouped_value_keeps_suffix_after_selected_result(self) -> None:
        function = _function(
            _build(
                "<S> ::= @НовыйУзел Значение = "
                "(<A> ',' | <B> ';') END\n"
                "<A> ::= @НовыйA A\n<B> ::= @НовыйB B",
                k=2,
            ).module_text,
            "НеТерминалS",
        )

        first_branch = function.split("Если ", 1)[1].split(
            "ИначеЕсли ",
            1,
        )[0]
        self.assertLess(
            first_branch.index("Значение1 = НеТерминалA();"),
            first_branch.index('Лексема(",");'),
        )
        self.assertIn("Значение2 = Значение1;", first_branch)
        self.assertIn("ЭтотУзел.Значение = Значение2;", function)


if __name__ == "__main__":
    unittest.main()
