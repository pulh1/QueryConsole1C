from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from .analysis import AnalysisResult, MatcherDefinition, _CompressedAnalysis


@dataclass(frozen=True, slots=True)
class TokenSetPredicate:
    token_types: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not self.token_types
            or tuple(sorted(set(self.token_types))) != self.token_types
        ):
            raise ValueError(
                "token predicate must be sorted, unique, and non-empty"
            )


@dataclass(frozen=True, slots=True)
class SymbolicLanguageEdge:
    predicate: TokenSetPredicate
    target: int


@dataclass(frozen=True, slots=True)
class SymbolicLanguageNode:
    accepting: bool
    edges: tuple[SymbolicLanguageEdge, ...]


@dataclass(frozen=True, slots=True)
class SymbolicLanguage:
    root: int
    nodes: tuple[SymbolicLanguageNode, ...]


@dataclass(frozen=True, slots=True)
class AlternativeOutcome:
    production: str
    alternative: int


@dataclass(frozen=True, slots=True)
class ExitOutcome:
    production: str
    alternative: int


CanonicalOutcome: TypeAlias = AlternativeOutcome | ExitOutcome


@dataclass(frozen=True, slots=True)
class OutcomeLanguage:
    outcome: CanonicalOutcome
    language: SymbolicLanguage


@dataclass(frozen=True, slots=True)
class CanonicalDecisionSource:
    production: str
    lookahead: int
    languages: tuple[OutcomeLanguage, ...]


def _require_compressed(analysis: AnalysisResult) -> _CompressedAnalysis:
    compressed = analysis._compressed
    if compressed is None:
        raise ValueError("compressed analysis is required for canonical decisions")
    return compressed


def _export_language(
    compressed: _CompressedAnalysis,
    position: int,
) -> SymbolicLanguage:
    root_state = compressed.descriptor_root(position)
    indexed: dict[tuple[object, int], int] = {(root_state, 0): 0}
    pending: list[tuple[object, int]] = [(root_state, 0)]
    nodes: list[SymbolicLanguageNode | None] = [None]

    while pending:
        state_value, depth = pending.pop(0)
        state = state_value
        node_index = indexed[(state, depth)]
        edges: list[SymbolicLanguageEdge] = []
        if depth < compressed.k:
            for matcher_id, target_state in compressed.factor_state_children(
                state
            ):
                target_key = (target_state, depth + 1)
                target = indexed.get(target_key)
                if target is None:
                    target = len(nodes)
                    indexed[target_key] = target
                    nodes.append(None)
                    pending.append(target_key)
                edges.append(
                    SymbolicLanguageEdge(
                        TokenSetPredicate(
                            compressed.matcher_token_types(matcher_id)
                        ),
                        target,
                    )
                )
        nodes[node_index] = SymbolicLanguageNode(
            depth == compressed.k
            or compressed.factor_state_terminal(state),
            tuple(
                sorted(
                    edges,
                    key=lambda edge: (edge.predicate.token_types, edge.target),
                )
            ),
        )

    return SymbolicLanguage(
        0,
        tuple(node for node in nodes if node is not None),
    )


def build_canonical_decision_source(
    analysis: AnalysisResult,
    production: str,
    *,
    exit_alternative: int | None = None,
) -> CanonicalDecisionSource:
    compressed = _require_compressed(analysis)
    positions = compressed.select_positions(production)
    if exit_alternative is not None and sum(
        alternative == exit_alternative for _, alternative in positions
    ) != 1:
        raise ValueError("exit alternative must exist exactly once")
    languages = tuple(
        OutcomeLanguage(
            ExitOutcome(production, alternative)
            if alternative == exit_alternative
            else AlternativeOutcome(production, alternative),
            _export_language(compressed, position),
        )
        for position, alternative in positions
    )
    return CanonicalDecisionSource(production, analysis.k, languages)


def canonical_matcher_definitions(
    analysis: AnalysisResult,
) -> tuple[MatcherDefinition, ...]:
    compressed = _require_compressed(analysis)
    return tuple(
        MatcherDefinition(
            compressed.matcher_labels[matcher_id],
            compressed.matcher_token_types(matcher_id),
        )
        for matcher_id in compressed.matcher_definition_order
    )


def intersect_languages(
    left: SymbolicLanguage,
    right: SymbolicLanguage,
) -> SymbolicLanguage:
    indexed = {(left.root, right.root): 0}
    pending = [(left.root, right.root)]
    nodes: list[SymbolicLanguageNode | None] = [None]

    while pending:
        left_state, right_state = pending.pop(0)
        node_index = indexed[(left_state, right_state)]
        targets: dict[int, set[str]] = {}
        for left_edge in left.nodes[left_state].edges:
            left_tokens = frozenset(left_edge.predicate.token_types)
            for right_edge in right.nodes[right_state].edges:
                token_types = left_tokens.intersection(
                    right_edge.predicate.token_types
                )
                if not token_types:
                    continue
                target_key = (left_edge.target, right_edge.target)
                target = indexed.get(target_key)
                if target is None:
                    target = len(nodes)
                    indexed[target_key] = target
                    nodes.append(None)
                    pending.append(target_key)
                targets.setdefault(target, set()).update(token_types)
        nodes[node_index] = SymbolicLanguageNode(
            left.nodes[left_state].accepting
            and right.nodes[right_state].accepting,
            tuple(
                SymbolicLanguageEdge(
                    TokenSetPredicate(tuple(sorted(token_types))),
                    target,
                )
                for target, token_types in sorted(
                    targets.items(),
                    key=lambda item: (tuple(sorted(item[1])), item[0]),
                )
            ),
        )

    return SymbolicLanguage(
        0,
        tuple(node for node in nodes if node is not None),
    )


def _language_is_empty(language: SymbolicLanguage) -> bool:
    pending = [language.root]
    visited: set[int] = set()
    while pending:
        node_index = pending.pop()
        if node_index in visited:
            continue
        visited.add(node_index)
        node = language.nodes[node_index]
        if node.accepting:
            return False
        pending.extend(edge.target for edge in node.edges)
    return True


def specialize_outcome(
    source: CanonicalDecisionSource,
    outcome: CanonicalOutcome,
    callee: CanonicalDecisionSource,
) -> CanonicalDecisionSource:
    if source.lookahead != callee.lookahead:
        raise ValueError("caller and callee lookahead must match")
    matching = tuple(
        item for item in source.languages if item.outcome == outcome
    )
    if len(matching) != 1:
        raise ValueError("specialized outcome must exist exactly once")
    caller_language = matching[0].language
    languages: list[OutcomeLanguage] = []
    for item in source.languages:
        if item.outcome != outcome:
            languages.append(item)
            continue
        for callee_item in callee.languages:
            intersection = intersect_languages(
                caller_language,
                callee_item.language,
            )
            if not _language_is_empty(intersection):
                languages.append(
                    OutcomeLanguage(callee_item.outcome, intersection)
                )
    return CanonicalDecisionSource(
        source.production,
        source.lookahead,
        tuple(languages),
    )
