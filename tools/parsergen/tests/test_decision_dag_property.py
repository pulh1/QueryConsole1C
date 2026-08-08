from __future__ import annotations

from dataclasses import fields, is_dataclass
from itertools import product
import random
import unittest

from parsergen.decision_dag import (
    CommitAlternative,
    ExitDecision,
    ImmediateError,
    build_decision_dag,
    evaluate_decision,
)
from parsergen.canonical_select import (
    AlternativeOutcome,
    CanonicalOutcome,
    ExitOutcome,
    build_canonical_decision_source,
)
from tests.test_canonical_select import _analysis


def _oracle(
    materialized_select: dict[CanonicalOutcome, frozenset[tuple[str, ...]]],
    word: tuple[str, ...],
) -> CanonicalOutcome | None:
    matches = tuple(
        outcome for outcome, words in materialized_select.items() if word in words
    )
    assert len(matches) <= 1
    return matches[0] if matches else None


def _leaf(outcome: CanonicalOutcome):
    if isinstance(outcome, ExitOutcome):
        return ExitDecision(outcome)
    return CommitAlternative(outcome)


def _first_singleton_prefix(
    materialized_select: dict[CanonicalOutcome, frozenset[tuple[str, ...]]],
    word: tuple[str, ...],
) -> CanonicalOutcome | None:
    for length in range(len(word) + 1):
        prefix = word[:length]
        viable = tuple(
            outcome
            for outcome, words in materialized_select.items()
            if any(candidate[:length] == prefix for candidate in words)
        )
        if len(viable) == 1:
            return viable[0]
        if not viable:
            return None
    return None


def _plain(value):
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple((field.name, _plain(getattr(value, field.name))) for field in fields(value)),
        )
    if isinstance(value, dict):
        return tuple(sorted((key, _plain(item)) for key, item in value.items()))
    if hasattr(value, "items"):
        return tuple(sorted((key, _plain(item)) for key, item in value.items()))
    if isinstance(value, tuple):
        return tuple(_plain(item) for item in value)
    return value


def _case(rng: random.Random, index: int) -> tuple[str, int, int, tuple[str, ...]]:
    k = index % 3 + 1
    literals = list("ABCDE")
    rng.shuffle(literals)
    p, q, x, y, z = literals
    identifier_lines = "#ID_L ::= ID | KW_L\n#ID_R ::= ID | KW_R\n"
    if k == 1:
        alternatives = (p, q, "#ID_L", "ПУСТО")
        alphabet = (p, q, "ID", "KW_L", "KW_R", "$", "OUTSIDE")
    elif k == 2:
        alternatives = (
            f"{p} {x}",
            f"{p} {y}",
            f"{q} #ID_L",
            "ПУСТО",
        )
        alphabet = (p, q, x, y, "ID", "KW_L", "KW_R", "$", "OUTSIDE")
    else:
        alternatives = (
            f"{p} #ID_L {x}",
            f"{p} #ID_R {y}",
            f"{q} {z}",
            "ПУСТО",
        )
        alphabet = (
            p,
            q,
            x,
            y,
            z,
            "ID",
            "KW_L",
            "KW_R",
            "$",
            "OUTSIDE",
        )
    grammar = identifier_lines + "<S> ::= " + " | ".join(alternatives)
    return grammar, k, 4, tuple(sorted(set(alphabet)))


class DecisionDagPropertyTests(unittest.TestCase):
    def test_matches_independent_materialized_oracle_for_200_decisions(
        self,
    ) -> None:
        rng = random.Random(0xDAD2026)
        seen_k: set[int] = set()
        serialized_shapes = []

        for index in range(200):
            grammar, k, exit_alternative, alphabet = _case(rng, index)
            seen_k.add(k)
            analysis = _analysis(grammar, k)
            source = build_canonical_decision_source(
                analysis,
                "S",
                exit_alternative=exit_alternative,
            )
            dag = build_decision_dag(source)
            serialized_shapes.append(_plain(dag))
            materialized = {
                item.outcome: analysis.select[("S", item.outcome.alternative)]
                for item in source.languages
            }

            for outcome, words in materialized.items():
                for word in words:
                    with self.subTest(index=index, k=k, word=word):
                        self.assertEqual(_oracle(materialized, word), outcome)
                        self.assertEqual(evaluate_decision(dag, word), _leaf(outcome))

            for length in range(1, k + 1):
                for word in product(alphabet, repeat=length):
                    if "$" in word[:-1]:
                        continue
                    if _oracle(materialized, word) is not None:
                        continue
                    result = evaluate_decision(dag, word)
                    with self.subTest(index=index, k=k, outside=word):
                        if isinstance(result, ImmediateError):
                            continue
                        self.assertNotIsInstance(result, ExitDecision)
                        sole = _first_singleton_prefix(materialized, word)
                        self.assertIsNotNone(sole)
                        self.assertEqual(result, _leaf(sole))

        self.assertEqual(seen_k, {1, 2, 3})

        repeat_rng = random.Random(0xDAD2026)
        repeated_shapes = []
        for index in range(200):
            grammar, k, exit_alternative, _ = _case(repeat_rng, index)
            source = build_canonical_decision_source(
                _analysis(grammar, k),
                "S",
                exit_alternative=exit_alternative,
            )
            repeated_shapes.append(_plain(build_decision_dag(source)))
        self.assertEqual(serialized_shapes, repeated_shapes)


if __name__ == "__main__":
    unittest.main()
