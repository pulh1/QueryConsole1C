from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, TypeAlias

from .diagnostics import (
    Diagnostic,
    DiagnosticBag,
    Severity,
    SourceSpan,
)
from .model import (
    Action,
    Alternative,
    Constant,
    Grammar,
    IdentifierDefinition,
    IdentifierRef,
    Lexeme,
    NonterminalCall,
    Production,
    SyntaxSymbol,
    Terminal,
)


TokenWord: TypeAlias = tuple[str, ...]
RESERVED_END_TOKEN = "$"


@dataclass(frozen=True, slots=True)
class ResolvedToken:
    token_types: frozenset[str]
    source: SyntaxSymbol


@dataclass(frozen=True, slots=True)
class ResolvedNonterminal:
    name: str
    arguments: tuple[str, ...]
    source: NonterminalCall


ResolvedSymbol: TypeAlias = ResolvedToken | ResolvedNonterminal


@dataclass(frozen=True, slots=True)
class ResolvedAlternative:
    production: str
    index: int
    symbols: tuple[ResolvedSymbol, ...]
    actions: tuple[Action, ...]
    source: Alternative


@dataclass(frozen=True, slots=True)
class ResolvedGrammar:
    productions: Mapping[str, tuple[ResolvedAlternative, ...]]
    production_order: tuple[str, ...]
    identifier_tokens: Mapping[str, frozenset[str]]
    occurrences: Mapping[str, tuple[tuple[str, int, int], ...]]


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    grammar: ResolvedGrammar | None
    diagnostics: tuple[Diagnostic, ...]


def resolve_grammar(grammar: Grammar) -> ResolutionResult:
    """Resolve syntax references without changing the parsed grammar's order."""
    bag = DiagnosticBag()
    identifiers, first_definitions = _resolve_identifier_definitions(
        grammar.identifier_definitions
    )
    productions = {production.name: production for production in grammar.productions}
    resolved_productions: dict[str, tuple[ResolvedAlternative, ...]] = {}
    occurrence_lists: dict[str, list[tuple[str, int, int]]] = {}
    referenced_identifiers: set[str] = set()
    unsafe = False

    for definition in grammar.identifier_definitions:
        if (
            definition.name == RESERVED_END_TOKEN
            or RESERVED_END_TOKEN in definition.token_types
        ):
            bag.add(
                _diagnostic(
                    "RES004",
                    definition.span,
                    RESERVED_END_TOKEN,
                )
            )
            unsafe = True

    for production in grammar.productions:
        alternatives: list[ResolvedAlternative] = []
        for alternative in production.alternatives:
            symbols: list[ResolvedSymbol] = []
            for source_symbol in alternative.syntax_symbols:
                if isinstance(source_symbol, IdentifierRef):
                    referenced_identifiers.add(source_symbol.name)
                resolved_symbol = _resolve_symbol(
                    source_symbol,
                    identifiers,
                    productions,
                    bag,
                )
                if resolved_symbol is None:
                    unsafe = True
                    continue
                symbol_index = len(symbols)
                symbols.append(resolved_symbol)
                if isinstance(resolved_symbol, ResolvedNonterminal):
                    occurrence_lists.setdefault(resolved_symbol.name, []).append(
                        (production.name, alternative.index, symbol_index)
                    )
            alternatives.append(
                ResolvedAlternative(
                    production.name,
                    alternative.index,
                    tuple(symbols),
                    tuple(item for item in alternative.elements if isinstance(item, Action)),
                    alternative,
                )
            )
        resolved_productions[production.name] = tuple(alternatives)

    for name, definition in first_definitions.items():
        if not identifiers[name] and name not in referenced_identifiers:
            bag.add(_diagnostic("RES003", definition.span, name))
            unsafe = True

    resolved = ResolvedGrammar(
        MappingProxyType(resolved_productions),
        tuple(production.name for production in grammar.productions),
        MappingProxyType(identifiers),
        MappingProxyType(
            {name: tuple(items) for name, items in occurrence_lists.items()}
        ),
    )
    return ResolutionResult(None if unsafe else resolved, bag.sorted())


def _resolve_identifier_definitions(
    definitions: tuple[IdentifierDefinition, ...],
) -> tuple[
    dict[str, frozenset[str]],
    dict[str, IdentifierDefinition],
]:
    ordered_tokens: dict[str, dict[str, None]] = {}
    first_definitions: dict[str, IdentifierDefinition] = {}
    for definition in definitions:
        if definition.name not in first_definitions:
            first_definitions[definition.name] = definition
            ordered_tokens[definition.name] = {}
        tokens = ordered_tokens[definition.name]
        for token_type in definition.token_types:
            tokens.setdefault(token_type, None)
    return (
        {
            name: frozenset(tokens)
            for name, tokens in ordered_tokens.items()
        },
        first_definitions,
    )


def _resolve_symbol(
    symbol: SyntaxSymbol,
    identifiers: Mapping[str, frozenset[str]],
    productions: Mapping[str, Production],
    bag: DiagnosticBag,
) -> ResolvedSymbol | None:
    if isinstance(symbol, Terminal):
        if symbol.token_type == RESERVED_END_TOKEN:
            bag.add(_diagnostic("RES004", symbol.span, symbol.token_type))
            return None
        return ResolvedToken(frozenset({symbol.token_type}), symbol)
    if isinstance(symbol, Lexeme):
        if symbol.text == RESERVED_END_TOKEN:
            bag.add(_diagnostic("RES004", symbol.span, symbol.text))
            return None
        return ResolvedToken(frozenset({symbol.text}), symbol)
    if isinstance(symbol, Constant):
        if symbol.token_type == RESERVED_END_TOKEN:
            bag.add(_diagnostic("RES004", symbol.span, symbol.token_type))
            return None
        return ResolvedToken(frozenset({symbol.token_type}), symbol)
    if isinstance(symbol, IdentifierRef):
        token_types = identifiers.get(symbol.name)
        if token_types is None:
            bag.add(_diagnostic("RES002", symbol.span, symbol.name))
            return None
        if not token_types:
            bag.add(_diagnostic("RES003", symbol.span, symbol.name))
            return None
        return ResolvedToken(token_types, symbol)
    if isinstance(symbol, NonterminalCall):
        production = productions.get(symbol.name)
        if production is None:
            bag.add(_diagnostic("RES001", symbol.span, symbol.name))
            return None
        if len(symbol.arguments) > len(production.parameters):
            bag.add(_diagnostic("GR003", symbol.span, symbol.name))
        return ResolvedNonterminal(symbol.name, symbol.arguments, symbol)
    raise TypeError(type(symbol))


def _diagnostic(
    code: str,
    span: SourceSpan,
    symbol: str,
    *,
    related: tuple[RelatedLocation, ...] = (),
) -> Diagnostic:
    messages = {
        "RES001": "unknown nonterminal",
        "RES002": "unknown identifier class",
        "RES003": "identifier class has no token types",
        "RES004": (
            "reserved '$' cannot be used as a grammar token "
            "or identifier class name"
        ),
        "GR003": "too many arguments for nonterminal",
    }
    return Diagnostic(code, Severity.ERROR, messages[code], span, related)
