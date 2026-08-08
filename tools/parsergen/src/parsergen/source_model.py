from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

from .diagnostics import SourceSpan
from .model import Action, IdentifierDefinition, SyntaxSymbol


class QuantifierKind(StrEnum):
    ZERO_OR_MORE = "star"
    ONE_OR_MORE = "plus"


class BindingMode(StrEnum):
    SCALAR = "scalar"
    APPEND = "append"
    EXTEND = "extend"
    CONCAT = "concat"
    INCREMENT = "increment"
    DISCARD = "discard"
    WRAP = "wrap"


@dataclass(frozen=True, slots=True)
class SourceSequence:
    items: tuple[SourceItem, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceAlternative:
    index: int
    body: SourceSequence
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceGroup:
    alternatives: tuple[SourceAlternative, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceRepeat:
    body: SourcePrimary
    kind: QuantifierKind
    span: SourceSpan
    operator_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceOptional:
    body: SourcePrimary
    span: SourceSpan
    operator_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceConstructor:
    name: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceBinding:
    property: str | None
    mode: BindingMode
    value: SourceValue
    span: SourceSpan
    operator_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceConstantBinding:
    property: str | None
    value: str
    span: SourceSpan
    operator_span: SourceSpan


SourcePrimary: TypeAlias = SyntaxSymbol | SourceGroup
SourceValue: TypeAlias = SourcePrimary | SourceRepeat | SourceOptional
SourceItem: TypeAlias = (
    SyntaxSymbol
    | Action
    | SourceGroup
    | SourceRepeat
    | SourceOptional
    | SourceConstructor
    | SourceBinding
    | SourceConstantBinding
)


@dataclass(frozen=True, slots=True)
class SourceProduction:
    name: str
    parameters: tuple[str, ...]
    alternatives: tuple[SourceAlternative, ...]
    order: int
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceGrammar:
    productions: tuple[SourceProduction, ...]
    identifier_definitions: tuple[IdentifierDefinition, ...]
    path: str
