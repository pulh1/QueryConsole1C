from __future__ import annotations

from dataclasses import dataclass
import re

from .binding_validation import validate_bindings
from .diagnostics import Diagnostic, DiagnosticBag, Severity, SourcePosition, SourceSpan
from .lowering import LoweringResult, lower_source_grammar
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
    Terminal,
)
from .source_model import (
    BindingMode,
    QuantifierKind,
    SourceAlternative,
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
    SourceGrammar,
    SourceGroup,
    SourceItem,
    SourceOptional,
    SourceProduction,
    SourceRepeat,
    SourceSequence,
)
from .source_validation import validate_source_grammar


@dataclass(frozen=True, slots=True)
class ParseResult:
    grammar: Grammar | None
    diagnostics: tuple[Diagnostic, ...]
    source_grammar: SourceGrammar | None = None
    lowering: LoweringResult | None = None


@dataclass(frozen=True, slots=True)
class SourceParseResult:
    grammar: SourceGrammar | None
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True, slots=True)
class LogicalDeclaration:
    text: str
    start_offset: int
    end_offset: int


class Cursor:
    def __init__(self, text: str, path: str) -> None:
        self.text = text
        self.path = path
        self.offset = 0
        self.line = 1
        self.column = 1

    def position(self) -> SourcePosition:
        return SourcePosition(self.line, self.column, self.offset)

    def advance(self) -> str:
        char = self.text[self.offset]
        self.offset += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char


_BINDING_IDENTIFIER = re.compile(
    r"[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*"
)
_BINDING_CONSTANT = re.compile(
    r"[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*"
    r"(?:\.[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*)*"
)


def parse_grammar(text: str, path: str = "<memory>") -> ParseResult:
    source_result = parse_source_grammar(text, path)
    diagnostics = DiagnosticBag(source_result.diagnostics)
    if (
        source_result.grammar is not None
        and not diagnostics.has_errors
    ):
        diagnostics.extend(
            _parser_stage_diagnostics(
                validate_source_grammar(source_result.grammar).diagnostics
            )
        )
        diagnostics.extend(
            validate_bindings(source_result.grammar).diagnostics
        )
    lowering = None
    if source_result.grammar is not None and not diagnostics.has_errors:
        lowering = lower_source_grammar(source_result.grammar)
        diagnostics.extend(_parser_stage_diagnostics(lowering.diagnostics))
        grammar = lowering.grammar
    else:
        grammar, _ = _flatten_bnf_source(source_result.grammar)
    return ParseResult(
        grammar,
        diagnostics.sorted(),
        source_result.grammar,
        lowering,
    )


def _parser_stage_diagnostics(
    diagnostics: tuple[Diagnostic, ...],
) -> tuple[Diagnostic, ...]:
    # Direct-LR diagnostics are formal validation results. Keep the parse
    # facade usable by low-level CFG analysis/oracle tests, which intentionally
    # inspect invalid recursive grammars, and publish LR diagnostics through
    # validate_grammar when its lowering sidecar is available.
    return tuple(
        item for item in diagnostics if not item.code.startswith("LR")
    )


def parse_source_grammar(
    text: str,
    path: str = "<memory>",
) -> SourceParseResult:
    bag = DiagnosticBag()
    declarations = _logical_declarations(text, path, bag)
    production_builders: dict[str, _SourceProductionBuilder] = {}
    identifiers: list[IdentifierDefinition] = []
    production_order = 0
    identifier_order = 0

    for declaration in declarations:
        header, body, header_span, body_start_offset = _split_declaration(
            declaration, text, path, bag
        )
        if header is None:
            continue
        if header.startswith("#"):
            definition = _parse_identifier_definition(
                header, body, header_span, identifier_order, path, bag
            )
            if definition is not None:
                identifiers.append(definition)
                identifier_order += 1
            continue
        parsed_header = _parse_production_header(header, header_span, bag)
        if parsed_header is None:
            continue
        name, parameters = parsed_header
        alternatives = _parse_source_alternatives(
            body,
            body_start_offset,
            text,
            path,
            bag,
        )
        builder = production_builders.get(name)
        if builder is None:
            builder = _SourceProductionBuilder(
                name,
                parameters,
                production_order,
                header_span,
            )
            production_builders[name] = builder
            production_order += 1
        builder.add_declaration(parameters, alternatives, header_span, bag)

    productions = tuple(builder.build() for builder in production_builders.values())
    grammar = SourceGrammar(productions, tuple(identifiers), path)
    return SourceParseResult(grammar, bag.sorted())


def _flatten_bnf_source(
    grammar: SourceGrammar | None,
) -> tuple[Grammar | None, SourceSpan | None]:
    if grammar is None:
        return None, None
    productions: list[Production] = []
    for production in grammar.productions:
        alternatives: list[Alternative] = []
        for alternative in production.alternatives:
            first_ebnf = next(
                (
                    item.span
                    for item in alternative.body.items
                    if isinstance(
                        item,
                        (
                            SourceGroup,
                            SourceRepeat,
                            SourceOptional,
                            SourceConstructor,
                            SourceBinding,
                            SourceConstantBinding,
                        ),
                    )
                ),
                None,
            )
            if first_ebnf is not None:
                return None, first_ebnf
            alternatives.append(
                Alternative(
                    alternative.index,
                    tuple(alternative.body.items),
                    alternative.span,
                )
            )
        productions.append(
            Production(
                production.name,
                production.parameters,
                tuple(alternatives),
                production.order,
                production.span,
            )
        )
    return (
        Grammar(
            tuple(productions),
            grammar.identifier_definitions,
            grammar.path,
        ),
        None,
    )


def _first_binding_span(
    grammar: SourceGrammar | None,
) -> SourceSpan | None:
    if grammar is None:
        return None
    for production in grammar.productions:
        for alternative in production.alternatives:
            found = _first_binding_in_sequence(alternative.body)
            if found is not None:
                return found
    return None


def _first_binding_in_sequence(
    sequence: SourceSequence,
) -> SourceSpan | None:
    for item in sequence.items:
        if isinstance(
            item,
            (SourceConstructor, SourceBinding, SourceConstantBinding),
        ):
            return item.span
        if isinstance(item, SourceGroup):
            for alternative in item.alternatives:
                found = _first_binding_in_sequence(alternative.body)
                if found is not None:
                    return found
        if isinstance(item, (SourceRepeat, SourceOptional)) and isinstance(
            item.body,
            SourceGroup,
        ):
            for alternative in item.body.alternatives:
                found = _first_binding_in_sequence(alternative.body)
                if found is not None:
                    return found
    return None


def _logical_declarations(text: str, path: str, bag: DiagnosticBag) -> tuple[LogicalDeclaration, ...]:
    declarations: list[LogicalDeclaration] = []
    cleaned = list(text)
    start = _next_nonspace(text, 0)
    if start is None:
        return ()
    lexeme_quote = False
    bsl_quote = False
    line_comment = False
    braces = 0
    angles = 0
    parentheses = 0
    quote_start: int | None = None
    brace_start: int | None = None
    angle_start: int | None = None
    parenthesis_start: int | None = None
    index = start
    while index < len(text):
        char = text[index]
        next_start = _next_nonspace(text, index + 1) if char == "\n" else None
        if char == "\n" and next_start is not None and _looks_like_declaration(text, next_start):
            _report_unclosed(
                text, path, bag, quote_start, brace_start, angle_start, parenthesis_start
            )
            end = _trim_end(text, start, index)
            if end > start:
                cleaned_declaration = "".join(cleaned[start:end])
                if cleaned_declaration.strip():
                    declarations.append(LogicalDeclaration(cleaned_declaration, start, end))
            start = next_start
            if start is None:
                break
            lexeme_quote = bsl_quote = line_comment = False
            braces = angles = parentheses = 0
            quote_start = brace_start = angle_start = parenthesis_start = None
            index = start
            continue
        if line_comment:
            if char == "\n":
                line_comment = False
            else:
                if braces == 0:
                    cleaned[index] = " "
                index += 1
                continue
        if lexeme_quote:
            if char == "'" and index + 1 < len(text) and text[index + 1] == "'":
                index += 1
            elif char == "'":
                lexeme_quote = False
                quote_start = None
        elif bsl_quote:
            if char == '"' and index + 1 < len(text) and text[index + 1] == '"':
                index += 1
            elif char == '"':
                bsl_quote = False
        elif char == "'":
            lexeme_quote = True
            quote_start = index
        elif char == "{":
            if braces == 0:
                brace_start = index
            braces += 1
        elif char == "}" and braces:
            braces -= 1
            if braces == 0:
                brace_start = None
        elif char == "}" and not braces:
            _error(bag, "GP006", "unexpected closing delimiter", _span(text, path, index, index + 1))
        elif char == '"' and (braces or parentheses):
            bsl_quote = True
        elif braces and char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            line_comment = True
            index += 1
        elif braces == 0 and char == "<":
            if angles == 0:
                angle_start = index
            angles += 1
        elif braces == 0 and char == ">" and angles:
            angles -= 1
            if angles == 0:
                angle_start = None
        elif braces == 0 and char == ">" and not angles:
            _error(bag, "GP006", "unexpected closing delimiter", _span(text, path, index, index + 1))
        elif braces == 0 and angles == 0 and char == "(":
            if parentheses == 0:
                parenthesis_start = index
            parentheses += 1
        elif braces == 0 and angles == 0 and char == ")" and parentheses:
            parentheses -= 1
            if parentheses == 0:
                parenthesis_start = None
        elif braces == 0 and angles == 0 and char == ")" and not parentheses:
            _error(bag, "GP006", "unexpected closing delimiter", _span(text, path, index, index + 1))
        elif (
            braces == 0
            and angles == 0
            and parentheses == 0
            and not lexeme_quote
            and char == "/"
            and index + 1 < len(text)
            and text[index + 1] == "/"
        ):
            line_comment = True
            cleaned[index] = cleaned[index + 1] = " "
            index += 1
        index += 1
    _report_unclosed(text, path, bag, quote_start, brace_start, angle_start, parenthesis_start)
    end = _trim_end(text, start, len(text))
    if end > start:
        cleaned_declaration = "".join(cleaned[start:end])
        if cleaned_declaration.strip():
            declarations.append(LogicalDeclaration(cleaned_declaration, start, end))
    return tuple(declarations)


def _split_declaration(
    declaration: LogicalDeclaration, text: str, path: str, bag: DiagnosticBag
) -> tuple[str | None, str, SourceSpan, int]:
    split = _find_top_level(declaration.text, "::=")
    span = _span(text, path, declaration.start_offset, declaration.end_offset)
    if split is None:
        _error(bag, "GP001", "expected ::= in declaration", span)
        return None, "", span, declaration.start_offset
    header = declaration.text[:split].strip()
    body_start_offset = declaration.start_offset + split + 3
    body = declaration.text[split + 3 :]
    header_start = declaration.start_offset + declaration.text.index(header) if header else declaration.start_offset
    header_span = _span(text, path, header_start, header_start + len(header))
    if not header:
        _error(bag, "GP001", "declaration header is empty", header_span)
        return None, body, header_span, body_start_offset
    return header, body, header_span, body_start_offset


def _parse_identifier_definition(
    header: str,
    body: str,
    span: SourceSpan,
    order: int,
    path: str,
    bag: DiagnosticBag,
) -> IdentifierDefinition | None:
    del path
    name = header[1:].strip()
    token_types = tuple(part.strip() for part in _split_top_level(body, "|") if part.strip())
    if not name:
        _error(bag, "GP001", "invalid identifier definition", span)
        return None
    return IdentifierDefinition(name, token_types, order, span)


def _parse_production_header(
    header: str, span: SourceSpan, bag: DiagnosticBag
) -> tuple[str, tuple[str, ...]] | None:
    if not header.startswith("<"):
        _error(bag, "GP001", "production header must start with <", span)
        return None
    closing = header.find(">")
    if closing <= 1:
        _error(bag, "GP001", "invalid production header", span)
        return None
    name = header[1:closing].strip()
    rest = header[closing + 1 :].strip()
    if not name or (rest and not (rest.startswith("(") and rest.endswith(")"))):
        _error(bag, "GP001", "invalid production header", span)
        return None
    parameters = _split_arguments(rest[1:-1]) if rest else ()
    if not name or any(not parameter for parameter in parameters):
        _error(bag, "GP001", "invalid production header", span)
        return None
    if len(set(parameters)) != len(parameters):
        _error(bag, "GR002", "duplicate formal parameter", span)
    return name, parameters


def _parse_source_alternatives(
    body: str,
    body_start_offset: int,
    text: str,
    path: str,
    bag: DiagnosticBag,
) -> tuple[SourceAlternative, ...]:
    alternatives: list[SourceAlternative] = []
    consumed = 0
    for index, raw in enumerate(_split_top_level(body, "|")):
        stripped = raw.strip()
        start = body_start_offset + consumed + (len(raw) - len(raw.lstrip()))
        span = _span(text, path, start, start + len(stripped))
        if not stripped:
            _error(bag, "GP007", "alternative is empty", span)
        alternatives.append(
            SourceAlternative(
                index,
                _parse_source_sequence(stripped, text, path, start, bag),
                span,
            )
        )
        consumed += len(raw) + 1
    return tuple(alternatives)


def _parse_source_sequence(
    body: str,
    text: str,
    path: str,
    start_offset: int,
    bag: DiagnosticBag,
) -> SourceSequence:
    items: list[SourceItem] = []
    epsilon_seen = False
    pending_binding: tuple[
        str,
        BindingMode,
        int,
        SourceSpan,
    ] | None = None
    index = 0
    while index < len(body):
        if body[index].isspace():
            index += 1
            continue
        symbol_start = index
        char = body[index]
        if char == "@":
            if pending_binding is not None:
                _error(
                    bag,
                    "GP010",
                    "binding value is missing",
                    pending_binding[3],
                )
                pending_binding = None
            matched = _BINDING_IDENTIFIER.match(body, index + 1)
            if matched is None:
                _error(
                    bag,
                    "GP010",
                    "constructor name is missing",
                    _span(
                        text,
                        path,
                        start_offset + index,
                        start_offset + index + 1,
                    ),
                )
                index += 1
                continue
            items.append(
                SourceConstructor(
                    matched.group(0),
                    _span(
                        text,
                        path,
                        start_offset + index,
                        start_offset + matched.end(),
                    ),
                )
            )
            index = matched.end()
            continue

        binding_prefix = (
            _binding_prefix(body, index)
            if pending_binding is None
            else None
        )
        if binding_prefix is not None:
            property_name, operator, operator_start, operator_end = (
                binding_prefix
            )
            operator_span = _span(
                text,
                path,
                start_offset + operator_start,
                start_offset + operator_end,
            )
            index = operator_end
            if operator == ":=":
                value_start = _next_nonspace(body, index)
                if value_start is None:
                    _error(
                        bag,
                        "GP010",
                        "constant binding value is missing",
                        operator_span,
                    )
                    index = len(body)
                    continue
                matched = _BINDING_CONSTANT.match(body, value_start)
                if matched is None or (
                    matched.end() < len(body)
                    and body[matched.end()] == "."
                ):
                    _error(
                        bag,
                        "GP010",
                        "constant binding value is malformed",
                        _span(
                            text,
                            path,
                            start_offset + value_start,
                            start_offset + min(value_start + 1, len(body)),
                        ),
                    )
                    index = _next_token_boundary(body, value_start)
                    continue
                end = matched.end()
                items.append(
                    SourceConstantBinding(
                        property_name,
                        matched.group(0),
                        _span(
                            text,
                            path,
                            start_offset + symbol_start,
                            start_offset + end,
                        ),
                        operator_span,
                    )
                )
                index = end
                continue
            pending_binding = (
                property_name,
                (
                    BindingMode.APPEND
                    if operator == "+="
                    else BindingMode.SCALAR
                ),
                symbol_start,
                operator_span,
            )
            continue

        if char in "=:":
            _error(
                bag,
                "GP010",
                "binding operator has no property",
                _span(text, path, start_offset + index, start_offset + index + 1),
            )
            index += 1
            continue
        if char in "*+?":
            _error(
                bag,
                "GP008",
                "postfix operator has no operand",
                _span(text, path, start_offset + index, start_offset + index + 1),
            )
            index += 1
            continue
        if char == "{":
            if pending_binding is not None:
                _error(
                    bag,
                    "GP010",
                    "binding value is missing",
                    pending_binding[3],
                )
                pending_binding = None
            end = _matching_action(body, index)
            if end is None:
                break
            items.append(
                Action(
                    body[index + 1 : end].strip(),
                    _syntax_boundary(items),
                    _span(
                        text,
                        path,
                        start_offset + index,
                        start_offset + end + 1,
                    ),
                )
            )
            index = end + 1
            continue

        primary: SourceItem | None = None
        if char == "'":
            end = _quoted_end(body, index)
            if end is None:
                break
            primary = Lexeme(
                body[index + 1 : end].replace("''", "'"),
                _span(
                    text,
                    path,
                    start_offset + index,
                    start_offset + end + 1,
                ),
            )
            index = end + 1
        elif char == "<":
            end = body.find(">", index + 1)
            if end < 0:
                break
            name = body[index + 1 : end].strip()
            if not name:
                _error(
                    bag,
                    "GP007",
                    "invalid symbol",
                    _span(
                        text,
                        path,
                        start_offset + index,
                        start_offset + end + 1,
                    ),
                )
                index = end + 1
                continue
            index = end + 1
            arguments: tuple[str, ...] = ()
            if index < len(body) and body[index] == "(":
                argument_end = _matching_parenthesis(body, index)
                if argument_end is None:
                    break
                arguments = _split_arguments(body[index + 1 : argument_end])
                index = argument_end + 1
            primary = NonterminalCall(
                name,
                arguments,
                _span(
                    text,
                    path,
                    start_offset + symbol_start,
                    start_offset + index,
                ),
            )
        elif char == "(":
            end = _matching_grammar_group(body, index)
            if end is None:
                break
            content = body[index + 1 : end]
            group_span = _span(
                text,
                path,
                start_offset + index,
                start_offset + end + 1,
            )
            if not content.strip():
                _error(bag, "GP009", "group is empty", group_span)
                alternatives: tuple[SourceAlternative, ...] = ()
            else:
                alternatives = _parse_source_alternatives(
                    content,
                    start_offset + index + 1,
                    text,
                    path,
                    bag,
                )
            primary = SourceGroup(alternatives, group_span)
            index = end + 1
        else:
            index += 1
            while (
                index < len(body)
                and not body[index].isspace()
                and body[index] not in "{'<#&()*+?|@=:"
            ):
                index += 1
            token = body[symbol_start:index]
            if token == "ПУСТО":
                if pending_binding is not None:
                    _error(
                        bag,
                        "GP010",
                        "binding value cannot be ПУСТО",
                        pending_binding[3],
                    )
                    pending_binding = None
                epsilon_seen = True
                continue
            span = _span(
                text,
                path,
                start_offset + symbol_start,
                start_offset + index,
            )
            if token.startswith("#"):
                if len(token) == 1:
                    _error(bag, "GP007", "invalid symbol", span)
                else:
                    primary = IdentifierRef(token[1:], span)
            elif token.startswith("&"):
                if len(token) == 1:
                    _error(bag, "GP007", "invalid symbol", span)
                else:
                    primary = Constant(token[1:], span)
            else:
                primary = Terminal(token, span)

        if primary is None:
            continue
        postfix_index = _next_nonspace(body, index)
        if postfix_index is not None and body[postfix_index] in "*+?":
            operator = body[postfix_index]
            operator_span = _span(
                text,
                path,
                start_offset + postfix_index,
                start_offset + postfix_index + 1,
            )
            construct_span = SourceSpan(
                primary.span.path,
                primary.span.start,
                operator_span.end,
            )
            if operator == "?":
                primary = SourceOptional(
                    primary,
                    construct_span,
                    operator_span,
                )
            else:
                primary = SourceRepeat(
                    primary,
                    (
                        QuantifierKind.ZERO_OR_MORE
                        if operator == "*"
                        else QuantifierKind.ONE_OR_MORE
                    ),
                    construct_span,
                    operator_span,
                )
            index = postfix_index + 1
            repeated_index = _next_nonspace(body, index)
            if (
                repeated_index is not None
                and body[repeated_index] in "*+?"
            ):
                _error(
                    bag,
                    "EBNF203",
                    "repeated postfix operator is not allowed",
                    _span(
                        text,
                        path,
                        start_offset + repeated_index,
                        start_offset + repeated_index + 1,
                    ),
                )
                while (
                    repeated_index < len(body)
                    and body[repeated_index] in "*+?"
                ):
                    repeated_index += 1
                index = repeated_index
        if pending_binding is not None:
            property_name, mode, binding_start, operator_span = (
                pending_binding
            )
            primary = SourceBinding(
                property_name,
                mode,
                primary,
                SourceSpan(
                    primary.span.path,
                    _span(
                        text,
                        path,
                        start_offset + binding_start,
                        start_offset + binding_start + 1,
                    ).start,
                    primary.span.end,
                ),
                operator_span,
            )
            pending_binding = None
        items.append(primary)

    if pending_binding is not None:
        _error(
            bag,
            "GP010",
            "binding value is missing",
            pending_binding[3],
        )
    if epsilon_seen and any(_is_syntax_item(item) for item in items):
        _error(
            bag,
            "GR004",
            "ПУСТО cannot be mixed with a syntax symbol",
            _span(text, path, start_offset, start_offset + len(body)),
        )
    sequence_span = _span(
        text,
        path,
        start_offset,
        start_offset + len(body),
    )
    return SourceSequence(tuple(items), sequence_span)


def _binding_prefix(
    text: str,
    start: int,
) -> tuple[str, str, int, int] | None:
    matched = _BINDING_IDENTIFIER.match(text, start)
    if matched is None:
        return None
    operator_start = matched.end()
    while operator_start < len(text) and text[operator_start].isspace():
        operator_start += 1
    for operator in ("+=", ":=", "="):
        if text.startswith(operator, operator_start):
            return (
                matched.group(0),
                operator,
                operator_start,
                operator_start + len(operator),
            )
    return None


def _next_token_boundary(text: str, start: int) -> int:
    position = start
    while position < len(text) and not text[position].isspace():
        position += 1
    return position


def _is_syntax_item(item: SourceItem) -> bool:
    return not isinstance(
        item,
        (Action, SourceConstructor, SourceConstantBinding),
    )


def _syntax_boundary(items: list[SourceItem]) -> int:
    return sum(1 for item in items if _is_syntax_item(item))


@dataclass(slots=True)
class _SourceProductionBuilder:
    name: str
    parameters: tuple[str, ...]
    order: int
    span: SourceSpan
    alternatives: list[SourceAlternative] | None = None

    def add_declaration(
        self,
        parameters: tuple[str, ...],
        alternatives: tuple[SourceAlternative, ...],
        span: SourceSpan,
        bag: DiagnosticBag,
    ) -> None:
        if parameters and self.parameters and parameters != self.parameters:
            _error(
                bag,
                "GR001",
                "incompatible repeated production parameters",
                span,
            )
            return
        if parameters and not self.parameters:
            self.parameters = parameters
        if self.alternatives is None:
            self.alternatives = []
        offset = len(self.alternatives)
        self.alternatives.extend(
            SourceAlternative(
                offset + alternative.index,
                alternative.body,
                alternative.span,
            )
            for alternative in alternatives
        )

    def build(self) -> SourceProduction:
        return SourceProduction(
            self.name,
            self.parameters,
            tuple(self.alternatives or ()),
            self.order,
            self.span,
        )


def _next_nonspace(text: str, index: int) -> int | None:
    while index < len(text) and text[index].isspace():
        index += 1
    return index if index < len(text) else None


def _trim_end(text: str, start: int, end: int) -> int:
    while end > start and text[end - 1].isspace():
        end -= 1
    return end


def _looks_like_declaration(text: str, index: int) -> bool:
    if text[index] == "#":
        return "::=" in text[index : text.find("\n", index) if text.find("\n", index) >= 0 else len(text)]
    if text[index] != "<":
        return False
    line_end = text.find("\n", index)
    line = text[index : line_end if line_end >= 0 else len(text)]
    return ">" in line and "::=" in line


def _report_unclosed(
    text: str,
    path: str,
    bag: DiagnosticBag,
    quote_start: int | None,
    brace_start: int | None,
    angle_start: int | None,
    parenthesis_start: int | None,
) -> None:
    if quote_start is not None:
        _error(bag, "GP002", "unclosed quote", _span(text, path, quote_start, quote_start + 1))
    elif brace_start is not None:
        _error(bag, "GP003", "unclosed action", _span(text, path, brace_start, brace_start + 1))
    elif angle_start is not None:
        _error(bag, "GP004", "unclosed nonterminal", _span(text, path, angle_start, angle_start + 1))
    elif parenthesis_start is not None:
        _error(
            bag,
            "GP005",
            "unclosed argument list",
            _span(text, path, parenthesis_start, parenthesis_start + 1),
        )


def _find_top_level(text: str, marker: str) -> int | None:
    quote = False
    bsl_quote = False
    line_comment = False
    braces = 0
    angles = 0
    parentheses = 0
    index = 0
    while index < len(text):
        char = text[index]
        if line_comment:
            if char == "\n":
                line_comment = False
        elif quote:
            if char == "'" and index + 1 < len(text) and text[index + 1] == "'":
                index += 1
            elif char == "'":
                quote = False
        elif bsl_quote:
            if char == '"' and index + 1 < len(text) and text[index + 1] == '"':
                index += 1
            elif char == '"':
                bsl_quote = False
        elif braces and char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            line_comment = True
            index += 1
        elif char == "'":
            quote = True
        elif char == '"' and (braces or parentheses):
            bsl_quote = True
        elif char == "{":
            braces += 1
        elif char == "}" and braces:
            braces -= 1
        elif not braces and char == "<":
            angles += 1
        elif not braces and char == ">" and angles:
            angles -= 1
        elif not braces and not angles and char == "(":
            parentheses += 1
        elif not braces and not angles and char == ")" and parentheses:
            parentheses -= 1
        elif not quote and not bsl_quote and not line_comment and not braces and not angles and not parentheses and text.startswith(marker, index):
            return index
        index += 1
    return None


def _split_top_level(text: str, delimiter: str) -> tuple[str, ...]:
    parts: list[str] = []
    start = 0
    index = 0
    quote = False
    bsl_quote = False
    line_comment = False
    braces = 0
    angles = 0
    parentheses = 0
    while index < len(text):
        char = text[index]
        if line_comment:
            if char == "\n":
                line_comment = False
        elif quote:
            if char == "'" and index + 1 < len(text) and text[index + 1] == "'":
                index += 1
            elif char == "'":
                quote = False
        elif bsl_quote:
            if char == '"' and index + 1 < len(text) and text[index + 1] == '"':
                index += 1
            elif char == '"':
                bsl_quote = False
        elif braces and char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            line_comment = True
            index += 1
        elif char == "'":
            quote = True
        elif char == '"':
            bsl_quote = True
        elif char == "{":
            braces += 1
        elif char == "}" and braces:
            braces -= 1
        elif not braces and char == "<":
            angles += 1
        elif not braces and char == ">" and angles:
            angles -= 1
        elif not braces and not angles and char == "(":
            parentheses += 1
        elif not braces and not angles and char == ")" and parentheses:
            parentheses -= 1
        elif not quote and not bsl_quote and not line_comment and not braces and not angles and not parentheses and text.startswith(delimiter, index):
            parts.append(text[start:index])
            index += len(delimiter)
            start = index
            continue
        index += 1
    parts.append(text[start:])
    return tuple(parts)


def _quoted_end(text: str, start: int) -> int | None:
    index = start + 1
    while index < len(text):
        if text[index] == "'" and index + 1 < len(text) and text[index + 1] == "'":
            index += 2
        elif text[index] == "'":
            return index
        else:
            index += 1
    return None


def _matching_action(text: str, start: int) -> int | None:
    depth = 0
    quote = False
    line_comment = False
    index = start
    while index < len(text):
        char = text[index]
        if line_comment:
            if char == "\n":
                line_comment = False
        elif quote:
            if char == '"' and index + 1 < len(text) and text[index + 1] == '"':
                index += 2
                continue
            if char == '"':
                quote = False
        elif char == '"':
            quote = True
        elif char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            line_comment = True
            index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _matching_parenthesis(text: str, start: int) -> int | None:
    depth = 0
    quote = False
    index = start
    while index < len(text):
        char = text[index]
        if quote:
            if char == '"' and index + 1 < len(text) and text[index + 1] == '"':
                index += 2
                continue
            if char == '"':
                quote = False
        elif char == '"':
            quote = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _matching_grammar_group(text: str, start: int) -> int | None:
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "'":
            end = _quoted_end(text, index)
            if end is None:
                return None
            index = end + 1
            continue
        if char == "{":
            end = _matching_action(text, index)
            if end is None:
                return None
            index = end + 1
            continue
        if char == "<":
            end = text.find(">", index + 1)
            if end < 0:
                return None
            index = end + 1
            if index < len(text) and text[index] == "(":
                argument_end = _matching_parenthesis(text, index)
                if argument_end is None:
                    return None
                index = argument_end + 1
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _split_arguments(text: str) -> tuple[str, ...]:
    if not text.strip():
        return ()
    return tuple(item.strip() for item in _split_top_level(text, ","))


def _span(text: str, path: str, start: int, end: int) -> SourceSpan:
    def position(offset: int) -> SourcePosition:
        line = text.count("\n", 0, offset) + 1
        previous_newline = text.rfind("\n", 0, offset)
        return SourcePosition(line, offset - previous_newline, offset)

    return SourceSpan(path, position(start), position(end))


def _error(bag: DiagnosticBag, code: str, message: str, span: SourceSpan) -> None:
    bag.add(Diagnostic(code, Severity.ERROR, message, span))
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
