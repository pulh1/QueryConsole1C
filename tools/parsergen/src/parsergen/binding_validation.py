from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import Diagnostic, DiagnosticBag, Severity, SourceSpan
from .model import Action, Constant, IdentifierRef, NonterminalCall
from .source_model import (
    BindingMode,
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
    SourceGrammar,
    SourceGroup,
    SourceItem,
    SourceOptional,
    SourceRepeat,
    SourceSequence,
    SourceValue,
)


@dataclass(frozen=True, slots=True)
class BindingCardinality:
    min_values: int
    max_values: int | None


@dataclass(frozen=True, slots=True)
class BindingValidationReport:
    diagnostics: tuple[Diagnostic, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.diagnostics)


def validate_bindings(grammar: SourceGrammar) -> BindingValidationReport:
    validator = _BindingValidator(grammar)
    return BindingValidationReport(validator.run())


class _BindingValidator:
    def __init__(self, grammar: SourceGrammar) -> None:
        self.grammar = grammar
        self.bag = DiagnosticBag()
        self._reported: set[tuple[str, str, int]] = set()

    def run(self) -> tuple[Diagnostic, ...]:
        for production in self.grammar.productions:
            if not any(
                _contains_directive(alternative.body)
                for alternative in production.alternatives
            ):
                continue
            for alternative in production.alternatives:
                self._validate_alternative(alternative.body)
        return self.bag.sorted()

    def _validate_alternative(self, sequence: SourceSequence) -> None:
        constructors = _collect(sequence, SourceConstructor)
        bindings = _collect(
            sequence,
            (SourceBinding, SourceConstantBinding),
        )
        actions = _collect(sequence, Action)

        if actions:
            self._add(
                "BIND205",
                "legacy action cannot be mixed with canonical directives",
                actions[0].span,
            )

        top_level_constructors = tuple(
            item
            for item in sequence.items
            if isinstance(item, SourceConstructor)
        )
        if len(constructors) > 1:
            self._add(
                "BIND200",
                "alternative must have exactly one constructor",
                constructors[1].span,
            )
        elif constructors and not top_level_constructors:
            self._add(
                "BIND200",
                "constructor must be declared at alternative scope",
                constructors[0].span,
            )

        constructor = (
            top_level_constructors[0]
            if len(top_level_constructors) == 1
            else None
        )
        if bindings and constructor is None:
            self._add(
                "BIND201",
                "binding requires an active constructor",
                bindings[0].span,
            )
        elif constructor is not None:
            earlier = next(
                (
                    item
                    for item in bindings
                    if item.span.start.offset < constructor.span.start.offset
                ),
                None,
            )
            if earlier is not None:
                self._add(
                    "BIND200",
                    "constructor must precede every binding",
                    earlier.span,
                )

        modes: dict[str, set[BindingMode]] = {}
        for binding in bindings:
            mode = (
                binding.mode
                if isinstance(binding, SourceBinding)
                else BindingMode.SCALAR
            )
            modes.setdefault(binding.property, set()).add(mode)
            if isinstance(binding, SourceConstantBinding):
                if not _valid_constant(binding.value):
                    self._add(
                        "BIND204",
                        "constant binding value is not allowed",
                        binding.span,
                        binding.property,
                    )
            elif (
                mode is BindingMode.SCALAR
                and _cardinality(binding.value).max_values != 1
            ):
                self._add(
                    "BIND203",
                    "scalar binding cannot produce multiple values",
                    binding.span,
                    binding.property,
                )

        for property_name, property_modes in modes.items():
            if len(property_modes) > 1:
                conflict = next(
                    item
                    for item in bindings
                    if item.property == property_name
                )
                self._add(
                    "BIND202",
                    "property mixes scalar and collection binding modes",
                    conflict.span,
                    property_name,
                )

        self._validate_paths(sequence, [frozenset()], repeated=False)

        if not constructors and not bindings:
            semantic_counts = _semantic_child_counts(sequence)
            if any(count > 1 for count in semantic_counts):
                self._add(
                    "BIND206",
                    "transparent alternative has multiple semantic children",
                    sequence.span,
                )

    def _validate_paths(
        self,
        sequence: SourceSequence,
        paths: list[frozenset[str]],
        *,
        repeated: bool,
    ) -> list[frozenset[str]]:
        current = paths
        for item in sequence.items:
            if isinstance(item, SourceBinding):
                if item.mode is BindingMode.SCALAR:
                    if repeated:
                        self._add(
                            "BIND203",
                            "scalar binding cannot execute in a repeat",
                            item.span,
                            item.property,
                        )
                    updated: list[frozenset[str]] = []
                    for path in current:
                        if item.property in path:
                            self._add(
                                "BIND203",
                                "scalar property is assigned twice on one path",
                                item.span,
                                item.property,
                            )
                        updated.append(path | {item.property})
                    current = updated
                current = self._walk_value(item.value, current, repeated)
            elif isinstance(item, SourceConstantBinding):
                updated = []
                for path in current:
                    if item.property in path:
                        self._add(
                            "BIND203",
                            "scalar property is assigned twice on one path",
                            item.span,
                            item.property,
                        )
                    updated.append(path | {item.property})
                current = updated
            elif isinstance(item, SourceGroup):
                current = self._walk_group(item, current, repeated)
            elif isinstance(item, SourceRepeat):
                present = self._walk_value(item.body, current, True)
                current = [*current, *present]
            elif isinstance(item, SourceOptional):
                present = self._walk_value(item.body, current, repeated)
                current = [*current, *present]
        return current

    def _walk_value(
        self,
        value: SourceValue,
        paths: list[frozenset[str]],
        repeated: bool,
    ) -> list[frozenset[str]]:
        if isinstance(value, SourceGroup):
            return self._walk_group(value, paths, repeated)
        if isinstance(value, SourceRepeat):
            present = self._walk_value(value.body, paths, True)
            return [*paths, *present]
        if isinstance(value, SourceOptional):
            present = self._walk_value(value.body, paths, repeated)
            return [*paths, *present]
        return paths

    def _walk_group(
        self,
        group: SourceGroup,
        paths: list[frozenset[str]],
        repeated: bool,
    ) -> list[frozenset[str]]:
        return [
            result
            for alternative in group.alternatives
            for result in self._validate_paths(
                alternative.body,
                list(paths),
                repeated=repeated,
            )
        ]

    def _add(
        self,
        code: str,
        message: str,
        span: SourceSpan,
        property_name: str = "",
    ) -> None:
        key = (code, property_name, span.start.offset)
        if key in self._reported:
            return
        self._reported.add(key)
        self.bag.add(Diagnostic(code, Severity.ERROR, message, span))


def _contains_directive(sequence: SourceSequence) -> bool:
    return bool(
        _collect(
            sequence,
            (SourceConstructor, SourceBinding, SourceConstantBinding),
        )
    )


def _collect(sequence: SourceSequence, kinds):
    result = []
    for item in sequence.items:
        if isinstance(item, kinds):
            result.append(item)
        if isinstance(item, SourceGroup):
            for alternative in item.alternatives:
                result.extend(_collect(alternative.body, kinds))
        elif isinstance(item, (SourceRepeat, SourceOptional)):
            result.extend(_collect_value(item.body, kinds))
        elif isinstance(item, SourceBinding):
            result.extend(_collect_value(item.value, kinds))
    return tuple(result)


def _collect_value(value: SourceValue, kinds):
    if isinstance(value, SourceGroup):
        return tuple(
            item
            for alternative in value.alternatives
            for item in _collect(alternative.body, kinds)
        )
    if isinstance(value, (SourceRepeat, SourceOptional)):
        return _collect_value(value.body, kinds)
    return ()


def _cardinality(value: SourceValue) -> BindingCardinality:
    if isinstance(value, SourceOptional):
        return BindingCardinality(0, 1)
    if isinstance(value, SourceRepeat):
        return BindingCardinality(
            0 if value.kind.value == "star" else 1,
            None,
        )
    if isinstance(value, SourceGroup):
        cardinalities = tuple(
            _sequence_value_cardinality(alternative.body)
            for alternative in value.alternatives
        )
        maximums = tuple(item.max_values for item in cardinalities)
        return BindingCardinality(
            min(item.min_values for item in cardinalities),
            (
                None
                if any(item is None for item in maximums)
                else max(item for item in maximums if item is not None)
            ),
        )
    return BindingCardinality(1, 1)


def _sequence_value_cardinality(
    sequence: SourceSequence,
) -> BindingCardinality:
    semantic = [
        item
        for item in sequence.items
        if isinstance(item, (NonterminalCall, IdentifierRef, Constant))
    ]
    count = len(semantic)
    return BindingCardinality(count, count)


def _valid_constant(value: str) -> bool:
    return value in {"Истина", "Ложь", "Неопределено"} or "." in value


def _semantic_child_counts(sequence: SourceSequence) -> tuple[int, ...]:
    counts = (0,)
    for item in sequence.items:
        if isinstance(item, (NonterminalCall, IdentifierRef, Constant)):
            counts = tuple(value + 1 for value in counts)
        elif isinstance(item, SourceGroup):
            counts = tuple(
                base + branch
                for base in counts
                for alternative in item.alternatives
                for branch in _semantic_child_counts(alternative.body)
            )
        elif isinstance(item, SourceOptional):
            nested = _value_semantic_counts(item.body)
            counts = tuple(
                base + extra
                for base in counts
                for extra in (0, *nested)
            )
        elif isinstance(item, SourceRepeat):
            nested = _value_semantic_counts(item.body)
            if any(value for value in nested):
                return (2,)
    return counts


def _value_semantic_counts(value: SourceValue) -> tuple[int, ...]:
    if isinstance(value, SourceGroup):
        return tuple(
            count
            for alternative in value.alternatives
            for count in _semantic_child_counts(alternative.body)
        )
    if isinstance(value, (NonterminalCall, IdentifierRef, Constant)):
        return (1,)
    return (0,)
