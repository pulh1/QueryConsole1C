from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import TypeAlias


_VALUE_TABLE_TYPE_MARKER = "acf6192e-81ca-46ef-93a6-5a6968b78663"
_INTEGER_RE = re.compile(r"[+-]?\d+\Z")
_DECIMAL_CHUNK_DIGITS = 9
_DECIMAL_CHUNK_BASE = 10**_DECIMAL_CHUNK_DIGITS
# Keeps recursive scanner frames well below Python's recursion limit.
_MAX_NESTING_DEPTH = 256


def _parse_decimal_integer(text: str) -> int:
    sign = 1
    position = 0
    if text[0] in "+-":
        if text[0] == "-":
            sign = -1
        position = 1

    value = 0
    while position < len(text):
        chunk_end = min(
            position + _DECIMAL_CHUNK_DIGITS, len(text)
        )
        chunk_value = 0
        for character in text[position:chunk_end]:
            chunk_value = chunk_value * 10 + ord(character) - ord("0")
        value = (
            value * 10 ** (chunk_end - position) + chunk_value
        )
        position = chunk_end
    return sign * value


def _format_decimal_integer(value: int) -> str:
    if value == 0:
        return "0"

    sign = ""
    if value < 0:
        sign = "-"
        value = -value

    chunks: list[int] = []
    while value:
        value, remainder = divmod(value, _DECIMAL_CHUNK_BASE)
        chunks.append(remainder)

    head = str(chunks.pop())
    tail = "".join(
        str(chunk).rjust(_DECIMAL_CHUNK_DIGITS, "0")
        for chunk in reversed(chunks)
    )
    return sign + head + tail

_ParsedNodeValue: TypeAlias = (
    int | str | tuple["_ParsedNode", ...]
)


@dataclass(frozen=True, slots=True)
class _ParsedNode:
    value: _ParsedNodeValue
    offset: int
    quoted: bool = False


@dataclass(frozen=True, slots=True)
class _ParsedList:
    node: _ParsedNode
    items: tuple[_ParsedNode, ...]

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> _ParsedNode:
        return self.items[index]

    def __bool__(self) -> bool:
        return bool(self.items)


class ColumnKind(StrEnum):
    STRING = "string"
    NUMBER = "number"


@dataclass(frozen=True, slots=True)
class ValueColumn:
    name: str
    kind: ColumnKind


@dataclass(frozen=True, slots=True)
class ValueTable:
    columns: tuple[ValueColumn, ...]
    rows: tuple[tuple[str | int | None, ...], ...]


class _SerializationScanner:
    def __init__(self, text: str) -> None:
        self._text = text
        self._offset = 0

    def scan(self) -> _ParsedNode:
        value = self._scan_value(nesting=0)
        self._skip_whitespace()
        if self._offset != len(self._text):
            self._fail("trailing data")
        return value

    def _scan_value(self, *, nesting: int) -> _ParsedNode:
        self._skip_whitespace()
        if self._offset >= len(self._text):
            self._fail("expected a value")

        current = self._text[self._offset]
        if current == "{":
            if nesting >= _MAX_NESTING_DEPTH:
                self._fail("nesting limit exceeded")
            return self._scan_list(nesting=nesting)
        if current == '"':
            return self._scan_string()
        if current in "},":
            self._fail("expected a value")
        return self._scan_atom()

    def _scan_list(self, *, nesting: int) -> _ParsedNode:
        list_offset = self._offset
        self._offset += 1
        result: list[_ParsedNode] = []
        self._skip_whitespace()
        if self._peek("}"):
            self._offset += 1
            return _ParsedNode((), list_offset)

        while True:
            result.append(self._scan_value(nesting=nesting + 1))
            self._skip_whitespace()
            if self._peek(","):
                self._offset += 1
                continue
            if self._peek("}"):
                self._offset += 1
                return _ParsedNode(tuple(result), list_offset)
            self._fail("expected ',' or '}'")

    def _scan_string(self) -> _ParsedNode:
        string_offset = self._offset
        self._offset += 1
        parts: list[str] = []
        start = self._offset
        while self._offset < len(self._text):
            if self._text[self._offset] != '"':
                self._offset += 1
                continue
            parts.append(self._text[start : self._offset])
            if self._peek('"', lookahead=1):
                parts.append('"')
                self._offset += 2
                start = self._offset
                continue
            self._offset += 1
            return _ParsedNode(
                "".join(parts), string_offset, quoted=True
            )
        self._fail("unterminated quoted string")

    def _scan_atom(self) -> _ParsedNode:
        start = self._offset
        while (
            self._offset < len(self._text)
            and self._text[self._offset] not in "{},"
            and not self._text[self._offset].isspace()
        ):
            self._offset += 1
        atom = self._text[start : self._offset]
        if _INTEGER_RE.fullmatch(atom):
            return _ParsedNode(_parse_decimal_integer(atom), start)
        return _ParsedNode(atom, start)

    def _skip_whitespace(self) -> None:
        while (
            self._offset < len(self._text)
            and self._text[self._offset].isspace()
        ):
            self._offset += 1

    def _peek(self, expected: str, *, lookahead: int = 0) -> bool:
        offset = self._offset + lookahead
        return (
            offset < len(self._text)
            and self._text[offset] == expected
        )

    def _fail(self, message: str) -> None:
        raise ValueError(f"{message} at offset {self._offset}")


class _ValueTableDecoder:
    def __init__(self, text: str) -> None:
        self._scanner = _SerializationScanner(text)

    def decode(self) -> ValueTable:
        root = self._expect_tuple(
            self._scanner.scan(), "value-table root", length=3
        )
        self._expect_equal(
            root, 0, "#", "value-table marker", quoted=True
        )
        self._expect_equal(
            root,
            1,
            _VALUE_TABLE_TYPE_MARKER,
            "value-table type marker",
            quoted=False,
        )

        payload = self._expect_tuple(
            root[2],
            "value-table payload",
            length=4,
            parent=root,
            index=2,
        )
        self._expect_equal(payload, 0, 9, "payload version")
        column_data = self._expect_tuple(
            payload[1],
            "column collection",
            parent=payload,
            index=1,
        )
        table_data = self._expect_tuple(
            payload[2],
            "table data",
            parent=payload,
            index=2,
        )
        indexes = self._expect_tuple(
            payload[3],
            "index collection",
            length=2,
            parent=payload,
            index=3,
        )
        self._expect_equal(indexes, 0, 0, "index collection marker")
        self._expect_equal(indexes, 1, 0, "index collection count")

        column_count = self._expect_nonnegative_int(
            column_data, 0, "column count"
        )
        if len(column_data) != column_count + 1:
            self._fail("incorrect column count", value=column_data)

        column_ids: list[int] = []
        column_names: list[str] = []
        declared_kinds: list[ColumnKind | None] = []
        for definition_index in range(column_count):
            definition = self._expect_tuple(
                column_data[definition_index + 1],
                "column definition",
                length=5,
                parent=column_data,
                index=definition_index + 1,
            )
            column_id = self._expect_nonnegative_int(
                definition, 0, "column identifier"
            )
            if column_id in column_ids:
                self._fail(
                    "duplicate column identifier",
                    parent=definition,
                    index=0,
                )
            column_ids.append(column_id)

            name = self._expect_quoted_string(
                definition, 1, "column name"
            )
            column_names.append(name)

            pattern = self._expect_tuple(
                definition[2],
                "column pattern",
                parent=definition,
                index=2,
            )
            if not pattern:
                self._fail("unsupported column pattern", value=pattern)
            self._expect_equal(
                pattern,
                0,
                "Pattern",
                "column pattern marker",
                quoted=True,
            )
            if len(pattern) == 1:
                declared_kinds.append(None)
            elif len(pattern) == 2:
                kind_data = self._expect_tuple(
                    pattern[1],
                    "column kind",
                    length=1,
                    parent=pattern,
                    index=1,
                )
                tag = kind_data[0].value
                if not kind_data[0].quoted:
                    self._fail(
                        "column kind must be quoted",
                        parent=kind_data,
                        index=0,
                    )
                if tag == "S":
                    declared_kinds.append(ColumnKind.STRING)
                elif tag == "N":
                    declared_kinds.append(ColumnKind.NUMBER)
                else:
                    self._fail("unsupported column kind", value=kind_data)
            else:
                self._fail("unsupported column pattern", value=pattern)
            self._expect_equal(
                definition, 3, "", "column title", quoted=True
            )
            self._expect_equal(definition, 4, 0, "column width")

        expected_table_length = 5 + 2 * column_count
        if len(table_data) != expected_table_length:
            self._fail("malformed table data", value=table_data)
        self._expect_equal(table_data, 0, 2, "table data marker")
        self._expect_equal(
            table_data, 1, column_count, "table column count"
        )
        for column_index, column_id in enumerate(column_ids):
            mapping_offset = 2 + 2 * column_index
            self._expect_equal(
                table_data,
                mapping_offset,
                column_index,
                "column order",
            )
            self._expect_equal(
                table_data,
                mapping_offset + 1,
                column_id,
                "column identifier mapping",
            )

        row_store_index = 2 + 2 * column_count
        row_store = self._expect_tuple(
            table_data[row_store_index],
            "row collection",
            parent=table_data,
            index=row_store_index,
        )
        if len(row_store) < 2:
            self._fail("malformed row collection", value=row_store)
        self._expect_equal(row_store, 0, 1, "row collection marker")
        row_count = self._expect_nonnegative_int(
            row_store, 1, "row count"
        )
        if len(row_store) != row_count + 2:
            self._fail("incorrect row count", value=row_store)

        expected_last_column = column_ids[-1] if column_ids else -1
        self._expect_equal(
            table_data,
            row_store_index + 1,
            expected_last_column,
            "last column identifier",
        )
        self._expect_equal(
            table_data,
            row_store_index + 2,
            row_count - 1,
            "last row identifier",
        )

        observed_kinds: list[set[ColumnKind]] = [
            set() for _ in range(column_count)
        ]
        rows: list[tuple[str | int | None, ...]] = []
        for row_index in range(row_count):
            row_value = self._expect_tuple(
                row_store[row_index + 2],
                "row",
                length=column_count + 4,
                parent=row_store,
                index=row_index + 2,
            )
            self._expect_equal(row_value, 0, 2, "row marker")
            self._expect_equal(row_value, 1, row_index, "row order")
            self._expect_equal(
                row_value, 2, column_count, "row width"
            )
            self._expect_equal(
                row_value,
                column_count + 3,
                0,
                "row terminator",
            )

            cells: list[str | int | None] = []
            for column_index in range(column_count):
                cell_index = 3 + column_index
                cell_node = row_value[cell_index]
                value, cell_kind = self._decode_cell(cell_node)
                declared_kind = declared_kinds[column_index]
                if (
                    cell_kind is not None
                    and declared_kind is not None
                    and cell_kind is not declared_kind
                ):
                    self._fail(
                        "cell kind does not match column kind",
                        value=cell_node,
                    )
                if cell_kind is not None:
                    observed_kinds[column_index].add(cell_kind)
                cells.append(value)
            rows.append(tuple(cells))

        columns: list[ValueColumn] = []
        for index, (name, declared_kind) in enumerate(
            zip(column_names, declared_kinds, strict=True)
        ):
            kind = declared_kind
            if kind is None:
                observed = observed_kinds[index]
                if len(observed) > 1:
                    definition = column_data[index + 1]
                    self._fail(
                        "untyped column contains mixed cell kinds",
                        value=definition,
                    )
                kind = next(iter(observed), ColumnKind.STRING)
            columns.append(ValueColumn(name, kind))

        return ValueTable(tuple(columns), tuple(rows))

    def _decode_cell(
        self, cell_node: _ParsedNode
    ) -> tuple[str | int | None, ColumnKind | None]:
        cell = self._expect_tuple(cell_node, "cell")
        if not cell:
            self._fail("empty cell", value=cell)
        if not cell[0].quoted:
            self._fail("cell tag must be quoted", parent=cell, index=0)
        tag = cell[0].value
        if tag == "U":
            if len(cell) != 1:
                self._fail("malformed undefined cell", value=cell)
            return None, None
        if tag == "S":
            if len(cell) != 2:
                self._fail("malformed string cell", value=cell)
            value = self._expect_quoted_string(
                cell, 1, "string cell value"
            )
            return value, ColumnKind.STRING
        if tag == "N":
            number = cell[1].value if len(cell) == 2 else None
            if (
                len(cell) != 2
                or not isinstance(number, int)
                or isinstance(number, bool)
            ):
                self._fail("malformed number cell", value=cell)
            return number, ColumnKind.NUMBER
        self._fail("unsupported cell tag", value=cell)

    def _expect_tuple(
        self,
        value: _ParsedNode,
        description: str,
        *,
        length: int | None = None,
        parent: _ParsedList | None = None,
        index: int | None = None,
    ) -> _ParsedList:
        if not isinstance(value.value, tuple):
            self._fail(
                f"{description} must be a list",
                value=value,
            )
        parsed = _ParsedList(value, value.value)
        if length is not None and len(parsed) != length:
            self._fail(f"malformed {description}", value=parsed)
        return parsed

    def _expect_nonnegative_int(
        self,
        parent: _ParsedList,
        index: int,
        description: str,
    ) -> int:
        if index >= len(parent):
            self._fail(f"missing {description}", value=parent)
        value = parent[index].value
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
        ):
            self._fail(
                f"{description} must be a nonnegative integer",
                parent=parent,
                index=index,
            )
        return value

    def _expect_equal(
        self,
        parent: _ParsedList,
        index: int,
        expected: object,
        description: str,
        *,
        quoted: bool | None = None,
    ) -> None:
        if index >= len(parent):
            self._fail(f"missing {description}", value=parent)
        node = parent[index]
        if node.value != expected:
            self._fail(
                f"incorrect {description}",
                parent=parent,
                index=index,
            )
        if (
            quoted is not None
            and node.quoted is not quoted
        ):
            qualifier = "quoted" if quoted else "unquoted"
            self._fail(
                f"{description} must be {qualifier}",
                parent=parent,
                index=index,
            )

    def _expect_quoted_string(
        self,
        parent: _ParsedList,
        index: int,
        description: str,
    ) -> str:
        if index >= len(parent):
            self._fail(f"missing {description}", value=parent)
        node = parent[index]
        value = node.value
        if (
            not isinstance(value, str)
            or not node.quoted
        ):
            self._fail(
                f"{description} must be a quoted string",
                parent=parent,
                index=index,
            )
        return value

    def _fail(
        self,
        message: str,
        *,
        value: _ParsedNode | _ParsedList | None = None,
        parent: _ParsedList | None = None,
        index: int | None = None,
    ) -> None:
        if (
            parent is not None
            and index is not None
            and index < len(parent)
        ):
            offset = parent[index].offset
        elif isinstance(value, _ParsedList):
            offset = value.node.offset
        elif isinstance(value, _ParsedNode):
            offset = value.offset
        elif parent is not None:
            offset = parent.node.offset
        else:
            offset = 0
        raise ValueError(f"{message} at offset {offset}")


class _ValueTableEncoder:
    def __init__(self, table: ValueTable) -> None:
        self._table = table

    def encode(self) -> str:
        self._validate()
        newline = "\r\n"
        column_count = len(self._table.columns)
        row_count = len(self._table.rows)

        column_parts: list[str] = []
        for index, column in enumerate(self._table.columns):
            tag = "S" if column.kind is ColumnKind.STRING else "N"
            column_parts.append(
                f'{{{index},{self._quote(column.name)},{newline}'
                f'{{"Pattern",{newline}{{"{tag}"}}{newline}}},"",0}}'
            )
        columns = f"{{{column_count}"
        if column_parts:
            columns += f",{newline}{f',{newline}'.join(column_parts)}{newline}"
        columns += "}"

        mapping = "".join(
            f",{index},{index}" for index in range(column_count)
        )
        row_parts: list[str] = []
        for row_index, row in enumerate(self._table.rows):
            cells = f",{newline}".join(
                self._encode_cell(value) for value in row
            )
            row_parts.append(
                f"{{2,{row_index},{column_count}"
                f"{f',{newline}{cells}' if cells else ''},0}}"
            )
        rows = f"{{1,{row_count}"
        if row_parts:
            rows += f",{newline}{f',{newline}'.join(row_parts)}{newline}"
        rows += "}"

        return (
            f'{{"#",{_VALUE_TABLE_TYPE_MARKER},{newline}'
            f"{{9,{newline}"
            f"{columns},{newline}"
            f"{{2,{column_count}{mapping},{newline}"
            f"{rows},{column_count - 1},{row_count - 1}}},{newline}"
            f"{{0,0}}{newline}"
            f"}}{newline}"
            f"}}"
        )

    @staticmethod
    def _quote(value: str) -> str:
        return f'"{value.replace(chr(34), chr(34) * 2)}"'

    def _encode_cell(self, value: str | int | None) -> str:
        if value is None:
            return '{"U"}'
        if isinstance(value, str):
            return f'{{"S",{self._quote(value)}}}'
        return f'{{"N",{_format_decimal_integer(value)}}}'

    def _validate(self) -> None:
        if not isinstance(self._table, ValueTable):
            raise ValueError("expected a ValueTable")
        if not isinstance(self._table.columns, tuple):
            raise ValueError("ValueTable columns must be a tuple")
        if not isinstance(self._table.rows, tuple):
            raise ValueError("ValueTable rows must be a tuple")
        for column_index, column in enumerate(self._table.columns):
            if not isinstance(column, ValueColumn):
                raise ValueError(
                    f"column {column_index} must be a ValueColumn"
                )
            if not isinstance(column.name, str):
                raise ValueError(
                    f"column {column_index} name must be a string"
                )
            if not isinstance(column.kind, ColumnKind):
                raise ValueError(
                    f"column {column_index} has an unsupported kind"
                )

        column_count = len(self._table.columns)
        for row_index, row in enumerate(self._table.rows):
            if not isinstance(row, tuple):
                raise ValueError(f"row {row_index} must be a tuple")
            if len(row) != column_count:
                raise ValueError(
                    f"row {row_index} has {len(row)} cells; "
                    f"expected {column_count}"
                )
            for column_index, (column, value) in enumerate(
                zip(self._table.columns, row, strict=True)
            ):
                if value is None:
                    continue
                if column.kind is ColumnKind.STRING:
                    valid = isinstance(value, str)
                else:
                    valid = (
                        isinstance(value, int)
                        and not isinstance(value, bool)
                    )
                if not valid:
                    raise ValueError(
                        f"cell ({row_index}, {column_index}) does not "
                        f"match {column.kind.value} column"
                    )


def encode_value_table(table: ValueTable) -> str:
    return _ValueTableEncoder(table).encode()


def decode_value_table(text: str) -> ValueTable:
    return _ValueTableDecoder(text).decode()
