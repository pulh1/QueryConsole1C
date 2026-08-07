import unittest

from parsergen.bsl_rendering import (
    bsl_string,
    normalize_newlines,
    validate_bsl_identifier,
)


class BslRenderingTests(unittest.TestCase):
    def test_accepts_latin_and_cyrillic_bsl_identifiers(self) -> None:
        for name in ("ParseQuery2", "РазобратьЗапрос_2", "_Узел"):
            with self.subTest(name=name):
                validate_bsl_identifier(name, "generated symbol")

    def test_rejects_invalid_identifier_with_stable_origin(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "generated symbol '2Node' is not a valid BSL identifier",
        ):
            validate_bsl_identifier("2Node", "generated symbol")

    def test_rejects_reserved_words_from_every_runtime_category(self) -> None:
        names = (
            "Если",
            "Else",
            "Функция",
            "EndProcedure",
            "Новый",
            "Undefined",
            "Область",
            "EndRegion",
        )
        for name in names:
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    ValueError,
                    "is a reserved BSL keyword",
                ):
                    validate_bsl_identifier(name, "generated symbol")

    def test_escapes_quotes_in_bsl_string_literal(self) -> None:
        self.assertEqual(bsl_string('a"b'), '"a""b"')

    def test_normalizes_every_newline_form_to_crlf(self) -> None:
        self.assertEqual(
            normalize_newlines("a\nb\rc\r\nd"),
            "a\r\nb\r\nc\r\nd",
        )


if __name__ == "__main__":
    unittest.main()
