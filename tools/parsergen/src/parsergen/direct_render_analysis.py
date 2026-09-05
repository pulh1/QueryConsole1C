from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .decision_dag import LookaheadDecision
from .parser_ir import (
    AppendCollection,
    AssignConstant,
    BindScalar,
    BranchIr,
    CanonicalDecision,
    ConcatScalar,
    ConsumeKnownSymbol,
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
    suffix_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class RecursiveCallSite:
    site: IrSite
    kind: RecursiveKind
    layout: ContinuationLayout | None


@dataclass(frozen=True, slots=True)
class ResultFlowFact:
    site: IrSite
    propagates_unchanged: bool


@dataclass(frozen=True, slots=True)
class DirectRenderAnalysis:
    sequence_liveness: tuple[SequenceLiveness, ...]
    recursive_calls: tuple[RecursiveCallSite, ...]
    result_flow: tuple[ResultFlowFact, ...]
    decisions: tuple[DecisionRenderFacts, ...]


class _Analyzer:
    def __init__(self) -> None:
        self.sequence_liveness: list[SequenceLiveness] = []
        self.recursive_calls: list[RecursiveCallSite] = []
        self.result_flow: list[ResultFlowFact] = []
        self.decisions: list[DecisionRenderFacts] = []
        self._resultless_productions: frozenset[str] = frozenset()

    def analyze(self, parser_ir: ParserIr) -> DirectRenderAnalysis:
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
        self._resultless_productions = frozenset(
            production.name
            for production in parser_ir.productions
            if all(
                alternative.result_index is None
                # A top-level constructor is the implicit alternative result.
                and not any(
                    isinstance(operation, ConstructNode)
                    for operation in alternative.operations
                )
                for alternative in production.alternatives
            )
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
        return DirectRenderAnalysis(
            tuple(self.sequence_liveness),
            tuple(self.recursive_calls),
            tuple(self.result_flow),
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
            or _contains_left_fold(operations)
        ):
            return
        for index, operation in enumerate(operations):
            suffix_indices = tuple(range(index + 1, len(operations)))
            if suffix_indices and not _is_admissible_semantic_suffix(
                operations[index + 1 :]
            ):
                continue
            operation_site = _child_site(site, "operation", index)
            for candidate in _final_direct_self_call_sites(
                operation_site,
                operation,
                production,
            ):
                call_site = candidate.site
                if call_site not in {
                    operation_site,
                    _child_site(operation_site, "value", 0),
                }:
                    if suffix_indices:
                        continue
                    layout = _nested_continuation_layout(
                        operations,
                        sequence_liveness,
                        call_site,
                    )
                    if layout is not None:
                        self.recursive_calls.append(
                            RecursiveCallSite(
                                call_site,
                                "local_continuation",
                                layout,
                            )
                        )
                        continue
                    if candidate.requires_post_return:
                        continue
                    propagates_unchanged = self._has_unchanged_result_flow(candidate)
                    self.result_flow.append(
                        ResultFlowFact(call_site, propagates_unchanged)
                    )
                    if (
                        _contains_continuation_state(operations)
                        or self._has_live_enclosing_result(call_site)
                        or (
                            not propagates_unchanged
                            and production not in self._resultless_productions
                        )
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
                if suffix_indices:
                    layout = ContinuationLayout(layout.slots, suffix_indices)
                if (
                    not layout.slots
                    and not layout.suffix_indices
                    and candidate.requires_post_return
                ):
                    continue
                if not layout.slots and not layout.suffix_indices:
                    propagates_unchanged = self._has_unchanged_result_flow(candidate)
                    self.result_flow.append(
                        ResultFlowFact(call_site, propagates_unchanged)
                    )
                    if (
                        not propagates_unchanged
                        and production not in self._resultless_productions
                    ):
                        continue
                self.recursive_calls.append(
                    RecursiveCallSite(
                        call_site,
                        (
                            "local_continuation"
                            if layout.slots or layout.suffix_indices
                            else "safe_tail_loop"
                        ),
                        (
                            layout
                            if layout.slots or layout.suffix_indices
                            else None
                        ),
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

    def _has_unchanged_result_flow(
        self,
        candidate: _FinalDirectSelfCall,
    ) -> bool:
        if not candidate.result_propagated:
            return False
        found_enclosing_sequence = False
        for sequence in self.sequence_liveness:
            if (
                sequence.site.production != candidate.site.production
                or sequence.site.alternative != candidate.site.alternative
            ):
                continue
            prefix = sequence.site.trail
            if (
                candidate.site.trail[: len(prefix)] != prefix
                or len(candidate.site.trail) <= len(prefix)
            ):
                continue
            kind, index = candidate.site.trail[len(prefix)]
            if kind != "operation":
                continue
            found_enclosing_sequence = True
            if sequence.live_after[index] != frozenset({index}):
                return False
        return found_enclosing_sequence

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
            WrapValue,
        ),
    ):
        value = operation.value
    if _call_name(value) == production:
        return _child_site(site, "value", 0)
    return None


@dataclass(frozen=True, slots=True)
class _FinalDirectSelfCall:
    site: IrSite
    result_propagated: bool
    requires_post_return: bool


def _final_direct_self_call_sites(
    site: IrSite,
    operation: Operation,
    production: str,
) -> tuple[_FinalDirectSelfCall, ...]:
    direct = _direct_self_call_site(site, operation, production)
    if direct is not None:
        return (
            _FinalDirectSelfCall(
                direct,
                isinstance(operation, ParseSymbol),
                # A call reached through an operand must return before its
                # enclosing semantic operation can apply that operand.
                direct != site,
            ),
        )
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
    if isinstance(operation, OptionalBranch):
        branch_calls = tuple(
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
        if not operation.exit_operations:
            return branch_calls
        index = len(operation.exit_operations) - 1
        return (
            *branch_calls,
            *_final_direct_self_call_sites(
                _child_site(
                    _child_site(site, "exit", 0),
                    "operation",
                    index,
                ),
                operation.exit_operations[index],
                production,
            ),
        )
    return ()


def _call_name(value: object) -> str | None:
    if isinstance(value, (ParseSymbol, DiscardSymbol)) and isinstance(
        value.symbol,
        NonterminalCall,
    ):
        return value.symbol.name
    return None


def _is_admissible_semantic_suffix(operations: tuple[Operation, ...]) -> bool:
    return all(isinstance(operation, AssignConstant) for operation in operations)


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


def _nested_continuation_layout(
    operations: tuple[Operation, ...],
    sequence_liveness: SequenceLiveness,
    call_site: IrSite,
) -> ContinuationLayout | None:
    trail = call_site.trail
    if not trail or trail[0][0] != "operation":
        return None
    call_index = trail[0][1]
    if call_index >= len(operations):
        return None
    layout = _continuation_layout(
        operations,
        call_index,
        sequence_liveness.live_after[call_index],
    )
    slots = list(layout.slots)
    if not _append_nested_path_slots(
        slots,
        operations[call_index],
        trail[1:],
    ):
        return None
    if not slots:
        return None
    return ContinuationLayout(tuple(slots))


def _append_nested_path_slots(
    slots: list[ContinuationSlot],
    operation: Operation,
    trail: Trail,
) -> bool:
    if len(trail) < 2:
        return False
    child_kind, child_index = trail[0]
    operation_kind, operation_index = trail[1]
    if operation_kind != "operation":
        return False
    nested_operations: tuple[Operation, ...]
    if isinstance(operation, ResolvedRegion):
        if child_kind != "region" or child_index != 0:
            return False
        nested_operations = operation.operations
    elif isinstance(operation, (Dispatch, RepeatLoop, OptionalBranch)):
        if child_kind == "branch" and child_index < len(operation.branches):
            nested_operations = operation.branches[child_index].operations
        elif (
            isinstance(operation, OptionalBranch)
            and child_kind == "exit"
            and child_index == 0
        ):
            nested_operations = operation.exit_operations
        else:
            return False
    else:
        return False
    if operation_index >= len(nested_operations):
        return False
    for nested in nested_operations[:operation_index]:
        _append_nested_builder_slots(slots, nested)
    nested_operation = nested_operations[operation_index]
    remainder = trail[2:]
    if remainder == (("value", 0),):
        return isinstance(nested_operation, BindScalar)
    return _append_nested_path_slots(slots, nested_operation, remainder)


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


def _contains_left_fold(
    operations: tuple[Operation, ...],
) -> bool:
    return any(
        isinstance(operation, LeftFold)
        for operation in _walk_operations(operations)
    )


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
            ),
        ):
            yield from _walk_bound_value_operations(operation.value)


def _walk_bound_value_operations(value: object):
    if isinstance(value, DispatchValue):
        for branch in value.branches:
            yield from _walk_operations(branch.value.operations)
    elif isinstance(value, ParseBranchValue):
        yield from _walk_operations(value.operations)


def analyze_direct_render(parser_ir: ParserIr) -> DirectRenderAnalysis:
    """Compute immutable rendering facts without copying executable IR."""
    return _Analyzer().analyze(parser_ir)
