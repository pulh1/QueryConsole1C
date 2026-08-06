from __future__ import annotations

import re

from .model import Action


CONSTRUCTOR = re.compile(r"^Новый[0-9A-Za-zА-Яа-яЁё_]+$")
_IDENTIFIER = re.compile(r"[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*")


class ActionCompiler:
    def __init__(self, *, indent: str, guard: bool) -> None:
        self._indent = indent
        self._guard = guard
        self._constructor_names: list[str] = []
        self._seen_constructor_names: set[str] = set()

    @property
    def constructor_names(self) -> tuple[str, ...]:
        return tuple(self._constructor_names)

    def compile(self, action: Action) -> str:
        statements = _split_statements(_normalize_newlines(action.text))
        if not statements:
            return ""

        body_indent = self._indent + ("\t" if self._guard else "")
        rendered = "".join(
            self._render_statement(statement, body_indent)
            for statement in statements
        )
        if not self._guard:
            return rendered
        return (
            f'{self._indent}Если ТекущийЭлемент <> "ПУСТО" Тогда\r\n'
            f"{rendered}"
            f"{self._indent}КонецЕсли;\r\n"
        )

    def _render_statement(self, statement: str, indent: str) -> str:
        rewritten = self._rewrite_assignment(statement)
        indented = rewritten.replace("\n", f"\r\n{indent}")
        return f"{indent}{indented};\r\n"

    def _rewrite_assignment(self, statement: str) -> str:
        assignment = _top_level_assignment(statement)
        if assignment is None:
            return statement
        left = statement[:assignment].rstrip()
        right = statement[assignment + 1 :].strip()
        if CONSTRUCTOR.fullmatch(right) is not None:
            self._record_constructor(right)
            right = (
                f"ЭлементыМоделиЗапроса.{right}(ТекущийТокен)"
            )
        # Legacy compatibility: canonical semantic-action rendering may keep
        # author spacing, but the reference 1C generator normalizes assignment
        # whitespace. Keep this visible so a future canonical-only renderer can
        # remove the normalization intentionally.
        return f"{left} = {right}"

    def _record_constructor(self, name: str) -> None:
        if name in self._seen_constructor_names:
            return
        self._seen_constructor_names.add(name)
        self._constructor_names.append(name)


def compile_action(action: Action, indent: str, guard: bool) -> str:
    return ActionCompiler(indent=indent, guard=guard).compile(action)


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_statements(text: str) -> tuple[str, ...]:
    result: list[str] = []
    start = 0
    for position in _top_level_positions(text, ";"):
        statement = text[start:position].strip()
        # Legacy compatibility: 1C СтрРазделить preserves empty fields. The
        # reference renderer consequently emits a standalone ";" for empty
        # semantic-action statements, including a trailing delimiter.
        result.append(statement)
        start = position + 1
    tail = text[start:].strip()
    if tail or result:
        result.append(tail)
    return tuple(result)


def _top_level_assignment(text: str) -> int | None:
    for position in _top_level_positions(text, "="):
        if position and text[position - 1] in "<>!=":
            continue
        if _is_assignable_left(text[:position]):
            return position
    return None


def _is_assignable_left(text: str) -> bool:
    normalized = text.strip()
    if "\n" in normalized:
        *prefix, normalized = normalized.split("\n")
        if any(
            line.strip() and not line.lstrip().startswith("//")
            for line in prefix
        ):
            return False
        normalized = normalized.strip()
    if not normalized:
        return False

    position = _consume_identifier(normalized, 0)
    if position is None:
        return False
    while True:
        position = _skip_space(normalized, position)
        if position == len(normalized):
            return True
        if normalized[position] == ".":
            position = _skip_space(normalized, position + 1)
            position = _consume_identifier(normalized, position)
            if position is None:
                return False
            continue
        if normalized[position] == "[":
            position = _consume_index(normalized, position)
            if position is None:
                return False
            continue
        return False


def _consume_identifier(text: str, position: int) -> int | None:
    matched = _IDENTIFIER.match(text, position)
    return matched.end() if matched is not None else None


def _skip_space(text: str, position: int) -> int:
    while position < len(text) and text[position].isspace():
        position += 1
    return position


def _consume_index(text: str, position: int) -> int | None:
    start = position
    depth = 0
    in_string = False
    position += 1
    while position < len(text):
        current = text[position]
        following = text[position + 1] if position + 1 < len(text) else ""
        if in_string:
            if current == '"' and following == '"':
                position += 2
                continue
            if current == '"':
                in_string = False
            position += 1
            continue
        if current == '"':
            in_string = True
        elif current == "[":
            depth += 1
        elif current == "]":
            if depth == 0:
                if not text[start + 1 : position].strip():
                    return None
                return position + 1
            depth -= 1
        position += 1
    return None


def _top_level_positions(text: str, target: str):
    in_string = False
    in_comment = False
    parenthesis_depth = 0
    bracket_depth = 0
    position = 0
    while position < len(text):
        current = text[position]
        following = text[position + 1] if position + 1 < len(text) else ""

        if in_comment:
            if current == "\n":
                in_comment = False
            position += 1
            continue

        if in_string:
            if current == '"' and following == '"':
                position += 2
                continue
            if current == '"':
                in_string = False
            position += 1
            continue

        if current == "/" and following == "/":
            in_comment = True
            position += 2
            continue
        if current == '"':
            in_string = True
            position += 1
            continue
        if current == "(":
            parenthesis_depth += 1
        elif current == ")" and parenthesis_depth:
            parenthesis_depth -= 1
        elif current == "[":
            bracket_depth += 1
        elif current == "]" and bracket_depth:
            bracket_depth -= 1
        elif (
            current == target
            and parenthesis_depth == 0
            and bracket_depth == 0
        ):
            yield position
        position += 1
