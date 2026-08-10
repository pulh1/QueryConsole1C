from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest
from unittest.mock import patch

import parsergen.decision_dag as decision_dag_module
from parsergen.decision_dag import (
    CanonicalDecisionDag,
    CommitAlternative,
    DecisionEdge,
    ExitDecision,
    ImmediateError,
    LookaheadDecision,
    build_decision_dag,
    evaluate_decision,
    validate_decision_dag,
)
from parsergen.canonical_select import (
    AlternativeOutcome,
    CanonicalDecisionSource,
    ExitOutcome,
    TokenSetPredicate,
    build_canonical_decision_source,
)
from tests.test_canonical_select import _accepts, _analysis


def _source(grammar: str, k: int = 1) -> CanonicalDecisionSource:
    return build_canonical_decision_source(_analysis(grammar, k), "S")


def _replace_node(dag, node_id: int, node):
    nodes = list(dag.nodes)
    nodes[node_id] = node
    return replace(dag, nodes=tuple(nodes))


def _node_for_word(dag, word: tuple[str, ...]) -> int:
    node_id = dag.root
    while isinstance(dag.nodes[node_id], LookaheadDecision):
        node = dag.nodes[node_id]
        assert isinstance(node, LookaheadDecision)
        token = word[node.offset]
        node_id = next(
            edge.target
            for edge in node.edges
            if token in edge.predicate.token_types
        )
    return node_id


class DecisionDagTests(unittest.TestCase):
    def test_decision_paths_preserve_distinct_facts_for_one_leaf(self) -> None:
        alternative_1 = CommitAlternative(AlternativeOutcome("S", 1))
        alternative_2 = CommitAlternative(AlternativeOutcome("S", 2))
        offset_1 = LookaheadDecision(
            1,
            ("A", "B"),
            (
                DecisionEdge(TokenSetPredicate(("A",)), 0),
                DecisionEdge(TokenSetPredicate(("B",)), 1),
            ),
        )
        root = LookaheadDecision(
            0,
            ("A", "НЕ"),
            (
                DecisionEdge(TokenSetPredicate(("A",)), 0),
                DecisionEdge(TokenSetPredicate(("НЕ",)), 2),
            ),
        )
        dag = CanonicalDecisionDag(
            "S",
            2,
            3,
            (alternative_1, alternative_2, offset_1, root),
            {},
        )

        paths = decision_dag_module.decision_paths(dag)

        self.assertEqual(
            tuple(path.facts for path in paths if path.leaf == alternative_1),
            (
                (
                    decision_dag_module.DecisionPathFact(
                        0,
                        TokenSetPredicate(("A",)),
                    ),
                ),
                (
                    decision_dag_module.DecisionPathFact(
                        0,
                        TokenSetPredicate(("НЕ",)),
                    ),
                    decision_dag_module.DecisionPathFact(
                        1,
                        TokenSetPredicate(("A",)),
                    ),
                ),
            ),
        )

    def test_path_grouped_decision_edges_union_duplicate_targets(self) -> None:
        node = LookaheadDecision(
            0,
            ("A", "B", "C"),
            (
                DecisionEdge(TokenSetPredicate(("B",)), 7),
                DecisionEdge(TokenSetPredicate(("C",)), 9),
                DecisionEdge(TokenSetPredicate(("A",)), 7),
            ),
        )

        self.assertEqual(
            decision_dag_module.grouped_decision_edges(node),
            (
                DecisionEdge(TokenSetPredicate(("A", "B")), 7),
                DecisionEdge(TokenSetPredicate(("C",)), 9),
            ),
        )

    def test_decision_paths_reject_duplicate_offset_on_one_path(self) -> None:
        leaf = CommitAlternative(AlternativeOutcome("S", 1))
        repeated_offset = LookaheadDecision(
            0,
            ("B",),
            (DecisionEdge(TokenSetPredicate(("B",)), 0),),
        )
        root = LookaheadDecision(
            0,
            ("A",),
            (DecisionEdge(TokenSetPredicate(("A",)), 1),),
        )
        dag = CanonicalDecisionDag("S", 2, 2, (leaf, repeated_offset, root), {})

        with self.assertRaisesRegex(ValueError, "offset.*twice"):
            decision_dag_module.decision_paths(dag)

    def test_reads_second_token_only_for_shared_first_prefix(self) -> None:
        source = _source("<S> ::= A X | A Y | B Z", k=2)

        dag = build_decision_dag(source)

        self.assertEqual(
            evaluate_decision(dag, ("B",)),
            CommitAlternative(AlternativeOutcome("S", 3)),
        )
        self.assertEqual(
            evaluate_decision(dag, ("A", "X")),
            CommitAlternative(AlternativeOutcome("S", 1)),
        )
        root = dag.nodes[dag.root]
        self.assertIsInstance(root, LookaheadDecision)
        assert isinstance(root, LookaheadDecision)
        self.assertEqual(root.offset, 0)
        self.assertEqual(root.expected, ("A", "B"))

    def test_single_viable_alternative_commits_before_invalid_suffix(self) -> None:
        dag = build_decision_dag(_source("<S> ::= A X | B Y", k=2))

        self.assertEqual(
            evaluate_decision(dag, ("A", "WRONG")),
            CommitAlternative(AlternativeOutcome("S", 1)),
        )

    def test_saturated_follow_prefix_remains_viable_at_lookahead_limit(
        self,
    ) -> None:
        source = build_canonical_decision_source(
            _analysis("<S> ::= <A> Z\n<A> ::= X | Y", k=2),
            "A",
        )

        self.assertFalse(
            _accepts(source, AlternativeOutcome("A", 1), ("X",))
        )
        self.assertTrue(
            _accepts(source, AlternativeOutcome("A", 1), ("X", "Z"))
        )

        dag = build_decision_dag(source)

        self.assertEqual(
            evaluate_decision(dag, ("X", "Z")),
            CommitAlternative(AlternativeOutcome("A", 1)),
        )
        self.assertEqual(
            evaluate_decision(dag, ("Y", "Z")),
            CommitAlternative(AlternativeOutcome("A", 2)),
        )

    def test_exit_and_immediate_error_are_distinct_leaves(self) -> None:
        source = build_canonical_decision_source(
            _analysis("<S> ::= A | ПУСТО"),
            "S",
            exit_alternative=2,
        )
        dag = build_decision_dag(source)

        self.assertEqual(
            evaluate_decision(dag, ("$",)),
            ExitDecision(ExitOutcome("S", 2)),
        )
        error = evaluate_decision(dag, ("WRONG",))
        self.assertEqual(error, ImmediateError(("$", "A")))

    def test_end_never_reads_a_deeper_lookahead_offset(self) -> None:
        source = build_canonical_decision_source(
            _analysis("<S> ::= <A>\n<A> ::= X | ПУСТО", k=3),
            "A",
            exit_alternative=2,
        )

        dag = build_decision_dag(source)

        self.assertEqual(
            evaluate_decision(dag, ("$", "WRONG", "WRONG")),
            ExitDecision(ExitOutcome("A", 2)),
        )

    def test_ambiguous_canonical_outcomes_are_not_resolved_by_order(self) -> None:
        source = _source("<S> ::= A | A")

        with self.assertRaisesRegex(
            ValueError,
            "canonical decision remains ambiguous at lookahead limit",
        ):
            build_decision_dag(source)

    def test_dag_is_immutable_reports_stats_and_validates_source(self) -> None:
        source = _source("<S> ::= A X | A Y | B Z", k=2)
        dag = build_decision_dag(source)

        self.assertEqual(
            set(dag.stats),
            {"source_states", "dag_states", "shared_states", "max_depth"},
        )
        self.assertEqual(dag.stats["dag_states"], len(dag.nodes))
        validate_decision_dag(source, dag)
        with self.assertRaises(FrozenInstanceError):
            dag.root = 1  # type: ignore[misc]
        with self.assertRaisesRegex(ValueError, "production does not match"):
            validate_decision_dag(source, replace(dag, production="Other"))

    def test_validator_does_not_call_builder_decision_semantics(self) -> None:
        source = _source("<S> ::= A X | A Y | B Z", k=2)
        dag = build_decision_dag(source)

        with patch(
            "parsergen.decision_dag._DecisionSemantics",
            side_effect=AssertionError("builder semantics must stay unused"),
        ):
            validate_decision_dag(source, dag)

    def test_validator_rejects_wrong_leaf(self) -> None:
        source = _source("<S> ::= A X | A Y | B Z", k=2)
        dag = build_decision_dag(source)
        leaf = _node_for_word(dag, ("A", "X"))
        corrupted = _replace_node(
            dag,
            leaf,
            CommitAlternative(AlternativeOutcome("S", 2)),
        )

        with self.assertRaises(ValueError):
            validate_decision_dag(source, corrupted)

    def test_validator_rejects_wrong_derivative_target(self) -> None:
        source = _source("<S> ::= A X | A Y | B Z", k=2)
        dag = build_decision_dag(source)
        root = dag.nodes[dag.root]
        assert isinstance(root, LookaheadDecision)
        target_b = next(
            edge.target for edge in root.edges if "B" in edge.predicate.token_types
        )
        corrupted_root = replace(
            root,
            edges=tuple(
                replace(edge, target=target_b)
                if "A" in edge.predicate.token_types
                else edge
                for edge in root.edges
            ),
        )

        with self.assertRaises(ValueError):
            validate_decision_dag(
                source,
                _replace_node(dag, dag.root, corrupted_root),
            )

    def test_validator_rejects_wrong_offset(self) -> None:
        source = _source("<S> ::= A X | A Y | B Z", k=2)
        dag = build_decision_dag(source)
        root = dag.nodes[dag.root]
        assert isinstance(root, LookaheadDecision)

        with self.assertRaises(ValueError):
            validate_decision_dag(
                source,
                _replace_node(dag, dag.root, replace(root, offset=1)),
            )

    def test_validator_rejects_missing_coverage(self) -> None:
        source = _source("<S> ::= A X | A Y | B Z", k=2)
        dag = build_decision_dag(source)
        root = dag.nodes[dag.root]
        assert isinstance(root, LookaheadDecision)
        corrupted_root = replace(
            root,
            expected=("A",),
            edges=tuple(
                edge for edge in root.edges if "B" not in edge.predicate.token_types
            ),
        )

        with self.assertRaises(ValueError):
            validate_decision_dag(
                source,
                _replace_node(dag, dag.root, corrupted_root),
            )

    def test_validator_rejects_overlapping_edge_predicates(self) -> None:
        source = _source("<S> ::= A X | A Y | B Z", k=2)
        dag = build_decision_dag(source)
        root = dag.nodes[dag.root]
        assert isinstance(root, LookaheadDecision)
        corrupted_root = replace(
            root,
            edges=tuple(
                replace(edge, predicate=TokenSetPredicate(("A", "B")))
                if "B" in edge.predicate.token_types
                else edge
                for edge in root.edges
            ),
        )

        with self.assertRaises(ValueError):
            validate_decision_dag(
                source,
                _replace_node(dag, dag.root, corrupted_root),
            )

    def test_validator_rejects_wrong_eof_leaf(self) -> None:
        source = build_canonical_decision_source(
            _analysis("<S> ::= A | ПУСТО"),
            "S",
            exit_alternative=2,
        )
        dag = build_decision_dag(source)
        eof_leaf = _node_for_word(dag, ("$",))
        corrupted = _replace_node(
            dag,
            eof_leaf,
            CommitAlternative(AlternativeOutcome("S", 1)),
        )

        with self.assertRaises(ValueError):
            validate_decision_dag(source, corrupted)


if __name__ == "__main__":
    unittest.main()
