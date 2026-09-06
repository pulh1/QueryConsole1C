from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .decision_dag import LookaheadDecision
from .parser_ir import (
    AppendCollection,
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
from .recursion_plan import (
    IrSite,
    RecursionPlan,
    analyze_recursion_plan,
    child_site,
)


@dataclass(frozen=True, slots=True)
class DecisionRenderFacts:
    site: IrSite
    node_indegrees: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DirectRenderAnalysis:
    """Python rendering facts, with recursion supplied by ``RecursionPlan``."""

    recursion_plan: RecursionPlan
    decisions: tuple[DecisionRenderFacts, ...]


class _DecisionFactsAnalyzer:
    def __init__(self) -> None:
        self.decisions: list[DecisionRenderFacts] = []

    def analyze(self, parser_ir: ParserIr) -> tuple[DecisionRenderFacts, ...]:
        for production in parser_ir.productions:
            production_site = IrSite(production.name, None, ())
            if production.decision is not None:
                self._decision(production_site, production.decision)
            for alternative in production.alternatives:
                self._sequence(
                    IrSite(production.name, alternative.index, ()),
                    alternative.operations,
                )
        return tuple(self.decisions)

    def _sequence(self, site: IrSite, operations: tuple[Operation, ...]) -> None:
        for index, operation in enumerate(operations):
            self._operation(child_site(site, "operation", index), operation)

    def _operation(self, site: IrSite, operation: Operation) -> None:
        if isinstance(operation, ResolvedRegion):
            self._sequence(child_site(site, "region", 0), operation.operations)
        elif isinstance(operation, (Dispatch, RepeatLoop)):
            self._decision(site, operation.decision)
            self._branches(site, "branch", operation.branches)
        elif isinstance(operation, OptionalBranch):
            self._decision(site, operation.decision)
            self._branches(site, "branch", operation.branches)
            self._sequence(child_site(site, "exit", 0), operation.exit_operations)
        elif isinstance(operation, WrapOptional):
            self._operation(child_site(site, "seed", 0), operation.seed)
            self._decision(site, operation.decision)
            self._branches(site, "branch", operation.branches)
        elif isinstance(operation, WrapValue):
            self._operation(child_site(site, "seed", 0), operation.seed)
            self._bound_value(child_site(site, "value", 0), operation.value)
        elif isinstance(operation, LeftFold):
            if operation.base_decision is not None:
                self._decision(site, operation.base_decision)
            self._branches(site, "base_branch", operation.base_branches)
            self._decision(
                child_site(site, "recursive_branch", 0),
                operation.recursive_decision,
            )
            self._branches(site, "recursive_branch", operation.recursive_branches)
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
            self._bound_value(child_site(site, "value", 0), operation.value)

    def _bound_value(self, site: IrSite, value: object) -> None:
        if isinstance(value, DispatchValue):
            self._decision(site, value.decision)
            for index, branch in enumerate(value.branches):
                self._sequence(
                    child_site(site, "value_branch", index),
                    branch.value.operations,
                )
        elif isinstance(value, ParseBranchValue):
            self._sequence(site, value.operations)
        elif isinstance(value, Operation):
            self._operation(site, value)

    def _branches(
        self,
        site: IrSite,
        kind: Literal["branch", "base_branch", "recursive_branch"],
        branches: tuple[BranchIr, ...],
    ) -> None:
        for index, branch in enumerate(branches):
            self._sequence(child_site(site, kind, index), branch.operations)

    def _decision(self, site: IrSite, decision: CanonicalDecision) -> None:
        indegrees = [0] * len(decision.dag.nodes)
        for node in decision.dag.nodes:
            if isinstance(node, LookaheadDecision):
                for edge in node.edges:
                    indegrees[edge.target] += 1
        self.decisions.append(DecisionRenderFacts(site, tuple(indegrees)))


def analyze_direct_render(parser_ir: ParserIr) -> DirectRenderAnalysis:
    """Compute Python-only render facts while sharing recursion classification."""
    return DirectRenderAnalysis(
        analyze_recursion_plan(parser_ir.source_grammar, parser_ir),
        _DecisionFactsAnalyzer().analyze(parser_ir),
    )
