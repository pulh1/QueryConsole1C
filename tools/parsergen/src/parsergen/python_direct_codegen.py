from __future__ import annotations

from pprint import pformat
from typing import TYPE_CHECKING, Mapping

from .model import Constant, IdentifierRef, Lexeme, NonterminalCall, SyntaxSymbol, Terminal
from .parser_ir import (
    ConsumeKnownSymbol,
    DiscardSymbol,
    Operation,
    ParseSymbol,
    ParserIr,
    ResolvedRegion,
    ReturnConstant,
    UndefinedValue,
)
from .source_model import SourceGrammar

if TYPE_CHECKING:
    from .direct_render_analysis import DirectRenderAnalysis
    from .python_semantic_codegen import AstNodeSchema


PYTHON_SEMANTIC_BACKEND_ID = "python-semantic-direct-v1"


class _DirectPythonRenderer:
    def __init__(
        self,
        source: SourceGrammar,
        parser_ir: ParserIr,
        entrypoints: Mapping[str, str],
        schema: tuple[AstNodeSchema, ...],
        analysis: DirectRenderAnalysis,
    ) -> None:
        self.source = source
        self.parser_ir = parser_ir
        self.entrypoints = dict(entrypoints)
        self.schema = schema
        self.analysis = analysis
        self.production_names = {
            item.name: f"_p_{index:04d}"
            for index, item in enumerate(parser_ir.productions)
        }
        self.identifier_types = {
            item.name: item.token_types for item in source.identifier_definitions
        }

    def render(self) -> str:
        return "\n\n".join((self._render_prelude(), self._render_parser())) + "\n"

    def _render_prelude(self) -> str:
        lines = [
            "from __future__ import annotations",
            "",
            "from dataclasses import dataclass",
            "",
            "",
            "@dataclass(frozen=True, slots=True)",
            "class SourceSpan:",
            "    start: int",
            "    end: int",
        ]
        for node in self.schema:
            lines.extend(("", "", "@dataclass(frozen=True, slots=True)", f"class {node.name}:"))
            for field in node.fields:
                lines.append(f"    {field.name}: object")
            lines.append("    span: SourceSpan")
        lines.extend(("", "", "AST_CLASSES = {"))
        lines.extend(f'    "{node.name}": {node.name},' for node in self.schema)
        lines.append("}")
        defaults = {
            node.name: tuple((field.name, field.category) for field in node.fields)
            for node in self.schema
        }
        lines.extend(("", f"NODE_DEFAULTS = {pformat(defaults, width=100, sort_dicts=True)}"))
        return "\n".join(lines)

    def _render_productions(self) -> str:
        return "\n\n".join(self._render_production(item) for item in self.parser_ir.productions)

    def _render_production(self, production) -> str:
        if production.decision is not None or len(production.alternatives) != 1:
            raise ValueError(
                "direct renderer does not support production decisions before Task 5"
            )
        alternative = production.alternatives[0]
        lines = [f"    def {self.production_names[production.name]}(self):", "        start = self._offset()"]
        lines.extend(
            self._render_sequence(
                alternative.operations,
                alternative.result_index,
                "        ",
                (),
            )
        )
        lines.append(
            "        return None"
            if alternative.result_index is None
            else f"        return {self._value_name((alternative.result_index,))}"
        )
        return "\n".join(lines)

    def _render_sequence(
        self,
        operations: tuple[Operation, ...],
        result_index: int | None,
        indent: str,
        trail: tuple[int, ...],
    ) -> list[str]:
        lines: list[str] = []
        for index, operation in enumerate(operations):
            lines.extend(self._render_operation(operation, indent, (*trail, index)))
        if result_index is None:
            return lines
        return lines

    def _render_operation(
        self,
        operation: Operation,
        indent: str,
        trail: tuple[int, ...],
    ) -> list[str]:
        value = self._value_name(trail)
        if isinstance(operation, ParseSymbol):
            if isinstance(operation.symbol, NonterminalCall):
                return [f"{indent}{value} = self.{self._production_name(operation.symbol.name)}()"]
            expected, capture = self._terminal_parts(operation.symbol)
            return [f"{indent}{value} = self._consume({expected!r}, {capture!r})"]
        if isinstance(operation, DiscardSymbol):
            if isinstance(operation.symbol, NonterminalCall):
                return [f"{indent}self.{self._production_name(operation.symbol.name)}()"]
            expected, _ = self._terminal_parts(operation.symbol)
            return [f"{indent}self._consume({expected!r}, False)"]
        if isinstance(operation, ConsumeKnownSymbol):
            expected, capture = self._terminal_parts(operation.symbol)
            if operation.capture_value:
                return [f"{indent}{value} = self._consume({expected!r}, {capture!r})"]
            return [f"{indent}self._consume({expected!r}, False)"]
        if isinstance(operation, ResolvedRegion):
            lines = self._render_sequence(
                operation.operations,
                operation.result_index,
                indent,
                (*trail, 0),
            )
            if operation.result_index is None:
                lines.append(f"{indent}{value} = None")
            else:
                lines.append(
                    f"{indent}{value} = {self._value_name((*trail, 0, operation.result_index))}"
                )
            return lines
        if isinstance(operation, (UndefinedValue, ReturnConstant)):
            return [f"{indent}{value} = {self._constant(operation.value)!r}"]
        raise TypeError(
            f"direct renderer does not support {type(operation).__name__} before its task"
        )

    def _render_parser(self) -> str:
        lines = [
            "class GeneratedParseError(ValueError):",
            "    def __init__(self, position, actual, expected):",
            "        self.position = position",
            "        self.actual = actual",
            "        self.expected = tuple(expected)",
            "        super().__init__(",
            "            f\"unexpected {actual!r} at token {position}; expected {self.expected!r}\"",
            "        )",
            "",
            "",
            "class GeneratedParser:",
            "    def parse(self, tokens, entrypoint):",
            "        self._tokens = tuple(tokens)",
            "        self._position = 0",
        ]
        for index, (entrypoint, production) in enumerate(self.entrypoints.items()):
            prefix = "if" if index == 0 else "elif"
            lines.extend(
                (
                    f"        {prefix} entrypoint == {entrypoint!r}:",
                    f"            result = self.{self._production_name(production)}()",
                )
            )
        lines.extend(
            (
                "        else:",
                "            raise ValueError(f\"unknown entrypoint {entrypoint!r}\")",
                "        if self._position != len(self._tokens):",
                "            self._raise(('$',))",
                "        return result",
                "",
                "    def _consume(self, expected, capture):",
                "        actual = self._lookahead(0)",
                "        if actual not in expected:",
                "            self._raise(expected)",
                "        token = self._tokens[self._position]",
                "        self._position += 1",
                "        if not capture:",
                "            return None",
                "        if capture == 'type':",
                "            return token.type",
                "        if capture == 'text':",
                "            return token.text",
                "        value = getattr(token, 'value', None)",
                "        return token.text if value is None else value",
                "",
                "    def _lookahead(self, offset):",
                "        index = self._position + offset",
                "        if index >= len(self._tokens):",
                "            return '$'",
                "        return self._tokens[index].type",
                "",
                "    def _offset(self):",
                "        if self._position < len(self._tokens):",
                "            return self._tokens[self._position].start",
                "        if self._tokens:",
                "            return self._tokens[-1].end",
                "        return 0",
                "",
                "    def _raise(self, expected):",
                "        raise GeneratedParseError(self._position, self._lookahead(0), expected)",
            )
        )
        lines.extend(("", *self._render_productions().splitlines()))
        return "\n".join(lines)

    def _terminal_parts(self, symbol: SyntaxSymbol) -> tuple[tuple[str, ...], str]:
        if isinstance(symbol, Terminal):
            return (symbol.token_type,), "type"
        if isinstance(symbol, Lexeme):
            return (symbol.text,), "type"
        if isinstance(symbol, Constant):
            return (symbol.token_type,), "value"
        if isinstance(symbol, IdentifierRef):
            try:
                return self.identifier_types[symbol.name], "text"
            except KeyError as error:
                raise ValueError(
                    f"unknown identifier definition {symbol.name!r}"
                ) from error
        raise TypeError(type(symbol))

    def _production_name(self, production: str) -> str:
        try:
            return self.production_names[production]
        except KeyError as error:
            raise ValueError(f"unknown production {production!r}") from error

    @staticmethod
    def _value_name(trail: tuple[int, ...]) -> str:
        return "value_" + "_".join(str(item) for item in trail)

    @staticmethod
    def _constant(value: str) -> object:
        normalized = value.casefold()
        if normalized == "истина":
            return True
        if normalized == "ложь":
            return False
        if normalized == "неопределено":
            return None
        return value


def render_direct_python_module(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
    schema: tuple[AstNodeSchema, ...],
    analysis: DirectRenderAnalysis,
) -> str:
    return _DirectPythonRenderer(
        source,
        parser_ir,
        entrypoints,
        schema,
        analysis,
    ).render()
