from __future__ import annotations

from dataclasses import dataclass
from pprint import pformat
from typing import TYPE_CHECKING, Mapping

from .model import Constant, IdentifierRef, Lexeme, NonterminalCall, SyntaxSymbol, Terminal
from .parser_ir import (
    AppendCollection,
    AssignConstant,
    BindScalar,
    ConcatScalar,
    ConsumeKnownSymbol,
    ConstructNode,
    DiscardSymbol,
    ExtendCollection,
    IncrementScalar,
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


@dataclass(frozen=True, slots=True)
class _ConstructorSite:
    name: str
    trail: tuple[int, ...]


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
        self.schema_by_name = {item.name: item for item in schema}
        self.local_names: dict[tuple[tuple[int, ...], str], str] = {}
        self.used_local_names: set[str] = set()

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
        self.local_names = {}
        self.used_local_names = {"start", *self._value_names(alternative.operations, ())}
        lines = [f"    def {self.production_names[production.name]}(self):", "        start = self._offset()"]
        body, constructor_site = self._render_sequence(
            alternative.operations,
            alternative.result_index,
            "        ",
            (),
            None,
        )
        lines.extend(body)
        if constructor_site is None:
            lines.append(
                "        return None"
                if alternative.result_index is None
                else f"        return {self._value_name((alternative.result_index,))}"
            )
        else:
            lines.append(f"        return {self._freeze_expression(constructor_site, 'start')}")
        return "\n".join(lines)

    def _render_sequence(
        self,
        operations: tuple[Operation, ...],
        result_index: int | None,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> tuple[list[str], _ConstructorSite | None]:
        lines: list[str] = []
        for index, operation in enumerate(operations):
            operation_lines, constructor_site = self._render_operation(
                operation,
                indent,
                (*trail, index),
                constructor_site,
            )
            lines.extend(operation_lines)
        return lines, constructor_site

    def _render_operation(
        self,
        operation: Operation,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> tuple[list[str], _ConstructorSite | None]:
        value = self._value_name(trail)
        if isinstance(operation, ParseSymbol):
            if isinstance(operation.symbol, NonterminalCall):
                return [f"{indent}{value} = self.{self._production_name(operation.symbol.name)}()"], constructor_site
            expected, capture = self._terminal_parts(operation.symbol)
            return [f"{indent}{value} = self._consume({expected!r}, {capture!r})"], constructor_site
        if isinstance(operation, DiscardSymbol):
            if isinstance(operation.symbol, NonterminalCall):
                return [f"{indent}self.{self._production_name(operation.symbol.name)}()"], constructor_site
            expected, _ = self._terminal_parts(operation.symbol)
            return [f"{indent}self._consume({expected!r}, False)"], constructor_site
        if isinstance(operation, ConsumeKnownSymbol):
            expected, capture = self._terminal_parts(operation.symbol)
            if operation.capture_value:
                return [f"{indent}{value} = self._consume({expected!r}, {capture!r})"], constructor_site
            return [f"{indent}self._consume({expected!r}, False)"], constructor_site
        if isinstance(operation, ResolvedRegion):
            lines, _ = self._render_sequence(
                operation.operations,
                operation.result_index,
                indent,
                (*trail, 0),
                constructor_site,
            )
            if operation.result_index is None:
                lines.append(f"{indent}{value} = None")
            else:
                lines.append(
                    f"{indent}{value} = {self._value_name((*trail, 0, operation.result_index))}"
                )
            return lines, constructor_site
        if isinstance(operation, (UndefinedValue, ReturnConstant)):
            return [f"{indent}{value} = {self._constant(operation.value)!r}"], constructor_site
        if isinstance(operation, ConstructNode):
            site = _ConstructorSite(operation.constructor, trail)
            return self._construct_locals(site, indent), site
        if isinstance(operation, BindScalar):
            return self._render_binding(
                operation.value,
                f"{self._field_local(constructor_site, operation.property)} = {value}",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, AppendCollection):
            property_name = "items" if operation.property is None else operation.property
            return self._render_binding(
                operation.value,
                f"{self._field_local(constructor_site, property_name)}.append({value})",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, ExtendCollection):
            target = self._field_local(constructor_site, operation.property)
            return self._render_binding(
                operation.value,
                f"{target}.extend({value}.items if hasattr({value}, 'items') else {value}) if {value} is not None else None",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, ConcatScalar):
            return self._render_binding(
                operation.value,
                f"{self._field_local(constructor_site, operation.property)} += {value}",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, IncrementScalar):
            return self._render_binding(
                operation.value,
                f"{self._field_local(constructor_site, operation.property)} += 1",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, AssignConstant):
            return [
                f"{indent}{self._field_local(constructor_site, operation.property)} = {self._constant(operation.value)!r}"
            ], constructor_site
        raise TypeError(
            f"direct renderer does not support {type(operation).__name__} before its task"
        )

    def _render_binding(
        self,
        bound_value: object,
        apply: str,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> tuple[list[str], _ConstructorSite | None]:
        if constructor_site is None:
            raise RuntimeError("semantic binding has no active constructor")
        if not isinstance(bound_value, (ParseSymbol, ConsumeKnownSymbol, UndefinedValue)):
            raise TypeError(
                f"direct renderer does not support {type(bound_value).__name__} bound values before its task"
            )
        lines, _ = self._render_operation(bound_value, indent, trail, constructor_site)
        lines.append(f"{indent}{apply}")
        return lines, constructor_site

    def _construct_locals(self, site: _ConstructorSite, indent: str) -> list[str]:
        try:
            fields = self.schema_by_name[site.name].fields
        except KeyError as error:
            raise ValueError(f"unknown constructor {site.name!r}") from error
        initial = {
            "scalar": "None",
            "collection": "[]",
            "concat": "\"\"",
            "increment": "0",
        }
        return [
            f"{indent}{self._field_local(site, field.name)} = {initial[field.category]}"
            for field in fields
        ]

    def _freeze_expression(self, site: _ConstructorSite, start: str) -> str:
        fields = self.schema_by_name[site.name].fields
        values = [
            (
                f"tuple({self._field_local(site, field.name)})"
                if field.category == "collection"
                else self._field_local(site, field.name)
            )
            for field in fields
        ]
        values.append(f"SourceSpan({start}, self._end_offset({start}))")
        return f"{site.name}({', '.join(values)})"

    def _field_local(self, site: _ConstructorSite | None, property_name: str) -> str:
        if site is None:
            raise RuntimeError("semantic binding has no active constructor")
        fields = self.schema_by_name[site.name].fields
        for field in fields:
            if field.name == property_name:
                return self._allocate_local(site, field.name)
        raise ValueError(f"unknown field {site.name}.{property_name}")

    def _allocate_local(self, site: _ConstructorSite, field_name: str) -> str:
        key = (site.trail, field_name)
        existing = self.local_names.get(key)
        if existing is not None:
            return existing
        base = "node_" + "_".join(str(item) for item in site.trail)
        base = f"{base}_{field_name.casefold()}"
        local = base
        suffix = 2
        while local in self.used_local_names:
            local = f"{base}_{suffix}"
            suffix += 1
        self.used_local_names.add(local)
        self.local_names[key] = local
        return local

    def _value_names(
        self,
        operations: tuple[Operation, ...],
        trail: tuple[int, ...],
    ) -> set[str]:
        names: set[str] = set()
        for index, operation in enumerate(operations):
            operation_trail = (*trail, index)
            names.add(self._value_name(operation_trail))
            if isinstance(operation, ResolvedRegion):
                names.update(self._value_names(operation.operations, (*operation_trail, 0)))
        return names

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
                "    def _end_offset(self, start):",
                "        if self._position:",
                "            end = self._tokens[self._position - 1].end",
                "            if end >= start:",
                "                return end",
                "        return start",
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
