from __future__ import annotations

from dataclasses import dataclass
import keyword
from typing import Mapping

from .direct_render_analysis import analyze_direct_render
from .model import NonterminalCall
from .parser_ir import (
    AppendCollection,
    AssignConstant,
    BindScalar,
    ConcatScalar,
    ConstructNode,
    Dispatch,
    DispatchValue,
    ExtendCollection,
    IncrementScalar,
    LeftFold,
    Operation,
    OptionalBranch,
    ParseBranchValue,
    ParseSymbol,
    ParserIr,
    RepeatLoop,
    ResolvedRegion,
    WrapOptional,
    WrapValue,
)
from .source_model import (
    SourceBinding,
    SourceGrammar,
    SourceGroup,
    SourceOptional,
    SourceRepeat,
)


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
        "DECISIONS",
        "ENTRYPOINTS",
        "GeneratedParseError",
        "GeneratedParser",
        "NODE_DEFAULTS",
        "PARSERGEN_BACKEND_ID",
        "PRODUCTIONS",
        "SourceSpan",
        "_Builder",
        "_Frame",
    }
)
_RESERVED_FIELDS = frozenset({"items", "span"})


def generate_python_semantic_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> GeneratedPythonSemanticParser:
    """Generate Python AST classes from canonical semantic Parser IR."""
    if source != parser_ir.source_grammar:
        raise ValueError("source grammar does not match Parser IR")
    _validate_python_call_contract(source)
    _validate_entrypoints(parser_ir, entrypoints)
    schema = _SchemaBuilder(parser_ir).build()
    from .python_direct_codegen import render_direct_python_module

    return GeneratedPythonSemanticParser(
        render_direct_python_module(
            source,
            parser_ir,
            entrypoints,
            schema,
            analyze_direct_render(parser_ir),
        ),
        schema,
    )


def _generate_direct_python_semantic_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> GeneratedPythonSemanticParser:
    """Private compatibility seam for direct-renderer tests."""
    return generate_python_semantic_parser(source, parser_ir, entrypoints)


def _validate_python_call_contract(source: SourceGrammar) -> None:
    """Reject opaque call state before schema discovery or direct rendering."""
    def has_arguments(value: object) -> bool:
        if isinstance(value, NonterminalCall):
            return bool(value.arguments)
        if isinstance(value, SourceBinding):
            return has_arguments(value.value)
        if isinstance(value, (SourceOptional, SourceRepeat)):
            return has_arguments(value.body)
        if isinstance(value, SourceGroup):
            return any(
                has_arguments(item)
                for alternative in value.alternatives
                for item in alternative.body.items
            )
        return False

    if any(production.parameters for production in source.productions) or any(
        has_arguments(item)
        for production in source.productions
        for alternative in production.alternatives
        for item in alternative.body.items
    ):
        raise ValueError(
            "Python target does not support production parameters "
            "or nonterminal call arguments"
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
        self.productions_by_name = {
            item.name: item for item in parser_ir.productions
        }
        self.order: list[str] = []
        self.fields: dict[str, list[AstFieldSchema]] = {}

    def build(self) -> tuple[AstNodeSchema, ...]:
        for production in self.parser_ir.productions:
            for alternative in production.alternatives:
                self._discover_constructors(alternative.operations)
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
                    root_collection=operation.property is None,
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
                targets: set[str] = set()
                for branch in operation.branches:
                    targets.update(self._result_constructors(branch.operations))
                    self._operations(branch.operations, None)
                for target in sorted(targets):
                    self._field(
                        target,
                        operation.property,
                        "collection" if operation.prepend else "scalar",
                    )
            elif isinstance(operation, WrapValue):
                for target in sorted(self._value_constructors(operation.value)):
                    self._field(
                        target,
                        operation.property,
                        "collection" if operation.prepend else "scalar",
                    )
            elif isinstance(operation, LeftFold):
                for branch in (*operation.base_branches, *operation.recursive_branches):
                    self._operations(branch.operations, None)
        return current

    def _bound_value_operations(
        self,
        value: object,
        active: str | None,
    ) -> None:
        if isinstance(value, ParseBranchValue):
            self._operations(value.operations, active)
        elif isinstance(value, DispatchValue):
            for branch in value.branches:
                self._bound_value_operations(branch.value, active)

    def _discover_constructors(self, operations: tuple[Operation, ...]) -> None:
        for operation in operations:
            if isinstance(operation, ConstructNode):
                self._constructor(operation.constructor)
            elif isinstance(operation, ResolvedRegion):
                self._discover_constructors(operation.operations)
            elif isinstance(operation, (Dispatch, RepeatLoop)):
                for branch in operation.branches:
                    self._discover_constructors(branch.operations)
            elif isinstance(operation, OptionalBranch):
                for branch in operation.branches:
                    self._discover_constructors(branch.operations)
                self._discover_constructors(operation.exit_operations)
            elif isinstance(operation, WrapOptional):
                for branch in operation.branches:
                    self._discover_constructors(branch.operations)
            elif isinstance(operation, LeftFold):
                for branch in (*operation.base_branches, *operation.recursive_branches):
                    self._discover_constructors(branch.operations)

    def _value_constructors(
        self,
        value: object,
        seen: frozenset[str] = frozenset(),
    ) -> set[str]:
        if isinstance(value, ParseSymbol):
            symbol = value.symbol
            if isinstance(symbol, NonterminalCall):
                if symbol.name in seen:
                    return set()
                try:
                    production = self.productions_by_name[symbol.name]
                except KeyError as error:
                    raise ValueError(
                        f"unknown production {symbol.name!r}"
                    ) from error
                return {
                    name
                    for alternative in production.alternatives
                    for name in self._result_constructors(
                        alternative.operations,
                        seen | {symbol.name},
                    )
                }
            return set()
        if isinstance(value, ParseBranchValue):
            return self._result_constructors(value.operations, seen)
        if isinstance(value, DispatchValue):
            return {
                name
                for branch in value.branches
                for name in self._value_constructors(branch.value, seen)
            }
        return set()

    def _result_constructors(
        self,
        operations: tuple[Operation, ...],
        seen: frozenset[str] = frozenset(),
    ) -> set[str]:
        result: set[str] = set()
        for operation in operations:
            if isinstance(operation, ConstructNode):
                result.add(operation.constructor)
            elif isinstance(operation, ParseSymbol) and isinstance(
                operation.symbol, NonterminalCall
            ):
                result.update(self._value_constructors(operation, seen))
            elif isinstance(operation, ResolvedRegion):
                result.update(self._result_constructors(operation.operations, seen))
        return result

    def _constructor(self, name: str) -> None:
        _validate_identifier(name, "constructor")
        if name in _RESERVED_CLASSES:
            raise ValueError(f"constructor name is reserved: {name}")
        if name not in self.fields:
            self.order.append(name)
            self.fields[name] = []

    def _field(
        self,
        constructor: str | None,
        name: str,
        category: str,
        *,
        root_collection: bool = False,
    ) -> None:
        if constructor is None:
            raise ValueError("semantic binding has no active constructor")
        _validate_identifier(name, "field")
        fields = self.fields[constructor]
        existing = next((item for item in fields if item.name == name), None)
        if existing is not None:
            if existing.category != category:
                raise ValueError(
                    f"field {constructor}.{name} has incompatible binding categories"
                )
            return
        if name in _RESERVED_FIELDS and not (
            name == "items" and root_collection
        ):
            raise ValueError(f"field name is reserved: {name}")
        fields.append(AstFieldSchema(name, category))


def _validate_identifier(value: str, label: str) -> None:
    if (
        not value.isidentifier()
        or keyword.iskeyword(value)
        or (value.startswith("__") and value.endswith("__"))
    ):
        raise ValueError(f"{label} is not a valid Python identifier: {value!r}")
