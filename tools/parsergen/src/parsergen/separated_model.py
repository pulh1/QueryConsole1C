from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import Diagnostic, SourceSpan
from .source_model import BindingMode, SourceGrammar


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


@dataclass(frozen=True, slots=True)
class SemanticAnchorBinding:
    property: str | None
    mode: BindingMode
    anchor: str
    span: SourceSpan
    operator_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SemanticConstantBinding:
    property: str | None
    value: str
    span: SourceSpan
    operator_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SemanticScopedAppend:
    production: str
    alternative: str | None
    owner: str
    property: str
    anchor: str | None
    current_field: str | None
    span: SourceSpan
    operator_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SemanticAlternative:
    production: str
    alternative: str | None
    constructor: str | None
    constructor_span: SourceSpan | None
    anchor_bindings: tuple[SemanticAnchorBinding, ...]
    constants: tuple[SemanticConstantBinding, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SemanticProfile:
    name: str
    alternatives: tuple[SemanticAlternative, ...]
    source_sha256: str
    path: str
    scoped_appends: tuple[SemanticScopedAppend, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticProfileParseResult:
    profile: SemanticProfile | None
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True, slots=True)
class SemanticBindingResult:
    source_grammar: SourceGrammar | None
    diagnostics: tuple[Diagnostic, ...]
