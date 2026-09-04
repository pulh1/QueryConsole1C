from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .decision_dag import LookaheadDecision
from .parser_ir import (
    AppendCollection,
    AppendNearestOwner,
    BindScalar,
    BranchIr,
    CanonicalDecision,
    ConcatScalar,
    Dispatch,
    DispatchValue,
    ExtendCollection,
    IncrementScalar,
    LeftFold,
    Operation,
    OptionalBranch,
    ParseBranchValue,
    ParserIr,
    RepeatLoop,
    ResolvedRegion,
    WrapOptional,
    WrapValue,
)


TrailKind = Literal[
    "operation",
    "region",
    "branch",
    "exit",
    "value",
    "value_branch",
    "seed",
    "base_branch",
    "recursive_branch",
]
Trail = tuple[tuple[TrailKind, int], ...]


@dataclass(frozen=True, slots=True)
class IrSite:
    production: str
    alternative: int | None
    trail: Trail


@dataclass(frozen=True, slots=True)
class SequenceLiveness:
    site: IrSite
    live_after: tuple[frozenset[int], ...]


@dataclass(frozen=True, slots=True)
class DecisionRenderFacts:
    site: IrSite
    node_indegrees: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DirectRenderAnalysis:
    sequence_liveness: tuple[SequenceLiveness, ...]
    mutable_owner_types: frozenset[str]
    recursive_calls: tuple[RecursiveCallSite, ...]
    decisions: tuple[DecisionRenderFacts, ...]


class _Analyzer:
    def __init__(self) -> None:
        self.sequence_liveness: list[SequenceLiveness] = []
        self.mutable_owner_types: set[str] = set()
        self.decisions: list[DecisionRenderFacts] = []

    def analyze(self, parser_ir: ParserIr) -> DirectRenderAnalysis:
        for production in parser_ir.productions:
            production_site = IrSite(production.name, None, ())
            if production.decision is not None:
                self._decision(production_site, production.decision)
            for alternative in production.alternatives:
                self._sequence(
                    IrSite(production.name, alternative.index, ()),
                    alternative.operations,
                    alternative.result_index,
                )
        return DirectRenderAnalysis(
            tuple(self.sequence_liveness),
            frozenset(self.mutable_owner_types),
            (),
            tuple(self.decisions),
        )

    def _sequence(
        self,
        site: IrSite,
        operations: tuple[Operation, ...],
        result_index: int | None,
    ) -> None:
        self.sequence_liveness.append(
            SequenceLiveness(
                site,
                tuple(
                    frozenset({result_index})
                    if result_index is not None and index >= result_index
                    else frozenset()
                    for index in range(len(operations))
                ),
            )
        )
        for index, operation in enumerate(operations):
            self._operation(
                _child_site(site, "operation", index),
                operation,
            )

    def _operation(self, site: IrSite, operation: Operation) -> None:
        if isinstance(operation, ResolvedRegion):
            self._sequence(
                _child_site(site, "region", 0),
                operation.operations,
                operation.result_index,
            )
        elif isinstance(operation, (Dispatch, RepeatLoop)):
            self._decision(site, operation.decision)
            self._branches(site, "branch", operation.branches)
        elif isinstance(operation, OptionalBranch):
            self._decision(site, operation.decision)
            self._branches(site, "branch", operation.branches)
            self._sequence(
                _child_site(site, "exit", 0),
                operation.exit_operations,
                None,
            )
        elif isinstance(operation, WrapOptional):
            self._operation(_child_site(site, "seed", 0), operation.seed)
            self._decision(site, operation.decision)
            self._branches(site, "branch", operation.branches)
        elif isinstance(operation, WrapValue):
            self._operation(_child_site(site, "seed", 0), operation.seed)
            self._bound_value(_child_site(site, "value", 0), operation.value)
        elif isinstance(operation, LeftFold):
            if operation.base_decision is not None:
                self._decision(site, operation.base_decision)
            self._branches(site, "base_branch", operation.base_branches)
            self._decision(
                _child_site(site, "recursive_branch", 0),
                operation.recursive_decision,
            )
            self._branches(
                site,
                "recursive_branch",
                operation.recursive_branches,
            )
        elif isinstance(operation, AppendNearestOwner):
            self.mutable_owner_types.add(operation.owner)
            if operation.value is not None:
                self._bound_value(
                    _child_site(site, "value", 0),
                    operation.value,
                )
        elif isinstance(
            operation,
            (
                BindScalar,
                AppendCollection,
                ExtendCollection,
                ConcatScalar,
                IncrementScalar,
            ),
        ):
            self._bound_value(_child_site(site, "value", 0), operation.value)

    def _bound_value(self, site: IrSite, value: object) -> None:
        if isinstance(value, DispatchValue):
            self._decision(site, value.decision)
            for index, branch in enumerate(value.branches):
                self._sequence(
                    _child_site(site, "value_branch", index),
                    branch.value.operations,
                    branch.value.result_index,
                )
        elif isinstance(value, ParseBranchValue):
            self._sequence(site, value.operations, value.result_index)
        elif isinstance(value, Operation):
            self._operation(site, value)

    def _branches(
        self,
        site: IrSite,
        kind: Literal["branch", "base_branch", "recursive_branch"],
        branches: tuple[BranchIr, ...],
    ) -> None:
        for index, branch in enumerate(branches):
            self._sequence(
                _child_site(site, kind, index),
                branch.operations,
                branch.result_index,
            )

    def _decision(self, site: IrSite, decision: CanonicalDecision) -> None:
        indegrees = [0] * len(decision.dag.nodes)
        for node in decision.dag.nodes:
            if isinstance(node, LookaheadDecision):
                for edge in node.edges:
                    indegrees[edge.target] += 1
        self.decisions.append(DecisionRenderFacts(site, tuple(indegrees)))


def _child_site(site: IrSite, kind: TrailKind, index: int) -> IrSite:
    return IrSite(site.production, site.alternative, (*site.trail, (kind, index)))


def analyze_direct_render(parser_ir: ParserIr) -> DirectRenderAnalysis:
    """Compute immutable rendering facts without copying executable IR."""
    return _Analyzer().analyze(parser_ir)
