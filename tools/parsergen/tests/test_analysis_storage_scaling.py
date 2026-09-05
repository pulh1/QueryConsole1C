"""Suffix preparation stores shared sequences, not every copied tail."""

import tracemalloc

import pytest

from parsergen.analysis import _ContinuationFirst, compute_analysis
from tests.helpers import resolved
from tests.oracles import oracle_analysis


@pytest.mark.parametrize("length", [512, 1024])
def test_long_nonterminal_rhs_has_linear_suffix_preparation_storage(length):
    grammar = resolved("<S> ::= " + " ".join(["<A>"] * length) + "\n<A> ::= ITEM")
    tracemalloc.start()
    try:
        solver = _ContinuationFirst(grammar, 1)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert len(solver.occurrences) == length
    # Includes all solver initialization, including both RHS and productivity
    # storage. Copying tails alone exceeds this linear per-symbol allowance.
    assert peak < 1600 * length, (length, peak)


@pytest.mark.parametrize("k", [1, 2, 3, 4])
@pytest.mark.parametrize("grammar_text", [
    "<S> ::= <A> <B> <A> <B>\n<T> ::= <A> <B>\n<A> ::= A | ПУСТО\n<B> ::= B | ПУСТО",
    "<S> ::= <A> <B> | <B> <A>\n<A> ::= A\n<B> ::= <B>",
    "<S> ::= <A> <B> | C\n<A> ::= A <B> | ПУСТО\n<B> ::= B <A> | ПУСТО",
])
def test_shared_suffixes_preserve_nullable_productivity_and_oracle_sets(k, grammar_text):
    grammar = resolved(grammar_text)
    starts = tuple(grammar.production_order)
    actual = compute_analysis(grammar, k, starts)
    nullable, first, follow, select = oracle_analysis(grammar, k, starts)
    assert actual.nullable == nullable
    assert actual.first == first
    assert actual.follow == follow
    assert actual.select == select
