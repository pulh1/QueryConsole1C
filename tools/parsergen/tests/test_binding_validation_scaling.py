"""Equivalent syntax paths must not multiply abstract binding states."""

import tracemalloc

import pytest

from parsergen.binding_validation import _semantic_execution_counts, validate_bindings
from parsergen.grammar_parser import parse_source_grammar


@pytest.mark.parametrize("mode", ["bindings", "semantic_counts"])
def test_optional_terminals_have_bounded_validation_storage(mode):
    parsed = parse_source_grammar("<S> ::= @Node " + " ".join(f"T{i}?" for i in range(20)))
    assert parsed.diagnostics == ()
    tracemalloc.start()
    try:
        if mode == "bindings":
            assert validate_bindings(parsed.grammar).diagnostics == ()
        else:
            counts = _semantic_execution_counts(parsed.grammar.productions[0].alternatives[0].body)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    # Old optional concatenation retains 1,048,576 entries (> 16 MB).
    # The one distinct abstract state needs far below this generous allowance.
    assert peak < 512_000, (mode, peak)
    if mode == "semantic_counts":
        assert counts == (0,)


@pytest.mark.parametrize("body, codes", [
    ("@Node (A Value = X)? B? Value = Y", ("BIND203",)),
    ("@Node (A Value = X)*", ("BIND203",)),
    ("@Node (A Value := Истина)? B? Value := Ложь", ("BIND203",)),
    ("@Node (A Value = X | B Value = Y)", ()),
    ("<Seed>? Value => <Child>", ("BIND210",)),
    ("<Seed> <Seed> Value => <Child>", ("BIND210",)),
    ("<Seed> A? B? Value => <Child>", ("BIND210",)),
    ("A? B? <Seed> Value => <Child>", ()),
])
def test_deduplication_preserves_path_and_wrap_diagnostics(body, codes):
    parsed = parse_source_grammar("<S> ::= " + body + "\n<Seed> ::= @Seed ITEM\n<Child> ::= @Child END")
    assert parsed.diagnostics == ()
    report = validate_bindings(parsed.grammar)
    assert tuple(d.code for d in report.diagnostics) == codes


def test_semantic_counts_preserve_distinct_optional_outcomes():
    parsed = parse_source_grammar("<S> ::= <A>? <B>?\n<A> ::= A\n<B> ::= B")
    counts = _semantic_execution_counts(parsed.grammar.productions[0].alternatives[0].body)
    assert counts == (0, 1, 2)
