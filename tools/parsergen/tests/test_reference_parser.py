from __future__ import annotations

from collections import Counter
import unittest
from pathlib import Path

from parsergen.artifacts import render_artifacts
from parsergen.cli import compile_from_config, generate_from_compilation
from parsergen.config import load_config
from parsergen.grammar_parser import parse_grammar
from parsergen.value_table_codec import (
    ColumnKind,
    ValueColumn,
    ValueTable,
    decode_value_table,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
GRAMMAR = PACKAGE_ROOT / "grammar/query-language.grammar"
REFERENCE = Path(__file__).parent / "fixtures/reference_parser"
def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def first_text_difference(expected: str, actual: str) -> str:
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    for line_number, (expected_line, actual_line) in enumerate(
        zip(expected_lines, actual_lines),
        start=1,
    ):
        if expected_line != actual_line:
            return (
                f"first difference at line {line_number}:\n"
                f"reference: {expected_line!r}\n"
                f"generated: {actual_line!r}"
            )
    return (
        "line counts differ: "
        f"reference={len(expected_lines)}, generated={len(actual_lines)}"
    )


class ReferenceParserTests(unittest.TestCase):
    def assert_value_table_equivalent(
        self,
        actual: ValueTable,
        expected: ValueTable,
    ) -> None:
        self.assertEqual(actual.columns, expected.columns)
        self.assertEqual(Counter(actual.rows), Counter(expected.rows))

    def test_value_table_oracle_detects_duplicate_row_count(self) -> None:
        columns = (ValueColumn("Тип", ColumnKind.STRING),)
        expected = ValueTable(columns, (("ID",), ("ID",)))
        actual = ValueTable(columns, (("ID",),))

        with self.assertRaises(AssertionError):
            self.assert_value_table_equivalent(actual, expected)

    def test_full_extended_grammar_matches_reference_parser(self) -> None:
        parsed = parse_grammar(
            GRAMMAR.read_text(encoding="utf-8"),
            str(GRAMMAR),
        )
        self.assertIsNotNone(parsed.grammar)
        assert parsed.grammar is not None
        self.assertEqual(len(parsed.grammar.productions), 156)
        self.assertEqual(
            sum(
                len(production.alternatives)
                for production in parsed.grammar.productions
            ),
            334,
        )

        config = load_config(REPOSITORY_ROOT / "parsergen.toml")
        compilation = compile_from_config(config)
        generated = generate_from_compilation(config, compilation)
        artifacts = render_artifacts(generated)
        reference_module = (REFERENCE / "ObjectModule.bsl").read_text(
            encoding="utf-8"
        )
        expected_module = normalize_newlines(reference_module)
        actual_module = normalize_newlines(
            artifacts.object_module.decode("utf-8")
        )
        self.assertEqual(
            actual_module,
            expected_module,
            first_text_difference(expected_module, actual_module),
        )

        generated_select = decode_value_table(
            artifacts.select_template.decode("utf-8")
        )
        reference_select = decode_value_table(
            (
                REFERENCE
                / "Templates/ТаблицаПервыхСимволовВариантов/Template.txt"
            ).read_text(encoding="utf-8")
        )
        self.assert_value_table_equivalent(generated_select, reference_select)

        generated_identifiers = decode_value_table(
            artifacts.identifier_template.decode("utf-8")
        )
        reference_identifiers = decode_value_table(
            (
                REFERENCE
                / "Templates/ОпределенияИдентификаторов/Template.txt"
            ).read_text(encoding="utf-8")
        )
        self.assert_value_table_equivalent(
            generated_identifiers,
            reference_identifiers,
        )


if __name__ == "__main__":
    unittest.main()
