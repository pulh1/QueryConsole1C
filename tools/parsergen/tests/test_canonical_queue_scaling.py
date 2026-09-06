"""Canonical language BFS must not shift a growing list at each dequeue."""

import sys

import pytest

from parsergen.canonical_select import (
    _export_language, build_canonical_decision_source, intersect_languages,
)
from tests.test_canonical_select import _analysis


@pytest.mark.parametrize("operation", ["export", "intersection"])
@pytest.mark.parametrize("width", [128, 256])
def test_canonical_breadth_first_queue_work_is_linear(operation, width):
    analysis = _analysis("<S> ::= <A>\n<A> ::= " + " | ".join(
        f"T{i} X{i}" for i in range(width)
    ), k=2)
    language = build_canonical_decision_source(analysis, "S").languages[0].language
    shifted = 0
    dequeues = 0
    monitored = {_export_language.__code__, intersect_languages.__code__}

    def profile(frame, event, function):
        nonlocal shifted, dequeues
        if event != "c_call" or frame.f_code not in monitored:
            return
        name = getattr(function, "__name__", "")
        queue = getattr(function, "__self__", None)
        if name == "pop" and isinstance(queue, list):
            shifted += max(0, len(queue) - 1)
            dequeues += 1
        elif name == "popleft":
            dequeues += 1

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        actual = (
            build_canonical_decision_source(analysis, "S").languages[0].language
            if operation == "export" else intersect_languages(language, language)
        )
    finally:
        sys.setprofile(previous)
    words = {
        (first.predicate.token_types[0], second.predicate.token_types[0])
        for first in actual.nodes[actual.root].edges
        for second in actual.nodes[first.target].edges
        if actual.nodes[second.target].accepting
    }
    assert words == {(f"T{i}", f"X{i}") for i in range(width)}
    assert len(actual.nodes) == 2 * width + 1
    assert shifted + dequeues <= 4 * len(actual.nodes), (shifted, dequeues)
