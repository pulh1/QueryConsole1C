from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from random import Random
from types import MappingProxyType

from parsergen.resolver import (
    ResolvedAlternative,
    ResolvedGrammar,
    ResolvedNonterminal,
)
from tests.helpers import resolved


TERMINALS = ("a", "b", "c")


def generated_resolved_grammar(seed: int) -> ResolvedGrammar:
    random = Random(seed)
    names = tuple(f"N{index}" for index in range(random.randint(1, 6)))
    lines: list[str] = []
    for name in names:
        alternatives: list[str] = []
        for _ in range(random.randint(1, 3)):
            symbols = [
                random.choice(TERMINALS)
                if random.randrange(2) == 0
                else f"<{random.choice(names)}>"
                for _ in range(random.randint(0, 4))
            ]
            alternatives.append(" ".join(symbols) if symbols else "ПУСТО")
        lines.append(f"<{name}> ::= {' | '.join(alternatives)}")
    return resolved("\n".join(lines))


def permuted_resolved_grammar(
    grammar: ResolvedGrammar,
    seed: int,
) -> ResolvedGrammar:
    order = list(grammar.production_order)
    Random(seed).shuffle(order)
    return replace(
        grammar,
        productions=MappingProxyType(
            {name: grammar.productions[name] for name in order}
        ),
        production_order=tuple(order),
    )


def renamed_resolved_grammar(
    grammar: ResolvedGrammar,
) -> tuple[ResolvedGrammar, dict[str, str]]:
    renames = {
        old_name: f"Renamed{index}"
        for index, old_name in enumerate(grammar.production_order)
    }
    productions: dict[str, tuple[ResolvedAlternative, ...]] = {}
    occurrences: dict[str, list[tuple[str, int, int]]] = defaultdict(list)

    for old_owner in grammar.production_order:
        new_owner = renames[old_owner]
        alternatives: list[ResolvedAlternative] = []
        for alternative in grammar.productions[old_owner]:
            symbols = []
            for symbol_index, symbol in enumerate(alternative.symbols):
                if isinstance(symbol, ResolvedNonterminal):
                    referenced_name = renames[symbol.name]
                    symbol = replace(
                        symbol,
                        name=referenced_name,
                        source=replace(symbol.source, name=referenced_name),
                    )
                    occurrences[referenced_name].append(
                        (new_owner, alternative.index, symbol_index)
                    )
                symbols.append(symbol)
            alternatives.append(
                replace(
                    alternative,
                    production=new_owner,
                    symbols=tuple(symbols),
                )
            )
        productions[new_owner] = tuple(alternatives)

    renamed = ResolvedGrammar(
        productions=MappingProxyType(productions),
        production_order=tuple(renames[name] for name in grammar.production_order),
        identifier_tokens=grammar.identifier_tokens,
        occurrences=MappingProxyType(
            {name: tuple(items) for name, items in occurrences.items()}
        ),
    )
    return renamed, renames

