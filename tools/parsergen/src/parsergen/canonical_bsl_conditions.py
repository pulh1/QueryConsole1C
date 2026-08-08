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

    def for_alternative_with_unique_first(
        self,
        decision: CanonicalDecision,
        alternative: int,
    ) -> str:
        return self.for_alternatives_with_unique_first(
            decision,
            (alternative,),
        )

    def for_alternatives_with_unique_first(
        self,
        decision: CanonicalDecision,
        alternatives: tuple[int, ...],
    ) -> str:
        exact = self.for_alternatives(decision, alternatives)
        requested = set(alternatives)
        requested_tokens = self._first_token_types(
            decision,
            requested,
        )
        competing_tokens = self._first_token_types(
            decision,
            {
                row.alternative
                for row in decision.rows
                if row.alternative not in requested
            },
        )
        unique_tokens = tuple(
            token
            for token in requested_tokens
            if token not in competing_tokens
        )
        if not unique_tokens:
            return exact
        prefix = self._token_types(unique_tokens, 0)
        if len(unique_tokens) == len(requested_tokens):
            return prefix if prefix.startswith("(") else f"({prefix})"
        return f"({exact} Или {prefix})"

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
            row.matchers
            for row in decision.rows
            if row.alternative in requested
        )
        return self._rows(rows, 0)

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

    def _rows(
        self,
        rows: tuple[tuple[str, ...], ...],
        offset: int,
    ) -> str:
        by_label: dict[str, list[tuple[str, ...]]] = {}
        for row in rows:
            if not row:
                raise ValueError("canonical row has empty matcher sequence")
            by_label.setdefault(row[0], []).append(row[1:])

        grouped: dict[
            tuple[tuple[str, ...], ...] | None,
            list[str],
        ] = {}
        for label, tails in by_label.items():
            unique_tails = tuple(sorted(set(tails)))
            signature = None if () in unique_tails else unique_tails
            grouped.setdefault(signature, []).append(label)

        branches: list[str] = []
        for signature, labels in grouped.items():
            prefix = self._matchers(tuple(labels), offset)
            if signature is None:
                branches.append(prefix)
            else:
                suffix = self._rows(signature, offset + 1)
                branches.append(f"({prefix} И {suffix})")
        if len(branches) == 1:
            branch = branches[0]
            return branch if branch.startswith("(") else f"({branch})"
        return f"({' Или '.join(branches)})"

    def _matchers(self, labels: tuple[str, ...], offset: int) -> str:
        token_types: list[str] = []
        for label in labels:
            matched_types = self._by_label.get(label)
            if matched_types is None:
                raise ValueError(f"unknown matcher {label!r}")
            for token_type in matched_types:
                if token_type not in token_types:
                    token_types.append(token_type)
        return self._token_types(tuple(token_types), offset)

    def _first_token_types(
        self,
        decision: CanonicalDecision,
        alternatives: set[int],
    ) -> tuple[str, ...]:
        result: list[str] = []
        for row in decision.rows:
            if row.alternative not in alternatives:
                continue
            label = row.matchers[0]
            matched_types = self._by_label.get(label)
            if matched_types is None:
                raise ValueError(f"unknown matcher {label!r}")
            for token_type in matched_types:
                if token_type not in result:
                    result.append(token_type)
        return tuple(result)

    def _token_types(
        self,
        token_types: tuple[str, ...],
        offset: int,
    ) -> str:
        lookahead = f"{_LOOKAHEAD_FUNCTION}({offset})"
        comparisons = [
            (
                f"{lookahead} = Неопределено"
                if token_type == _END_MATCHER
                else f"{lookahead} = {bsl_string(token_type)}"
            )
            for token_type in token_types
        ]
        if len(comparisons) == 1:
            return comparisons[0]
        return f"({' Или '.join(comparisons)})"
