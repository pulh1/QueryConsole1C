from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .diagnostics import SourceSpan
from .model import Action, NonterminalCall
from .source_model import (
    BindingMode,
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
    SourceGrammar,
)


@dataclass(frozen=True, slots=True)
class DirectSelfReference:
    item_index: int
    call: NonterminalCall
    property: str | None
    binding_mode: BindingMode | None
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class DirectRecursiveAlternative:
    alternative: int
    self_reference: DirectSelfReference
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class DirectLeftRecursion:
    production: str
    base_alternatives: tuple[int, ...]
    recursive_alternatives: tuple[DirectRecursiveAlternative, ...]
    source_span: SourceSpan


def classify_direct_left_recursion(
    grammar: SourceGrammar,
) -> Mapping[str, DirectLeftRecursion]:
    result: dict[str, DirectLeftRecursion] = {}
    for production in grammar.productions:
        recursive: list[DirectRecursiveAlternative] = []
        base: list[int] = []
        for alternative in production.alternatives:
            reference = _direct_self_reference(
                production.name,
                alternative.body.items,
            )
            if reference is None:
                base.append(alternative.index)
            else:
                recursive.append(
                    DirectRecursiveAlternative(
                        alternative.index,
                        reference,
                        alternative.span,
                    )
                )
        if recursive:
            result[production.name] = DirectLeftRecursion(
                production.name,
                tuple(base),
                tuple(recursive),
                production.span,
            )
    return MappingProxyType(result)


def _direct_self_reference(
    production: str,
    items: tuple[object, ...],
) -> DirectSelfReference | None:
    for index, item in enumerate(items):
        if isinstance(
            item,
            (SourceConstructor, SourceConstantBinding, Action),
        ):
            continue
        if isinstance(item, NonterminalCall):
            if item.name != production:
                return None
            return DirectSelfReference(
                index,
                item,
                None,
                None,
                item.span,
            )
        if isinstance(item, SourceBinding):
            value = item.value
            if not isinstance(value, NonterminalCall):
                return None
            if value.name != production:
                return None
            return DirectSelfReference(
                index,
                value,
                item.property,
                item.mode,
                item.span,
            )
        return None
    return None
