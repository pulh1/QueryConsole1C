from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re

from .diagnostics import Diagnostic, DiagnosticBag, Severity, SourcePosition, SourceSpan
from .separated_model import (
    SemanticAlternative,
    SemanticAnchorBinding,
    SemanticConstantBinding,
    SemanticProfile,
    SemanticProfileParseResult,
    SemanticScopedAppend,
)
from .source_model import BindingMode


_IDENTIFIER = r"[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*"
_PROPERTY = rf"{_IDENTIFIER}(?:\[[0-9]+\]|\.{_IDENTIFIER})*"
_PROFILE = re.compile(rf"profile[ \t]+(?P<name>{_IDENTIFIER})")
_SELECTOR_PREFIX = re.compile(
    rf"<(?P<production>{_IDENTIFIER})>(?:\[(?P<alternative>{_IDENTIFIER})\])?"
)
_CONSTRUCTOR = re.compile(rf"@(?P<name>{_IDENTIFIER})")
_NAMED_ANCHOR_BINDING = re.compile(
    rf"(?P<property>{_PROPERTY})[ \t]*(?P<operator>\+=>|\+\+=|\+=|\*=|~=|=>|=)[ \t]*(?P<anchor>{_IDENTIFIER})"
)
_PROPERTYLESS_ANCHOR_BINDING = re.compile(
    rf"(?P<operator>\+=|-=)[ \t]*(?P<anchor>{_IDENTIFIER})"
)
_CONSTANT_BINDING = re.compile(
    rf"(?:(?P<property>{_PROPERTY})[ \t]*)?:=[ \t]*(?P<value>{_PROPERTY})"
)
_SCOPED_APPEND = re.compile(
    rf"\^(?P<owner>{_IDENTIFIER})\.(?P<property>{_IDENTIFIER})"
    rf"[ \t]*(?P<operator>\+=)[ \t]*"
    rf"(?:(?P<current_field>\${_IDENTIFIER})|(?P<anchor>{_IDENTIFIER}))"
)

_BINDING_MODES = {
    "=": BindingMode.SCALAR,
    "+=": BindingMode.APPEND,
    "*=": BindingMode.EXTEND,
    "~=": BindingMode.CONCAT,
    "++=": BindingMode.INCREMENT,
    "=>": BindingMode.WRAP,
    "+=>": BindingMode.WRAP_PREPEND,
    "-=": BindingMode.DISCARD,
}


@dataclass(frozen=True, slots=True)
class _Line:
    path: str
    number: int
    offset: int
    text: str

    def position(self, index: int) -> SourcePosition:
        return SourcePosition(self.number, index + 1, self.offset + index)

    def span(self, start: int, end: int) -> SourceSpan:
        return SourceSpan(self.path, self.position(start), self.position(end))


@dataclass(slots=True)
class _AlternativeBuilder:
    production: str
    alternative: str | None
    start: SourcePosition
    constructor: str | None = None
    constructor_span: SourceSpan | None = None
    anchor_bindings: list[SemanticAnchorBinding] = field(default_factory=list)
    constants: list[SemanticConstantBinding] = field(default_factory=list)
    scoped_appends: list[SemanticScopedAppend] = field(default_factory=list)


def parse_semantic_profile(
    text: str,
    path: str = "<memory>",
) -> SemanticProfileParseResult:
    source_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    bag = DiagnosticBag()
    profile_name: str | None = None
    alternatives: list[SemanticAlternative] = []
    scoped_appends: list[SemanticScopedAppend] = []
    current: _AlternativeBuilder | None = None
    first_content: SourceSpan | None = None

    for line in _lines(text, path):
        content = _without_comment(line.text)
        stripped_start = _first_nonspace(content)
        if stripped_start is None:
            continue
        if first_content is None:
            first_content = line.span(stripped_start, stripped_start + 1)

        if current is not None:
            current = _parse_block_line(
                line,
                content,
                stripped_start,
                current,
                alternatives,
                scoped_appends,
                bag,
            )
            continue

        profile = _PROFILE.match(content, stripped_start)
        if profile is not None and _only_space(content, profile.end()):
            if profile_name is None:
                profile_name = profile.group("name")
            else:
                _error(bag, "SPP100", "duplicate profile declaration", line.span(stripped_start, profile.end()))
            continue
        if content.startswith("profile", stripped_start):
            _error(bag, "SPP100", "profile declaration is malformed", line.span(stripped_start, len(content.rstrip())))
            continue

        block_start = content.find("{", stripped_start)
        selector_end = block_start if block_start >= 0 else len(content)
        while selector_end > stripped_start and content[selector_end - 1] in " \t":
            selector_end -= 1
        selector = _SELECTOR_PREFIX.fullmatch(content, stripped_start, selector_end)
        if selector is not None:
            if block_start < 0:
                _error(bag, "SPP102", "semantic profile block is malformed", line.span(selector_end, selector_end))
                continue
            if not _only_space(content, block_start + 1):
                _error(bag, "SPP102", "semantic profile block is malformed", line.span(block_start, block_start + 1))
                continue
            current = _AlternativeBuilder(
                selector.group("production"),
                selector.group("alternative"),
                line.position(stripped_start),
            )
            continue
        if content[stripped_start] == "<":
            _error(bag, "SPP101", "semantic profile selector is malformed", line.span(stripped_start, stripped_start + 1))
            continue
        _error(bag, "SPP102", "semantic profile block is malformed", line.span(stripped_start, stripped_start + 1))

    if current is not None:
        _error(
            bag,
            "SPP102",
            "semantic profile block is not closed",
            SourceSpan(path, current.start, current.start),
        )
    if profile_name is None:
        missing_span = first_content or SourceSpan(
            path,
            SourcePosition(1, 1, 0),
            SourcePosition(1, 1, 0),
        )
        _error(bag, "SPP100", "profile declaration is missing", missing_span)

    diagnostics = bag.sorted()
    if any(item.severity is Severity.ERROR for item in diagnostics):
        return SemanticProfileParseResult(None, diagnostics)
    assert profile_name is not None
    return SemanticProfileParseResult(
        SemanticProfile(
            profile_name,
            tuple(alternatives),
            source_sha256,
            path,
            tuple(scoped_appends),
        ),
        diagnostics,
    )


def _parse_block_line(
    line: _Line,
    content: str,
    start: int,
    current: _AlternativeBuilder,
    alternatives: list[SemanticAlternative],
    scoped_appends: list[SemanticScopedAppend],
    bag: DiagnosticBag,
) -> _AlternativeBuilder | None:
    if "{" in content[start:]:
        index = content.index("{", start)
        _error(bag, "SPP104", "inline actions are not supported", line.span(index, index + 1))
        return current
    if content[start] == "}":
        if not _only_space(content, start + 1):
            _error(bag, "SPP102", "semantic profile block is malformed", line.span(start, start + 1))
            return current
        alternatives.append(
            SemanticAlternative(
                current.production,
                current.alternative,
                current.constructor,
                current.constructor_span,
                tuple(current.anchor_bindings),
                tuple(current.constants),
                SourceSpan(line.path, current.start, line.position(start + 1)),
            )
        )
        scoped_appends.extend(current.scoped_appends)
        return None

    constructor = _CONSTRUCTOR.match(content, start)
    if constructor is not None and _only_space(content, constructor.end()):
        span = line.span(start, constructor.end())
        if current.constructor is not None:
            _error(bag, "SPP103", "semantic profile constructor is duplicated", span)
        elif current.anchor_bindings or current.constants or current.scoped_appends:
            _error(
                bag,
                "SPP103",
                "semantic profile constructor must precede semantic statements",
                span,
            )
        else:
            current.constructor = constructor.group("name")
            current.constructor_span = span
        return current

    scoped_append = _SCOPED_APPEND.match(content, start)
    if scoped_append is not None and _only_space(content, scoped_append.end()):
        current_field = scoped_append.group("current_field")
        current.scoped_appends.append(
            SemanticScopedAppend(
                current.production,
                current.alternative,
                scoped_append.group("owner"),
                scoped_append.group("property"),
                scoped_append.group("anchor"),
                current_field[1:] if current_field is not None else None,
                line.span(start, scoped_append.end()),
                line.span(
                    scoped_append.start("operator"),
                    scoped_append.end("operator"),
                ),
                len(scoped_appends) + len(current.scoped_appends),
            )
        )
        return current

    anchor_binding = _NAMED_ANCHOR_BINDING.match(content, start)
    if anchor_binding is None:
        anchor_binding = _PROPERTYLESS_ANCHOR_BINDING.match(content, start)
    if anchor_binding is not None and _only_space(content, anchor_binding.end()):
        operator_start = anchor_binding.start("operator")
        operator_end = anchor_binding.end("operator")
        current.anchor_bindings.append(
            SemanticAnchorBinding(
                anchor_binding.groupdict().get("property"),
                _BINDING_MODES[anchor_binding.group("operator")],
                anchor_binding.group("anchor"),
                line.span(start, anchor_binding.end()),
                line.span(operator_start, operator_end),
            )
        )
        return current

    constant = _CONSTANT_BINDING.match(content, start)
    if constant is not None and _only_space(content, constant.end()):
        operator_start = content.index(":=", start, constant.end())
        current.constants.append(
            SemanticConstantBinding(
                constant.group("property"),
                constant.group("value"),
                line.span(start, constant.end()),
                line.span(operator_start, operator_start + 2),
            )
        )
        return current

    _error(bag, "SPP105", "semantic profile binding is malformed", _binding_error_span(line, content, start))
    return current


def _binding_error_span(line: _Line, content: str, start: int) -> SourceSpan:
    operator = re.search(r"\+=>|\+\+=|\+=|\*=|~=|:=|=>|=|-=" , content[start:])
    if operator is None:
        return line.span(start, start + 1)
    operator_start = start + operator.start()
    return line.span(operator_start, operator_start + len(operator.group(0)))


def _lines(text: str, path: str) -> tuple[_Line, ...]:
    lines: list[_Line] = []
    offset = 0
    number = 1
    for raw_line in text.splitlines(keepends=True):
        line_text = raw_line.rstrip("\r\n")
        lines.append(_Line(path, number, offset, line_text))
        offset += len(raw_line)
        number += 1
    if not lines or offset < len(text):
        lines.append(_Line(path, number, offset, text[offset:]))
    return tuple(lines)


def _without_comment(line: str) -> str:
    comment = line.find("//")
    return line if comment < 0 else line[:comment]


def _first_nonspace(text: str) -> int | None:
    for index, char in enumerate(text):
        if char not in " \t":
            return index
    return None


def _only_space(text: str, start: int) -> bool:
    return all(char in " \t" for char in text[start:])


def _error(bag: DiagnosticBag, code: str, message: str, span: SourceSpan) -> None:
    bag.add(Diagnostic(code, Severity.ERROR, message, span))
