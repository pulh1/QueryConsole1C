from __future__ import annotations

from .analysis import MatcherDefinition
from .bsl_rendering import bsl_string
from .parser_ir import CanonicalDecision


_LOOKAHEAD_FUNCTION = "ТипТокенаПросмотра"
_END_MATCHER = "$"


class CanonicalConditionRenderer:
    def __init__(
        self,
        matcher_definitions: tuple[MatcherDefinition, ...],
    ) -> None:
        self._definitions = matcher_definitions
        self._by_label: dict[str, tuple[str, ...]] = {}
        for definition in matcher_definitions:
            if definition.label in self._by_label:
                raise ValueError(
                    f"duplicate matcher definition {definition.label!r}"
                )
            if not definition.token_types:
                raise ValueError(
                    f"matcher {definition.label!r} has empty token set"
                )
            if (
                definition.label == _END_MATCHER
                and definition.token_types != (_END_MATCHER,)
            ) or (
                definition.label != _END_MATCHER
                and _END_MATCHER in definition.token_types
            ):
                raise ValueError(
                    "reserved EOF matcher must map only '$' to '$'"
                )
            self._by_label[definition.label] = definition.token_types

    def for_alternative(
        self,
        decision: CanonicalDecision,
        alternative: int,
    ) -> str:
        return self.for_alternatives(decision, (alternative,))

    def for_alternatives(
        self,
        decision: CanonicalDecision,
        alternatives: tuple[int, ...],
    ) -> str:
        self._validate_decision(decision)
        if not alternatives:
            raise ValueError("at least one alternative is required")
        if len(set(alternatives)) != len(alternatives):
            raise ValueError("requested alternatives must be unique")
        requested = set(alternatives)
        observed = {
            row.alternative
            for row in decision.rows
            if row.alternative in requested
        }
        missing = requested - observed
        if missing:
            formatted = ", ".join(str(item) for item in sorted(missing))
            raise ValueError(
                f"alternative {formatted} has no canonical rows"
            )
        rows = tuple(
            self._row(row.matchers)
            for row in decision.rows
            if row.alternative in requested
        )
        if len(rows) == 1:
            return rows[0]
        return f"({' Или '.join(rows)})"

    def _validate_decision(self, decision: CanonicalDecision) -> None:
        if decision.matcher_definitions != self._definitions:
            raise ValueError(
                "decision matcher definitions do not match renderer"
            )
        for row in decision.rows:
            if row.production != decision.production:
                raise ValueError(
                    "canonical row belongs to another production"
                )

    def _row(self, matchers: tuple[str, ...]) -> str:
        if not matchers:
            raise ValueError("canonical row has empty matcher sequence")
        conditions = tuple(
            self._matcher(label, offset)
            for offset, label in enumerate(matchers)
        )
        return f"({' И '.join(conditions)})"

    def _matcher(self, label: str, offset: int) -> str:
        token_types = self._by_label.get(label)
        if token_types is None:
            raise ValueError(f"unknown matcher {label!r}")
        lookahead = f"{_LOOKAHEAD_FUNCTION}({offset})"
        if label == _END_MATCHER:
            return f"{lookahead} = Неопределено"
        comparisons = tuple(
            f"{lookahead} = {bsl_string(token_type)}"
            for token_type in token_types
        )
        if len(comparisons) == 1:
            return comparisons[0]
        return f"({' Или '.join(comparisons)})"
