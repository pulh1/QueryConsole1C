from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from .diagnostics import (
    Diagnostic,
    DiagnosticBag,
    RelatedLocation,
    Severity,
    SourcePosition,
    SourceSpan,
)
from .grammar_parser import parse_source_grammar
from .model import Action
from .separated_model import (
    SyntaxAlternativeName,
    SyntaxAnchor,
    SyntaxGrammar,
    SyntaxItemAddress,
    SyntaxParseResult,
)
from .source_model import (
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
    SourceGrammar,
    SourceGroup,
    SourceItem,
    SourceOptional,
    SourceRepeat,
    SourceSequence,
)


_IDENTIFIER = re.compile(r"[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*")
_DECLARATION = re.compile(
    r"(?m)^[ \t]*(?P<header>#[ \t]*[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*|<[^\r\n>]+>)"
    r"[ \t]*(?:\([^\r\n]*\))?[ \t]*::="
)


@dataclass(frozen=True, slots=True)
class _Body:
    production: str | None
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class _AlternativeAnnotation:
    production: str
    name: str
    span: SourceSpan
    at_alternative_start: bool


@dataclass(frozen=True, slots=True)
class _AnchorAnnotation:
    production: str
    name: str
    span: SourceSpan
    target_offset: int


@dataclass(frozen=True, slots=True)
class _AlternativeLocation:
    production: str
    path: tuple[int, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class _ItemLocation:
    production: str
    alternative_path: tuple[int, ...]
    path: tuple[int, ...]
    item: SourceItem


def parse_syntax_grammar(text: str, path: str = "<memory>") -> SyntaxParseResult:
    source_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    masked, alternative_annotations, anchor_annotations = _mask_annotations(text, path)
    source_result = parse_source_grammar(masked, path)
    bag = DiagnosticBag(source_result.diagnostics)
    source_grammar = source_result.grammar
    if source_grammar is None:
        return SyntaxParseResult(None, bag.sorted())

    alternatives, items = _structural_locations(source_grammar)
    named_alternatives = _resolve_alternatives(
        alternative_annotations,
        alternatives,
        bag,
    )
    anchors = _resolve_anchors(anchor_annotations, items, named_alternatives, bag)
    _validate_forbidden_constructs(source_grammar, bag)

    diagnostics = bag.sorted()
    if any(item.severity is Severity.ERROR for item in diagnostics):
        return SyntaxParseResult(None, diagnostics)
    return SyntaxParseResult(
        SyntaxGrammar(
            source_grammar,
            tuple(named_alternatives),
            tuple(anchors),
            source_sha256,
            path,
        ),
        diagnostics,
    )


def _mask_annotations(
    text: str,
    path: str,
) -> tuple[str, tuple[_AlternativeAnnotation, ...], tuple[_AnchorAnnotation, ...]]:
    masked = list(text)
    alternatives: list[_AlternativeAnnotation] = []
    anchors: list[_AnchorAnnotation] = []
    for body in _grammar_bodies(text):
        if body.production is not None:
            _scan_body(text, path, body, masked, alternatives, anchors)
    return "".join(masked), tuple(alternatives), tuple(anchors)


def _grammar_bodies(text: str) -> tuple[_Body, ...]:
    declarations = tuple(_DECLARATION.finditer(text))
    bodies: list[_Body] = []
    for index, declaration in enumerate(declarations):
        header = declaration.group("header")
        production = header[1:-1].strip() if header.startswith("<") else None
        end = declarations[index + 1].start() if index + 1 < len(declarations) else len(text)
        bodies.append(_Body(production, declaration.end(), end))
    return tuple(bodies)


def _scan_body(
    text: str,
    path: str,
    body: _Body,
    masked: list[str],
    alternatives: list[_AlternativeAnnotation],
    anchors: list[_AnchorAnnotation],
) -> None:
    assert body.production is not None
    index = body.start
    lexeme_quote = False
    bsl_quote = False
    line_comment = False
    action_depth = 0
    angle_depth = 0
    argument_depth = 0
    after_angle = False
    alternative_starts = [True]
    while index < body.end:
        char = text[index]
        if line_comment:
            if char in "\r\n":
                line_comment = False
            index += 1
            continue
        if lexeme_quote:
            if char == "'" and index + 1 < body.end and text[index + 1] == "'":
                index += 2
                continue
            if char == "'":
                lexeme_quote = False
            index += 1
            continue
        if bsl_quote:
            if char == '"' and index + 1 < body.end and text[index + 1] == '"':
                index += 2
                continue
            if char == '"':
                bsl_quote = False
            index += 1
            continue
        if action_depth:
            if char == "/" and index + 1 < body.end and text[index + 1] == "/":
                line_comment = True
                index += 2
                continue
            if char == '"':
                bsl_quote = True
            elif char == "{":
                action_depth += 1
            elif char == "}":
                action_depth -= 1
            index += 1
            continue
        if angle_depth:
            if char == ">":
                angle_depth -= 1
                after_angle = angle_depth == 0
            index += 1
            continue
        if argument_depth:
            if char == '"':
                bsl_quote = True
            elif char == "(":
                argument_depth += 1
            elif char == ")":
                argument_depth -= 1
            index += 1
            continue
        if after_angle:
            after_angle = False
            if char == "(":
                argument_depth = 1
                index += 1
                continue
        if char == "'":
            alternative_starts[-1] = False
            lexeme_quote = True
            index += 1
            continue
        if char == "{":
            alternative_starts[-1] = False
            action_depth = 1
            index += 1
            continue
        if char == "/" and index + 1 < body.end and text[index + 1] == "/":
            line_comment = True
            index += 2
            continue
        if char == "<":
            alternative_starts[-1] = False
            angle_depth = 1
            index += 1
            continue
        if char == "(":
            alternative_starts[-1] = False
            alternative_starts.append(True)
            index += 1
            continue
        if char == ")":
            if len(alternative_starts) > 1:
                alternative_starts.pop()
            index += 1
            continue
        if char == "|":
            alternative_starts[-1] = True
            index += 1
            continue
        if char == "[":
            match = _IDENTIFIER.match(text, index + 1)
            if match is not None and match.end() < body.end and text[match.end()] == "]":
                end = match.end() + 1
                alternatives.append(
                    _AlternativeAnnotation(
                        body.production,
                        match.group(0),
                        _span(text, path, index, end),
                        alternative_starts[-1],
                    )
                )
                _blank(masked, index, end)
                alternative_starts[-1] = False
                index = end
                continue
        match = _IDENTIFIER.match(text, index)
        if (
            match is not None
            and _is_anchor_identifier_start(text, body.start, index)
            and match.end() < body.end
            and text[match.end()] == ":"
        ):
            end = match.end() + 1
            target_offset = end
            while target_offset < body.end and text[target_offset].isspace():
                target_offset += 1
            anchors.append(
                _AnchorAnnotation(
                    body.production,
                    match.group(0),
                    _span(text, path, index, end),
                    target_offset,
                )
            )
            _blank(masked, index, end)
            index = end
            continue
        if not char.isspace():
            alternative_starts[-1] = False
        index += 1


def _is_anchor_identifier_start(text: str, body_start: int, index: int) -> bool:
    if index == body_start:
        return True
    previous = text[index - 1]
    return previous.isspace() or previous in "'()>?*+|]"


def _blank(masked: list[str], start: int, end: int) -> None:
    for index in range(start, end):
        if masked[index] not in "\r\n":
            masked[index] = " "


def _structural_locations(
    grammar: SourceGrammar,
) -> tuple[tuple[_AlternativeLocation, ...], dict[tuple[str, int], _ItemLocation]]:
    alternatives: list[_AlternativeLocation] = []
    items: dict[tuple[str, int], _ItemLocation] = {}
    for production in grammar.productions:
        for alternative in production.alternatives:
            alternative_path = (alternative.index,)
            alternatives.append(
                _AlternativeLocation(production.name, alternative_path, alternative.span)
            )
            _visit_sequence(
                production.name,
                alternative_path,
                alternative.body,
                alternatives,
                items,
            )
    return tuple(alternatives), items


def _visit_sequence(
    production: str,
    alternative_path: tuple[int, ...],
    sequence: SourceSequence,
    alternatives: list[_AlternativeLocation],
    items: dict[tuple[str, int], _ItemLocation],
) -> None:
    for index, item in enumerate(sequence.items):
        item_path = alternative_path + (index,)
        items[(production, item.span.start.offset)] = _ItemLocation(
            production,
            alternative_path,
            item_path,
            item,
        )
        group = _item_group(item)
        if group is None:
            continue
        for alternative in group.alternatives:
            nested_path = item_path + (alternative.index,)
            alternatives.append(
                _AlternativeLocation(production, nested_path, alternative.span)
            )
            _visit_sequence(production, nested_path, alternative.body, alternatives, items)


def _item_group(item: SourceItem) -> SourceGroup | None:
    if isinstance(item, SourceGroup):
        return item
    if isinstance(item, (SourceRepeat, SourceOptional)) and isinstance(item.body, SourceGroup):
        return item.body
    return None


def _resolve_alternatives(
    annotations: tuple[_AlternativeAnnotation, ...],
    locations: tuple[_AlternativeLocation, ...],
    bag: DiagnosticBag,
) -> list[SyntaxAlternativeName]:
    named: list[SyntaxAlternativeName] = []
    names: dict[tuple[str, str], SourceSpan] = {}
    paths: dict[tuple[str, tuple[int, ...]], SourceSpan] = {}
    for annotation in annotations:
        if not annotation.at_alternative_start:
            _error(bag, "SGP104", "unresolved syntax annotation", annotation.span)
            continue
        candidates = [
            location
            for location in locations
            if location.production == annotation.production
            and location.span.start.offset >= annotation.span.end.offset
        ]
        if not candidates:
            _error(bag, "SGP104", "unresolved syntax annotation", annotation.span)
            continue
        location = min(candidates, key=lambda item: item.span.start.offset)
        name_key = (annotation.production, annotation.name)
        first_name_span = names.get(name_key)
        if first_name_span is not None:
            _error(
                bag,
                "SGP101",
                "duplicate alternative name",
                annotation.span,
                (
                    RelatedLocation(
                        "first alternative name is declared here",
                        first_name_span,
                    ),
                ),
            )
            continue
        path_key = (annotation.production, location.path)
        first_path_span = paths.get(path_key)
        if first_path_span is not None:
            _error(
                bag,
                "SGP101",
                "alternative already has a name",
                annotation.span,
                (
                    RelatedLocation(
                        "first alternative name is declared here",
                        first_path_span,
                    ),
                ),
            )
            continue
        names[name_key] = annotation.span
        paths[path_key] = annotation.span
        named.append(
            SyntaxAlternativeName(
                annotation.production,
                annotation.name,
                location.path,
                annotation.span,
            )
        )
    return named


def _resolve_anchors(
    annotations: tuple[_AnchorAnnotation, ...],
    items: dict[tuple[str, int], _ItemLocation],
    alternatives: list[SyntaxAlternativeName],
    bag: DiagnosticBag,
) -> list[SyntaxAnchor]:
    names_by_path = {(item.production, item.path): item.name for item in alternatives}
    anchors: list[SyntaxAnchor] = []
    seen: dict[tuple[str, tuple[int, ...], str], SourceSpan] = {}
    for annotation in annotations:
        location = items.get((annotation.production, annotation.target_offset))
        if location is None:
            _error(bag, "SGP104", "unresolved syntax annotation", annotation.span)
            continue
        key = (annotation.production, location.alternative_path, annotation.name)
        first_span = seen.get(key)
        if first_span is not None:
            _error(
                bag,
                "SGP102",
                "duplicate anchor name",
                annotation.span,
                (
                    RelatedLocation(
                        "first anchor name is declared here",
                        first_span,
                    ),
                ),
            )
            continue
        seen[key] = annotation.span
        anchors.append(
            SyntaxAnchor(
                annotation.name,
                SyntaxItemAddress(
                    annotation.production,
                    names_by_path.get((annotation.production, location.alternative_path)),
                    location.path,
                ),
                annotation.span,
                location.item.span,
            )
        )
    return anchors


def _validate_forbidden_constructs(grammar: SourceGrammar, bag: DiagnosticBag) -> None:
    for production in grammar.productions:
        for alternative in production.alternatives:
            _validate_sequence_forbidden(alternative.body, bag)


def _validate_sequence_forbidden(sequence: SourceSequence, bag: DiagnosticBag) -> None:
    for item in sequence.items:
        if isinstance(
            item,
            (Action, SourceConstructor, SourceBinding, SourceConstantBinding),
        ):
            _error(
                bag,
                "SGP103",
                "constructors, bindings, and actions are not allowed in syntax grammars",
                item.span,
            )
        group = _item_group(item)
        if group is not None:
            for alternative in group.alternatives:
                _validate_sequence_forbidden(alternative.body, bag)


def _span(text: str, path: str, start: int, end: int) -> SourceSpan:
    def position(offset: int) -> SourcePosition:
        line = text.count("\n", 0, offset) + 1
        previous_newline = text.rfind("\n", 0, offset)
        return SourcePosition(line, offset - previous_newline, offset)

    return SourceSpan(path, position(start), position(end))


def _error(
    bag: DiagnosticBag,
    code: str,
    message: str,
    span: SourceSpan,
    related: tuple[RelatedLocation, ...] = (),
) -> None:
    bag.add(Diagnostic(code, Severity.ERROR, message, span, related))
