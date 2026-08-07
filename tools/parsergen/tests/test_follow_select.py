import ast
import gc
import os
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType
import unittest

from parsergen.analysis import (
    AnalysisResult,
    END,
    LookaheadMaterializationError,
    SelectConflict,
    build_select_matcher_artifact,
    compatible_lookahead,
    compute_analysis,
    find_canonical_select_conflicts,
    find_runtime_dispatch_conflicts,
    find_select_conflicts,
    materialize_lookahead,
    runtime_rows_overlap,
)
from tests.grammar_factory import generated_resolved_grammar
from tests.grammar_cases import CONFLICT_DEPTH_CASES, FOLLOW_CASES
from tests.helpers import resolved
from tests.oracles import oracle_analysis


def _factorized_adversarial_grammar(size: int):
    prefixes = " | ".join(f"p{index:03d}" for index in range(size))
    tails = " | ".join(f"t{index:03d}" for index in range(size))
    return resolved(
        "<S> ::= <Owner> <Tail>\n"
        "<Owner> ::= <Prefix> | <Prefix>\n"
        f"<Prefix> ::= {prefixes}\n"
        f"<Tail> ::= {tails}"
    )


def _materialized_conflicts(grammar, select) -> tuple[SelectConflict, ...]:
    conflicts = []
    for production in grammar.production_order:
        alternatives = grammar.productions[production]
        for left in range(1, len(alternatives) + 1):
            for right in range(left + 1, len(alternatives) + 1):
                intersection = select[(production, left)].intersection(
                    select[(production, right)]
                )
                witness = min(
                    intersection,
                    key=lambda word: (len(word), word),
                    default=None,
                )
                if witness is not None:
                    conflicts.append(
                        SelectConflict(production, left, right, witness)
                    )
    return tuple(conflicts)


class FollowAnalysisTests(unittest.TestCase):
    def test_follow_cases(self) -> None:
        for name, grammar, k, production, expected in FOLLOW_CASES:
            with self.subTest(name=name, k=k, production=production):
                result = compute_analysis(resolved(grammar), k, ("S",))
                self.assertEqual(result.follow[production], frozenset(expected))

    def test_nullable_start_is_followed_by_end(self) -> None:
        result = compute_analysis(resolved("<S> ::= ПУСТО"), 3, ("S",))
        self.assertEqual(result.follow["S"], frozenset({(END,)}))
        self.assertEqual(result.select[("S", 1)], frozenset({(END,)}))

    def test_suffix_and_parent_follow_cross_k_boundary(self) -> None:
        grammar = resolved(
            "<S> ::= <B> c d\n"
            "<B> ::= <A> b\n"
            "<A> ::= a"
        )
        result = compute_analysis(grammar, 3, ("S",))
        self.assertEqual(result.follow["B"], frozenset({("c", "d", END)}))
        self.assertEqual(result.follow["A"], frozenset({("b", "c", "d")}))

    def test_saturated_suffix_fact_does_not_wait_for_parent_follow(self) -> None:
        grammar = resolved(
            "<S> ::= start\n"
            "<Unused> ::= <A> x y\n"
            "<A> ::= a"
        )
        result = compute_analysis(grammar, 2, ("S",))
        self.assertEqual(result.follow["Unused"], frozenset())
        self.assertEqual(result.follow["A"], frozenset({("x", "y")}))

    def test_multiple_short_complete_suffix_facts_extend_parent_delta(self) -> None:
        grammar = resolved(
            "<S> ::= <Parent>\n"
            "<Parent> ::= <A> <Tail>\n"
            "<Tail> ::= x | y\n"
            "<A> ::= a"
        )
        result = compute_analysis(grammar, 2, ("S",))
        self.assertEqual(
            result.follow["A"],
            frozenset({("x", END), ("y", END)}),
        )

    def test_dead_suffix_does_not_publish_a_saturated_follow_fact(self) -> None:
        result = compute_analysis(
            resolved(
                "<S> ::= start\n"
                "<Unused> ::= <A> x <Dead>\n"
                "<A> ::= a\n"
                "<Dead> ::= <Dead>"
            ),
            1,
            ("S",),
        )
        self.assertEqual(result.follow["A"], frozenset())

    def test_overlapping_suffix_matchers_expand_without_duplicates(self) -> None:
        result = compute_analysis(
            resolved(
                "#ID_X ::= ID | ГДЕ\n"
                "<S> ::= <A> #ID_X | <A> ГДЕ\n"
                "<A> ::= a"
            ),
            2,
            ("S",),
        )
        self.assertEqual(
            result.follow["A"],
            frozenset({("ID", END), ("ГДЕ", END)}),
        )

    def test_compressed_follow_reports_delta_only_work(self) -> None:
        grammar = resolved(
            "<S> ::= <A>\n"
            "<A> ::= <B> | <B>\n"
            "<B> ::= b"
        )
        result = compute_analysis(grammar, 3, ("S",))
        stats = result._compressed.stats
        self.assertGreaterEqual(stats["follow_transforms"], 2)
        self.assertEqual(stats["follow_delta_facts"], 3)
        self.assertEqual(stats["follow_transform_applications"], 2)
        self.assertEqual(stats["follow_facts"], 3)

    def test_follow_projection_deduplicates_irrelevant_delta_tails(self) -> None:
        grammar = resolved(
            "<S> ::= start\n"
            "<Owner> ::= <Parent> x u z | <Parent> x v z\n"
            "<Parent> ::= <A> p q\n"
            "<A> ::= a"
        )

        result = compute_analysis(grammar, 3, ("S",))

        self.assertEqual(
            result.follow["Parent"],
            frozenset({("x", "u", "z"), ("x", "v", "z")}),
        )
        self.assertEqual(result.follow["A"], frozenset({("p", "q", "x")}))
        stats = result._compressed.stats
        self.assertEqual(stats["follow_transform_applications"], 1)
        self.assertEqual(stats["follow_projection_checks"], 2)
        self.assertEqual(stats["duplicate_follow_projections"], 1)

    def test_short_follow_delta_is_projected_at_its_own_length(self) -> None:
        grammar = resolved(
            "<S> ::= <Parent> x\n"
            "<Other> ::= <Parent> x y z\n"
            "<Parent> ::= <A>\n"
            "<A> ::= a"
        )

        result = compute_analysis(grammar, 3, ("S",))

        expected = frozenset({("x", END), ("x", "y", "z")})
        self.assertEqual(result.follow["Parent"], expected)
        self.assertEqual(result.follow["A"], expected)
        stats = result._compressed.stats
        self.assertEqual(stats["follow_transform_applications"], 3)
        self.assertEqual(stats["follow_projection_checks"], 3)
        self.assertEqual(stats["duplicate_follow_projections"], 0)

    def test_public_follow_mapping_is_lazy_cached_and_immutable(self) -> None:
        result = compute_analysis(
            resolved("<S> ::= <A> x\n<A> ::= a"),
            2,
            ("S",),
        )
        stats = result._compressed.stats
        self.assertEqual(stats["public_follow_expansions"], 0)
        expected = frozenset({("x", END)})
        self.assertEqual(result.follow["A"], expected)
        self.assertEqual(stats["public_follow_expansions"], 1)
        self.assertIs(result.follow["A"], result.follow["A"])
        self.assertEqual(stats["public_follow_expansions"], 1)
        with self.assertRaises(TypeError):
            result.follow["A"] = frozenset()  # type: ignore[index]

    def test_repeated_full_analysis_does_not_require_cyclic_gc(self) -> None:
        grammar = resolved(
            "<S> ::= <A> <A>\n"
            "<A> ::= a <A> | <B> | ПУСТО\n"
            "<B> ::= b <A> | ПУСТО"
        )
        expected = compute_analysis(grammar, 3, ("S",))
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            for _ in range(10):
                self.assertEqual(
                    compute_analysis(grammar, 3, ("S",)),
                    expected,
                )
        finally:
            if gc_was_enabled:
                gc.enable()

    def test_follow_propagates_through_three_levels(self) -> None:
        grammar = resolved(
            "<S> ::= <A>\n"
            "<A> ::= <B>\n"
            "<B> ::= <C>\n"
            "<C> ::= c"
        )
        result = compute_analysis(grammar, 2, ("S",))
        for production in ("S", "A", "B", "C"):
            with self.subTest(production=production):
                self.assertEqual(result.follow[production], frozenset({(END,)}))

    def test_cyclic_follow_dependencies_reach_a_fixed_point(self) -> None:
        grammar = resolved(
            "<S> ::= <A>\n"
            "<A> ::= <B>\n"
            "<B> ::= <A> | b"
        )
        result = compute_analysis(grammar, 3, ("S",))
        self.assertEqual(result.follow["A"], frozenset({(END,)}))
        self.assertEqual(result.follow["B"], frozenset({(END,)}))

    def test_multiple_start_productions_receive_end(self) -> None:
        grammar = resolved("<S> ::= a\n<A> ::= b")
        result = compute_analysis(grammar, 2, ("A", "S", "A"))
        self.assertEqual(result.follow["S"], frozenset({(END,)}))
        self.assertEqual(result.follow["A"], frozenset({(END,)}))

    def test_compute_analysis_rejects_non_positive_k(self) -> None:
        grammar = resolved("<S> ::= a")
        for k in (0, -1):
            with self.subTest(k=k):
                with self.assertRaisesRegex(ValueError, "k must be at least 1"):
                    compute_analysis(grammar, k, ("S",))


class SelectAnalysisTests(unittest.TestCase):
    def test_select_uses_first_for_nonempty_and_follow_for_epsilon(self) -> None:
        result = compute_analysis(resolved("<S> ::= a | ПУСТО"), 1, ("S",))
        self.assertEqual(result.select[("S", 1)], frozenset({("a",)}))
        self.assertEqual(result.select[("S", 2)], frozenset({(END,)}))

    def test_nonproductive_suffix_does_not_publish_saturated_prefix(self) -> None:
        result = compute_analysis(
            resolved("<S> ::= b <A> | d\n<A> ::= <A>"),
            1,
            ("S",),
        )
        self.assertEqual(result.first["S"], frozenset({("d",)}))
        self.assertEqual(result.first["A"], frozenset())
        self.assertEqual(result.select[("S", 1)], frozenset())
        self.assertEqual(result.select[("S", 2)], frozenset({("d",)}))

    def test_conflict_disappears_at_sufficient_k(self) -> None:
        for name, grammar, conflicts_at, clean_at in CONFLICT_DEPTH_CASES:
            resolved_grammar = resolved(grammar)
            with self.subTest(name=name, k=conflicts_at):
                conflicting = compute_analysis(
                    resolved_grammar,
                    conflicts_at,
                    ("S",),
                )
                self.assertTrue(find_select_conflicts(resolved_grammar, conflicting))
            with self.subTest(name=name, k=clean_at):
                clean = compute_analysis(resolved_grammar, clean_at, ("S",))
                self.assertEqual(find_select_conflicts(resolved_grammar, clean), ())

    def test_canonical_conflict_includes_follow_continuation(self) -> None:
        grammar = resolved(
            "<S> ::= <A>\n"
            "<A> ::= a <B> | a b d\n"
            "<B> ::= ПУСТО | b c"
        )
        result = compute_analysis(grammar, 2, ("S",))

        self.assertEqual(
            result.select[("A", 1)],
            frozenset({("a", END), ("a", "b")}),
        )
        self.assertEqual(
            result.select[("A", 2)],
            frozenset({("a", "b")}),
        )
        self.assertEqual(
            find_canonical_select_conflicts(grammar, result),
            (SelectConflict("A", 1, 2, ("a", "b")),),
        )

    def test_canonical_conflicts_do_not_depend_on_analysis_representation(
        self,
    ) -> None:
        grammar = resolved(
            "<S> ::= <A>\n"
            "<A> ::= a <B> | a b d\n"
            "<B> ::= ПУСТО | b c"
        )
        compressed = compute_analysis(grammar, 2, ("S",))
        materialized = AnalysisResult(
            k=compressed.k,
            nullable=compressed.nullable,
            first=MappingProxyType(dict(compressed.first.items())),
            follow=MappingProxyType(dict(compressed.follow.items())),
            select=MappingProxyType(dict(compressed.select.items())),
            updates=compressed.updates,
        )

        self.assertEqual(
            find_canonical_select_conflicts(grammar, compressed),
            find_canonical_select_conflicts(grammar, materialized),
        )

    def test_nullable_fallback_is_canonical_conflict_but_runtime_clean(
        self,
    ) -> None:
        grammar = resolved("<S> ::= <A> a\n<A> ::= a | ПУСТО")
        result = compute_analysis(grammar, 1, ("S",))
        self.assertEqual(
            find_select_conflicts(grammar, result),
            (SelectConflict("A", 1, 2, ("a",)),),
        )
        self.assertEqual(find_runtime_dispatch_conflicts(grammar, result), ())

    def test_runtime_shadowing_is_not_used_as_canonical_semantics(
        self,
    ) -> None:
        grammar = resolved("<S> ::= <A> | a b\n<A> ::= a | a b")
        result = compute_analysis(grammar, 2, ("S",))

        self.assertEqual(
            find_select_conflicts(grammar, result),
            (SelectConflict("S", 1, 2, ("a", "b")),),
        )
        self.assertEqual(find_runtime_dispatch_conflicts(grammar, result), ())

    def test_two_epsilon_alternatives_conflict_at_end(self) -> None:
        grammar = resolved("<S> ::= ПУСТО | ПУСТО")
        result = compute_analysis(grammar, 3, ("S",))
        self.assertEqual(
            find_select_conflicts(grammar, result),
            (SelectConflict("S", 1, 2, (END,)),),
        )

    def test_duplicate_alternatives_conflict_on_complete_prefix(self) -> None:
        grammar = resolved("<S> ::= a b | a b")
        result = compute_analysis(grammar, 2, ("S",))
        self.assertEqual(
            find_select_conflicts(grammar, result),
            (SelectConflict("S", 1, 2, ("a", "b")),),
        )

    def test_identifier_class_conflicts_with_explicit_keyword(self) -> None:
        grammar = resolved("#ID_X ::= ID | ГДЕ\n<S> ::= #ID_X | ГДЕ")
        result = compute_analysis(grammar, 1, ("S",))
        self.assertEqual(
            find_select_conflicts(grammar, result),
            (SelectConflict("S", 1, 2, ("ГДЕ",)),),
        )

    def test_compressed_conflict_scan_does_not_expand_public_select(self) -> None:
        grammar = resolved("#ID_X ::= ID | ГДЕ\n<S> ::= #ID_X | ГДЕ")
        result = compute_analysis(grammar, 1, ("S",))
        stats = result._compressed.stats
        self.assertEqual(stats["public_select_expansions"], 0)
        self.assertEqual(
            find_select_conflicts(grammar, result),
            (SelectConflict("S", 1, 2, ("ГДЕ",)),),
        )
        self.assertEqual(stats["public_select_expansions"], 0)

    def test_factorized_select_avoids_prefix_follow_cartesian_rows(self) -> None:
        grammar = _factorized_adversarial_grammar(150)
        result = compute_analysis(grammar, 2, ("S",))
        stats = result._compressed.stats

        self.assertEqual(stats["select_cartesian_materializations"], 0)
        self.assertEqual(stats["select_packed_product_rows"], 0)
        self.assertEqual(stats["select_concatenations"], 0)
        self.assertEqual(stats["select_descriptors"], 303)
        self.assertEqual(
            stats["select_short_complete_prefixes"],
            600,
        )
        self.assertEqual(
            result._compressed.select_descriptor(("Owner", 1)).prefix_count,
            150,
        )
        self.assertEqual(
            result._compressed.select_descriptor(("Owner", 2)).prefix_count,
            150,
        )

        self.assertTrue(find_select_conflicts(grammar, result))
        self.assertEqual(stats["select_cartesian_materializations"], 0)
        self.assertEqual(stats["public_select_expansions"], 0)

    def test_oversized_public_select_requires_explicit_guarded_materialize(
        self,
    ) -> None:
        grammar = _factorized_adversarial_grammar(150)
        result = compute_analysis(grammar, 2, ("S",))

        with self.assertRaises(LookaheadMaterializationError) as raised:
            result.select[("Owner", 1)]
        self.assertGreater(raised.exception.estimated_rows, 10_000)
        self.assertEqual(
            result._compressed.stats["select_cartesian_materializations"],
            0,
        )

        tiny = compute_analysis(
            resolved("<S> ::= a | b"),
            1,
            ("S",),
        )
        self.assertEqual(
            materialize_lookahead(
                tiny,
                "select",
                ("S", 1),
                max_rows=1,
            ),
            frozenset({("a",)}),
        )
        with self.assertRaises(LookaheadMaterializationError):
            materialize_lookahead(
                tiny,
                "select",
                ("S", 1),
                max_rows=0,
            )

    def test_cached_materialization_still_obeys_each_caller_limit(self) -> None:
        tokens = tuple(f"T{index:03d}" for index in range(101))
        result = compute_analysis(
            resolved(
                f"#ID_X ::= {' | '.join(tokens)}\n"
                "<S> ::= #ID_X #ID_X"
            ),
            2,
            ("S",),
        )

        cases = (
            ("first", "S", result.first),
            ("select", ("S", 1), result.select),
        )
        for phase, key, mapping in cases:
            with self.subTest(phase=phase):
                populated = materialize_lookahead(
                    result,
                    phase,
                    key,
                    max_rows=20_000,
                )
                self.assertEqual(len(populated), 10_201)
                self.assertIs(
                    materialize_lookahead(
                        result,
                        phase,
                        key,
                        max_rows=20_000,
                    ),
                    populated,
                )

                with self.assertRaises(LookaheadMaterializationError):
                    mapping[key]
                with self.assertRaises(LookaheadMaterializationError):
                    materialize_lookahead(
                        result,
                        phase,
                        key,
                        max_rows=10_000,
                    )

    def test_codegen_adapter_expands_identifier_classes_for_reference_runtime(self) -> None:
        tokens = tuple(f"T{index:03d}" for index in range(500))
        grammar = resolved(
            f"#ID_First ::= {' | '.join(tokens)}\n"
            f"#ID_Equal ::= {' | '.join(tokens)}\n"
            "#ID_Overlap ::= T000 | Extra\n"
            "<S> ::= #ID_Equal | #ID_Overlap"
        )
        result = compute_analysis(grammar, 1, ("S",))

        artifact = build_select_matcher_artifact(result, max_rows=1_000)
        self.assertEqual(
            {
                (row.production, row.alternative, row.matchers)
                for row in artifact.select_rows
            },
            {
                *(("S", 1, (token,)) for token in tokens),
                ("S", 2, ("Extra",)),
                ("S", 2, ("T000",)),
            },
        )
        self.assertEqual(artifact.matcher_definitions, ())
        self.assertEqual(
            result._compressed.stats["public_select_expansions"],
            0,
        )

    def test_disjoint_identifier_classes_are_clean(self) -> None:
        grammar = resolved(
            "#ID_Left ::= ID\n"
            "#ID_Right ::= ГДЕ\n"
            "<S> ::= #ID_Left | #ID_Right"
        )
        result = compute_analysis(grammar, 2, ("S",))
        self.assertEqual(find_select_conflicts(grammar, result), ())

    def test_conflict_persists_for_all_requested_depths(self) -> None:
        grammar = resolved(
            "<S> ::= a <A> | a <A>\n"
            "<A> ::= b | ПУСТО"
        )
        for k in (1, 2, 3):
            with self.subTest(k=k):
                result = compute_analysis(grammar, k, ("S",))
                self.assertTrue(find_select_conflicts(grammar, result))

    def test_several_conflicts_are_returned_in_grammar_order(self) -> None:
        grammar = resolved(
            "<S> ::= a | a | a\n"
            "<A> ::= b | b"
        )
        result = compute_analysis(grammar, 1, ("S", "A"))
        self.assertEqual(
            find_select_conflicts(grammar, result),
            (
                SelectConflict("S", 1, 2, ("a",)),
                SelectConflict("S", 1, 3, ("a",)),
                SelectConflict("S", 2, 3, ("a",)),
                SelectConflict("A", 1, 2, ("b",)),
            ),
        )

    def test_several_compressed_conflicts_are_stable_across_hash_seeds(
        self,
    ) -> None:
        script = """
from tests.helpers import resolved
from parsergen.analysis import compute_analysis, find_select_conflicts

grammar = resolved(
    "#ID_X ::= b | a\\n"
    "<S> ::= #ID_X | a | b\\n"
    "<A> ::= x | x"
)
analysis = compute_analysis(grammar, 1, ("S", "A"))
print(repr(tuple(
    (
        conflict.production,
        conflict.left_alternative,
        conflict.right_alternative,
        conflict.witness,
    )
    for conflict in find_select_conflicts(grammar, analysis)
)))
"""
        expected = (
            ("S", 1, 2, ("a",)),
            ("S", 1, 3, ("b",)),
            ("A", 1, 2, ("x",)),
        )
        root = Path(__file__).resolve().parents[1]
        observed = []
        for hash_seed in (0, 1, 7, 42):
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
                value = ast.literal_eval(completed.stdout.strip())
                observed.append(value)
                self.assertEqual(value, expected)
        self.assertTrue(all(value == observed[0] for value in observed[1:]))

    def test_witness_selection_is_shortest_then_lexicographic(self) -> None:
        grammar = resolved(
            "#ID_Left ::= b | a\n"
            "#ID_Right ::= b | a\n"
            "<S> ::= #ID_Left | #ID_Right"
        )
        result = compute_analysis(grammar, 1, ("S",))
        self.assertEqual(
            find_select_conflicts(grammar, result),
            (SelectConflict("S", 1, 2, ("a",)),),
        )


class RuntimeRowCompatibilityTests(unittest.TestCase):
    def test_strict_prefix_rows_are_distinct_exact_rows(self) -> None:
        self.assertFalse(runtime_rows_overlap(("a",), ("a", "b")))
        self.assertFalse(runtime_rows_overlap(("a", "b"), ("a",)))

    def test_only_equal_runtime_rows_conflict(self) -> None:
        self.assertTrue(compatible_lookahead(("a", "b"), ("a", "b")))
        self.assertFalse(compatible_lookahead(("a", END), ("a", "b")))
        self.assertFalse(compatible_lookahead(("a",), ("a", END)))
        self.assertFalse(compatible_lookahead(("a", "b"), ("a", "c")))

    def test_materialized_canonical_scan_uses_exact_word_intersection(
        self,
    ) -> None:
        grammar = resolved("<S> ::= a | b")
        analysis = AnalysisResult(
            k=2,
            nullable=frozenset(),
            first=MappingProxyType({"S": frozenset({("a",), ("b",)})}),
            follow=MappingProxyType({"S": frozenset({(END,)})}),
            select=MappingProxyType(
                {
                    ("S", 1): frozenset({("a",)}),
                    ("S", 2): frozenset({("a", "b")}),
                }
            ),
            updates=MappingProxyType({"S": 1}),
        )
        self.assertEqual(find_select_conflicts(grammar, analysis), ())


class GeneratedFollowSelectTests(unittest.TestCase):
    def test_work_list_matches_full_rescan_oracle_for_600_cases(self) -> None:
        for seed in range(200):
            grammar = generated_resolved_grammar(seed)
            starts = (grammar.production_order[0],)
            for k in (1, 2, 3):
                with self.subTest(seed=seed, k=k):
                    optimized = compute_analysis(grammar, k, starts)
                    (
                        oracle_nullable,
                        oracle_first,
                        oracle_follow,
                        oracle_select,
                    ) = oracle_analysis(grammar, k, starts)
                    self.assertEqual(optimized.nullable, oracle_nullable)
                    self.assertEqual(optimized.first, oracle_first)
                    self.assertEqual(optimized.follow, oracle_follow)
                    self.assertEqual(optimized.select, oracle_select)
                    self.assertEqual(
                        find_select_conflicts(grammar, optimized),
                        _materialized_conflicts(grammar, oracle_select),
                    )
                    for languages in (optimized.follow, optimized.select):
                        self.assertTrue(
                            all(
                                len(word) <= k
                                and (
                                    END not in word
                                    or word[-1] == END
                                )
                                for language in languages.values()
                                for word in language
                            )
                        )

    def test_compressed_solver_matches_full_rescan_oracle_for_100_k4_cases(
        self,
    ) -> None:
        for seed in range(100):
            grammar = generated_resolved_grammar(seed)
            starts = (grammar.production_order[0],)
            with self.subTest(seed=seed):
                optimized = compute_analysis(grammar, 4, starts)
                (
                    oracle_nullable,
                    oracle_first,
                    oracle_follow,
                    oracle_select,
                ) = oracle_analysis(grammar, 4, starts)
                self.assertEqual(optimized.nullable, oracle_nullable)
                self.assertEqual(optimized.first, oracle_first)
                self.assertEqual(optimized.follow, oracle_follow)
                self.assertEqual(optimized.select, oracle_select)


if __name__ == "__main__":
    unittest.main()

