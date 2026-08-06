import ast
import gc
import os
from pathlib import Path
import subprocess
import sys
import unittest

from parsergen.analysis import (
    EPSILON,
    compute_prefix_analysis,
    concat_languages,
    concat_words,
)
from tests.grammar_factory import (
    generated_resolved_grammar,
    permuted_resolved_grammar,
    renamed_resolved_grammar,
)
from tests.grammar_cases import FIRST_CASES, NULLABLE_CASES
from tests.helpers import resolved
from tests.oracles import oracle_prefix_analysis


class LanguageOperationTests(unittest.TestCase):
    def test_concat_words_truncates_to_k(self) -> None:
        self.assertEqual(concat_words(("a", "b"), ("c", "d"), 3), ("a", "b", "c"))

    def test_concat_words_rejects_non_positive_k(self) -> None:
        for k in (0, -1):
            with self.subTest(k=k):
                with self.assertRaisesRegex(ValueError, "k must be at least 1"):
                    concat_words(EPSILON, EPSILON, k)

    def test_concat_languages_forms_truncated_cartesian_product(self) -> None:
        self.assertEqual(
            concat_languages(
                {("a",), ("b",)},
                {("c",), ("d",)},
                1,
            ),
            frozenset({("a",), ("b",)}),
        )

    def test_concat_languages_preserves_empty_language(self) -> None:
        self.assertEqual(concat_languages(set(), {EPSILON}, 2), frozenset())
        self.assertEqual(concat_languages({EPSILON}, set(), 2), frozenset())

    def test_concat_languages_rejects_non_positive_k_with_empty_operand(self) -> None:
        operands = (
            (set(), {EPSILON}),
            ({EPSILON}, set()),
        )
        for k in (0, -1):
            for left, right in operands:
                with self.subTest(k=k, left=left, right=right):
                    with self.assertRaisesRegex(ValueError, "k must be at least 1"):
                        concat_languages(left, right, k)


class PrefixAnalysisTests(unittest.TestCase):
    def test_nullable_cases(self) -> None:
        for name, grammar, nullable in NULLABLE_CASES:
            with self.subTest(name=name):
                result = compute_prefix_analysis(resolved(grammar), 2)
                self.assertEqual(result.nullable, frozenset(nullable))

    def test_first_cases(self) -> None:
        for name, grammar, k, production, expected in FIRST_CASES:
            with self.subTest(name=name, k=k):
                result = compute_prefix_analysis(resolved(grammar), k)
                self.assertEqual(result.first[production], frozenset(expected))

    def test_analysis_rejects_non_positive_k(self) -> None:
        grammar = resolved("<S> ::= a")
        for k in (0, -1):
            with self.subTest(k=k):
                with self.assertRaisesRegex(ValueError, "k must be at least 1"):
                    compute_prefix_analysis(grammar, k)

    def test_continuations_cover_recursive_and_saturated_edges(self) -> None:
        cases = (
            (
                "mutual recursion without a base",
                "<S> ::= <A>\n<A> ::= <S>",
                4,
                "S",
                set(),
            ),
            (
                "nullable recursion",
                "<S> ::= <A> b\n<A> ::= <A> | ПУСТО",
                2,
                "S",
                {("b",)},
            ),
            (
                "short incomplete prefix is later completed",
                "<S> ::= <A> c\n<A> ::= <B>\n<B> ::= a <B> | a",
                2,
                "S",
                {("a", "a"), ("a", "c")},
            ),
            (
                "saturated child needs no completion",
                "<S> ::= <A> tail\n"
                "<A> ::= a b <Tail>\n"
                "<Tail> ::= <Tail> | done",
                2,
                "S",
                {("a", "b")},
            ),
            (
                "nullable suffix after saturation",
                "<S> ::= <A> <N>\n<A> ::= a b\n<N> ::= <N> | ПУСТО",
                2,
                "S",
                {("a", "b")},
            ),
            (
                "duplicates and repeated references",
                "<S> ::= <A> <A> | <A> <A>\n<A> ::= a | a | ПУСТО",
                2,
                "S",
                {(), ("a",), ("a", "a")},
            ),
            (
                "overlapping identifier class and explicit token",
                "#ID_X ::= ID\n#ID_X ::= WORD\n"
                "<S> ::= #ID_X tail | ID end",
                2,
                "S",
                {("ID", "tail"), ("WORD", "tail"), ("ID", "end")},
            ),
        )
        for name, source, k, production, expected in cases:
            with self.subTest(name=name):
                result = compute_prefix_analysis(resolved(source), k)
                self.assertEqual(result.first[production], frozenset(expected))

    def test_long_recursive_chain_reaches_late_base(self) -> None:
        chain_length = 160
        source = "\n".join(
            (
                f"<N{index}> ::= <N{index + 1}>"
                if index + 1 < chain_length
                else f"<N{index}> ::= late"
            )
            for index in range(chain_length)
        )
        result = compute_prefix_analysis(resolved(source), 4)
        self.assertEqual(result.first["N0"], frozenset({("late",)}))


class GeneratedPrefixAnalysisTests(unittest.TestCase):
    def test_work_list_matches_full_rescan_oracle_for_600_cases(self) -> None:
        for seed in range(200):
            grammar = generated_resolved_grammar(seed)
            for k in (1, 2, 3):
                with self.subTest(seed=seed, k=k):
                    optimized = compute_prefix_analysis(grammar, k)
                    oracle_nullable, oracle_first = oracle_prefix_analysis(grammar, k)
                    self.assertEqual(optimized.nullable, oracle_nullable)
                    self.assertEqual(optimized.first, oracle_first)
                    self.assertTrue(
                        all(
                            len(word) <= k
                            for language in optimized.first.values()
                            for word in language
                        )
                    )

    def test_continuations_match_independent_oracle_for_100_k4_cases(self) -> None:
        for seed in range(100):
            grammar = generated_resolved_grammar(seed + 20_000)
            with self.subTest(seed=seed):
                optimized = compute_prefix_analysis(grammar, 4)
                oracle_nullable, oracle_first = oracle_prefix_analysis(grammar, 4)
                self.assertEqual(optimized.nullable, oracle_nullable)
                self.assertEqual(optimized.first, oracle_first)

    def test_permuting_productions_preserves_analysis(self) -> None:
        for seed in range(200):
            grammar = generated_resolved_grammar(seed)
            permuted = permuted_resolved_grammar(grammar, seed + 10_000)
            for k in (1, 2, 3):
                with self.subTest(seed=seed, k=k):
                    original = compute_prefix_analysis(grammar, k)
                    transformed = compute_prefix_analysis(permuted, k)
                    self.assertEqual(transformed.nullable, original.nullable)
                    self.assertEqual(transformed.first, original.first)

    def test_consistent_nonterminal_rename_preserves_analysis(self) -> None:
        for seed in range(200):
            grammar = generated_resolved_grammar(seed)
            renamed, renames = renamed_resolved_grammar(grammar)
            for k in (1, 2, 3):
                with self.subTest(seed=seed, k=k):
                    original = compute_prefix_analysis(grammar, k)
                    transformed = compute_prefix_analysis(renamed, k)
                    self.assertEqual(
                        transformed.nullable,
                        frozenset(renames[name] for name in original.nullable),
                    )
                    self.assertEqual(
                        transformed.first,
                        {
                            renames[name]: language
                            for name, language in original.first.items()
                        },
                    )

    def test_repeated_analysis_is_deterministic(self) -> None:
        for seed in range(200):
            grammar = generated_resolved_grammar(seed)
            for k in (1, 2, 3):
                with self.subTest(seed=seed, k=k):
                    self.assertEqual(
                        compute_prefix_analysis(grammar, k),
                        compute_prefix_analysis(grammar, k),
                    )

    def test_repeated_recursive_analysis_does_not_require_cyclic_gc(self) -> None:
        grammar = resolved(
            "<S> ::= <A> <A>\n"
            "<A> ::= a <A> | <B> | ПУСТО\n"
            "<B> ::= b <A> | ПУСТО"
        )
        expected = compute_prefix_analysis(grammar, 4)
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            for _ in range(25):
                self.assertEqual(compute_prefix_analysis(grammar, 4), expected)
        finally:
            if gc_was_enabled:
                gc.enable()

    def test_complete_result_is_stable_across_python_hash_seeds(self) -> None:
        script = """
from tests.helpers import resolved
from parsergen.analysis import compute_prefix_analysis

grammar = resolved(
    "<N0> ::= ПУСТО | b <N1> | a <N0> <N1>\\n"
    "<N1> ::= ПУСТО | <N0> b a | ПУСТО"
)
result = compute_prefix_analysis(grammar, 2)
print(repr((
    tuple(sorted(result.nullable)),
    tuple(
        (name, tuple(sorted(result.first[name])))
        for name in grammar.production_order
    ),
    tuple(result.updates.items()),
)))
"""
        expected_prefix = (
            ("N0", "N1"),
            (
                (
                    "N0",
                    (
                        (),
                        ("a",),
                        ("a", "a"),
                        ("a", "b"),
                        ("b",),
                        ("b", "a"),
                        ("b", "b"),
                    ),
                ),
                ("N1", ((), ("a", "a"), ("a", "b"), ("b", "a"), ("b", "b"))),
            ),
        )
        root = Path(__file__).resolve().parents[1]
        observed = []
        for hash_seed in (0, 1, 7, 42):
            environment = os.environ.copy()
            environment["PYTHONHASHSEED"] = str(hash_seed)
            environment["PYTHONPATH"] = os.pathsep.join(
                part
                for part in (str(root / "src"), environment.get("PYTHONPATH"))
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
                value = ast.literal_eval(completed.stdout.strip())
                observed.append(value)
                self.assertEqual(value[:2], expected_prefix)
        self.assertTrue(all(value == observed[0] for value in observed[1:]))

    def test_projecting_first_k_matches_every_smaller_first_j(self) -> None:
        for seed in range(200):
            grammar = generated_resolved_grammar(seed)
            for k in (2, 3):
                larger = compute_prefix_analysis(grammar, k)
                for j in range(1, k):
                    smaller = compute_prefix_analysis(grammar, j)
                    with self.subTest(seed=seed, k=k, j=j):
                        self.assertEqual(
                            {
                                name: frozenset(word[:j] for word in language)
                                for name, language in larger.first.items()
                            },
                            smaller.first,
                        )


if __name__ == "__main__":
    unittest.main()

