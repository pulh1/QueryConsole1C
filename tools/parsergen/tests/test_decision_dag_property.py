from __future__ import annotations

from dataclasses import fields, is_dataclass
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import random
import subprocess
import sys
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
    CanonicalDecisionSource,
    CanonicalOutcome,
    ExitOutcome,
    OutcomeLanguage,
    SymbolicLanguage,
    SymbolicLanguageEdge,
    SymbolicLanguageNode,
    TokenSetPredicate,
    build_canonical_decision_source,
)
from tests.test_canonical_select import _analysis


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


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


IDENTIFIER_LINES = (
    "#ID_ALL ::= ID | KW_L | KW_R\n"
    "#ID_LEFT ::= ID | KW_L\n"
    "#ID_RIGHT ::= ID | KW_R\n"
    "#ID_SUB ::= ID\n"
)
ATOM_CHOICES = (
    "A",
    "B",
    "C",
    "D",
    "ID",
    "KW_L",
    "KW_R",
    "#ID_ALL",
    "#ID_LEFT",
    "#ID_RIGHT",
    "#ID_SUB",
)


def _case(
    rng: random.Random,
    index: int,
) -> tuple[str, int, int | None, tuple[str, ...]]:
    k = index % 3 + 1
    for _ in range(2_000):
        count = rng.randint(2, 5)
        alternatives: list[str] = []
        if rng.random() < 0.45:
            alternatives.append("ПУСТО")
        while len(alternatives) < count:
            length = rng.randint(1, k + 1)
            alternative = " ".join(
                rng.choice(ATOM_CHOICES) for _ in range(length)
            )
            if alternative not in alternatives:
                alternatives.append(alternative)
        rng.shuffle(alternatives)
        grammar = IDENTIFIER_LINES + "<S> ::= " + " | ".join(alternatives)
        analysis = _analysis(grammar, k)
        words_by_alternative = tuple(
            analysis.select[("S", alternative)]
            for alternative in range(1, count + 1)
        )
        seen: set[tuple[str, ...]] = set()
        disjoint = True
        for words in words_by_alternative:
            if seen.intersection(words):
                disjoint = False
                break
            seen.update(words)
        if not disjoint:
            continue
        exit_alternative = next(
            (
                position
                for position, alternative in enumerate(alternatives, 1)
                if alternative == "ПУСТО"
            ),
            None,
        )
        alphabet = {
            "$",
            "ID",
            "KW_L",
            "KW_R",
            "OUTSIDE",
        }
        alphabet.update(
            token
            for words in words_by_alternative
            for word in words
            for token in word
        )
        return grammar, k, exit_alternative, tuple(sorted(alphabet))
    raise AssertionError("failed to generate a disjoint canonical decision")


def _shape_digest() -> str:
    rng = random.Random(0xDAD2026)
    shapes = []
    for index in range(200):
        grammar, k, exit_alternative, _ = _case(rng, index)
        source = build_canonical_decision_source(
            _analysis(grammar, k),
            "S",
            exit_alternative=exit_alternative,
        )
        shapes.append(_plain(build_decision_dag(source)))
    payload = json.dumps(
        shapes,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class DecisionDagPropertyTests(unittest.TestCase):
    def test_random_cases_have_diverse_topologies(self) -> None:
        rng = random.Random(0xDAD2026)
        signatures = set()
        alternative_counts = set()
        nullable_positions = set()
        short_positions = set()
        for index in range(200):
            grammar, k, exit_alternative, _ = _case(rng, index)
            alternatives = grammar.rsplit("<S> ::= ", 1)[1].split(" | ")
            alternative_counts.add(len(alternatives))
            nullable_positions.add(exit_alternative)
            short_positions.update(
                position
                for position, alternative in enumerate(alternatives, 1)
                if alternative != "ПУСТО"
                and len(alternative.split()) < k
            )
            signatures.add((
                k,
                len(alternatives),
                exit_alternative,
                tuple(
                    0 if alternative == "ПУСТО" else len(alternative.split())
                    for alternative in alternatives
                ),
                tuple("#ID_" in alternative for alternative in alternatives),
            ))

        self.assertGreaterEqual(len(signatures), 20)
        self.assertEqual(alternative_counts, {2, 3, 4, 5})
        self.assertIn(None, nullable_positions)
        self.assertGreaterEqual(
            len(nullable_positions.difference({None})),
            3,
        )
        self.assertGreaterEqual(len(short_positions), 3)

    def test_literal_and_identifier_class_overlap_uses_exact_oracle(self) -> None:
        analysis = _analysis(
            "#ID_L ::= ID | KW_L\n"
            "<S> ::= ID X | #ID_L Y | Z",
            2,
        )
        source = build_canonical_decision_source(analysis, "S")
        materialized = {
            item.outcome: analysis.select[("S", item.outcome.alternative)]
            for item in source.languages
        }
        dag = build_decision_dag(source)

        for outcome, words in materialized.items():
            for word in words:
                self.assertEqual(evaluate_decision(dag, word), _leaf(outcome))

    def test_subset_and_partial_identifier_class_overlap_are_exact(self) -> None:
        analysis = _analysis(
            "#ID_ALL ::= ID | KW_L | KW_R\n"
            "#ID_LEFT ::= ID | KW_L\n"
            "#ID_RIGHT ::= ID | KW_R\n"
            "<S> ::= #ID_ALL A | #ID_LEFT B | #ID_RIGHT C",
            2,
        )
        source = build_canonical_decision_source(analysis, "S")
        materialized = {
            item.outcome: analysis.select[("S", item.outcome.alternative)]
            for item in source.languages
        }
        dag = build_decision_dag(source)

        for outcome, words in materialized.items():
            for word in words:
                self.assertEqual(evaluate_decision(dag, word), _leaf(outcome))

    def test_one_outcome_may_have_overlapping_symbolic_edges(self) -> None:
        first = AlternativeOutcome("S", 1)
        second = AlternativeOutcome("S", 2)
        overlapping = SymbolicLanguage(
            0,
            (
                SymbolicLanguageNode(
                    False,
                    (
                        SymbolicLanguageEdge(
                            TokenSetPredicate(("A", "B")),
                            1,
                        ),
                        SymbolicLanguageEdge(
                            TokenSetPredicate(("B", "C")),
                            2,
                        ),
                    ),
                ),
                SymbolicLanguageNode(True, ()),
                SymbolicLanguageNode(True, ()),
            ),
        )
        distinct = SymbolicLanguage(
            0,
            (
                SymbolicLanguageNode(
                    False,
                    (
                        SymbolicLanguageEdge(TokenSetPredicate(("D",)), 1),
                    ),
                ),
                SymbolicLanguageNode(True, ()),
            ),
        )
        source = CanonicalDecisionSource(
            "S",
            1,
            (
                OutcomeLanguage(first, overlapping),
                OutcomeLanguage(second, distinct),
            ),
        )
        dag = build_decision_dag(source)

        for word in (("A",), ("B",), ("C",)):
            self.assertEqual(evaluate_decision(dag, word), _leaf(first))
        self.assertEqual(evaluate_decision(dag, ("D",)), _leaf(second))

    def test_eof_and_saturation_are_exact_at_every_k(self) -> None:
        cases = (
            (1, "<S> ::= A | ПУСТО", ({("A",)}, {("$",)})),
            (
                2,
                "<S> ::= A B | C | ПУСТО",
                ({("A", "B")}, {("C", "$")}, {("$",)}),
            ),
            (
                3,
                "<S> ::= A B C | D E | ПУСТО",
                ({("A", "B", "C")}, {("D", "E", "$")}, {("$",)}),
            ),
        )
        for k, grammar, expected in cases:
            with self.subTest(k=k):
                analysis = _analysis(grammar, k)
                source = build_canonical_decision_source(
                    analysis,
                    "S",
                    exit_alternative=len(expected),
                )
                dag = build_decision_dag(source)
                actual = tuple(
                    set(analysis.select[("S", item.outcome.alternative)])
                    for item in source.languages
                )
                self.assertEqual(actual, expected)
                for item, words in zip(source.languages, expected, strict=True):
                    for word in words:
                        self.assertEqual(
                            evaluate_decision(dag, word),
                            _leaf(item.outcome),
                        )

    def test_serialized_shapes_match_across_python_hash_seeds(self) -> None:
        command = (
            "from tests.test_decision_dag_property import _shape_digest; "
            "print(_shape_digest())"
        )
        digests = []
        for seed in ("1", "777"):
            environment = os.environ.copy()
            environment["PYTHONHASHSEED"] = seed
            environment["PYTHONPATH"] = os.pathsep.join((
                str(PACKAGE_ROOT),
                str(PACKAGE_ROOT / "src"),
            ))
            result = subprocess.run(
                [sys.executable, "-c", command],
                cwd=REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            digest = result.stdout.strip()
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            digests.append(digest)
        self.assertEqual(digests[0], digests[1])

    def test_matches_independent_materialized_oracle_for_200_decisions(
        self,
    ) -> None:
        rng = random.Random(0xDAD2026)
        seen_k: set[int] = set()

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


if __name__ == "__main__":
    unittest.main()
