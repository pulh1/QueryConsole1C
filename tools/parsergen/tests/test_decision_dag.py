from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest
from unittest.mock import patch

from parsergen.decision_dag import (
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
from tests.test_canonical_select import _analysis


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
