from __future__ import annotations

from dataclasses import dataclass
import keyword
from pprint import pformat
from typing import Mapping

from .decision_dag import (
    CommitAlternative,
    ExitDecision,
    ImmediateError,
    LookaheadDecision,
)
from .model import Constant, IdentifierRef, Lexeme, NonterminalCall, SyntaxSymbol, Terminal
from .parser_ir import (
    AppendCollection,
    AssignConstant,
    BindScalar,
    CanonicalDecision,
    ConcatScalar,
    ConsumeKnownSymbol,
    ConstructNode,
    DiscardSymbol,
    Dispatch,
    DispatchValue,
    ExtendCollection,
    FoldLeftValue,
    IncrementScalar,
    LeftFold,
    Operation,
    OptionalBranch,
    ParseBranchValue,
    ParseSymbol,
    ParserIr,
    RepeatLoop,
    ResolvedRegion,
    ReturnConstant,
    UndefinedValue,
    WrapValue,
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
    module_text = _SemanticGenerator(
        source,
        parser_ir,
        entrypoints,
        schema,
    ).generate()
    return GeneratedPythonSemanticParser(
        module_text,
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
                for target in targets:
                    self._field(
                        target,
                        operation.property,
                        "collection" if operation.prepend else "scalar",
                    )
            elif isinstance(operation, WrapValue):
                for target in self._value_constructors(operation.value):
                    self._field(
                        target,
                        operation.property,
                        "collection" if operation.prepend else "scalar",
                    )
            elif isinstance(operation, LeftFold):
                for branch in (*operation.base_branches, *operation.recursive_branches):
                    self._operations(branch.operations, None)
        return current

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
                production = next(
                    item for item in self.parser_ir.productions if item.name == symbol.name
                )
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
    if (
        not value.isidentifier()
        or keyword.iskeyword(value)
        or (value.startswith("__") and value.endswith("__"))
    ):
        raise ValueError(f"{label} is not a valid Python identifier: {value!r}")


class _SemanticGenerator:
    def __init__(
        self,
        source: SourceGrammar,
        parser_ir: ParserIr,
        entrypoints: Mapping[str, str],
        schema: tuple[AstNodeSchema, ...],
    ) -> None:
        self.source = source
        self.parser_ir = parser_ir
        self.entrypoints = dict(entrypoints)
        self.schema = schema
        self.identifier_types = {
            item.name: item.token_types for item in source.identifier_definitions
        }
        self.decisions: list[tuple[object, ...]] = []
        self.decision_ids: dict[int, int] = {}

    def generate(self) -> str:
        productions = {
            production.name: (
                None
                if production.decision is None
                else self._decision_id(production.decision),
                tuple(
                    (
                        alternative.index + 1,
                        self._operations(alternative.operations),
                        alternative.result_index,
                    )
                    for alternative in production.alternatives
                ),
            )
            for production in self.parser_ir.productions
        }
        defaults = {
            node.name: tuple((field.name, field.category) for field in node.fields)
            for node in self.schema
        }
        header = "\n".join(
            (
                f"ENTRYPOINTS = {pformat(self.entrypoints, width=100, sort_dicts=True)}",
                f"PRODUCTIONS = {pformat(productions, width=100, sort_dicts=True)}",
                f"DECISIONS = {pformat(tuple(self.decisions), width=100, sort_dicts=True)}",
                f"NODE_DEFAULTS = {pformat(defaults, width=100, sort_dicts=True)}",
            )
        )
        return _render_ast_classes(self.schema) + "\n\n" + header + _RUNTIME_TEMPLATE

    def _decision_id(self, decision: CanonicalDecision) -> int:
        key = id(decision)
        existing = self.decision_ids.get(key)
        if existing is not None:
            return existing
        identifier = len(self.decisions)
        self.decision_ids[key] = identifier
        self.decisions.append(())
        nodes: list[tuple[object, ...]] = []
        for node in decision.dag.nodes:
            if isinstance(node, LookaheadDecision):
                nodes.append(
                    (
                        "look",
                        node.offset,
                        node.expected,
                        tuple(
                            (edge.predicate.token_types, edge.target)
                            for edge in node.edges
                        ),
                    )
                )
            elif isinstance(node, CommitAlternative):
                nodes.append(
                    ("commit", node.outcome.production, node.outcome.alternative)
                )
            elif isinstance(node, ExitDecision):
                nodes.append(("exit", node.outcome.production, node.outcome.alternative))
            elif isinstance(node, ImmediateError):
                nodes.append(("error", node.expected))
            else:
                raise TypeError(type(node))
        self.decisions[identifier] = (decision.dag.root, tuple(nodes))
        return identifier

    def _operations(
        self,
        operations: tuple[Operation, ...],
    ) -> tuple[tuple[object, ...], ...]:
        return tuple(self._operation(operation) for operation in operations)

    def _operation(self, operation: Operation) -> tuple[object, ...]:
        if isinstance(operation, ParseSymbol):
            return ("symbol", self._symbol(operation.symbol))
        if isinstance(operation, DiscardSymbol):
            return ("discard", self._symbol(operation.symbol))
        if isinstance(operation, ConsumeKnownSymbol):
            return (
                "known",
                self._symbol(operation.symbol),
                operation.capture_value,
            )
        if isinstance(operation, ResolvedRegion):
            return (
                "region",
                self._operations(operation.operations),
                operation.result_index,
            )
        if isinstance(operation, UndefinedValue):
            return ("constant", operation.value)
        if isinstance(operation, ConstructNode):
            return ("construct", operation.constructor)
        if isinstance(operation, BindScalar):
            return ("bind", operation.property, self._value(operation.value))
        if isinstance(operation, AppendCollection):
            return (
                "append",
                "items" if operation.property is None else operation.property,
                self._value(operation.value),
            )
        if isinstance(operation, ExtendCollection):
            return ("extend", operation.property, self._value(operation.value))
        if isinstance(operation, ConcatScalar):
            return ("concat", operation.property, self._value(operation.value))
        if isinstance(operation, IncrementScalar):
            return ("increment", operation.property, self._value(operation.value))
        if isinstance(operation, AssignConstant):
            return ("assign", operation.property, operation.value)
        if isinstance(operation, ReturnConstant):
            return ("constant", operation.value)
        if isinstance(operation, Dispatch):
            return (
                "dispatch",
                self._decision_id(operation.decision),
                self._branches(operation.branches),
            )
        if isinstance(operation, OptionalBranch):
            return (
                "optional",
                self._decision_id(operation.decision),
                self._branches(operation.branches),
                self._operations(operation.exit_operations),
            )
        if isinstance(operation, RepeatLoop):
            return (
                "repeat",
                self._decision_id(operation.decision),
                self._branches(operation.branches),
            )
        if isinstance(operation, WrapValue):
            return (
                "wrap_value",
                operation.property,
                operation.prepend,
                self._operation(operation.seed),
                self._value(operation.value),
            )
        if isinstance(operation, WrapOptional):
            return (
                "wrap_optional",
                operation.property,
                operation.prepend,
                self._operation(operation.seed),
                self._decision_id(operation.decision),
                self._branches(operation.branches),
            )
        if isinstance(operation, LeftFold):
            return (
                "left_fold",
                None
                if operation.base_decision is None
                else self._decision_id(operation.base_decision),
                self._branches(operation.base_branches),
                self._decision_id(operation.recursive_decision),
                self._branches(operation.recursive_branches),
            )
        raise TypeError(type(operation))

    def _value(self, value: object) -> tuple[object, ...]:
        if isinstance(value, (ParseSymbol, ConsumeKnownSymbol)):
            return self._operation(value)
        if isinstance(value, UndefinedValue):
            return ("constant", value.value)
        if isinstance(value, ParseBranchValue):
            return (
                "region",
                self._operations(value.operations),
                value.result_index,
            )
        if isinstance(value, DispatchValue):
            return (
                "dispatch_value",
                self._decision_id(value.decision),
                tuple(
                    (
                        (branch.outcome.production, branch.outcome.alternative),
                        self._value(branch.value),
                    )
                    for branch in value.branches
                ),
            )
        if isinstance(value, FoldLeftValue):
            return ("fold_value",)
        raise TypeError(type(value))

    def _branches(self, branches) -> tuple[tuple[object, ...], ...]:
        return tuple(
            (
                (branch.outcome.production, branch.outcome.alternative),
                None
                if branch.path_facts is None
                else tuple(
                    (fact.offset, fact.predicate.token_types)
                    for fact in branch.path_facts
                ),
                self._operations(branch.operations),
                branch.result_index,
            )
            for branch in branches
        )

    def _symbol(self, symbol: SyntaxSymbol) -> tuple[object, ...]:
        if isinstance(symbol, NonterminalCall):
            return ("call", symbol.name)
        if isinstance(symbol, Terminal):
            return ("consume", (symbol.token_type,), "type")
        if isinstance(symbol, Lexeme):
            return ("consume", (symbol.text,), "type")
        if isinstance(symbol, Constant):
            return ("consume", (symbol.token_type,), "value")
        if isinstance(symbol, IdentifierRef):
            try:
                expected = self.identifier_types[symbol.name]
            except KeyError as error:
                raise ValueError(
                    f"unknown identifier definition {symbol.name!r}"
                ) from error
            return ("consume", expected, "text")
        raise TypeError(type(symbol))


def _render_ast_classes(schema: tuple[AstNodeSchema, ...]) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass, replace",
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
    lines.append("}")
    return "\n".join(lines)


_RUNTIME_TEMPLATE = r'''


class GeneratedParseError(ValueError):
    def __init__(self, position, actual, expected):
        self.position = position
        self.actual = actual
        self.expected = tuple(expected)
        super().__init__(
            f"unexpected {actual!r} at token {position}; expected {self.expected!r}"
        )


class _Builder:
    __slots__ = ("name", "start", "values")

    def __init__(self, name, start):
        self.name = name
        self.start = start
        self.values = {}
        for field, category in NODE_DEFAULTS[name]:
            if category == "collection":
                self.values[field] = []
            elif category == "concat":
                self.values[field] = ""
            elif category == "increment":
                self.values[field] = 0
            else:
                self.values[field] = None


class _Frame:
    __slots__ = (
        "operations", "result_index", "receiver", "start", "index",
        "values", "builder", "prefer_builder", "fold_value",
    )

    def __init__(
        self,
        operations,
        result_index,
        receiver,
        start,
        *,
        builder=None,
        prefer_builder=True,
        fold_value=None,
    ):
        self.operations = operations
        self.result_index = result_index
        self.receiver = receiver
        self.start = start
        self.index = 0
        self.values = []
        self.builder = builder
        self.prefer_builder = prefer_builder
        self.fold_value = fold_value


class GeneratedParser:
    def parse(self, tokens, entrypoint):
        try:
            production = ENTRYPOINTS[entrypoint]
        except KeyError as error:
            raise ValueError(f"unknown entrypoint {entrypoint!r}") from error
        self.tokens = tokens if hasattr(tokens, "__getitem__") else tuple(tokens)
        self.position = 0
        self.result = None
        tasks = [("call", production, ("root",))]
        while tasks:
            task = tasks.pop()
            kind = task[0]
            if kind == "call":
                self._start_call(tasks, task[1], task[2])
            elif kind == "sequence":
                self._run_sequence(tasks, task[1])
            elif kind == "operation":
                self._run_operation(tasks, task[1], task[2], task[3])
            elif kind == "repeat":
                self._run_repeat(tasks, task[1], task[2], task[3])
            elif kind == "wrap_value":
                self._run_wrap_value(tasks, *task[1:])
            elif kind == "wrap_optional":
                self._run_wrap_optional(tasks, *task[1:])
            elif kind == "left_fold_loop":
                self._run_left_fold_loop(tasks, *task[1:])
            else:
                raise RuntimeError(f"unknown semantic parser task {kind!r}")
        if self.position != len(self.tokens):
            self._raise(("$",))
        return self.result

    def _start_call(self, tasks, production, receiver):
        decision, alternatives = PRODUCTIONS[production]
        if decision is None:
            _, operations, result_index = alternatives[0]
        else:
            leaf = self._decide(decision)
            if leaf[0] != "commit":
                self._raise(())
            _, operations, result_index = next(
                item for item in alternatives if item[0] == leaf[2]
            )
        frame = _Frame(
            operations,
            result_index,
            receiver,
            self._offset(),
        )
        tasks.append(("sequence", frame))

    def _run_sequence(self, tasks, frame):
        if frame.index == len(frame.operations):
            if frame.prefer_builder and frame.builder is not None:
                value = self._freeze(frame.builder)
            elif frame.result_index is None:
                value = None
            else:
                value = frame.values[frame.result_index]
            self._deliver(frame.receiver, value)
            return
        operation = frame.operations[frame.index]
        frame.index += 1
        tasks.append(("sequence", frame))
        tasks.append(("operation", operation, frame, ("frame", frame)))

    def _run_operation(self, tasks, operation, frame, receiver):
        kind = operation[0]
        if kind == "symbol":
            self._start_symbol(tasks, operation[1], receiver)
        elif kind == "discard":
            self._start_symbol(tasks, operation[1], ("discard", receiver))
        elif kind == "known":
            target = receiver if operation[2] else ("discard", receiver)
            self._start_symbol(tasks, operation[1], target)
        elif kind == "region":
            tasks.append(
                (
                    "sequence",
                    _Frame(
                        operation[1],
                        operation[2],
                        receiver,
                        frame.start,
                        builder=frame.builder,
                        prefer_builder=False,
                    ),
                )
            )
        elif kind == "constant":
            self._deliver(receiver, self._constant(operation[1]))
        elif kind == "construct":
            frame.builder = _Builder(operation[1], frame.start)
            self._deliver(receiver, None)
        elif kind in {"bind", "append", "extend", "concat", "increment"}:
            if frame.builder is None:
                raise RuntimeError(f"{kind} has no active constructor")
            self._run_bound_value(
                tasks,
                operation[2],
                frame,
                (kind, frame.builder, operation[1], receiver),
            )
        elif kind == "assign":
            if frame.builder is None:
                raise RuntimeError("assign has no active constructor")
            frame.builder.values[operation[1]] = self._constant(operation[2])
            self._deliver(receiver, None)
        elif kind == "dispatch":
            leaf = self._decide(operation[1])
            if leaf[0] != "commit":
                self._raise(())
            branch = self._select_branch(operation[2], leaf)
            has_construct = self._has_construct(branch[2])
            tasks.append(
                (
                    "sequence",
                    _Frame(
                        branch[2],
                        branch[3],
                        receiver,
                        self._offset() if has_construct else frame.start,
                        builder=frame.builder,
                        prefer_builder=has_construct,
                    ),
                )
            )
        elif kind == "optional":
            leaf = self._decide(operation[1])
            if leaf[0] == "exit":
                operations, result_index = operation[3], None
            elif leaf[0] == "commit":
                branch = self._select_branch(operation[2], leaf)
                operations, result_index = branch[2], branch[3]
            else:
                self._raise(())
            has_construct = self._has_construct(operations)
            tasks.append(
                (
                    "sequence",
                    _Frame(
                        operations,
                        result_index,
                        receiver,
                        self._offset() if has_construct else frame.start,
                        builder=frame.builder,
                        prefer_builder=has_construct,
                    ),
                )
            )
        elif kind == "repeat":
            tasks.append(("repeat", operation, frame, receiver))
        elif kind == "wrap_value":
            seed = []
            tasks.append(("wrap_value", operation, frame, receiver, seed))
            tasks.append(("operation", operation[3], frame, ("box", seed)))
        elif kind == "wrap_optional":
            seed = []
            tasks.append(("wrap_optional", operation, frame, receiver, seed))
            tasks.append(("operation", operation[3], frame, ("box", seed)))
        elif kind == "left_fold":
            accumulator = []
            base = self._left_fold_base(operation)
            tasks.append(
                ("left_fold_loop", operation, frame, receiver, accumulator)
            )
            tasks.append(
                (
                    "sequence",
                    _Frame(
                        base[2],
                        base[3],
                        ("box", accumulator),
                        frame.start,
                        prefer_builder=self._has_construct(base[2]),
                    ),
                )
            )
        else:
            raise RuntimeError(f"unsupported semantic operation {kind!r}")

    def _run_repeat(self, tasks, operation, frame, receiver):
        leaf = self._decide(operation[1])
        if leaf[0] == "exit":
            self._deliver(receiver, None)
            return
        if leaf[0] != "commit":
            self._raise(())
        branch = self._select_branch(operation[2], leaf)
        tasks.append(("repeat", operation, frame, receiver))
        tasks.append(
            (
                "sequence",
                _Frame(
                    branch[2],
                    branch[3],
                    ("ignore",),
                    frame.start,
                    builder=frame.builder,
                    prefer_builder=False,
                ),
            )
        )

    def _run_wrap_value(self, tasks, operation, frame, receiver, seed):
        self._run_bound_value(
            tasks,
            operation[4],
            frame,
            ("wrap_apply", seed[0], operation[1], operation[2], receiver),
        )

    def _run_wrap_optional(self, tasks, operation, frame, receiver, seed):
        leaf = self._decide(operation[4])
        if leaf[0] == "exit":
            self._deliver(receiver, seed[0])
            return
        if leaf[0] != "commit":
            self._raise(())
        branch = self._select_branch(operation[5], leaf)
        has_construct = self._has_construct(branch[2])
        tasks.append(
            (
                "sequence",
                _Frame(
                    branch[2],
                    branch[3],
                    (
                        "wrap_apply",
                        seed[0],
                        operation[1],
                        operation[2],
                        receiver,
                    ),
                    self._offset() if has_construct else frame.start,
                    prefer_builder=has_construct,
                ),
            )
        )

    def _left_fold_base(self, operation):
        if operation[1] is None:
            return operation[2][0]
        leaf = self._decide(operation[1])
        if leaf[0] != "commit":
            self._raise(())
        return self._select_branch(operation[2], leaf)

    def _run_left_fold_loop(
        self,
        tasks,
        operation,
        frame,
        receiver,
        accumulator,
    ):
        current = accumulator[0]
        leaf = self._decide(operation[3])
        if leaf[0] == "exit":
            self._deliver(receiver, current)
            return
        if leaf[0] != "commit":
            self._raise(())
        branch = self._select_branch(operation[4], leaf)
        next_accumulator = []
        tasks.append(
            (
                "left_fold_loop",
                operation,
                frame,
                receiver,
                next_accumulator,
            )
        )
        tasks.append(
            (
                "sequence",
                _Frame(
                    branch[2],
                    branch[3],
                    ("fold_result", current, next_accumulator),
                    frame.start,
                    prefer_builder=self._has_construct(branch[2]),
                    fold_value=current,
                ),
            )
        )

    def _run_bound_value(self, tasks, value, frame, receiver):
        kind = value[0]
        if kind == "symbol":
            self._start_symbol(tasks, value[1], receiver)
        elif kind == "known":
            target = receiver if value[2] else ("discard", receiver)
            self._start_symbol(tasks, value[1], target)
        elif kind == "constant":
            self._deliver(receiver, self._constant(value[1]))
        elif kind == "region":
            tasks.append(
                (
                    "sequence",
                    _Frame(
                        value[1],
                        value[2],
                        receiver,
                        frame.start,
                        builder=frame.builder,
                        prefer_builder=False,
                    ),
                )
            )
        elif kind == "dispatch_value":
            leaf = self._decide(value[1])
            if leaf[0] != "commit":
                self._raise(())
            outcome = (leaf[1], leaf[2])
            selected = next(
                (branch_value for branch_outcome, branch_value in value[2]
                 if branch_outcome == outcome),
                None,
            )
            if selected is None:
                raise RuntimeError("value decision outcome has no branch")
            self._run_bound_value(tasks, selected, frame, receiver)
        elif kind == "fold_value":
            self._deliver(receiver, frame.fold_value)
        else:
            raise RuntimeError(f"unsupported bound value {kind!r}")

    def _start_symbol(self, tasks, symbol, receiver):
        if symbol[0] == "call":
            tasks.append(("call", symbol[1], receiver))
            return
        _, expected, value_kind = symbol
        actual = self._lookahead(0)
        if actual not in expected:
            self._raise(expected)
        token = self.tokens[self.position]
        self.position += 1
        if value_kind == "type":
            value = token.type
        elif value_kind == "text":
            value = token.text
        else:
            value = getattr(token, "value", None)
            if value is None:
                value = token.text
        self._deliver(receiver, value)

    def _deliver(self, receiver, value):
        while True:
            kind = receiver[0]
            if kind == "root":
                self.result = value
                return
            if kind == "ignore":
                return
            if kind == "box":
                receiver[1].append(value)
                return
            if kind == "fold_result":
                receiver[2].append(receiver[1] if value is None else value)
                return
            if kind == "frame":
                receiver[1].values.append(value)
                return
            if kind == "discard":
                receiver = receiver[1]
                value = None
                continue
            if kind == "wrap_apply":
                seed, field, prepend, receiver = (
                    receiver[1],
                    receiver[2],
                    receiver[3],
                    receiver[4],
                )
                if prepend:
                    current = getattr(value, field)
                    replacement = (seed, *(current or ()))
                else:
                    replacement = seed
                value = replace(value, **{field: replacement})
                continue
            builder, field, receiver = receiver[1], receiver[2], receiver[3]
            if kind == "bind":
                builder.values[field] = value
            elif kind == "append":
                builder.values[field].append(value)
            elif kind == "extend":
                if value is not None:
                    builder.values[field].extend(
                        value.items if hasattr(value, "items") else value
                    )
            elif kind == "concat":
                builder.values[field] += value
            elif kind == "increment":
                builder.values[field] += 1
            else:
                raise RuntimeError(f"unknown semantic receiver {kind!r}")
            value = None

    def _has_construct(self, operations):
        return any(operation[0] == "construct" for operation in operations)

    def _select_branch(self, branches, leaf):
        outcome = (leaf[1], leaf[2])
        for branch in branches:
            if branch[0] != outcome:
                continue
            facts = branch[1]
            if facts is None or all(
                self._lookahead(offset) in token_types
                for offset, token_types in facts
            ):
                return branch
        raise RuntimeError(f"decision outcome has no semantic branch: {outcome!r}")

    def _freeze(self, builder):
        values = []
        for field, category in NODE_DEFAULTS[builder.name]:
            value = builder.values[field]
            values.append(tuple(value) if category == "collection" else value)
        return AST_CLASSES[builder.name](
            *values,
            SourceSpan(builder.start, self._offset()),
        )

    def _decide(self, decision):
        root, nodes = DECISIONS[decision]
        node = nodes[root]
        while node[0] == "look":
            actual = self._lookahead(node[1])
            target = next(
                (target for token_types, target in node[3] if actual in token_types),
                None,
            )
            if target is None:
                self._raise(node[2])
            node = nodes[target]
        if node[0] == "error":
            self._raise(node[1])
        return node

    def _lookahead(self, offset):
        index = self.position + offset
        if index >= len(self.tokens):
            return "$"
        return self.tokens[index].type

    def _offset(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position].start
        if self.tokens:
            return self.tokens[-1].end
        return 0

    def _constant(self, value):
        normalized = value.casefold()
        if normalized == "истина":
            return True
        if normalized == "ложь":
            return False
        if normalized == "неопределено":
            return None
        return value

    def _raise(self, expected):
        raise GeneratedParseError(self.position, self._lookahead(0), expected)
'''
