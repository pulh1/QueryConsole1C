from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import Diagnostic, SourceSpan
from .source_model import SourceGrammar


@dataclass(frozen=True, slots=True)
class SyntaxItemAddress:
    production: str
    alternative: str | None
    path: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SyntaxAlternativeName:
    production: str
    name: str
    path: tuple[int, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SyntaxAnchor:
    name: str
    address: SyntaxItemAddress
    span: SourceSpan
    target_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SyntaxGrammar:
    source_grammar: SourceGrammar
    alternatives: tuple[SyntaxAlternativeName, ...]
    anchors: tuple[SyntaxAnchor, ...]
    source_sha256: str
    path: str


@dataclass(frozen=True, slots=True)
class SyntaxParseResult:
    grammar: SyntaxGrammar | None
    diagnostics: tuple[Diagnostic, ...]
