from __future__ import annotations

from parsergen.resolver import ResolvedGrammar, ResolvedNonterminal, ResolvedToken


LookaheadWord = tuple[str, ...]
LookaheadSet = frozenset[LookaheadWord]
EPSILON: LookaheadWord = ()
END = "$"


def oracle_prefix_analysis(
    grammar: ResolvedGrammar,
    k: int,
) -> tuple[frozenset[str], dict[str, LookaheadSet]]:
    if k < 1:
        raise ValueError("k must be at least 1")
    return _oracle_nullable(grammar), _oracle_first(grammar, k)


def oracle_analysis(
    grammar: ResolvedGrammar,
    k: int,
    start_productions: tuple[str, ...],
) -> tuple[
    frozenset[str],
    dict[str, LookaheadSet],
    dict[str, LookaheadSet],
    dict[tuple[str, int], LookaheadSet],
]:
    if k < 1:
        raise ValueError("k must be at least 1")
    nullable = _oracle_nullable(grammar)
    first = _oracle_first(grammar, k)
    follow = _oracle_follow(grammar, first, k, start_productions)
    select = _oracle_select(grammar, first, follow, k)
    return nullable, first, follow, select


def _oracle_nullable(grammar: ResolvedGrammar) -> frozenset[str]:
    nullable: set[str] = set()
    while True:
        changed = False
        for production_name in grammar.production_order:
            if production_name in nullable:
                continue
            for alternative in grammar.productions[production_name]:
                if all(
                    isinstance(symbol, ResolvedNonterminal)
                    and symbol.name in nullable
                    for symbol in alternative.symbols
                ):
                    nullable.add(production_name)
                    changed = True
                    break
        if not changed:
            return frozenset(nullable)


def _oracle_first(
    grammar: ResolvedGrammar,
    k: int,
) -> dict[str, LookaheadSet]:
    first: dict[str, set[LookaheadWord]] = {
        name: set() for name in grammar.production_order
    }
    while True:
        changed = False
        for production_name in grammar.production_order:
            additions: set[LookaheadWord] = set()
            for alternative in grammar.productions[production_name]:
                additions.update(
                    _oracle_first_of_sequence(alternative.symbols, first, k)
                )
            previous_size = len(first[production_name])
            first[production_name].update(additions)
            changed |= len(first[production_name]) != previous_size
        if not changed:
            return {name: frozenset(words) for name, words in first.items()}


def _oracle_follow(
    grammar: ResolvedGrammar,
    first: dict[str, LookaheadSet],
    k: int,
    start_productions: tuple[str, ...],
) -> dict[str, LookaheadSet]:
    follow: dict[str, set[LookaheadWord]] = {
        name: set() for name in grammar.production_order
    }
    for production_name in start_productions:
        follow[production_name].add((END,))

    while True:
        changed = False
        for parent in grammar.production_order:
            for alternative in grammar.productions[parent]:
                for symbol_position, symbol in enumerate(alternative.symbols):
                    if not isinstance(symbol, ResolvedNonterminal):
                        continue
                    suffix_first = _oracle_first_of_sequence(
                        alternative.symbols[symbol_position + 1 :],
                        first,
                        k,
                    )
                    candidate = {
                        prefix
                        for prefix in suffix_first
                        if len(prefix) == k
                    }
                    candidate.update(
                        (prefix + following)[:k]
                        for prefix in suffix_first
                        if len(prefix) < k
                        for following in follow[parent]
                    )
                    previous_size = len(follow[symbol.name])
                    follow[symbol.name].update(candidate)
                    changed |= len(follow[symbol.name]) != previous_size
        if not changed:
            return {
                name: frozenset(words)
                for name, words in follow.items()
            }


def _oracle_select(
    grammar: ResolvedGrammar,
    first: dict[str, LookaheadSet],
    follow: dict[str, LookaheadSet],
    k: int,
) -> dict[tuple[str, int], LookaheadSet]:
    select: dict[tuple[str, int], LookaheadSet] = {}
    for production_name in grammar.production_order:
        for alternative_number, alternative in enumerate(
            grammar.productions[production_name],
            start=1,
        ):
            alternative_first = _oracle_first_of_sequence(
                alternative.symbols,
                first,
                k,
            )
            words = {
                prefix
                for prefix in alternative_first
                if len(prefix) == k
            }
            words.update(
                (prefix + following)[:k]
                for prefix in alternative_first
                if len(prefix) < k
                for following in follow[production_name]
            )
            select[(production_name, alternative_number)] = frozenset(words)
    return select


def _oracle_first_of_sequence(
    symbols,
    first: dict[str, set[LookaheadWord] | LookaheadSet],
    k: int,
) -> set[LookaheadWord]:
    language: set[LookaheadWord] = {EPSILON}
    for symbol in symbols:
        if isinstance(symbol, ResolvedToken):
            symbol_language = {(token,) for token in symbol.token_types}
        else:
            symbol_language = first[symbol.name]
        language = {
            (left + right)[:k]
            for left in language
            for right in symbol_language
        }
        if not language:
            break
    return language

