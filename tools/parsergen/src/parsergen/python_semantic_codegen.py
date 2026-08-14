from __future__ import annotations

from dataclasses import dataclass
import keyword
from typing import Mapping

from .parser_ir import (
    AppendCollection,
    AssignConstant,
    BindScalar,
    ConcatScalar,
    ConstructNode,
    Dispatch,
    ExtendCollection,
    IncrementScalar,
    LeftFold,
    Operation,
    OptionalBranch,
    ParserIr,
    RepeatLoop,
    ResolvedRegion,
    WrapOptional,
)
from .source_model import SourceGrammar


@dataclass(frozen=True, slots=True)
class AstFieldSchema:
    name: str
    category: str


@dataclass(frozen=True, slots=True)
class AstNodeSchema:
    name: str
    fields: tuple[AstFieldSchema, ...]


@dataclass(frozen=True, slots=True)
class GeneratedPythonSemanticParser:
    module_text: str
    ast_schema: tuple[AstNodeSchema, ...]


_RESERVED_CLASSES = frozenset(
    {
        "AST_CLASSES",
        "GeneratedParseError",
        "GeneratedParser",
        "SourceSpan",
    }
)
_RESERVED_FIELDS = frozenset({"span"})


def generate_python_semantic_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> GeneratedPythonSemanticParser:
    """Generate Python AST classes from canonical semantic Parser IR."""
    if source != parser_ir.source_grammar:
        raise ValueError("source grammar does not match Parser IR")
    _validate_entrypoints(parser_ir, entrypoints)
    schema = _SchemaBuilder(parser_ir).build()
    return GeneratedPythonSemanticParser(
        _render_module(schema),
        schema,
    )


def _validate_entrypoints(
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> None:
    if not entrypoints:
        raise ValueError("entrypoint mapping must not be empty")
    productions = {item.name for item in parser_ir.productions}
    for name, production in entrypoints.items():
        if not name:
            raise ValueError("entrypoint name must not be empty")
        if production not in productions:
            raise ValueError(
                f"entrypoint {name!r} references unknown production {production!r}"
            )


class _SchemaBuilder:
    def __init__(self, parser_ir: ParserIr) -> None:
        self.parser_ir = parser_ir
        self.order: list[str] = []
        self.fields: dict[str, list[AstFieldSchema]] = {}

    def build(self) -> tuple[AstNodeSchema, ...]:
        for production in self.parser_ir.productions:
            for alternative in production.alternatives:
                self._operations(alternative.operations, None)
        return tuple(
            AstNodeSchema(name, tuple(self.fields[name])) for name in self.order
        )

    def _operations(
        self,
        operations: tuple[Operation, ...],
        active: str | None,
    ) -> str | None:
        current = active
        for operation in operations:
            if isinstance(operation, ConstructNode):
                self._constructor(operation.constructor)
                current = operation.constructor
            elif isinstance(operation, (BindScalar, AssignConstant)):
                self._field(current, operation.property, "scalar")
            elif isinstance(operation, (AppendCollection, ExtendCollection)):
                self._field(
                    current,
                    "items" if operation.property is None else operation.property,
                    "collection",
                )
            elif isinstance(operation, ConcatScalar):
                self._field(current, operation.property, "concat")
            elif isinstance(operation, IncrementScalar):
                self._field(current, operation.property, "increment")
            elif isinstance(operation, ResolvedRegion):
                current = self._operations(operation.operations, current)
            elif isinstance(operation, Dispatch):
                for branch in operation.branches:
                    self._operations(branch.operations, current)
            elif isinstance(operation, OptionalBranch):
                for branch in operation.branches:
                    self._operations(branch.operations, current)
                self._operations(operation.exit_operations, current)
            elif isinstance(operation, RepeatLoop):
                for branch in operation.branches:
                    self._operations(branch.operations, current)
            elif isinstance(operation, WrapOptional):
                for branch in operation.branches:
                    self._operations(branch.operations, None)
            elif isinstance(operation, LeftFold):
                for branch in (*operation.base_branches, *operation.recursive_branches):
                    self._operations(branch.operations, None)
        return current

    def _constructor(self, name: str) -> None:
        _validate_identifier(name, "constructor")
        if name in _RESERVED_CLASSES:
            raise ValueError(f"constructor name is reserved: {name}")
        if name not in self.fields:
            self.order.append(name)
            self.fields[name] = []

    def _field(self, constructor: str | None, name: str, category: str) -> None:
        if constructor is None:
            raise ValueError("semantic binding has no active constructor")
        _validate_identifier(name, "field")
        if name in _RESERVED_FIELDS:
            raise ValueError(f"field name is reserved: {name}")
        fields = self.fields[constructor]
        existing = next((item for item in fields if item.name == name), None)
        if existing is not None:
            if existing.category != category:
                raise ValueError(
                    f"field {constructor}.{name} has incompatible binding categories"
                )
            return
        fields.append(AstFieldSchema(name, category))


def _validate_identifier(value: str, label: str) -> None:
    if not value.isidentifier() or keyword.iskeyword(value):
        raise ValueError(f"{label} is not a valid Python identifier: {value!r}")


def _render_module(schema: tuple[AstNodeSchema, ...]) -> str:
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
    for node in schema:
        lines.extend(("", "", "@dataclass(frozen=True, slots=True)", f"class {node.name}:"))
        for field in node.fields:
            lines.append(f"    {field.name}: object")
        lines.append("    span: SourceSpan")
    lines.extend(("", "", "AST_CLASSES = {"))
    lines.extend(f'    "{node.name}": {node.name},' for node in schema)
    lines.extend(
        (
            "}",
            "",
            "",
            "class GeneratedParseError(ValueError):",
            "    pass",
            "",
            "",
            "class GeneratedParser:",
            "    def parse(self, tokens, entrypoint):",
            '        raise NotImplementedError("semantic runtime is not generated yet")',
            "",
        )
    )
    return "\n".join(lines)
