from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass, replace

from .canonical_select import (
    AlternativeOutcome,
    CanonicalDecisionSource,
    OutcomeLanguage,
    specialize_outcome,
)
from .decision_dag import build_decision_dag
from .model import Constant, IdentifierRef, NonterminalCall
from .parser_ir import (
    AlternativeIr,
    AppendCollection,
    AssignConstant,
    BindScalar,
    BranchIr,
    CanonicalDecision,
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
    ProductionIr,
    RepeatLoop,
    ReturnConstant,
    UndefinedValue,
    WrapOptional,
    WrapValue,
)


@dataclass(frozen=True, slots=True)
class TransparencyResult:
    transparent: bool
    reason: str


_SEMANTIC_OPERATIONS = (
    ConstructNode,
    BindScalar,
    AppendCollection,
    ExtendCollection,
    ConcatScalar,
    IncrementScalar,
    AssignConstant,
    ReturnConstant,
    WrapOptional,
    WrapValue,
    LeftFold,
)


def classify_semantic_transparency(
    production: ProductionIr,
    *,
    entrypoints: frozenset[str],
    recursive_productions: frozenset[str],
) -> TransparencyResult:
    if production.name in entrypoints:
        return TransparencyResult(False, "public entrypoint")
    if production.name in recursive_productions:
        return TransparencyResult(False, "recursive SCC")
    if production.parameters:
        return TransparencyResult(False, "formal parameters")
    if production.decision is not None:
        return TransparencyResult(False, "decision diagnostic boundary")
    if any(
        span.path != production.source_span.path
        for alternative in production.alternatives
        for span in _operation_spans(alternative.operations)
    ):
        return TransparencyResult(False, "source provenance boundary")
    if any(
        _contains_semantic_operation(alternative.operations)
        for alternative in production.alternatives
    ):
        return TransparencyResult(False, "semantic operation")
    path_kinds = tuple(
        _transparent_path_kind(alternative)
        for alternative in production.alternatives
    )
    if any(kind is None for kind in path_kinds):
        return TransparencyResult(False, "transformed or ambiguous result")
    if len(set(path_kinds)) != 1:
        return TransparencyResult(False, "inconsistent successful paths")
    return TransparencyResult(True, str(path_kinds[0]))


def _operation_spans(operations: tuple[Operation, ...]):
    for operation in operations:
        yield operation.source_span
        if isinstance(operation, (Dispatch, RepeatLoop)):
            for branch in operation.branches:
                yield from _operation_spans(branch.operations)
        elif isinstance(operation, OptionalBranch):
            for branch in operation.branches:
                yield from _operation_spans(branch.operations)
            yield from _operation_spans(operation.exit_operations)
        elif isinstance(operation, WrapOptional):
            yield from _operation_spans((operation.seed,))
            for branch in operation.branches:
                yield from _operation_spans(branch.operations)
        elif isinstance(operation, WrapValue):
            yield from _operation_spans((operation.seed,))
            yield from _bound_operation_spans(operation.value)
        elif isinstance(operation, LeftFold):
            for branch in (*operation.base_branches, *operation.recursive_branches):
                yield from _operation_spans(branch.operations)
        elif isinstance(
            operation,
            (BindScalar, AppendCollection, ExtendCollection, ConcatScalar, IncrementScalar),
        ):
            yield from _bound_operation_spans(operation.value)


def _bound_operation_spans(value):
    if isinstance(value, ParseBranchValue):
        yield from _operation_spans(value.operations)
    elif isinstance(value, DispatchValue):
        for branch in value.branches:
            yield from _bound_operation_spans(branch.value)


def _contains_semantic_operation(operations: tuple[Operation, ...]) -> bool:
    for operation in operations:
        if isinstance(operation, _SEMANTIC_OPERATIONS):
            return True
        if isinstance(operation, (Dispatch, RepeatLoop)):
            if any(
                _contains_semantic_operation(branch.operations)
                for branch in operation.branches
            ):
                return True
            return True
        if isinstance(operation, OptionalBranch):
            if any(
                _contains_semantic_operation(branch.operations)
                for branch in operation.branches
            ) or _contains_semantic_operation(operation.exit_operations):
                return True
            return True
    return False


def _transparent_path_kind(alternative: AlternativeIr) -> str | None:
    if alternative.result_index is None:
        return "syntax-only"
    if not 0 <= alternative.result_index < len(alternative.operations):
        return None
    operation = alternative.operations[alternative.result_index]
    if isinstance(operation, ParseSymbol) and isinstance(
        operation.symbol,
        (NonterminalCall, IdentifierRef, Constant),
    ):
        return "unchanged child result"
    return None


def optimize_parser_ir(parser_ir: ParserIr) -> ParserIr:
    recursive = _recursive_productions(parser_ir.productions)
    transparent = frozenset(
        production.name
        for production in parser_ir.productions
        if classify_semantic_transparency(
            production,
            entrypoints=parser_ir.entrypoint_productions,
            recursive_productions=recursive,
        ).transparent
    )
    result = parser_ir
    for _ in range(max(1, len(parser_ir.productions) * 2)):
        optimizer = _Optimizer(result, transparent)
        updated = replace(
            result,
            productions=tuple(
                optimizer.production(production)
                for production in result.productions
            ),
        )
        if updated == result:
            break
        result = updated
    return replace(
        result,
        productions=_reachable_productions(result),
    )


class _Optimizer:
    def __init__(
        self,
        parser_ir: ParserIr,
        transparent: frozenset[str],
    ) -> None:
        self.productions = {
            production.name: production
            for production in parser_ir.productions
        }
        self.transparent = transparent

    def production(self, production: ProductionIr) -> ProductionIr:
        alternatives = tuple(
            self.alternative(alternative, (production.name,))
            for alternative in production.alternatives
        )
        return replace(production, alternatives=alternatives)

    def alternative(
        self,
        alternative: AlternativeIr,
        stack: tuple[str, ...],
    ) -> AlternativeIr:
        operations = self.operations(alternative.operations, stack)
        return replace(
            alternative,
            operations=operations,
            result_index=(
                alternative.result_index
                if operations == alternative.operations
                else _result_index(operations)
            ),
        )

    def operations(
        self,
        operations: tuple[Operation, ...],
        stack: tuple[str, ...],
    ) -> tuple[Operation, ...]:
        result: list[Operation] = []
        for operation in operations:
            transformed = self.operation(operation, stack)
            if (
                isinstance(transformed, ParseSymbol)
                and isinstance(transformed.symbol, NonterminalCall)
                and not transformed.symbol.arguments
                and transformed.symbol.name in self.transparent
                and transformed.symbol.name not in stack
            ):
                callee = self.productions.get(transformed.symbol.name)
                if callee is not None and len(callee.alternatives) == 1:
                    result.extend(
                        self.operations(
                            callee.alternatives[0].operations,
                            (*stack, callee.name),
                        )
                    )
                    continue
            result.append(transformed)
        return tuple(result)

    def operation(
        self,
        operation: Operation,
        stack: tuple[str, ...],
    ) -> Operation:
        if isinstance(operation, Dispatch):
            return replace(
                operation,
                branches=tuple(
                    self.branch(branch, stack)
                    for branch in operation.branches
                ),
            )
        if isinstance(operation, RepeatLoop):
            return replace(
                operation,
                branches=tuple(
                    self.branch(branch, stack)
                    for branch in operation.branches
                ),
            )
        if isinstance(operation, OptionalBranch):
            return replace(
                operation,
                branches=tuple(
                    self.branch(branch, stack)
                    for branch in operation.branches
                ),
                exit_operations=self.operations(operation.exit_operations, stack),
            )
        if isinstance(operation, WrapOptional):
            decision, branches = self.control(
                operation.decision,
                operation.branches,
                stack,
            )
            return replace(
                operation,
                seed=self.operation(operation.seed, stack),
                decision=decision,
                branches=branches,
            )
        if isinstance(operation, WrapValue):
            return replace(
                operation,
                seed=self.operation(operation.seed, stack),
                value=self.bound_value(operation.value, stack),
            )
        if isinstance(operation, LeftFold):
            return replace(
                operation,
                base_branches=tuple(
                    self.branch(branch, stack)
                    for branch in operation.base_branches
                ),
                recursive_branches=tuple(
                    self.branch(branch, stack)
                    for branch in operation.recursive_branches
                ),
            )
        if isinstance(
            operation,
            (BindScalar, AppendCollection, ExtendCollection, ConcatScalar, IncrementScalar),
        ):
            return replace(
                operation,
                value=self.bound_value(operation.value, stack),
            )
        return operation

    def branch(
        self,
        branch: BranchIr,
        stack: tuple[str, ...],
    ) -> BranchIr:
        operations = self.operations(branch.operations, stack)
        return replace(
            branch,
            operations=operations,
            result_index=(
                branch.result_index
                if operations == branch.operations
                else _result_index(operations)
            ),
        )

    def control(
        self,
        decision: CanonicalDecision,
        branches: tuple[BranchIr, ...],
        stack: tuple[str, ...],
    ) -> tuple[CanonicalDecision, tuple[BranchIr, ...]]:
        transformed = tuple(self.branch(branch, stack) for branch in branches)
        for position, branch in enumerate(transformed):
            call = _direct_parameter_free_call(branch.operations)
            if call is None:
                continue
            callee = self.productions.get(call.name)
            if (
                callee is None
                or callee.parameters
                or _production_contains_left_fold(callee)
                or _has_repeated_leading_semantic_action(callee)
            ):
                continue
            callee_alternatives = tuple(
                self.alternative(item, (*stack, callee.name))
                for item in callee.alternatives
            )
            if callee.decision is None:
                if len(callee_alternatives) != 1:
                    continue
                new_outcome = AlternativeOutcome(callee.name, 1)
                source = _rename_outcome(
                    decision.source,
                    branch.outcome,
                    new_outcome,
                )
            else:
                source = specialize_outcome(
                    decision.source,
                    branch.outcome,
                    callee.decision.source,
                )
            replacements = tuple(
                BranchIr(
                    AlternativeOutcome(callee.name, item.index + 1),
                    item.operations,
                    item.result_index,
                    item.source_span,
                )
                for item in callee_alternatives
            )
            updated_branches = (
                *transformed[:position],
                *replacements,
                *transformed[position + 1 :],
            )
            updated_decision = CanonicalDecision(
                source,
                build_decision_dag(source),
            )
            return updated_decision, tuple(updated_branches)
        return decision, transformed

    def bound_value(self, value, stack: tuple[str, ...]):
        if isinstance(value, ParseSymbol) and isinstance(
            value.symbol,
            NonterminalCall,
        ) and (
            not value.symbol.arguments
            and value.symbol.name in self.transparent
            and value.symbol.name not in stack
        ):
            callee = self.productions.get(value.symbol.name)
            if callee is not None and len(callee.alternatives) == 1:
                operations = self.operations(
                    callee.alternatives[0].operations,
                    (*stack, callee.name),
                )
                result_index = _result_index(operations)
                if result_index is None:
                    return UndefinedValue("Неопределено", value.source_span)
                return ParseBranchValue(
                    operations,
                    result_index,
                    value.source_span,
                )
        if isinstance(value, ParseBranchValue):
            operations = self.operations(value.operations, stack)
            result_index = (
                value.result_index
                if operations == value.operations
                else _result_index(operations)
            )
            if result_index is None:
                return UndefinedValue("Неопределено", value.source_span)
            return replace(
                value,
                operations=operations,
                result_index=result_index,
            )
        if isinstance(value, DispatchValue):
            return replace(
                value,
                branches=tuple(
                    replace(
                        branch,
                        value=self.bound_value(branch.value, stack),
                    )
                    for branch in value.branches
                ),
            )
        return value


def _direct_parameter_free_call(
    operations: tuple[Operation, ...],
) -> NonterminalCall | None:
    if len(operations) != 1 or not isinstance(operations[0], ParseSymbol):
        return None
    symbol = operations[0].symbol
    if not isinstance(symbol, NonterminalCall) or symbol.arguments:
        return None
    return symbol


def _production_contains_left_fold(production: ProductionIr) -> bool:
    return any(
        isinstance(operation, LeftFold)
        for alternative in production.alternatives
        for operation in alternative.operations
    )


def _has_repeated_leading_semantic_action(
    production: ProductionIr,
) -> bool:
    """Reject composition that would duplicate an unfactored action prefix.

    Canonical production rendering can emit an identical leading semantic
    action once before its alternative decision.  The specialized branch
    renderer has no equivalent common-prefix proof, so copying such branches
    would lose the exact-once textual action region.  Comparing the semantic
    operation itself, rather than production names, keeps eligibility
    structural.
    """
    seen: set[tuple[object, ...]] = set()
    for alternative in production.alternatives:
        if not alternative.operations:
            continue
        signature = _leading_semantic_action_signature(
            alternative.operations[0]
        )
        if signature is None:
            continue
        if signature in seen:
            return True
        seen.add(signature)
    return False


def _leading_semantic_action_signature(
    operation: Operation,
) -> tuple[object, ...] | None:
    if isinstance(operation, ConstructNode):
        return (ConstructNode, operation.constructor)
    if isinstance(operation, AssignConstant):
        return (
            AssignConstant,
            operation.property,
            operation.value,
        )
    if isinstance(operation, ReturnConstant):
        return (ReturnConstant, operation.value)
    return None


def _rename_outcome(
    source: CanonicalDecisionSource,
    old: AlternativeOutcome,
    new: AlternativeOutcome,
) -> CanonicalDecisionSource:
    matching = sum(item.outcome == old for item in source.languages)
    if matching != 1:
        raise ValueError("renamed outcome must exist exactly once")
    return CanonicalDecisionSource(
        source.production,
        source.lookahead,
        tuple(
            OutcomeLanguage(
                new if item.outcome == old else item.outcome,
                item.language,
            )
            for item in source.languages
        ),
    )


def _result_index(operations: tuple[Operation, ...]) -> int | None:
    if any(
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
            ),
        )
        for operation in operations
    ):
        return None
    indices = tuple(
        index
        for index, operation in enumerate(operations)
        if _produces_value(operation)
    )
    return indices[0] if len(indices) == 1 else None


def _produces_value(operation: Operation) -> bool:
    if isinstance(operation, (LeftFold, ReturnConstant, WrapOptional, WrapValue)):
        return True
    if isinstance(operation, ParseSymbol):
        return isinstance(
            operation.symbol,
            (NonterminalCall, IdentifierRef, Constant),
        )
    if isinstance(operation, (Dispatch, OptionalBranch)):
        return bool(operation.branches) and all(
            branch.result_index is not None
            for branch in operation.branches
        )
    return False


def _recursive_productions(
    productions: tuple[ProductionIr, ...],
) -> frozenset[str]:
    names = frozenset(item.name for item in productions)
    graph = {
        production.name: frozenset(
            call for call in _production_calls(production) if call in names
        )
        for production in productions
    }
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    recursive: set[str] = set()

    def visit(name: str) -> None:
        nonlocal index
        indices[name] = index
        lowlinks[name] = index
        index += 1
        stack.append(name)
        on_stack.add(name)
        for target in graph[name]:
            if target not in indices:
                visit(target)
                lowlinks[name] = min(lowlinks[name], lowlinks[target])
            elif target in on_stack:
                lowlinks[name] = min(lowlinks[name], indices[target])
        if lowlinks[name] != indices[name]:
            return
        component: list[str] = []
        while True:
            target = stack.pop()
            on_stack.remove(target)
            component.append(target)
            if target == name:
                break
        if len(component) > 1 or name in graph[name]:
            recursive.update(component)

    for name in graph:
        if name not in indices:
            visit(name)
    recursive.update(
        production.name
        for production in productions
        if any(
            isinstance(operation, LeftFold)
            for alternative in production.alternatives
            for operation in alternative.operations
        )
    )
    return frozenset(recursive)


def _production_calls(production: ProductionIr) -> set[str]:
    return {
        call.name
        for alternative in production.alternatives
        for call in _nonterminal_calls(alternative.operations)
    }


def _nonterminal_calls(value) -> Iterable[NonterminalCall]:
    if isinstance(value, NonterminalCall):
        yield value
        return
    if isinstance(value, (str, bytes, int, bool, type(None))):
        return
    if isinstance(value, (tuple, list, frozenset)):
        for item in value:
            yield from _nonterminal_calls(item)
        return
    if is_dataclass(value):
        for field in fields(value):
            if field.name in {"decision", "source_span", "span"}:
                continue
            yield from _nonterminal_calls(getattr(value, field.name))


def _reachable_productions(parser_ir: ParserIr) -> tuple[ProductionIr, ...]:
    productions = {
        production.name: production
        for production in parser_ir.productions
    }
    selected = frozenset(productions)
    external_roots = {
        call.name
        for production in parser_ir.source_grammar.productions
        if production.name not in selected
        for call in _nonterminal_calls(production)
        if call.name in selected
    }
    roots = set(parser_ir.entrypoint_productions).union(external_roots)
    reachable: set[str] = set()
    pending = [name for name in roots if name in productions]
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        reachable.add(name)
        pending.extend(
            call
            for call in _production_calls(productions[name])
            if call in productions and call not in reachable
        )
    return tuple(
        production
        for production in parser_ir.productions
        if production.name in reachable
    )
