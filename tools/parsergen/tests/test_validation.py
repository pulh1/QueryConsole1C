import ast
import os
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType
import unittest

from parsergen.analysis import compute_analysis
from parsergen.diagnostics import Severity
from parsergen.grammar_parser import parse_grammar
from parsergen.resolver import resolve_grammar
from parsergen.validation import validate_grammar
from tests.grammar_cases import VALIDATION_CASES
from tests.helpers import validate_text


class ValidationPipelineTests(unittest.TestCase):
    def test_exact_validation_cases(self) -> None:
        for name, grammar, entrypoints, k, codes in VALIDATION_CASES:
            with self.subTest(name=name):
                report = validate_text(grammar, entrypoints, k)
                self.assertEqual(
                    tuple(item.code for item in report.diagnostics),
                    codes,
                )

    def test_empty_and_missing_entry_pipelines_do_not_crash(self) -> None:
        cases = (
            ("", {"Разобрать": "S"}, ("VAL100", "VAL101")),
            ("<S> ::= a", {"Разобрать": "Absent"}, ("VAL101",)),
        )
        for grammar, entrypoints, codes in cases:
            with self.subTest(grammar=grammar):
                report = validate_text(grammar, entrypoints, k=2)
                self.assertEqual(
                    tuple(item.code for item in report.diagnostics),
                    codes,
                )

    def test_independent_errors_are_aggregated_in_source_order(self) -> None:
        report = validate_text(
            "<S> ::= <Missing>\n<Unused> ::= <Unused>",
            {"Разобрать": "Absent"},
            k=1,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["VAL101", "RES001", "VAL102", "VAL200", "VAL202"],
        )

    def test_prior_parser_and_resolver_diagnostics_remain_in_one_report(self) -> None:
        report = validate_text(
            "<S>(X, X) ::= <Missing> ПУСТО a",
            {"Разобрать": "S"},
            k=1,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["GR002", "GR004", "RES001"],
        )

    def test_reserved_end_token_is_a_validation_error(self) -> None:
        report = validate_text(
            "#ID_X ::= $\n<S> ::= #ID_X",
            {"Разобрать": "S"},
            k=1,
        )

        self.assertTrue(report.has_errors)
        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["RES004"],
        )


class GraphValidationTests(unittest.TestCase):
    def test_indirect_nonproductive_component_has_one_root_cause_error(self) -> None:
        report = validate_text(
            "<S> ::= <A>\n<A> ::= <B>\n<B> ::= <A>",
            {"Разобрать": "S"},
            k=2,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["VAL200", "VAL202"],
        )
        nonproductive = report.diagnostics[0]
        self.assertEqual(nonproductive.severity, Severity.ERROR)
        self.assertTrue(nonproductive.related)

    def test_direct_and_indirect_left_recursion_report_concrete_paths(self) -> None:
        cases = (
            (
                "direct",
                "<S> ::= <S> a | b",
                ("S", "S"),
            ),
            (
                "indirect",
                "<S> ::= <A> | s\n<A> ::= <S> a | a",
                ("S", "A", "S"),
            ),
        )
        for name, grammar, path in cases:
            with self.subTest(name=name):
                report = validate_text(grammar, {"Разобрать": "S"}, k=2)
                recursion = [
                    item for item in report.diagnostics if item.code == "VAL202"
                ]
                self.assertEqual(len(recursion), 1)
                self.assertEqual(recursion[0].details["path"], path)
                self.assertTrue(recursion[0].related)

    def test_left_recursion_through_nullable_prefix_reports_path(self) -> None:
        report = validate_text(
            "<S> ::= <A> <S> | b\n<A> ::= ПУСТО",
            {"Разобрать": "S"},
            k=2,
        )

        diagnostic = next(
            item for item in report.diagnostics if item.code == "VAL202"
        )
        self.assertEqual(diagnostic.details["path"], ("S", "S"))
        self.assertTrue(diagnostic.related)

    def test_action_does_not_hide_left_recursion(self) -> None:
        report = validate_text(
            "<S> ::= {x = 1} <S> | b",
            {"Разобрать": "S"},
            k=1,
        )

        self.assertIn("VAL202", [item.code for item in report.diagnostics])

    def test_shortest_source_ordered_cycle_is_deterministic(self) -> None:
        grammar = (
            "<S> ::= <A> | <B>\n"
            "<A> ::= <S>\n"
            "<B> ::= <S>"
        )

        for _ in range(3):
            report = validate_text(grammar, {"Разобрать": "S"}, k=2)
            diagnostic = next(
                item for item in report.diagnostics if item.code == "VAL202"
            )
            self.assertEqual(
                diagnostic.details["path"],
                ("S", "A", "S"),
            )

    def test_nullable_subcycle_survives_a_mixed_nullability_scc(self) -> None:
        report = validate_text(
            "<A> ::= <B> | ПУСТО\n"
            "<B> ::= <A> | <C> | ПУСТО\n"
            "<C> ::= <A> x | c",
            {"Разобрать": "A"},
            k=2,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["VAL201", "VAL202"],
        )
        self.assertEqual(
            report.diagnostics[0].details["path"],
            ("A", "B", "A"),
        )

    def test_nullable_self_cycle_survives_a_mixed_nullability_scc(self) -> None:
        report = validate_text(
            "<A> ::= <A> | <C> | ПУСТО\n"
            "<C> ::= <A> x | c",
            {"Разобрать": "A"},
            k=2,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["VAL201", "VAL202"],
        )
        self.assertEqual(
            report.diagnostics[0].details["path"],
            ("A", "A"),
        )

    def test_valid_recursion_after_a_token_has_no_recursion_diagnostic(self) -> None:
        grammars = (
            "<S> ::= a <S> | ПУСТО",
            "<S> ::= <A> | b\n<A> ::= a <S>",
        )
        for grammar in grammars:
            with self.subTest(grammar=grammar):
                report = validate_text(grammar, {"Разобрать": "S"}, k=2)
                self.assertNotIn(
                    "VAL202",
                    [item.code for item in report.diagnostics],
                )


class LookaheadValidationTests(unittest.TestCase):
    def test_consuming_alternative_precedes_nullable_fallback(self) -> None:
        report = validate_text(
            "<S> ::= <A> a\n<A> ::= a | ПУСТО",
            {"Разобрать": "S"},
            k=1,
        )

        self.assertNotIn(
            "LLK202",
            [item.code for item in report.diagnostics],
        )

    def test_reports_every_conflict_with_witness_and_related_span(self) -> None:
        report = validate_text(
            "<S> ::= a b | a c | a d",
            {"Разобрать": "S"},
            k=1,
        )

        conflicts = [
            item for item in report.diagnostics if item.code == "LLK202"
        ]
        self.assertEqual(len(conflicts), 3)
        self.assertEqual(
            {item.details["witness"] for item in conflicts},
            {("a",)},
        )
        self.assertTrue(all(item.details["k"] == 1 for item in conflicts))
        self.assertTrue(all(len(item.related) == 1 for item in conflicts))

    def test_multiple_epsilon_alternatives_are_a_separate_first_error(self) -> None:
        report = validate_text(
            "<S> ::= ПУСТО | {x = 1} ПУСТО",
            {"Разобрать": "S"},
            k=2,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["LLK201", "LLK202"],
        )

    def test_empty_select_is_reported_for_each_reachable_alternative(self) -> None:
        report = validate_text(
            "<S> ::= <A> | s\n"
            "<A> ::= <Dead> <A> | ПУСТО\n"
            "<Dead> ::= <Dead>",
            {"Разобрать": "S"},
            k=2,
        )

        empty_select = [
            item for item in report.diagnostics if item.code == "LLK200"
        ]
        self.assertEqual(len(empty_select), 1)
        self.assertEqual(empty_select[0].span.start.line, 2)

    def test_identifier_overlap_has_exact_conflict_witness(self) -> None:
        report = validate_text(
            "#ID_X ::= ID | ГДЕ\n<S> ::= #ID_X | ГДЕ",
            {"Разобрать": "S"},
            k=1,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["LLK202"],
        )
        self.assertEqual(
            report.diagnostics[0].details["witness"],
            ("ГДЕ",),
        )

    def test_left_recursion_does_not_hide_an_independent_conflict(self) -> None:
        report = validate_text(
            "<S> ::= <S> x | a | a",
            {"Разобрать": "S"},
            k=1,
        )

        self.assertEqual(
            [item.code for item in report.diagnostics],
            ["VAL202", "LLK202"],
        )
        self.assertEqual(
            report.diagnostics[1].details["witness"],
            ("a",),
        )


class ValidationReportTests(unittest.TestCase):
    def test_warnings_do_not_block_generation_but_errors_do(self) -> None:
        warning = validate_text(
            "<S> ::= a\n<Unused> ::= b",
            {"Разобрать": "S"},
            k=1,
        )
        error = validate_text(
            "<S> ::= <Missing>",
            {"Разобрать": "S"},
            k=1,
        )

        self.assertFalse(warning.has_errors)
        self.assertEqual(warning.diagnostics[0].severity, Severity.WARNING)
        self.assertTrue(error.has_errors)
        self.assertEqual(error.diagnostics[0].severity, Severity.ERROR)

    def test_diagnostics_keep_source_path_spans_and_related_locations(self) -> None:
        parsed = parse_grammar(
            "<S> ::= a | a",
            "grammars/query-console.grammar",
        )
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(resolution.grammar, 1, ("S",))

        report = validate_grammar(
            parsed.grammar,
            resolution.grammar,
            analysis,
            MappingProxyType({"Разобрать": "S"}),
            (*parsed.diagnostics, *resolution.diagnostics),
        )

        self.assertEqual([item.code for item in report.diagnostics], ["LLK202"])
        diagnostic = report.diagnostics[0]
        self.assertEqual(
            diagnostic.span.path,
            "grammars/query-console.grammar",
        )
        self.assertEqual(
            diagnostic.related[0].span.path,
            "grammars/query-console.grammar",
        )

    def test_tied_missing_entries_are_stable_across_hash_seeds(self) -> None:
        script = """
from tests.helpers import validate_text

entrypoints = dict({("z", "MZ"), ("a", "MA"), ("q", "MQ")})
report = validate_text("<S> ::= a", entrypoints, k=1)
print(repr(tuple(
    (
        item.code,
        item.severity.value,
        item.span.path,
        item.span.start.offset,
        tuple(
            (
                related.message,
                related.span.path,
                related.span.start.offset,
            )
            for related in item.related
        ),
        tuple(sorted(item.details.items())),
    )
    for item in report.diagnostics
)))
"""
        expected = (
            (
                "VAL101",
                "error",
                "<memory>",
                0,
                (),
                (("entrypoint", "a"), ("production", "MA")),
            ),
            (
                "VAL101",
                "error",
                "<memory>",
                0,
                (),
                (("entrypoint", "q"), ("production", "MQ")),
            ),
            (
                "VAL101",
                "error",
                "<memory>",
                0,
                (),
                (("entrypoint", "z"), ("production", "MZ")),
            ),
        )
        root = Path(__file__).resolve().parents[1]
        for hash_seed in (0, 1, 7, 42, 99):
            environment = os.environ.copy()
            environment["PYTHONHASHSEED"] = str(hash_seed)
            environment["PYTHONPATH"] = os.pathsep.join(
                part
                for part in (
                    str(root / "src"),
                    environment.get("PYTHONPATH"),
                )
                if part
            )
            with self.subTest(hash_seed=hash_seed):
                completed = subprocess.run(
                    [sys.executable, "-c", script],
                    cwd=root,
                    env=environment,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    ast.literal_eval(completed.stdout.strip()),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()

