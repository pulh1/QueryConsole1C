from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from .diagnostics import SourceSpan


@dataclass(frozen=True, slots=True)
class Terminal:
    token_type: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Lexeme:
    text: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Constant:
    token_type: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class IdentifierRef:
    name: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class NonterminalCall:
    name: str
    arguments: tuple[str, ...]
    span: SourceSpan


SyntaxSymbol: TypeAlias = Terminal | Lexeme | Constant | IdentifierRef | NonterminalCall


@dataclass(frozen=True, slots=True)
class Action:
    text: str
    boundary: int
    span: SourceSpan


AlternativeElement: TypeAlias = SyntaxSymbol | Action


@dataclass(frozen=True, slots=True)
class Alternative:
    index: int
    elements: tuple[AlternativeElement, ...]
    span: SourceSpan

    @property
    def syntax_symbols(self) -> tuple[SyntaxSymbol, ...]:
        return tuple(item for item in self.elements if not isinstance(item, Action))


@dataclass(frozen=True, slots=True)
class Production:
    name: str
    parameters: tuple[str, ...]
    alternatives: tuple[Alternative, ...]
    order: int
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class IdentifierDefinition:
    name: str
    token_types: tuple[str, ...]
    order: int
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Grammar:
    productions: tuple[Production, ...]
    identifier_definitions: tuple[IdentifierDefinition, ...]
    path: str
