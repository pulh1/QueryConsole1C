from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import (
    Diagnostic,
    DiagnosticBag,
    RelatedLocation,
    Severity,
    SourceSpan,
)
from .left_recursion import classify_direct_left_recursion
from .model import Constant, IdentifierRef, Lexeme, NonterminalCall, Terminal
from .source_model import (
    BindingMode,
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
    SourceGrammar,
    SourceGroup,
    SourceItem,
    SourceOptional,
    SourceProduction,
    SourceRepeat,
    SourceScopedValue,
    SourceSequence,
    SourceValue,
)


@dataclass(frozen=True, slots=True)
class ScopedAppendValidationReport:
    diagnostics: tuple[Diagnostic, ...]


def validate_scoped_appends(
    grammar: SourceGrammar,
) -> ScopedAppendValidationReport:
    bag = DiagnosticBag()
    constructors = _constructors(grammar)
    scalar_fields = _scalar_fields(grammar)
    left_recursions = classify_direct_left_recursion(grammar)

    for production in grammar.productions:
        recursion = left_recursions.get(production.name)
        recursive = (
            {
                item.alternative: item
                for item in recursion.recursive_alternatives
            }
            if recursion is not None
            else {}
        )
        for alternative in production.alternatives:
            for effect in _scoped_effects(alternative.body):
                if effect.owner not in constructors:
                    _add(
                        bag,
                        "SCOP200",
                        "scoped append references an unknown owner constructor",
                        effect.span,
                    )
                if effect.property in scalar_fields.get(effect.owner, {}):
                    _add(
                        bag,
                        "SCOP201",
                        "scoped append target conflicts with a scalar field",
                        effect.span,
                        (
                            RelatedLocation(
                                "conflicting scalar field is declared here",
                                scalar_fields[effect.owner][effect.property],
                            ),
                        ),
                    )
                if effect.value is not None:
                    payload = _tap_payload(effect.value)
                    if (
                        isinstance(payload, SourceGroup)
                        and any(
                            len(_branch_results(alternative.body)) != 1
                            for alternative in payload.alternatives
                        )
                    ):
                        _add(
                            bag,
                            "SCOP205",
                            "scoped append anchor must expose exactly one "
                            "capturable value per branch",
                            effect.span,
                        )
            _validate_current_fields(
                alternative.body,
                bag,
                constructor=None,
                definite=frozenset(),
            )
            recursive_alternative = recursive.get(alternative.index)
            if recursive_alternative is not None:
                recursive_region = SourceSequence(
                    alternative.body.items[
                        recursive_alternative.self_reference.item_index :
                    ],
                    alternative.body.span,
                )
                for effect in _scoped_effects(recursive_region):
                    _add(
                        bag,
                        "SCOP204",
                        "scoped append is not supported in a recursive suffix",
                        effect.span,
                    )

    return ScopedAppendValidationReport(bag.sorted())


def _constructors(grammar: SourceGrammar) -> set[str]:
    return {
        item.name
        for production in grammar.productions
        for alternative in production.alternatives
        for item in _items(alternative.body)
        if isinstance(item, SourceConstructor)
    }


def _scalar_fields(
    grammar: SourceGrammar,
) -> dict[str, dict[str, SourceSpan]]:
    result: dict[str, dict[str, SourceSpan]] = {}
    productions = {item.name: item for item in grammar.productions}
    for production in grammar.productions:
        for alternative in production.alternatives:
            constructor = next(
                (
                    item
                    for item in alternative.body.items
                    if isinstance(item, SourceConstructor)
                ),
                None,
            )
            fields = (
                result.setdefault(constructor.name, {})
                if constructor is not None
                else None
            )
            for item in _items(alternative.body):
                if isinstance(item, SourceBinding):
                    if (
                        item.mode is BindingMode.WRAP
                        and item.property is not None
                    ):
                        for owner in _value_constructors(item.value, productions):
                            result.setdefault(owner, {}).setdefault(
                                item.property,
                                item.span,
                            )
                    elif (
                        fields is not None
                        and item.property is not None
                        and item.mode
                        not in (
                            BindingMode.APPEND,
                            BindingMode.EXTEND,
                            BindingMode.DISCARD,
                            BindingMode.WRAP,
                            BindingMode.WRAP_PREPEND,
                        )
                    ):
                        fields.setdefault(item.property, item.span)
                elif (
                    fields is not None
                    and isinstance(item, SourceConstantBinding)
                    and item.property is not None
                ):
                    fields.setdefault(item.property, item.span)
    return result


def _value_constructors(
    value: SourceValue,
    productions: dict[str, SourceProduction],
    seen: frozenset[str] = frozenset(),
) -> set[str]:
    current = value
    while isinstance(current, SourceScopedValue) and current.value is not None:
        current = current.value
    if isinstance(current, (SourceOptional, SourceRepeat)):
        return _value_constructors(current.body, productions, seen)
    if isinstance(current, SourceGroup):
        return {
            name
            for alternative in current.alternatives
            for name in _sequence_constructors(
                alternative.body,
                productions,
                seen,
            )
        }
    if not isinstance(current, NonterminalCall) or current.name in seen:
        return set()
    production = productions.get(current.name)
    if production is None:
        return set()
    return {
        name
        for alternative in production.alternatives
        for name in _sequence_constructors(
            alternative.body,
            productions,
            seen | {current.name},
        )
    }


def _sequence_constructors(
    sequence: SourceSequence,
    productions: dict[str, SourceProduction],
    seen: frozenset[str],
) -> set[str]:
    direct = {
        item.name for item in sequence.items if isinstance(item, SourceConstructor)
    }
    if direct:
        return direct
    wrappers = tuple(
        item
        for item in sequence.items
        if isinstance(item, SourceBinding)
        and item.mode in (BindingMode.WRAP, BindingMode.WRAP_PREPEND)
    )
    if wrappers:
        return {
            name
            for item in wrappers
            for name in _value_constructors(item.value, productions, seen)
        }
    result: set[str] = set()
    for item in _branch_results(sequence):
        value = item.value if isinstance(item, SourceScopedValue) else item
        if isinstance(
            value,
            (
                NonterminalCall,
                SourceGroup,
                SourceOptional,
                SourceRepeat,
                SourceScopedValue,
            ),
        ):
            result.update(_value_constructors(value, productions, seen))
    return result


def _branch_results(sequence: SourceSequence) -> tuple[SourceItem, ...]:
    semantic = tuple(
        item
        for item in sequence.items
        if _branch_result_category(item) == 1
    )
    if semantic:
        return semantic
    return tuple(
        item
        for item in sequence.items
        if _branch_result_category(item) == 2
    )


def _branch_result_category(value: object) -> int:
    if isinstance(value, SourceScopedValue):
        if value.value is None:
            return 0
        return _branch_result_category(_tap_payload(value.value))
    if isinstance(value, SourceConstantBinding):
        return 1 if value.property is None else 0
    if isinstance(value, (NonterminalCall, IdentifierRef, Constant)):
        return 1
    if isinstance(value, (Terminal, Lexeme)):
        return 2
    return 0


def _validate_current_fields(
    sequence: SourceSequence,
    bag: DiagnosticBag,
    *,
    constructor: SourceConstructor | None,
    definite: frozenset[str],
) -> tuple[SourceConstructor | None, frozenset[str]]:
    current_constructor = constructor
    current = definite
    for item in sequence.items:
        if isinstance(item, SourceConstructor):
            current_constructor = item
            current = frozenset()
        elif isinstance(item, SourceBinding):
            current_constructor, current = _validate_current_value(
                item.value,
                bag,
                constructor=current_constructor,
                definite=current,
            )
            if (
                item.mode
                in (
                    BindingMode.SCALAR,
                    BindingMode.CONCAT,
                    BindingMode.INCREMENT,
                )
                and item.property is not None
            ):
                current = current | {item.property}
        elif isinstance(item, SourceConstantBinding):
            if item.property is not None:
                current = current | {item.property}
        elif isinstance(item, SourceScopedValue):
            if item.value is not None:
                current_constructor, current = _validate_current_value(
                    item.value,
                    bag,
                    constructor=current_constructor,
                    definite=current,
                )
            if item.current_field is not None:
                if current_constructor is None:
                    _add(
                        bag,
                        "SCOP202",
                        "current-field scoped append requires an active builder",
                        item.span,
                    )
                elif item.current_field not in current:
                    _add(
                        bag,
                        "SCOP203",
                        "current-field scoped append requires a definite scalar write",
                        item.span,
                    )
        elif isinstance(item, SourceGroup):
            current_constructor, current = _validate_group(
                item,
                bag,
                constructor=current_constructor,
                definite=current,
            )
        elif isinstance(item, (SourceOptional, SourceRepeat)):
            _validate_current_value(
                item.body,
                bag,
                constructor=current_constructor,
                definite=current,
            )
    return current_constructor, current


def _validate_current_value(
    value: SourceValue,
    bag: DiagnosticBag,
    *,
    constructor: SourceConstructor | None,
    definite: frozenset[str],
) -> tuple[SourceConstructor | None, frozenset[str]]:
    if isinstance(value, SourceScopedValue):
        return _validate_current_fields(
            SourceSequence((value,), value.span),
            bag,
            constructor=constructor,
            definite=definite,
        )
    if isinstance(value, SourceGroup):
        return _validate_group(
            value,
            bag,
            constructor=constructor,
            definite=definite,
        )
    if isinstance(value, (SourceOptional, SourceRepeat)):
        _validate_current_value(
            value.body,
            bag,
            constructor=constructor,
            definite=definite,
        )
    return constructor, definite


def _validate_group(
    group: SourceGroup,
    bag: DiagnosticBag,
    *,
    constructor: SourceConstructor | None,
    definite: frozenset[str],
) -> tuple[SourceConstructor | None, frozenset[str]]:
    states = tuple(
        _validate_current_fields(
            alternative.body,
            bag,
            constructor=constructor,
            definite=definite,
        )
        for alternative in group.alternatives
    )
    constructors = {state[0] for state in states}
    common = frozenset.intersection(*(state[1] for state in states))
    return (
        states[0][0] if len(constructors) == 1 else constructor,
        common,
    )


def _scoped_effects(sequence: SourceSequence) -> tuple[SourceScopedValue, ...]:
    return tuple(
        item
        for item in _items(sequence)
        if isinstance(item, SourceScopedValue)
    )


def _tap_payload(value: SourceValue) -> SourceValue:
    current = value
    while isinstance(current, SourceScopedValue) and current.value is not None:
        current = current.value
    if isinstance(current, (SourceOptional, SourceRepeat)):
        return current.body
    return current


def _items(sequence: SourceSequence) -> tuple[SourceItem, ...]:
    result: list[SourceItem] = []
    for item in sequence.items:
        result.append(item)
        if isinstance(item, SourceBinding):
            result.extend(_value_items(item.value))
        elif isinstance(item, SourceScopedValue) and item.value is not None:
            result.extend(_value_items(item.value))
        elif isinstance(item, SourceGroup):
            for alternative in item.alternatives:
                result.extend(_items(alternative.body))
        elif isinstance(item, (SourceOptional, SourceRepeat)):
            result.extend(_value_items(item.body))
    return tuple(result)


def _value_items(value: SourceValue) -> tuple[SourceItem, ...]:
    if isinstance(value, SourceScopedValue):
        nested = _value_items(value.value) if value.value is not None else ()
        return (value, *nested)
    if isinstance(value, SourceGroup):
        return tuple(
            item
            for alternative in value.alternatives
            for item in _items(alternative.body)
        )
    if isinstance(value, (SourceOptional, SourceRepeat)):
        return _value_items(value.body)
    return ()


def _add(
    bag: DiagnosticBag,
    code: str,
    message: str,
    span: SourceSpan,
    related: tuple[RelatedLocation, ...] = (),
) -> None:
    bag.add(Diagnostic(code, Severity.ERROR, message, span, related))
