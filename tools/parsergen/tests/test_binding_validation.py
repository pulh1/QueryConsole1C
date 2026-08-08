import unittest

from parsergen.binding_validation import validate_bindings
from parsergen.grammar_parser import parse_grammar, parse_source_grammar


def _validate(source: str):
    parsed = parse_source_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    return validate_bindings(parsed.grammar)


class BindingValidationTests(unittest.TestCase):
    def test_accepts_scalar_choice_of_terminal_values(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел Операция = ('=' | '<>' | '>=')"
        )

        self.assertEqual(report.diagnostics, ())

    def test_accepts_optional_returned_child_decorator_without_constructor(
        self,
    ) -> None:
        report = _validate(
            "<S> ::= <Base> Операнд => <Postfix>?\n"
            "<Base> ::= @НовыйБаза BASE\n"
            "<Postfix> ::= @НовыйPostfix POSTFIX"
        )

        self.assertEqual(report.diagnostics, ())

    def test_accepts_required_returned_child_decorator_without_constructor(
        self,
    ) -> None:
        report = _validate(
            "<S> ::= <Seed> Тип => <Child>\n"
            "<Seed> ::= @НовыйТип TYPE\n"
            "<Child> ::= @НовыйУзел CHILD"
        )

        self.assertEqual(report.diagnostics, ())

    def test_rejects_returned_child_decorator_without_seed(self) -> None:
        cases = (
            "<S> ::= Операнд => <Postfix>?\n<Postfix> ::= POSTFIX",
            "<S> ::= Операнд => <Postfix>\n<Postfix> ::= POSTFIX",
        )
        for source in cases:
            with self.subTest(source=source):
                report = _validate(source)
                self.assertEqual(
                    [item.code for item in report.diagnostics],
                    ["BIND210"],
                )

    def test_rejects_repeated_returned_child_decorator(self) -> None:
        report = _validate(
            "<S> ::= <Seed> Тип => <Child>*\n"
            "<Seed> ::= TYPE\n<Child> ::= CHILD"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND210"],
        )

    def test_rejects_binding_without_constructor(self) -> None:
        report = _validate("<S> ::= Значение = <A>\n<A> ::= a")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND201"],
        )

    def test_rejects_root_collection_binding_without_constructor(self) -> None:
        report = _validate("<S> ::= += a")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND201"],
        )

    def test_accepts_discard_binding_without_constructor(self) -> None:
        report = _validate("<S> ::= -= <A>\n<A> ::= a")

        self.assertEqual(report.diagnostics, ())

    def test_rejects_binding_before_constructor_and_duplicate_constructor(
        self,
    ) -> None:
        cases = (
            "<S> ::= Значение = a @НовыйУзел",
            "<S> ::= @НовыйУзел @ДругойУзел a",
        )
        for source in cases:
            with self.subTest(source=source):
                report = _validate(source)
                self.assertEqual(
                    [item.code for item in report.diagnostics],
                    ["BIND200"],
                )

    def test_rejects_mixed_scalar_and_collection_modes(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел Значение = a Значение += b"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND202"],
        )

    def test_rejects_duplicate_scalar_on_one_execution_path(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел Значение = a Значение = b"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND203"],
        )

    def test_allows_same_scalar_in_mutually_exclusive_group_branches(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел (Значение = a | Значение = b)"
        )

        self.assertEqual(report.diagnostics, ())

    def test_rejects_scalar_inside_repeat_or_wrapping_multi_value(self) -> None:
        cases = (
            "<S> ::= @НовыйУзел (Значение = a)*",
            "<S> ::= @НовыйУзел Значение = a*",
            "<S> ::= @НовыйУзел Значение = a+",
        )
        for source in cases:
            with self.subTest(source=source):
                report = _validate(source)
                self.assertEqual(
                    [item.code for item in report.diagnostics],
                    ["BIND203"],
                )

    def test_accepts_optional_scalar_and_repeated_collection_append(self) -> None:
        source = (
            "<S> ::= @НовыйУзел Значение = a? "
            "Элементы += b (',' Элементы += b)*"
        )
        report = _validate(source)

        self.assertEqual(report.diagnostics, ())

    def test_accepts_root_collection_append_with_constructor(self) -> None:
        report = _validate(
            "<S> ::= @НовыйСписок += a (',' += a)*"
        )

        self.assertEqual(report.diagnostics, ())

    def test_accepts_collection_extend_with_constructor(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел Элементы *= <Items>\n"
            "<Items> ::= @НовыйСписок += ITEM"
        )

        self.assertEqual(report.diagnostics, ())

    def test_accepts_collection_extend_to_member_path(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел "
            "Операторы[0].ОтборыСКД *= <Items>\n"
            "<Items> ::= @НовыйСписок += ITEM"
        )

        self.assertEqual(report.diagnostics, ())

    def test_rejects_member_path_for_other_binding_modes(self) -> None:
        cases = (
            "<S> ::= @НовыйУзел Вложенный.Элемент = ITEM",
            "<S> ::= @НовыйУзел Вложенный.Элементы += ITEM",
            "<S> ::= @НовыйУзел Вложенный.Флаг := Истина",
        )
        for source in cases:
            with self.subTest(source=source):
                report = _validate(source)
                self.assertEqual(
                    [item.code for item in report.diagnostics],
                    ["BIND211"],
                )

    def test_rejects_collection_extend_without_constructor(self) -> None:
        report = _validate(
            "<S> ::= Элементы *= <Items>\n<Items> ::= ITEM"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND201"],
        )

    def test_accepts_repeated_scalar_concat_with_constructor(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел Путь ~= ID "
            "(Путь ~= '.' Путь ~= ID)*"
        )

        self.assertEqual(report.diagnostics, ())

    def test_rejects_mixed_scalar_and_concat_modes(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел Путь = ID Путь ~= ID"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND202"],
        )

    def test_rejects_concat_of_structural_nonterminal_value(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел Текст ~= <A>\n<A> ::= a"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND207"],
        )

    def test_accepts_repeated_scalar_increment_with_constructor(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел NOT (Количество ++= NOT)*"
        )

        self.assertEqual(report.diagnostics, ())

    def test_rejects_increment_of_structural_nonterminal_value(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел Количество ++= <A>\n<A> ::= a"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND209"],
        )

    def test_rejects_invalid_constant_value(self) -> None:
        report = _validate("<S> ::= @НовыйУзел Флаг := Да")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND204"],
        )

    def test_accepts_supported_literal_and_symbolic_constants(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел "
            "А := Истина Б := Ложь В := Неопределено Г := Null Д := Типы.Все"
        )

        self.assertEqual(report.diagnostics, ())

    def test_accepts_transparent_constant_without_constructor(self) -> None:
        report = _validate("<S> ::= VALUE | := Неопределено")

        self.assertEqual(report.diagnostics, ())

    def test_rejects_transparent_constant_with_other_semantic_result(self) -> None:
        cases = (
            "<S> ::= @НовыйУзел := Неопределено",
            "<S> ::= <A> := Неопределено\n<A> ::= a",
            "<S> ::= := Истина := Ложь",
        )
        for source in cases:
            with self.subTest(source=source):
                report = _validate(source)
                self.assertEqual(
                    [item.code for item in report.diagnostics],
                    ["BIND208"],
                )

    def test_rejects_invalid_transparent_constant(self) -> None:
        report = _validate("<S> ::= := Да")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND204"],
        )

    def test_rejects_legacy_action_mixed_with_canonical_directives(self) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел {ЭтотУзел = ЧтоТо} a"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND205"],
        )

    def test_rejects_ambiguous_transparent_alternative_in_canonical_production(
        self,
    ) -> None:
        report = _validate(
            "<S> ::= @НовыйУзел a | <A> <B>\n<A> ::= a\n<B> ::= b"
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["BIND206"],
        )

    def test_parse_facade_prefers_binding_error_to_temporary_lowering_gate(
        self,
    ) -> None:
        result = parse_grammar("<S> ::= Значение = a")

        self.assertEqual(
            [item.code for item in result.diagnostics],
            ["BIND201"],
        )


if __name__ == "__main__":
    unittest.main()
