from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
import tempfile
import unittest

from parsergen.analysis import compute_analysis
from parsergen.cli import compile_from_config
from parsergen.config import ParsergenConfig
from parsergen.grammar_parser import parse_grammar
from parsergen.resolver import resolve_grammar
from parsergen.validation import validate_grammar


def _validate(source: str, k: int = 1):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, k, ("S",))
    return validate_grammar(
        parsed.grammar,
        resolved.grammar,
        analysis,
        {"Parse": "S"},
        lowering=parsed.lowering,
    )


def _contains_synthetic(value: object) -> bool:
    if isinstance(value, str):
        return "__parsergen_ebnf__" in value
    if isinstance(value, Mapping):
        return any(
            _contains_synthetic(key) or _contains_synthetic(item)
            for key, item in value.items()
        )
    if isinstance(value, (tuple, list, set, frozenset)):
        return any(_contains_synthetic(item) for item in value)
    return False


class EbnfValidationTests(unittest.TestCase):
    def test_compilation_uses_source_mapping_for_canonical_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            grammar = root / "grammar.txt"
            grammar.write_text("<S> ::= 'a'* 'a'", encoding="utf-8")
            compilation = compile_from_config(
                ParsergenConfig(
                    grammar,
                    root / "target",
                    1,
                    MappingProxyType({"Parse": "S"}),
                )
            )

        conflict = next(
            item
            for item in compilation.report.diagnostics
            if item.code == "LLK202"
        )
        self.assertIsNotNone(compilation.source_grammar)
        self.assertIsNotNone(compilation.lowering)
        self.assertEqual(conflict.span.start.column, 9)
        self.assertEqual(conflict.span.end.column, 13)
        self.assertEqual(len(conflict.related), 2)
        self.assertFalse(_contains_synthetic(conflict.details))

    def test_accepts_disjoint_repeat_body_and_exit(self) -> None:
        report = _validate("<S> ::= 'a'* 'b'")

        self.assertEqual(report.diagnostics, ())

    def test_repeat_body_and_exit_select_must_be_disjoint(self) -> None:
        report = _validate("<S> ::= 'a'* 'a'")

        conflicts = [
            item for item in report.diagnostics if item.code == "LLK202"
        ]
        self.assertEqual(len(conflicts), 1)
        conflict = conflicts[0]
        self.assertEqual(conflict.details["witness"], ("a",))
        self.assertEqual(conflict.span.start.column, 9)
        self.assertEqual(conflict.span.end.column, 13)
        self.assertEqual(len(conflict.related), 2)
        self.assertFalse(_contains_synthetic(conflict.message))
        self.assertFalse(_contains_synthetic(conflict.details))

    def test_optional_body_and_exit_select_must_be_disjoint(self) -> None:
        report = _validate("<S> ::= 'a'? 'a'")

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["LLK202"],
        )

    def test_group_alternative_order_does_not_resolve_overlap(self) -> None:
        first = _validate("<S> ::= (a | #ID_A)* b\n#ID_A ::= a")
        second = _validate("<S> ::= (#ID_A | a)* b\n#ID_A ::= a")

        for report in (first, second):
            with self.subTest(report=report):
                conflicts = [
                    item
                    for item in report.diagnostics
                    if item.code == "LLK202"
                ]
                self.assertEqual(len(conflicts), 1)
                self.assertEqual(conflicts[0].details["witness"], ("a",))
                self.assertFalse(_contains_synthetic(conflicts[0].details))

    def test_unreachable_source_production_does_not_expose_synthetic_helper(
        self,
    ) -> None:
        report = _validate("<S> ::= a\n<Unused> ::= b*")

        warnings = [
            item for item in report.diagnostics if item.code == "VAL102"
        ]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].details["production"], "Unused")
        self.assertFalse(_contains_synthetic(warnings[0].message))
        self.assertFalse(_contains_synthetic(warnings[0].details))

    def test_nonproductive_and_cycle_diagnostics_hide_synthetic_paths(
        self,
    ) -> None:
        report = _validate("<S> ::= (<S>)")

        self.assertTrue(report.has_errors)
        self.assertIn(
            "VAL200",
            [item.code for item in report.diagnostics],
        )
        self.assertIn(
            "VAL202",
            [item.code for item in report.diagnostics],
        )
        for diagnostic in report.diagnostics:
            self.assertFalse(_contains_synthetic(diagnostic.message))
            self.assertFalse(_contains_synthetic(diagnostic.details))


if __name__ == "__main__":
    unittest.main()
