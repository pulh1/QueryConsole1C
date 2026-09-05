from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .diagnostics import Diagnostic, DiagnosticBag, Severity, SourceSpan
from .model import (
    Action,
    Constant,
    IdentifierRef,
    Lexeme,
    NonterminalCall,
    Terminal,
)
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


class _ResultKind(Enum):
    NONE = 0
    RAW = 1
    SEMANTIC = 2
    MULTIPLE = 3


@dataclass(frozen=True, slots=True)
class _SourceOperationResult:
    item: SourceItem
    kind: _ResultKind


def validate_bindings(grammar: SourceGrammar) -> BindingValidationReport:
    validator = _BindingValidator(grammar)
    return BindingValidationReport(validator.run())


class _BindingValidator:
    def __init__(self, grammar: SourceGrammar) -> None:
        self.grammar = grammar
        self.bag = DiagnosticBag()
        self._reported: set[tuple[str, str | None, int]] = set()

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
        all_bindings = _collect(
            sequence,
            (SourceBinding, SourceConstantBinding),
        )
        bindings = tuple(
            item
            for item in all_bindings
            if not (
                isinstance(item, SourceConstantBinding)
                and item.property is None
            )
        )
        wrap_bindings = tuple(
            item
            for item in bindings
            if isinstance(item, SourceBinding)
            and item.mode in (BindingMode.WRAP, BindingMode.WRAP_PREPEND)
        )
        node_bindings = tuple(
            item
            for item in bindings
            if item not in wrap_bindings
            and not (
                isinstance(item, SourceBinding)
                and item.mode is BindingMode.DISCARD
            )
        )
        actions = _collect(sequence, Action)

        self._validate_transparent_constants(sequence)

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
        self._validate_wrap_bindings(
            sequence,
            wrap_bindings,
            constructor,
        )

        if node_bindings and constructor is None:
            self._add(
                "BIND201",
                "binding requires an active constructor",
                node_bindings[0].span,
            )
        elif constructor is not None:
            earlier = next(
                (
                    item
                    for item in node_bindings
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

        modes: dict[str | None, set[BindingMode]] = {}
        for binding in bindings:
            mode = (
                binding.mode
                if isinstance(binding, SourceBinding)
                else BindingMode.SCALAR
            )
            if mode not in (
                BindingMode.DISCARD,
                BindingMode.WRAP,
                BindingMode.WRAP_PREPEND,
            ):
                modes.setdefault(binding.property, set()).add(mode)
            if (
                binding.property is not None
                and ("." in binding.property or "[" in binding.property)
                and mode is not BindingMode.EXTEND
            ):
                self._add(
                    "BIND211",
                    "member path is only supported by collection extend binding",
                    binding.span,
                    binding.property,
                )
            elif isinstance(binding, SourceConstantBinding):
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
            elif (
                mode is BindingMode.CONCAT
                and not isinstance(
                    binding.value,
                    (Constant, IdentifierRef, Lexeme, Terminal),
                )
            ):
                self._add(
                    "BIND207",
                    "concat binding requires terminal or identifier value",
                    binding.span,
                    binding.property,
                )
            elif (
                mode is BindingMode.INCREMENT
                and not isinstance(
                    binding.value,
                    (Constant, IdentifierRef, Lexeme, Terminal),
                )
            ):
                self._add(
                    "BIND209",
                    "increment binding requires terminal or identifier value",
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
                    "property mixes binding modes",
                    conflict.span,
                    property_name,
                )

        self._validate_paths(sequence, {frozenset()}, repeated=False)

        has_transparent_constant = any(
            isinstance(item, SourceConstantBinding)
            and item.property is None
            for item in sequence.items
        )
        if not constructors and not bindings and not has_transparent_constant:
            semantic_counts = semantic_child_counts(sequence)
            if any(count > 1 for count in semantic_counts):
                self._add(
                    "BIND206",
                    "transparent alternative has multiple semantic children",
                    sequence.span,
                )

    def _validate_wrap_bindings(
        self,
        sequence: SourceSequence,
        bindings: tuple[SourceBinding, ...],
        constructor: SourceConstructor | None,
    ) -> None:
        for binding in bindings:
            valid = constructor is None and binding in sequence.items
            if valid:
                index = sequence.items.index(binding)
                before = SourceSequence(sequence.items[:index], sequence.span)
                after = SourceSequence(sequence.items[index + 1 :], sequence.span)
                seed_counts = _semantic_execution_counts(before)
                valid = bool(seed_counts) and all(
                    count == 1 for count in seed_counts
                )
                valid = valid and bool(before.items)
                valid = valid and _source_operation_result(
                    before.items[-1]
                ).kind is _ResultKind.SEMANTIC
                valid = valid and semantic_child_counts(after) == (0,)
                value = binding.value
                valid = valid and not isinstance(value, SourceRepeat)
                child = value.body if isinstance(value, SourceOptional) else value
                valid = valid and _value_semantic_counts(child) == (1,)
            if not valid:
                self._add(
                    "BIND210",
                    "returned-child decorator requires one seed and one semantic child",
                    binding.span,
                    binding.property,
                )

    def _validate_transparent_constants(
        self,
        sequence: SourceSequence,
    ) -> None:
        constants = tuple(
            item
            for item in sequence.items
            if isinstance(item, SourceConstantBinding)
            and item.property is None
        )
        if constants:
            if not all(_valid_constant(item.value) for item in constants):
                invalid = next(
                    item
                    for item in constants
                    if not _valid_constant(item.value)
                )
                self._add(
                    "BIND204",
                    "constant binding value is not allowed",
                    invalid.span,
                )
            has_constructor = any(
                isinstance(item, SourceConstructor)
                for item in sequence.items
            )
            semantic_counts = semantic_child_counts(sequence)
            if (
                len(constants) > 1
                or has_constructor
                or semantic_counts != (1,)
            ):
                self._add(
                    "BIND208",
                    "transparent constant must be the only semantic result",
                    constants[-1].span,
                )

        for item in sequence.items:
            if isinstance(item, SourceGroup):
                for alternative in item.alternatives:
                    self._validate_transparent_constants(alternative.body)
            elif isinstance(item, (SourceRepeat, SourceOptional)):
                self._validate_transparent_primary(item.body)
            elif isinstance(item, SourceBinding):
                self._validate_transparent_value(item.value)

    def _validate_transparent_primary(self, primary) -> None:
        if isinstance(primary, SourceGroup):
            for alternative in primary.alternatives:
                self._validate_transparent_constants(alternative.body)

    def _validate_transparent_value(self, value) -> None:
        if isinstance(value, (SourceRepeat, SourceOptional)):
            self._validate_transparent_primary(value.body)
        elif isinstance(value, SourceGroup):
            self._validate_transparent_primary(value)

    def _validate_paths(
        self,
        sequence: SourceSequence,
        paths: set[frozenset[str]],
        *,
        repeated: bool,
    ) -> set[frozenset[str]]:
        current = paths
        for item in sequence.items:
            if isinstance(item, SourceBinding):
                if item.mode is BindingMode.SCALAR:
                    assert item.property is not None
                    if repeated:
                        self._add(
                            "BIND203",
                            "scalar binding cannot execute in a repeat",
                            item.span,
                            item.property,
                        )
                    updated: set[frozenset[str]] = set()
                    for path in current:
                        if item.property in path:
                            self._add(
                                "BIND203",
                                "scalar property is assigned twice on one path",
                                item.span,
                                item.property,
                            )
                        updated.add(path | {item.property})
                    current = updated
                current = self._walk_value(item.value, current, repeated)
            elif isinstance(item, SourceConstantBinding):
                if item.property is None:
                    continue
                updated = set()
                for path in current:
                    if item.property in path:
                        self._add(
                            "BIND203",
                            "scalar property is assigned twice on one path",
                            item.span,
                            item.property,
                        )
                    updated.add(path | {item.property})
                current = updated
            elif isinstance(item, SourceGroup):
                current = self._walk_group(item, current, repeated)
            elif isinstance(item, SourceRepeat):
                present = self._walk_value(item.body, current, True)
                current = current | present
            elif isinstance(item, SourceOptional):
                present = self._walk_value(item.body, current, repeated)
                current = current | present
        return current

    def _walk_value(
        self,
        value: SourceValue,
        paths: set[frozenset[str]],
        repeated: bool,
    ) -> set[frozenset[str]]:
        if isinstance(value, SourceGroup):
            return self._walk_group(value, paths, repeated)
        if isinstance(value, SourceRepeat):
            present = self._walk_value(value.body, paths, True)
            return paths | present
        if isinstance(value, SourceOptional):
            present = self._walk_value(value.body, paths, repeated)
            return paths | present
        return paths

    def _walk_group(
        self,
        group: SourceGroup,
        paths: set[frozenset[str]],
        repeated: bool,
    ) -> set[frozenset[str]]:
        return {
            result
            for alternative in group.alternatives
            for result in self._validate_paths(
                alternative.body,
                paths,
                repeated=repeated,
            )
        }

    def _add(
        self,
        code: str,
        message: str,
        span: SourceSpan,
        property_name: str | None = "",
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
            (
                SourceConstructor,
                SourceBinding,
                SourceConstantBinding,
            ),
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
    semantic_children = [
        item
        for item in sequence.items
        if _value_category(item) == 1
    ]
    semantic = semantic_children or [
        item
        for item in sequence.items
        if _value_category(item) == 2
    ]
    count = len(semantic)
    return BindingCardinality(count, count)


def _value_category(value: object) -> int:
    if isinstance(value, (NonterminalCall, IdentifierRef, Constant)):
        return 1
    if isinstance(value, (Terminal, Lexeme)):
        return 2
    return 0


def _valid_constant(value: str) -> bool:
    return value in {"Истина", "Ложь", "Неопределено", "Null"} or "." in value


def semantic_child_counts(sequence: SourceSequence) -> tuple[int, ...]:
    results = _branch_results(sequence)
    if any(result.kind is _ResultKind.MULTIPLE for result in results):
        return (2,)
    return (
        sum(
            result.kind is _ResultKind.SEMANTIC
            for result in results
        ),
    )


def _semantic_execution_counts(sequence: SourceSequence) -> tuple[int, ...]:
    counts = {0}
    for item in sequence.items:
        if isinstance(item, (NonterminalCall, IdentifierRef, Constant)) or (
            isinstance(item, SourceConstantBinding)
            and item.property is None
        ):
            counts = {value + 1 for value in counts}
        elif isinstance(item, SourceGroup):
            counts = {
                base + branch
                for base in counts
                for alternative in item.alternatives
                for branch in _semantic_execution_counts(alternative.body)
            }
        elif isinstance(item, SourceOptional):
            nested = _value_execution_counts(item.body)
            counts = {
                base + extra
                for base in counts
                for extra in (0, *nested)
            }
        elif isinstance(item, SourceRepeat):
            nested = _value_execution_counts(item.body)
            if any(nested):
                return (2,)
    return tuple(sorted(counts))


def _value_execution_counts(value: SourceValue) -> tuple[int, ...]:
    if isinstance(value, SourceOptional):
        return tuple(sorted({0, *_value_execution_counts(value.body)}))
    if isinstance(value, SourceRepeat):
        nested = _value_execution_counts(value.body)
        return (2,) if any(nested) else (0,)
    if isinstance(value, SourceGroup):
        return tuple(sorted({
            count
            for alternative in value.alternatives
            for count in _semantic_execution_counts(alternative.body)
        }))
    if isinstance(value, (NonterminalCall, IdentifierRef, Constant)):
        return (1,)
    return (0,)


def _value_semantic_counts(value: SourceValue) -> tuple[int, ...]:
    if isinstance(value, SourceOptional):
        return (0, *_value_semantic_counts(value.body))
    if isinstance(value, SourceRepeat):
        nested = _value_semantic_counts(value.body)
        return (2,) if any(nested) else (0,)
    if isinstance(value, SourceGroup):
        return tuple(
            count
            for alternative in value.alternatives
            for count in semantic_child_counts(alternative.body)
        )
    if isinstance(value, (NonterminalCall, IdentifierRef, Constant)):
        return (1,)
    return (0,)


def _branch_results(
    sequence: SourceSequence,
) -> tuple[_SourceOperationResult, ...]:
    operations: list[_SourceOperationResult] = []
    for item in sequence.items:
        if (
            isinstance(item, SourceBinding)
            and item.mode in (BindingMode.WRAP, BindingMode.WRAP_PREPEND)
            and operations
        ):
            operations.pop()
        operations.append(_source_operation_result(item))
    semantic = tuple(
        operation
        for operation in operations
        if operation.kind is _ResultKind.SEMANTIC
    )
    multiple = tuple(
        operation
        for operation in operations
        if operation.kind is _ResultKind.MULTIPLE
    )
    if multiple:
        return multiple
    if semantic:
        return semantic
    return tuple(
        operation
        for operation in operations
        if operation.kind is _ResultKind.RAW
    )


def _source_operation_result(value: SourceItem) -> _SourceOperationResult:
    kind = _ResultKind.NONE
    if isinstance(value, SourceGroup):
        branch_results = tuple(
            _branch_results(alternative.body)
            for alternative in value.alternatives
        )
        if any(
            any(result.kind is _ResultKind.MULTIPLE for result in results)
            or sum(
                result.kind is _ResultKind.SEMANTIC
                for result in results
            )
            > 1
            for results in branch_results
        ):
            kind = _ResultKind.MULTIPLE
        elif branch_results and all(
            len(results) == 1
            and results[0].kind is _ResultKind.SEMANTIC
            for results in branch_results
        ):
            kind = _ResultKind.SEMANTIC
    elif isinstance(value, SourceOptional):
        payload = _source_operation_result(value.body)
        if payload.kind in (_ResultKind.SEMANTIC, _ResultKind.MULTIPLE):
            kind = payload.kind
    elif isinstance(value, SourceRepeat):
        if any(_value_execution_counts(value.body)):
            kind = _ResultKind.MULTIPLE
    elif isinstance(value, SourceBinding):
        if value.mode in (BindingMode.WRAP, BindingMode.WRAP_PREPEND):
            kind = _ResultKind.SEMANTIC
    elif isinstance(value, SourceConstantBinding):
        if value.property is None:
            kind = _ResultKind.SEMANTIC
    elif isinstance(value, (NonterminalCall, IdentifierRef, Constant)):
        kind = _ResultKind.SEMANTIC
    elif isinstance(value, (Terminal, Lexeme)):
        kind = _ResultKind.RAW
    return _SourceOperationResult(value, kind)
