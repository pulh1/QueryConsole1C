import unittest

from parsergen.binding_validation import validate_bindings
from parsergen.grammar_parser import parse_grammar, parse_source_grammar


def _validate(source: str):
    parsed = parse_source_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    return validate_bindings(parsed.grammar)


class BindingValidationTests(unittest.TestCase):
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
