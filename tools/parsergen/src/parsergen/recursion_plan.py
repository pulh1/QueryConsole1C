from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .model import Constant, IdentifierRef, Lexeme, NonterminalCall, Terminal
from .parser_ir import (
    AppendCollection,
    AssignConstant,
    BindScalar,
    ConcatScalar,
    ConsumeKnownSymbol,
    DiscardSymbol,
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
    ConstructNode,
)
from .source_model import (
    SourceBinding,
    SourceGrammar,
    SourceGroup,
    SourceOptional,
    SourceRepeat,
    SourceSequence,
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
    """A stable location in ParserIr without retaining executable IR."""

    production: str
    alternative: int | None
    trail: Trail


@dataclass(frozen=True, slots=True)
class SequenceLiveness:
    site: IrSite
    live_after: tuple[frozenset[int], ...]


@dataclass(frozen=True, slots=True)
class ResultFlowFact:
    site: IrSite
    propagates_unchanged: bool


RecursiveKind = Literal["tail_loop", "local_continuation"]


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
    result_flow: bool
    layout: ContinuationLayout | None


@dataclass(frozen=True, slots=True)
class RecursionPlan:
    """Target-neutral recursion lowering facts over the final ParserIr."""

    sites: tuple[RecursiveCallSite, ...]
    sequence_liveness: tuple[SequenceLiveness, ...]
    result_flow: tuple[ResultFlowFact, ...]


@dataclass(frozen=True, slots=True)
class _FinalDirectSelfCall:
    site: IrSite
    result_propagated: bool
    requires_post_return: bool


class _RecursionPlanner:
    def __init__(self) -> None:
        self.sequence_liveness: list[SequenceLiveness] = []
        self.sites: list[RecursiveCallSite] = []
        self.result_flow: list[ResultFlowFact] = []
        self._resultless_productions: frozenset[str] = frozenset()
        self._source_progress_spans: frozenset[object] = frozenset()

    def analyze(
        self,
        source_grammar: SourceGrammar,
        parser_ir: ParserIr,
    ) -> RecursionPlan:
        self._source_progress_spans = _source_progress_spans(source_grammar)
        for production in parser_ir.productions:
            for alternative in production.alternatives:
                self._sequence(
                    IrSite(production.name, alternative.index, ()),
                    alternative.operations,
                    alternative.result_index,
                )
        self._resultless_productions = frozenset(
            production.name
            for production in parser_ir.productions
            if all(
                alternative.result_index is None
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
        return RecursionPlan(
            tuple(self.sites),
            tuple(self.sequence_liveness),
            tuple(self.result_flow),
        )

    def _direct_recursive_calls(
        self,
        production: str,
        site: IrSite,
        operations: tuple[Operation, ...],
        sequence_liveness: SequenceLiveness,
    ) -> None:
        if not operations or _contains_left_fold(operations):
            return
        for index, operation in enumerate(operations):
            suffix_indices = tuple(range(index + 1, len(operations)))
            if suffix_indices and not _is_admissible_semantic_suffix(
                operations[index + 1 :]
            ):
                continue
            operation_site = child_site(site, "operation", index)
            for candidate in _final_direct_self_call_sites(
                operation_site,
                operation,
                production,
            ):
                call_site = candidate.site
                if not self._has_proven_progress(
                    operations,
                    index,
                    call_site,
                ):
                    continue
                if call_site not in {
                    operation_site,
                    child_site(operation_site, "value", 0),
                }:
                    if suffix_indices:
                        continue
                    layout = _nested_continuation_layout(
                        operations,
                        sequence_liveness,
                        call_site,
                    )
                    if layout is not None:
                        self.sites.append(
                            RecursiveCallSite(
                                call_site,
                                "local_continuation",
                                self._unchanged_result_flow(candidate),
                                layout,
                            )
                        )
                        continue
                    if candidate.requires_post_return:
                        continue
                    result_flow = self._record_result_flow(candidate)
                    if (
                        _contains_continuation_state(operations)
                        or self._has_live_enclosing_result(call_site)
                        or (
                            not result_flow
                            and production not in self._resultless_productions
                        )
                    ):
                        continue
                    self.sites.append(
                        RecursiveCallSite(
                            call_site,
                            "tail_loop",
                            result_flow,
                            None,
                        )
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
                    result_flow = self._record_result_flow(candidate)
                    if (
                        not result_flow
                        and production not in self._resultless_productions
                    ):
                        continue
                else:
                    result_flow = self._unchanged_result_flow(candidate)
                self.sites.append(
                    RecursiveCallSite(
                        call_site,
                        (
                            "local_continuation"
                            if layout.slots or layout.suffix_indices
                            else "tail_loop"
                        ),
                        result_flow,
                        (
                            layout
                            if layout.slots or layout.suffix_indices
                            else None
                        ),
                    )
                )

    def _has_proven_progress(
        self,
        operations: tuple[Operation, ...],
        call_index: int,
        call_site: IrSite,
    ) -> bool:
        return any(
            self._operation_definitely_consumes(operation)
            for operation in operations[:call_index]
        ) or self._path_has_proven_progress(
            operations[call_index],
            call_site.trail[1:],
        )

    def _path_has_proven_progress(
        self,
        operation: Operation,
        trail: Trail,
    ) -> bool:
        if not trail:
            return False
        if trail == (("value", 0),):
            return (
                isinstance(operation, WrapValue)
                and self._operation_definitely_consumes(operation.seed)
            )
        child_kind, child_index = trail[0]
        if len(trail) < 2 or trail[1][0] != "operation":
            return False
        operation_index = trail[1][1]
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
        return any(
            self._operation_definitely_consumes(nested)
            for nested in nested_operations[:operation_index]
        ) or self._path_has_proven_progress(
            nested_operations[operation_index],
            trail[2:],
        )

    def _operation_definitely_consumes(self, operation: Operation) -> bool:
        if isinstance(operation, ConsumeKnownSymbol):
            return (
                isinstance(
                    operation.symbol,
                    (Terminal, Lexeme, Constant, IdentifierRef),
                )
                and operation.source_span in self._source_progress_spans
                and bool(operation.proven_token_types)
            )
        if isinstance(operation, ParseSymbol):
            return operation.source_span in self._source_progress_spans
        if isinstance(
            operation,
            (
                BindScalar,
                AppendCollection,
                ExtendCollection,
                ConcatScalar,
                IncrementScalar,
            ),
        ):
            return self._bound_value_definitely_consumes(operation.value)
        if isinstance(operation, ResolvedRegion):
            return any(
                self._operation_definitely_consumes(nested)
                for nested in operation.operations
            )
        if isinstance(operation, WrapValue):
            return self._operation_definitely_consumes(
                operation.seed
            ) or self._bound_value_definitely_consumes(operation.value)
        return False

    def _bound_value_definitely_consumes(self, value: object) -> bool:
        if isinstance(value, (ConsumeKnownSymbol, ParseSymbol)):
            return self._operation_definitely_consumes(value)
        if isinstance(value, ParseBranchValue):
            return any(
                self._operation_definitely_consumes(operation)
                for operation in value.operations
            )
        if isinstance(value, DispatchValue):
            return bool(value.branches) and all(
                self._bound_value_definitely_consumes(branch.value)
                for branch in value.branches
            )
        return False

    def _record_result_flow(self, candidate: _FinalDirectSelfCall) -> bool:
        propagates_unchanged = self._unchanged_result_flow(candidate)
        self.result_flow.append(
            ResultFlowFact(candidate.site, propagates_unchanged)
        )
        return propagates_unchanged

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
            if kind == "operation" and sequence.live_after[index] - {index}:
                return True
        return False

    def _unchanged_result_flow(self, candidate: _FinalDirectSelfCall) -> bool:
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
            self._operation(child_site(site, "operation", index), operation)
        return sequence_liveness

    def _operation(self, site: IrSite, operation: Operation) -> None:
        if isinstance(operation, ResolvedRegion):
            self._sequence(
                child_site(site, "region", 0),
                operation.operations,
                operation.result_index,
            )
        elif isinstance(operation, (Dispatch, RepeatLoop)):
            self._branches(site, "branch", operation.branches)
        elif isinstance(operation, OptionalBranch):
            self._branches(site, "branch", operation.branches)
            self._sequence(
                child_site(site, "exit", 0), operation.exit_operations, None
            )
        elif isinstance(operation, WrapOptional):
            self._operation(child_site(site, "seed", 0), operation.seed)
            self._branches(site, "branch", operation.branches)
        elif isinstance(operation, WrapValue):
            self._operation(child_site(site, "seed", 0), operation.seed)
            self._bound_value(child_site(site, "value", 0), operation.value)
        elif isinstance(operation, LeftFold):
            self._branches(site, "base_branch", operation.base_branches)
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
            for index, branch in enumerate(value.branches):
                self._sequence(
                    child_site(site, "value_branch", index),
                    branch.value.operations,
                    branch.value.result_index,
                )
        elif isinstance(value, ParseBranchValue):
            self._sequence(site, value.operations, value.result_index)
        elif isinstance(value, Operation):
            self._operation(site, value)

    def _branches(self, site: IrSite, kind: Literal["branch", "base_branch", "recursive_branch"], branches: tuple) -> None:
        for index, branch in enumerate(branches):
            self._sequence(
                child_site(site, kind, index),
                branch.operations,
                branch.result_index,
            )


def child_site(site: IrSite, kind: TrailKind, index: int) -> IrSite:
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
        return child_site(site, "value", 0)
    return None


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
                direct != site,
            ),
        )
    if isinstance(operation, ResolvedRegion) and operation.operations:
        index = len(operation.operations) - 1
        return _final_direct_self_call_sites(
            child_site(child_site(site, "region", 0), "operation", index),
            operation.operations[index],
            production,
        )
    if isinstance(operation, Dispatch):
        return tuple(
            call_site
            for index, branch in enumerate(operation.branches)
            if branch.operations
            for call_site in _final_direct_self_call_sites(
                child_site(
                    child_site(site, "branch", index),
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
                child_site(
                    child_site(site, "branch", index),
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
                child_site(
                    child_site(site, "exit", 0), "operation", index
                ),
                operation.exit_operations[index],
                production,
            ),
        )
    return ()


def _call_name(value: object) -> str | None:
    if isinstance(value, (ParseSymbol, DiscardSymbol)) and isinstance(
        value.symbol, NonterminalCall
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
    elif isinstance(operation, (ConcatScalar, IncrementScalar, AssignConstant)):
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
        operations, call_index, sequence_liveness.live_after[call_index]
    )
    slots = list(layout.slots)
    if not _append_nested_path_slots(slots, operations[call_index], trail[1:]):
        return None
    if not slots:
        return None
    return ContinuationLayout(tuple(slots))


def _append_nested_path_slots(
    slots: list[ContinuationSlot], operation: Operation, trail: Trail
) -> bool:
    if len(trail) < 2:
        return False
    child_kind, child_index = trail[0]
    operation_kind, operation_index = trail[1]
    if operation_kind != "operation":
        return False
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
    slots: list[ContinuationSlot], operation: Operation, index: int
) -> None:
    if isinstance(operation, ConstructNode):
        slots.append(ContinuationSlot("span_start", index))
    elif isinstance(operation, BindScalar):
        slots.append(ContinuationSlot("builder_field", index))
    elif isinstance(operation, (AppendCollection, ExtendCollection)):
        slots.append(ContinuationSlot("collection_accumulator", index))
    elif isinstance(operation, (ConcatScalar, IncrementScalar, AssignConstant)):
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
    slots: list[ContinuationSlot], operation: Operation
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
        for branch in operation.branches:
            for nested in branch.operations:
                _append_nested_builder_slots(slots, nested)
        if isinstance(operation, OptionalBranch):
            for nested in operation.exit_operations:
                _append_nested_builder_slots(slots, nested)


def _builder_property(operation: Operation) -> str | None:
    if isinstance(
        operation,
        (BindScalar, ExtendCollection, ConcatScalar, IncrementScalar, AssignConstant),
    ):
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


def _contains_left_fold(operations: tuple[Operation, ...]) -> bool:
    return any(isinstance(operation, LeftFold) for operation in _walk_operations(operations))


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
            (BindScalar, AppendCollection, ExtendCollection, ConcatScalar, IncrementScalar),
        ):
            yield from _walk_bound_value_operations(operation.value)


def _walk_bound_value_operations(value: object):
    if isinstance(value, DispatchValue):
        for branch in value.branches:
            yield from _walk_operations(branch.value.operations)
    elif isinstance(value, ParseBranchValue):
        yield from _walk_operations(value.operations)


def _source_progress_spans(source_grammar: SourceGrammar) -> frozenset[object]:
    """Return source spans guaranteed to advance on successful parsing.

    The proof is a least fixed point over source productions: a nonterminal
    qualifies only when every alternative reaches a qualifying item. Optional
    and zero-or-more items never qualify on their own.
    """
    productions = {item.name: item for item in source_grammar.productions}
    consumes = {name: False for name in productions}

    def value_consumes(value: object, known: dict[str, bool]) -> bool:
        if isinstance(value, (Terminal, Lexeme, Constant, IdentifierRef)):
            return True
        if isinstance(value, NonterminalCall):
            return known.get(value.name, False)
        if isinstance(value, SourceBinding):
            return value_consumes(value.value, known)
        if isinstance(value, SourceGroup):
            return all(
                sequence_consumes(alternative.body, known)
                for alternative in value.alternatives
            )
        if isinstance(value, SourceRepeat):
            return (
                value.kind.value == "plus"
                and value_consumes(value.body, known)
            )
        if isinstance(value, SourceOptional):
            return False
        return False

    def sequence_consumes(
        sequence: SourceSequence,
        known: dict[str, bool],
    ) -> bool:
        return any(value_consumes(item, known) for item in sequence.items)

    changed = True
    while changed:
        changed = False
        next_consumes = {
            name: all(
                sequence_consumes(alternative.body, consumes)
                for alternative in production.alternatives
            )
            for name, production in productions.items()
        }
        for name, value in next_consumes.items():
            if value != consumes[name]:
                consumes[name] = value
                changed = True

    spans: set[object] = set()

    def visit_value(value: object) -> None:
        if value_consumes(value, consumes) and hasattr(value, "span"):
            spans.add(value.span)
        if isinstance(value, SourceBinding):
            visit_value(value.value)
        elif isinstance(value, SourceGroup):
            for alternative in value.alternatives:
                visit_sequence(alternative.body)
        elif isinstance(value, (SourceOptional, SourceRepeat)):
            visit_value(value.body)

    def visit_sequence(sequence: SourceSequence) -> None:
        for item in sequence.items:
            visit_value(item)

    for production in source_grammar.productions:
        for alternative in production.alternatives:
            visit_sequence(alternative.body)
    return frozenset(spans)


def analyze_recursion_plan(
    source_grammar: SourceGrammar, parser_ir: ParserIr
) -> RecursionPlan:
    """Classify direct recursion once for every renderer over ``parser_ir``."""
    if source_grammar != parser_ir.source_grammar:
        raise ValueError("source grammar does not match Parser IR")
    return _RecursionPlanner().analyze(source_grammar, parser_ir)
