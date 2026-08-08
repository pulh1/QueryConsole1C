from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping

from .analysis import MatcherDefinition
from .bsl_rendering import bsl_string
from .decision_dag import (
    DecisionLeaf,
    ImmediateError,
    LookaheadDecision,
)
from .parser_ir import CanonicalDecision


_END = "$"
_LOOKAHEAD_FUNCTION = "ТипТокенаПросмотра"


def _predicate(variable: str, token_types: tuple[str, ...]) -> str:
    comparisons = tuple(
        f"{variable} = Неопределено"
        if token == _END
        else f"{variable} = {bsl_string(token)}"
        for token in token_types
    )
    if not comparisons:
        raise ValueError("decision predicate must not be empty")
    return (
        comparisons[0]
        if len(comparisons) == 1
        else f"({' Или '.join(comparisons)})"
    )


class CanonicalDecisionRenderer:
    def __init__(
        self,
        matcher_definitions: tuple[MatcherDefinition, ...],
        *,
        named_predicates: Mapping[tuple[str, ...], str] | None = None,
    ) -> None:
        self._definitions = matcher_definitions
        self._labels_by_token_types: dict[tuple[str, ...], tuple[str, ...]] = {}
        labels: dict[tuple[str, ...], list[str]] = defaultdict(list)
        observed: set[str] = set()
        for definition in matcher_definitions:
            if definition.label in observed:
                raise ValueError(
                    f"duplicate matcher definition {definition.label!r}"
                )
            observed.add(definition.label)
            if not definition.token_types:
                raise ValueError(
                    f"matcher {definition.label!r} has empty token set"
                )
            if (
                definition.label == _END
                and definition.token_types != (_END,)
            ) or (
                definition.label != _END
                and _END in definition.token_types
            ):
                raise ValueError(
                    "reserved EOF matcher must map only '$' to '$'"
                )
            labels[definition.token_types].append(definition.label)
        self._labels_by_token_types = {
            token_types: tuple(names)
            for token_types, names in labels.items()
        }
        self._named_predicates = dict(named_predicates or {})
        for token_types, label in self._named_predicates.items():
            if label not in self._labels_by_token_types.get(token_types, ()):
                raise ValueError(
                    "named predicate must reference an exact matcher set"
                )

    def render(
        self,
        decision: CanonicalDecision,
        *,
        indent: str,
        token_prefix: str,
        render_leaf: Callable[[DecisionLeaf, str], list[str]],
    ) -> list[str]:
        if decision.source.production != decision.dag.production:
            raise ValueError("decision source and DAG productions differ")
        if decision.source.lookahead != decision.dag.lookahead:
            raise ValueError("decision source and DAG lookahead differ")
        if not token_prefix:
            raise ValueError("decision token prefix must not be empty")
        return self._render_node(
            decision,
            decision.dag.root,
            indent,
            token_prefix,
            render_leaf,
        )

    def _render_node(
        self,
        decision: CanonicalDecision,
        node_index: int,
        indent: str,
        token_prefix: str,
        render_leaf: Callable[[DecisionLeaf, str], list[str]],
    ) -> list[str]:
        node = decision.dag.nodes[node_index]
        if not isinstance(node, LookaheadDecision):
            return render_leaf(node, indent)

        variable = f"{token_prefix}{node.offset}"
        lines = [
            f"{indent}{variable} = {_LOOKAHEAD_FUNCTION}({node.offset});"
        ]
        token_types_by_target: dict[int, set[str]] = defaultdict(set)
        target_order: list[int] = []
        for edge in node.edges:
            if edge.target not in token_types_by_target:
                target_order.append(edge.target)
            token_types_by_target[edge.target].update(
                edge.predicate.token_types
            )
        for position, target in enumerate(target_order):
            keyword = "Если" if position == 0 else "ИначеЕсли"
            token_types = tuple(sorted(token_types_by_target[target]))
            label = self._named_predicates.get(token_types)
            predicate = (
                f"ТокенПринадлежитКлассу({variable}, {bsl_string(label)})"
                if label is not None
                else _predicate(variable, token_types)
            )
            lines.append(f"{indent}{keyword} {predicate} Тогда")
            lines.extend(
                self._render_node(
                    decision,
                    target,
                    indent + "\t",
                    token_prefix,
                    render_leaf,
                )
            )
        lines.append(f"{indent}Иначе")
        lines.extend(render_leaf(ImmediateError(node.expected), indent + "\t"))
        lines.append(f"{indent}КонецЕсли;")
        return lines
