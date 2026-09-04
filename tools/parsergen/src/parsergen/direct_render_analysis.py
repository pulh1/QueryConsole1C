from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .decision_dag import LookaheadDecision
from .parser_ir import (
    AppendCollection,
    AppendNearestOwner,
    AssignConstant,
    BindScalar,
    BranchIr,
    CanonicalDecision,
    ConcatScalar,
    ConstructNode,
    DiscardSymbol,
    Dispatch,
    DispatchValue,
    ExtendCollection,
    IncrementScalar,
    LeftFold,
    Operation,
    OptionalBranch,
    ParseSymbol,
    ParseBranchValue,
    ParserIr,
    RepeatLoop,
    ResolvedRegion,
    WrapOptional,
    WrapValue,
)
from .model import NonterminalCall


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


RecursiveKind = Literal["safe_tail_loop", "local_continuation"]


@dataclass(frozen=True, slots=True)
class ContinuationSlot:
    kind: Literal[
        "operation_result",
        "span_start",
        "builder_field",
        "wrap_seed",
        "fold_accumulator",
        "collection_accumulator",
    ]
    index: int | None
    property: str | None = None


@dataclass(frozen=True, slots=True)
class ContinuationLayout:
    slots: tuple[ContinuationSlot, ...]


@dataclass(frozen=True, slots=True)
class RecursiveCallSite:
    site: IrSite
    kind: RecursiveKind
    layout: ContinuationLayout | None


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
        self.recursive_calls: list[RecursiveCallSite] = []
        self.decisions: list[DecisionRenderFacts] = []
        self._calls_by_production: dict[str, set[str]] = {}
        self._scoped_effect_productions: set[str] = set()

    def analyze(self, parser_ir: ParserIr) -> DirectRenderAnalysis:
        self._calls_by_production = {
            production.name: set() for production in parser_ir.productions
        }
        for production in parser_ir.productions:
            production_site = IrSite(production.name, None, ())
            if production.decision is not None:
                self._decision(production_site, production.decision)
            for alternative in production.alternatives:
                site = IrSite(production.name, alternative.index, ())
                sequence_liveness = self._sequence(
                    site,
                    alternative.operations,
                    alternative.result_index,
                )
        self._scoped_effect_productions = _transitive_scoped_effect_productions(
            self._calls_by_production,
            {
                production.name
                for production in parser_ir.productions
                if any(
                    isinstance(operation, AppendNearestOwner)
                    for alternative in production.alternatives
                    for operation in _walk_operations(alternative.operations)
                )
            },
        )
        for production in parser_ir.productions:
            for alternative in production.alternatives:
                site = IrSite(production.name, alternative.index, ())
                sequence_liveness = next(
                    item
                    for item in self.sequence_liveness
                    if item.site == site
                )
                self._direct_recursive_calls(
                    production.name,
                    site,
                    alternative.operations,
                    sequence_liveness,
                )
        components = _recursive_components(self._calls_by_production)
        return DirectRenderAnalysis(
            tuple(self.sequence_liveness),
            frozenset(self.mutable_owner_types),
            tuple(
                call
                for call in self.recursive_calls
                if _is_nonmutual_component(call.site.production, components)
            ),
            tuple(self.decisions),
        )

    def _direct_recursive_calls(
        self,
        production: str,
        site: IrSite,
        operations: tuple[Operation, ...],
        sequence_liveness: SequenceLiveness,
    ) -> None:
        if (
            not operations
            or production in self._scoped_effect_productions
            or _contains_forbidden_recursion_state(operations)
        ):
            return
        index = len(operations) - 1
        operation = operations[index]
        operation_site = _child_site(site, "operation", index)
        for call_site in _final_direct_self_call_sites(
            operation_site,
            operation,
            production,
        ):
            if call_site not in {
                operation_site,
                _child_site(operation_site, "value", 0),
            }:
                if (
                    _contains_continuation_state(operations)
                    or self._has_live_enclosing_result(call_site)
                ):
                    continue
                self.recursive_calls.append(
                    RecursiveCallSite(call_site, "safe_tail_loop", None)
                )
                continue
            layout = _continuation_layout(
                operations,
                index,
                sequence_liveness.live_after[index],
            )
            self.recursive_calls.append(
                RecursiveCallSite(
                    call_site,
                    "safe_tail_loop" if not layout.slots else "local_continuation",
                    None if not layout.slots else layout,
                )
            )

    def _has_live_enclosing_result(self, call_site: IrSite) -> bool:
        for sequence in self.sequence_liveness:
            if (
                sequence.site.production != call_site.production
                or sequence.site.alternative != call_site.alternative
            ):
                continue
            prefix = sequence.site.trail
            if (
                call_site.trail[: len(prefix)] != prefix
                or len(call_site.trail) <= len(prefix)
            ):
                continue
            kind, index = call_site.trail[len(prefix)]
            if kind != "operation":
                continue
            if sequence.live_after[index] - {index}:
                return True
        return False

    def _sequence(
        self,
        site: IrSite,
        operations: tuple[Operation, ...],
        result_index: int | None,
    ) -> SequenceLiveness:
        sequence_liveness = SequenceLiveness(
            site,
            tuple(
                frozenset({result_index})
                if result_index is not None and index >= result_index
                else frozenset()
                for index in range(len(operations))
            ),
        )
        self.sequence_liveness.append(sequence_liveness)
        for index, operation in enumerate(operations):
            self._operation(
                _child_site(site, "operation", index),
                operation,
            )
        return sequence_liveness

    def _operation(self, site: IrSite, operation: Operation) -> None:
        name = _call_name(operation)
        if name is not None:
            self._calls_by_production[site.production].add(name)
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


def _direct_self_call_site(
    site: IrSite,
    operation: Operation,
    production: str,
) -> IrSite | None:
    if _call_name(operation) == production:
        return site
    value = None
    if isinstance(
        operation,
        (
            BindScalar,
            AppendCollection,
            ExtendCollection,
            ConcatScalar,
            IncrementScalar,
            AppendNearestOwner,
            WrapValue,
        ),
    ):
        value = operation.value
    if _call_name(value) == production:
        return _child_site(site, "value", 0)
    return None


def _final_direct_self_call_sites(
    site: IrSite,
    operation: Operation,
    production: str,
) -> tuple[IrSite, ...]:
    direct = _direct_self_call_site(site, operation, production)
    if direct is not None:
        return (direct,)
    if isinstance(operation, ResolvedRegion) and operation.operations:
        index = len(operation.operations) - 1
        return _final_direct_self_call_sites(
            _child_site(_child_site(site, "region", 0), "operation", index),
            operation.operations[index],
            production,
        )
    if isinstance(operation, Dispatch):
        return tuple(
            call_site
            for index, branch in enumerate(operation.branches)
            if branch.operations
            for call_site in _final_direct_self_call_sites(
                _child_site(
                    _child_site(site, "branch", index),
                    "operation",
                    len(branch.operations) - 1,
                ),
                branch.operations[-1],
                production,
            )
        )
    return ()


def _call_name(value: object) -> str | None:
    if isinstance(value, (ParseSymbol, DiscardSymbol)) and isinstance(
        value.symbol,
        NonterminalCall,
    ):
        return value.symbol.name
    return None


def _continuation_layout(
    operations: tuple[Operation, ...],
    call_index: int,
    live_after: frozenset[int],
) -> ContinuationLayout:
    slots = [
        ContinuationSlot("operation_result", index)
        for index in sorted(live_after - {call_index})
    ]
    for index, operation in enumerate(operations[:call_index]):
        _append_continuation_slots(slots, operation, index)
    operation = operations[call_index]
    if isinstance(operation, WrapValue):
        slots.append(ContinuationSlot("wrap_seed", call_index))
    elif isinstance(operation, (AppendCollection, ExtendCollection)):
        slots.append(ContinuationSlot("collection_accumulator", call_index))
    elif isinstance(operation, (ConcatScalar, IncrementScalar)):
        slots.append(ContinuationSlot("builder_field", call_index))
    elif isinstance(operation, AssignConstant):
        slots.append(ContinuationSlot("builder_field", call_index))
    return ContinuationLayout(tuple(slots))


def _append_continuation_slots(
    slots: list[ContinuationSlot],
    operation: Operation,
    index: int,
) -> None:
    if isinstance(operation, ConstructNode):
        slots.append(ContinuationSlot("span_start", index))
    elif isinstance(operation, BindScalar):
        slots.append(ContinuationSlot("builder_field", index))
    elif isinstance(operation, (AppendCollection, ExtendCollection)):
        slots.append(ContinuationSlot("collection_accumulator", index))
    elif isinstance(operation, (ConcatScalar, IncrementScalar)):
        slots.append(ContinuationSlot("builder_field", index))
    elif isinstance(operation, AssignConstant):
        slots.append(ContinuationSlot("builder_field", index))
    elif isinstance(operation, ResolvedRegion):
        for nested in operation.operations:
            _append_nested_builder_slots(slots, nested)
    elif isinstance(operation, (Dispatch, RepeatLoop)):
        for branch in operation.branches:
            for nested in branch.operations:
                _append_nested_builder_slots(slots, nested)
    elif isinstance(operation, OptionalBranch):
        for branch in operation.branches:
            for nested in branch.operations:
                _append_nested_builder_slots(slots, nested)
        for nested in operation.exit_operations:
            _append_nested_builder_slots(slots, nested)
    elif isinstance(operation, WrapValue):
        slots.append(ContinuationSlot("wrap_seed", index))


def _append_nested_builder_slots(
    slots: list[ContinuationSlot],
    operation: Operation,
) -> None:
    property_name = _builder_property(operation)
    if property_name is not None:
        slot = ContinuationSlot("builder_field", None, property_name)
        if slot not in slots:
            slots.append(slot)
        return
    if isinstance(operation, ResolvedRegion):
        for nested in operation.operations:
            _append_nested_builder_slots(slots, nested)
    elif isinstance(operation, (Dispatch, RepeatLoop, OptionalBranch)):
        branches = operation.branches
        for branch in branches:
            for nested in branch.operations:
                _append_nested_builder_slots(slots, nested)
        if isinstance(operation, OptionalBranch):
            for nested in operation.exit_operations:
                _append_nested_builder_slots(slots, nested)


def _builder_property(operation: Operation) -> str | None:
    if isinstance(operation, (BindScalar, ExtendCollection, ConcatScalar, IncrementScalar, AssignConstant)):
        return operation.property
    if isinstance(operation, AppendCollection):
        return "items" if operation.property is None else operation.property
    return None


def _contains_continuation_state(operations: tuple[Operation, ...]) -> bool:
    return any(
        isinstance(
            operation,
            (
                ConstructNode,
                BindScalar,
                AppendCollection,
                ExtendCollection,
                ConcatScalar,
                IncrementScalar,
                AssignConstant,
                WrapValue,
                WrapOptional,
            ),
        )
        for operation in _walk_operations(operations)
    )


def _contains_forbidden_recursion_state(
    operations: tuple[Operation, ...],
) -> bool:
    return any(
        isinstance(operation, (AppendNearestOwner, LeftFold))
        for operation in _walk_operations(operations)
    )


def _recursive_components(
    calls_by_production: dict[str, set[str]],
) -> dict[str, frozenset[str]]:
    names = frozenset(calls_by_production)
    graph = {
        production: frozenset(name for name in calls if name in names)
        for production, calls in calls_by_production.items()
    }
    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: dict[str, frozenset[str]] = {}

    def visit(name: str) -> None:
        nonlocal index
        indexes[name] = index
        lowlinks[name] = index
        index += 1
        stack.append(name)
        on_stack.add(name)
        for target in graph[name]:
            if target not in indexes:
                visit(target)
                lowlinks[name] = min(lowlinks[name], lowlinks[target])
            elif target in on_stack:
                lowlinks[name] = min(lowlinks[name], indexes[target])
        if lowlinks[name] != indexes[name]:
            return
        component: list[str] = []
        while True:
            target = stack.pop()
            on_stack.remove(target)
            component.append(target)
            if target == name:
                break
        frozen_component = frozenset(component)
        components.update(
            (member, frozen_component) for member in frozen_component
        )

    for name in graph:
        if name not in indexes:
            visit(name)
    return components


def _transitive_scoped_effect_productions(
    calls_by_production: dict[str, set[str]],
    direct_effect_productions: set[str],
) -> set[str]:
    effect_productions = set(direct_effect_productions)
    changed = True
    while changed:
        changed = False
        for production, calls in calls_by_production.items():
            if production in effect_productions:
                continue
            if calls & effect_productions:
                effect_productions.add(production)
                changed = True
    return effect_productions


def _is_nonmutual_component(
    production: str,
    components: dict[str, frozenset[str]],
) -> bool:
    return len(components[production]) == 1


def _walk_operations(operations: tuple[Operation, ...]):
    for operation in operations:
        yield operation
        if isinstance(operation, ResolvedRegion):
            yield from _walk_operations(operation.operations)
        elif isinstance(operation, (Dispatch, RepeatLoop)):
            for branch in operation.branches:
                yield from _walk_operations(branch.operations)
        elif isinstance(operation, OptionalBranch):
            for branch in operation.branches:
                yield from _walk_operations(branch.operations)
            yield from _walk_operations(operation.exit_operations)
        elif isinstance(operation, WrapOptional):
            yield operation.seed
            for branch in operation.branches:
                yield from _walk_operations(branch.operations)
        elif isinstance(operation, WrapValue):
            yield operation.seed
            yield from _walk_bound_value_operations(operation.value)
        elif isinstance(operation, LeftFold):
            for branch in (*operation.base_branches, *operation.recursive_branches):
                yield from _walk_operations(branch.operations)
        elif isinstance(
            operation,
            (
                BindScalar,
                AppendCollection,
                ExtendCollection,
                ConcatScalar,
                IncrementScalar,
                AppendNearestOwner,
            ),
        ):
            yield from _walk_bound_value_operations(operation.value)


def _walk_bound_value_operations(value: object):
    if isinstance(value, AppendNearestOwner):
        yield value
        if value.value is not None:
            yield from _walk_bound_value_operations(value.value)
    elif isinstance(value, DispatchValue):
        for branch in value.branches:
            yield from _walk_operations(branch.value.operations)
    elif isinstance(value, ParseBranchValue):
        yield from _walk_operations(value.operations)


def analyze_direct_render(parser_ir: ParserIr) -> DirectRenderAnalysis:
    """Compute immutable rendering facts without copying executable IR."""
    return _Analyzer().analyze(parser_ir)
