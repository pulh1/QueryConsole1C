from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

from .canonical_select import (
    AlternativeOutcome,
    CanonicalDecisionSource,
    CanonicalOutcome,
    ExitOutcome,
    SymbolicLanguage,
    TokenSetPredicate,
)


@dataclass(frozen=True, slots=True)
class CommitAlternative:
    outcome: AlternativeOutcome


@dataclass(frozen=True, slots=True)
class ExitDecision:
    outcome: ExitOutcome


@dataclass(frozen=True, slots=True)
class ImmediateError:
    expected: tuple[str, ...]


DecisionLeaf: TypeAlias = CommitAlternative | ExitDecision | ImmediateError


@dataclass(frozen=True, slots=True)
class DecisionEdge:
    predicate: TokenSetPredicate
    target: int


@dataclass(frozen=True, slots=True)
class LookaheadDecision:
    offset: int
    expected: tuple[str, ...]
    edges: tuple[DecisionEdge, ...]


DecisionNode: TypeAlias = DecisionLeaf | LookaheadDecision


@dataclass(frozen=True, slots=True)
class CanonicalDecisionDag:
    production: str
    lookahead: int
    root: int
    nodes: tuple[DecisionNode, ...]
    stats: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class _BuildState:
    offset: int
    remaining: int
    residuals: tuple[tuple[CanonicalOutcome, frozenset[int]], ...]


def _outcome_key(outcome: CanonicalOutcome) -> tuple[str, int, int]:
    return (
        outcome.production,
        outcome.alternative,
        1 if isinstance(outcome, ExitOutcome) else 0,
    )


def _leaf_for_outcome(outcome: CanonicalOutcome) -> DecisionLeaf:
    if isinstance(outcome, ExitOutcome):
        return ExitDecision(outcome)
    return CommitAlternative(outcome)


class _DecisionSemantics:
    def __init__(self, source: CanonicalDecisionSource) -> None:
        self.source = source
        self.languages = {
            item.outcome: item.language for item in source.languages
        }
        self._viability: dict[
            tuple[CanonicalOutcome, frozenset[int], int],
            bool,
        ] = {}

    def initial_state(self) -> _BuildState:
        return _BuildState(
            0,
            self.source.lookahead,
            tuple(
                sorted(
                    (
                        (item.outcome, frozenset({item.language.root}))
                        for item in self.source.languages
                    ),
                    key=lambda item: _outcome_key(item[0]),
                )
            ),
        )

    def derivative(
        self,
        language: SymbolicLanguage,
        residual: frozenset[int],
        token: str,
    ) -> frozenset[int]:
        return frozenset(
            edge.target
            for state in residual
            for edge in language.nodes[state].edges
            if token in edge.predicate.token_types
        )

    def can_accept(
        self,
        outcome: CanonicalOutcome,
        residual: frozenset[int],
        remaining: int,
    ) -> bool:
        key = (outcome, residual, remaining)
        cached = self._viability.get(key)
        if cached is not None:
            return cached
        language = self.languages[outcome]
        if any(language.nodes[state].accepting for state in residual):
            self._viability[key] = True
            return True
        if remaining <= 0:
            self._viability[key] = False
            return False
        reachable = frozenset(
            edge.target
            for state in residual
            for edge in language.nodes[state].edges
        )
        result = bool(reachable) and self.can_accept(
            outcome,
            reachable,
            remaining - 1,
        )
        self._viability[key] = result
        return result

    def normalize(self, state: _BuildState) -> _BuildState:
        return _BuildState(
            state.offset,
            state.remaining,
            tuple(
                (outcome, residual)
                for outcome, residual in state.residuals
                if self.can_accept(outcome, residual, state.remaining)
            ),
        )

    def expected_tokens(self, state: _BuildState) -> tuple[str, ...]:
        tokens = {
            token
            for outcome, residual in state.residuals
            for node in residual
            for edge in self.languages[outcome].nodes[node].edges
            for token in edge.predicate.token_types
        }
        return tuple(sorted(tokens))

    def successor(self, state: _BuildState, token: str) -> _BuildState:
        return _BuildState(
            state.offset + 1,
            state.remaining - 1,
            tuple(
                (
                    outcome,
                    self.derivative(self.languages[outcome], residual, token),
                )
                for outcome, residual in state.residuals
            ),
        )

    def end_outcomes(
        self,
        state: _BuildState,
    ) -> tuple[CanonicalOutcome, ...]:
        accepting = []
        for outcome, residual in state.residuals:
            derivative = self.derivative(
                self.languages[outcome],
                residual,
                "$",
            )
            if any(
                self.languages[outcome].nodes[node].accepting
                for node in derivative
            ):
                accepting.append(outcome)
        return tuple(accepting)


class _DagBuilder:
    def __init__(self, source: CanonicalDecisionSource) -> None:
        self.source = source
        self.semantics = _DecisionSemantics(source)
        self.nodes: list[DecisionNode] = []
        self.node_index: dict[DecisionNode, int] = {}
        self.state_nodes: dict[_BuildState, int] = {}

    def intern(self, node: DecisionNode) -> int:
        existing = self.node_index.get(node)
        if existing is not None:
            return existing
        position = len(self.nodes)
        self.nodes.append(node)
        self.node_index[node] = position
        return position

    def build_state(self, raw_state: _BuildState) -> int:
        state = self.semantics.normalize(raw_state)
        cached = self.state_nodes.get(state)
        if cached is not None:
            return cached
        viable = tuple(outcome for outcome, _ in state.residuals)
        if not viable:
            target = self.intern(ImmediateError(()))
        elif len(viable) == 1:
            target = self.intern(_leaf_for_outcome(viable[0]))
        elif state.remaining <= 0:
            raise ValueError(
                "canonical decision remains ambiguous at lookahead limit"
            )
        else:
            expected = self.semantics.expected_tokens(state)
            grouped: dict[object, list[str]] = defaultdict(list)
            successors: dict[object, _BuildState | tuple[CanonicalOutcome, ...]] = {}
            for token in expected:
                if token == "$":
                    end_outcomes = self.semantics.end_outcomes(state)
                    signature: object = ("end", end_outcomes)
                    successors[signature] = end_outcomes
                else:
                    successor = self.semantics.normalize(
                        self.semantics.successor(state, token)
                    )
                    signature = ("state", successor)
                    successors[signature] = successor
                grouped[signature].append(token)

            edges: list[DecisionEdge] = []
            for signature, tokens in sorted(
                grouped.items(),
                key=lambda item: tuple(item[1]),
            ):
                successor = successors[signature]
                if signature[0] == "end":
                    assert isinstance(successor, tuple)
                    if len(successor) > 1:
                        raise ValueError(
                            "canonical decision remains ambiguous at lookahead limit"
                        )
                    child = self.intern(
                        _leaf_for_outcome(successor[0])
                        if successor
                        else ImmediateError(expected)
                    )
                else:
                    assert isinstance(successor, _BuildState)
                    child = self.build_state(successor)
                edges.append(
                    DecisionEdge(TokenSetPredicate(tuple(tokens)), child)
                )
            target = self.intern(
                LookaheadDecision(
                    state.offset,
                    expected,
                    tuple(edges),
                )
            )
        self.state_nodes[state] = target
        return target


def _validate_source(source: CanonicalDecisionSource) -> None:
    if source.lookahead < 1:
        raise ValueError("lookahead must be at least 1")
    outcomes = tuple(item.outcome for item in source.languages)
    if len(set(outcomes)) != len(outcomes):
        raise ValueError("canonical decision outcomes must be unique")
    for item in source.languages:
        language = item.language
        if not 0 <= language.root < len(language.nodes):
            raise ValueError("symbolic language root is out of range")
        if any(
            not 0 <= edge.target < len(language.nodes)
            for node in language.nodes
            for edge in node.edges
        ):
            raise ValueError("symbolic language edge is out of range")


def build_decision_dag(
    source: CanonicalDecisionSource,
) -> CanonicalDecisionDag:
    _validate_source(source)
    builder = _DagBuilder(source)
    root = builder.build_state(builder.semantics.initial_state())
    incoming = Counter(
        edge.target
        for node in builder.nodes
        if isinstance(node, LookaheadDecision)
        for edge in node.edges
    )
    nodes = tuple(builder.nodes)
    stats = MappingProxyType({
        "source_states": sum(
            len(item.language.nodes) for item in source.languages
        ),
        "dag_states": len(nodes),
        "shared_states": sum(count > 1 for count in incoming.values()),
        "max_depth": max(
            (
                node.offset + 1
                for node in nodes
                if isinstance(node, LookaheadDecision)
            ),
            default=0,
        ),
    })
    dag = CanonicalDecisionDag(
        source.production,
        source.lookahead,
        root,
        nodes,
        stats,
    )
    validate_decision_dag(source, dag)
    return dag


def evaluate_decision(
    dag: CanonicalDecisionDag,
    lookahead: tuple[str, ...],
) -> DecisionLeaf:
    node = dag.nodes[dag.root]
    while isinstance(node, LookaheadDecision):
        if node.offset >= len(lookahead):
            return ImmediateError(node.expected)
        token = lookahead[node.offset]
        target = next(
            (
                edge.target
                for edge in node.edges
                if token in edge.predicate.token_types
            ),
            None,
        )
        if target is None:
            return ImmediateError(node.expected)
        node = dag.nodes[target]
    return node


@dataclass(frozen=True, slots=True)
class _VerifyState:
    offset: int
    remaining: int
    residuals: tuple[tuple[int, frozenset[int]], ...]


def _verifier_leaf(outcome: CanonicalOutcome) -> DecisionLeaf:
    if isinstance(outcome, ExitOutcome):
        return ExitDecision(outcome)
    return CommitAlternative(outcome)


def _verifier_derivative(
    language: SymbolicLanguage,
    residual: frozenset[int],
    token: str,
) -> frozenset[int]:
    targets: set[int] = set()
    for node_id in residual:
        for edge in language.nodes[node_id].edges:
            if token in edge.predicate.token_types:
                targets.add(edge.target)
    return frozenset(targets)


def _verifier_can_finish(
    language: SymbolicLanguage,
    residual: frozenset[int],
    remaining: int,
) -> bool:
    frontier = set(residual)
    for depth in range(remaining + 1):
        if any(language.nodes[node_id].accepting for node_id in frontier):
            return True
        if depth == remaining:
            break
        frontier = {
            edge.target
            for node_id in frontier
            for edge in language.nodes[node_id].edges
        }
        if not frontier:
            return False
    return False


def _normalize_verify_state(
    source: CanonicalDecisionSource,
    state: _VerifyState,
) -> _VerifyState:
    return _VerifyState(
        state.offset,
        state.remaining,
        tuple(
            (language_id, residual)
            for language_id, residual in state.residuals
            if _verifier_can_finish(
                source.languages[language_id].language,
                residual,
                state.remaining,
            )
        ),
    )


def _verifier_expected_tokens(
    source: CanonicalDecisionSource,
    state: _VerifyState,
) -> tuple[str, ...]:
    tokens: set[str] = set()
    for language_id, residual in state.residuals:
        language = source.languages[language_id].language
        for node_id in residual:
            for edge in language.nodes[node_id].edges:
                tokens.update(edge.predicate.token_types)
    return tuple(sorted(tokens))


def _verifier_successor(
    source: CanonicalDecisionSource,
    state: _VerifyState,
    token: str,
) -> _VerifyState:
    return _VerifyState(
        state.offset + 1,
        state.remaining - 1,
        tuple(
            (
                language_id,
                _verifier_derivative(
                    source.languages[language_id].language,
                    residual,
                    token,
                ),
            )
            for language_id, residual in state.residuals
        ),
    )


def _verifier_eof_outcomes(
    source: CanonicalDecisionSource,
    state: _VerifyState,
) -> tuple[CanonicalOutcome, ...]:
    outcomes: list[CanonicalOutcome] = []
    for language_id, residual in state.residuals:
        item = source.languages[language_id]
        derivative = _verifier_derivative(item.language, residual, "$")
        if any(item.language.nodes[node_id].accepting for node_id in derivative):
            outcomes.append(item.outcome)
    return tuple(outcomes)


def validate_decision_dag(
    source: CanonicalDecisionSource,
    dag: CanonicalDecisionDag,
) -> None:
    _validate_source(source)
    if dag.production != source.production:
        raise ValueError("DAG production does not match decision source")
    if dag.lookahead != source.lookahead:
        raise ValueError("DAG lookahead does not match decision source")
    if not 0 <= dag.root < len(dag.nodes):
        raise ValueError("DAG root is out of range")
    for node in dag.nodes:
        if isinstance(node, LookaheadDecision) and any(
            not 0 <= edge.target < len(dag.nodes) for edge in node.edges
        ):
            raise ValueError("DAG edge is out of range")

    initial = _VerifyState(
        0,
        source.lookahead,
        tuple(
            (language_id, frozenset({item.language.root}))
            for language_id, item in enumerate(source.languages)
        ),
    )
    checked: set[tuple[_VerifyState, int]] = set()

    def visit(raw_state: _VerifyState, node_id: int) -> None:
        state = _normalize_verify_state(source, raw_state)
        key = (state, node_id)
        if key in checked:
            return
        checked.add(key)
        node = dag.nodes[node_id]
        viable = tuple(
            source.languages[language_id].outcome
            for language_id, _ in state.residuals
        )
        if not viable:
            if not isinstance(node, ImmediateError):
                raise ValueError("DAG must reject a state without outcomes")
            return
        if len(viable) == 1:
            if node != _verifier_leaf(viable[0]):
                raise ValueError("DAG singleton outcome does not match source")
            return
        if state.remaining <= 0:
            raise ValueError(
                "canonical decision remains ambiguous at lookahead limit"
            )
        if not isinstance(node, LookaheadDecision):
            raise ValueError("DAG commits while multiple outcomes remain")
        if node.offset != state.offset:
            raise ValueError("DAG lookahead offset does not match source")
        expected = _verifier_expected_tokens(source, state)
        if node.expected != expected:
            raise ValueError("DAG expected tokens do not match source")
        targets: dict[str, int] = {}
        for edge in node.edges:
            for token in edge.predicate.token_types:
                if token in targets:
                    raise ValueError("DAG edge predicates overlap")
                targets[token] = edge.target
        if tuple(sorted(targets)) != expected:
            raise ValueError("DAG edge predicates do not cover expected tokens")
        for token in expected:
            target = targets[token]
            if token == "$":
                outcomes = _verifier_eof_outcomes(source, state)
                if len(outcomes) > 1:
                    raise ValueError(
                        "canonical decision remains ambiguous at lookahead limit"
                    )
                expected_leaf: DecisionLeaf = (
                    _verifier_leaf(outcomes[0])
                    if outcomes
                    else ImmediateError(expected)
                )
                if dag.nodes[target] != expected_leaf:
                    raise ValueError("DAG EOF outcome does not match source")
            else:
                visit(_verifier_successor(source, state, token), target)

    visit(initial, dag.root)
