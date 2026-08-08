from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from parsergen.decision_dag import (
    CommitAlternative,
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
    build_canonical_decision_source,
)
from tests.test_canonical_select import _analysis


def _source(grammar: str, k: int = 1) -> CanonicalDecisionSource:
    return build_canonical_decision_source(_analysis(grammar, k), "S")


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


if __name__ == "__main__":
    unittest.main()
