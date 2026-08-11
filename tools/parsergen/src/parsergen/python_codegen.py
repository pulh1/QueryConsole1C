from __future__ import annotations

from dataclasses import dataclass
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
    CanonicalDecision,
    ConsumeKnownSymbol,
    DiscardSymbol,
    Dispatch,
    Operation,
    OptionalBranch,
    ParseSymbol,
    ParserIr,
    RepeatLoop,
    ResolvedRegion,
)
from .source_model import SourceGrammar


@dataclass(frozen=True, slots=True)
class GeneratedPythonParser:
    module_text: str


def generate_python_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> GeneratedPythonParser:
    """Generate a standalone syntax recognizer from canonical Parser IR.

    The current milestone deliberately emits no semantic values. A complete
    Python target must additionally generate AST classes from grammar semantic
    declarations and execute the corresponding semantic Parser IR operations.
    """
    return GeneratedPythonParser(
        _PythonGenerator(source, parser_ir, entrypoints).generate()
    )


class _PythonGenerator:
    def __init__(
        self,
        source: SourceGrammar,
        parser_ir: ParserIr,
        entrypoints: Mapping[str, str],
    ) -> None:
        self.source = source
        self.parser_ir = parser_ir
        self.entrypoints = dict(entrypoints)
        self.identifier_types = {
            item.name: item.token_types for item in source.identifier_definitions
        }
        self.decisions: list[tuple[object, ...]] = []
        self.decision_ids: dict[int, int] = {}

    def generate(self) -> str:
        self._validate()
        productions = {
            production.name: (
                None
                if production.decision is None
                else self._decision_id(production.decision),
                tuple(
                    (
                        alternative.index + 1,
                        self._operations(alternative.operations),
                    )
                    for alternative in production.alternatives
                ),
            )
            for production in self.parser_ir.productions
        }
        decisions = tuple(self.decisions)
        return _MODULE_TEMPLATE.format(
            entrypoints=pformat(self.entrypoints, width=100, sort_dicts=True),
            productions=pformat(productions, width=100, sort_dicts=True),
            decisions=pformat(decisions, width=100, sort_dicts=True),
        )

    def _validate(self) -> None:
        if self.source != self.parser_ir.source_grammar:
            raise ValueError("source grammar does not match Parser IR")
        if not self.entrypoints:
            raise ValueError("entrypoint mapping must not be empty")
        productions = {item.name for item in self.parser_ir.productions}
        for name, production in self.entrypoints.items():
            if not name:
                raise ValueError("entrypoint name must not be empty")
            if production not in productions:
                raise ValueError(
                    f"entrypoint {name!r} references unknown production {production!r}"
                )

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
                    (
                        "commit",
                        node.outcome.production,
                        node.outcome.alternative,
                    )
                )
            elif isinstance(node, ExitDecision):
                nodes.append(
                    (
                        "exit",
                        node.outcome.production,
                        node.outcome.alternative,
                    )
                )
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
        rendered: list[tuple[object, ...]] = []
        for operation in operations:
            if isinstance(operation, ResolvedRegion):
                rendered.extend(self._operations(operation.operations))
            elif isinstance(operation, (DiscardSymbol, ParseSymbol)):
                rendered.append(self._symbol(operation.symbol))
            elif isinstance(operation, ConsumeKnownSymbol):
                rendered.append(self._symbol(operation.symbol))
            elif isinstance(operation, Dispatch):
                rendered.append(
                    (
                        "dispatch",
                        self._decision_id(operation.decision),
                        self._branches(operation.branches),
                    )
                )
            elif isinstance(operation, OptionalBranch):
                if operation.exit_operations:
                    raise ValueError(
                        "syntax-only optional must not contain semantic exit operations"
                    )
                rendered.append(
                    (
                        "optional",
                        self._decision_id(operation.decision),
                        self._branches(operation.branches),
                    )
                )
            elif isinstance(operation, RepeatLoop):
                rendered.append(
                    (
                        "repeat",
                        self._decision_id(operation.decision),
                        self._branches(operation.branches),
                    )
                )
            else:
                raise ValueError(
                    "Python syntax target does not support semantic operation "
                    f"{type(operation).__name__}"
                )
        return tuple(rendered)

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
            )
            for branch in branches
        )

    def _symbol(self, symbol: SyntaxSymbol) -> tuple[object, ...]:
        if isinstance(symbol, NonterminalCall):
            return ("call", symbol.name)
        if isinstance(symbol, Terminal):
            expected = (symbol.token_type,)
        elif isinstance(symbol, Lexeme):
            expected = (symbol.text,)
        elif isinstance(symbol, Constant):
            expected = (symbol.token_type,)
        elif isinstance(symbol, IdentifierRef):
            try:
                expected = self.identifier_types[symbol.name]
            except KeyError as error:
                raise ValueError(
                    f"unknown identifier definition {symbol.name!r}"
                ) from error
        else:
            raise TypeError(type(symbol))
        return ("consume", tuple(expected))


_MODULE_TEMPLATE = '''from __future__ import annotations


ENTRYPOINTS = {entrypoints}
PRODUCTIONS = {productions}
DECISIONS = {decisions}


class GeneratedParseError(ValueError):
    def __init__(self, position, actual, expected):
        self.position = position
        self.actual = actual
        self.expected = tuple(expected)
        super().__init__(
            f"unexpected {{actual!r}} at token {{position}}; expected {{self.expected!r}}"
        )


class GeneratedParser:
    def parse(self, tokens, entrypoint):
        try:
            production = ENTRYPOINTS[entrypoint]
        except KeyError as error:
            raise ValueError(f"unknown entrypoint {{entrypoint!r}}") from error
        self.tokens = tokens if hasattr(tokens, "__getitem__") else tuple(tokens)
        self.position = 0
        tasks = [("call", production)]
        while tasks:
            task = tasks.pop()
            kind = task[0]
            if kind == "call":
                decision, alternatives = PRODUCTIONS[task[1]]
                if decision is None:
                    operations = alternatives[0][1]
                else:
                    leaf = self._decide(decision)
                    if leaf[0] != "commit":
                        self._raise(())
                    operations = next(
                        body for number, body in alternatives if number == leaf[2]
                    )
                tasks.extend(reversed(operations))
            elif kind == "consume":
                actual = self._lookahead(0)
                if actual not in task[1]:
                    self._raise(task[1])
                self.position += 1
            elif kind in ("dispatch", "optional", "repeat"):
                leaf = self._decide(task[1])
                if leaf[0] == "exit":
                    if kind == "dispatch":
                        self._raise(())
                    continue
                if leaf[0] != "commit":
                    self._raise(())
                operations = self._branch(task[2], leaf)
                if kind == "repeat":
                    tasks.append(task)
                tasks.extend(reversed(operations))
            else:
                raise RuntimeError(f"unknown generated parser operation {{kind!r}}")
        if self.position != len(self.tokens):
            self._raise(("$",))

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

    def _branch(self, branches, leaf):
        outcome = (leaf[1], leaf[2])
        for branch_outcome, facts, operations in branches:
            if branch_outcome != outcome:
                continue
            if facts is None or all(
                self._lookahead(offset) in token_types
                for offset, token_types in facts
            ):
                return operations
        raise RuntimeError(f"decision outcome has no generated branch: {{outcome!r}}")

    def _lookahead(self, offset):
        index = self.position + offset
        if index >= len(self.tokens):
            return "$"
        token = self.tokens[index]
        return token if isinstance(token, str) else token.type

    def _raise(self, expected):
        raise GeneratedParseError(
            self.position,
            self._lookahead(0),
            expected,
        )
'''
