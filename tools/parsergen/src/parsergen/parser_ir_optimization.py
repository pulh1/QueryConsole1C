from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass, replace

from .canonical_select import (
    AlternativeOutcome,
    CanonicalDecisionSource,
    OutcomeLanguage,
    specialize_outcome,
)
from .decision_dag import (
    CommitAlternative,
    DecisionPath,
    DecisionPathFact,
    ExitDecision,
    build_decision_dag,
    decision_paths,
)
from .model import (
    Constant,
    IdentifierRef,
    Lexeme,
    NonterminalCall,
    SyntaxSymbol,
    Terminal,
)
from .parser_ir import (
    AlternativeIr,
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
    ParseBranchValue,
    ParseSymbol,
    ParserIr,
    ProductionIr,
    RepeatLoop,
    ResolvedRegion,
    ReturnConstant,
    UndefinedValue,
    WrapOptional,
    WrapValue,
)


MAX_PATH_SPECIALIZATION_EXTRA_OPERATIONS = 32


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
        elif isinstance(operation, ResolvedRegion):
            yield from _operation_spans(operation.operations)
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
        if isinstance(operation, ResolvedRegion):
            if _contains_semantic_operation(operation.operations):
                return True
            continue
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
    if isinstance(operation, ConsumeKnownSymbol) and operation.capture_value:
        return "unchanged child result"
    if isinstance(operation, ResolvedRegion) and operation.result_index is not None:
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
        self.identifier_token_types = {
            definition.label: frozenset(definition.token_types)
            for definition in parser_ir.matcher_definitions
        }

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
        if isinstance(operation, ResolvedRegion):
            operations = self.operations(operation.operations, stack)
            return replace(
                operation,
                operations=operations,
                result_index=(
                    operation.result_index
                    if operations == operation.operations
                    else _result_index(operations)
                ),
            )
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
            return updated_decision, self._specialize_decision_paths(
                updated_decision,
                tuple(updated_branches),
            )
        return decision, transformed

    def _specialize_decision_paths(
        self,
        decision: CanonicalDecision,
        branches: tuple[BranchIr, ...],
    ) -> tuple[BranchIr, ...]:
        branches_by_outcome: dict[AlternativeOutcome, BranchIr] = {}
        for branch in branches:
            if branch.outcome in branches_by_outcome:
                return branches
            branches_by_outcome[branch.outcome] = branch

        paths_by_outcome: dict[AlternativeOutcome, list[DecisionPath]] = {}
        outcome_order: list[AlternativeOutcome] = []
        for path in decision_paths(decision.dag):
            if not isinstance(path.leaf, CommitAlternative):
                continue
            outcome = path.leaf.outcome
            if outcome not in paths_by_outcome:
                outcome_order.append(outcome)
                paths_by_outcome[outcome] = []
            paths_by_outcome[outcome].append(path)

        expanded: list[BranchIr] = []
        for outcome in outcome_order:
            branch = branches_by_outcome.get(outcome)
            if branch is None:
                return branches
            candidates = tuple(
                self._specialize_branch_path(branch, path.facts)
                for path in paths_by_outcome[outcome]
            )
            distinct_operations: list[tuple[Operation, ...]] = []
            for candidate in candidates:
                if candidate.operations not in distinct_operations:
                    distinct_operations.append(candidate.operations)
            if len(distinct_operations) == 1:
                candidate = candidates[0]
                expanded.append(
                    branch
                    if candidate.operations == branch.operations
                    else replace(candidate, path_facts=None)
                )
            else:
                expanded.extend(
                    replace(candidate, path_facts=path.facts)
                    for candidate, path in zip(
                        candidates,
                        paths_by_outcome[outcome],
                        strict=True,
                    )
                )

        expanded_outcomes = frozenset(outcome_order)
        expanded.extend(
            branch
            for branch in branches
            if branch.outcome not in expanded_outcomes
        )
        result = tuple(expanded)
        extra_cost = _branches_operation_tree_cost(result) - (
            _branches_operation_tree_cost(branches)
        )
        if extra_cost > MAX_PATH_SPECIALIZATION_EXTRA_OPERATIONS:
            return branches
        return result

    def _specialize_branch_path(
        self,
        branch: BranchIr,
        facts: tuple[DecisionPathFact, ...],
    ) -> BranchIr:
        if not facts:
            return branch
        operations, _, _ = self._partial_evaluate_operations(
            branch.operations,
            branch.result_index,
            facts,
            0,
        )
        if operations == branch.operations:
            return branch
        return replace(
            branch,
            operations=operations,
            result_index=(
                branch.result_index
                if len(operations) == len(branch.operations)
                else _result_index(operations)
            ),
            path_facts=facts,
        )

    def _partial_evaluate_operations(
        self,
        operations: tuple[Operation, ...],
        result_index: int | None,
        facts: tuple[DecisionPathFact, ...],
        cursor: int,
    ) -> tuple[tuple[Operation, ...], int, bool]:
        result: list[Operation] = []
        for index, operation in enumerate(operations):
            if isinstance(operation, (ParseSymbol, DiscardSymbol)):
                capture_value = (
                    isinstance(operation, ParseSymbol)
                    and result_index == index
                )
                known = self._known_consume(
                    operation.symbol,
                    capture_value,
                    operation.source_span,
                    facts,
                    cursor,
                )
                if known is None:
                    result.extend(operations[index:])
                    return tuple(result), cursor, True
                result.append(known)
                cursor += 1
                continue
            if isinstance(operation, (ConstructNode, AssignConstant, ReturnConstant)):
                result.append(operation)
                continue
            if isinstance(operation, (Dispatch, OptionalBranch)):
                resolved = self._resolve_region(
                    operation,
                    facts,
                    cursor,
                )
                if resolved is None:
                    result.extend(operations[index:])
                    return tuple(result), cursor, True
                region_operations, region_result, cursor, stopped = resolved
                result.append(
                    ResolvedRegion(
                        region_operations,
                        region_result,
                        operation.source_span,
                    )
                )
                if stopped:
                    result.extend(operations[index + 1 :])
                    return tuple(result), cursor, True
                continue
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
                value, cursor, stopped = self._partial_evaluate_bound_value(
                    operation.value,
                    facts,
                    cursor,
                )
                if stopped:
                    result.extend(operations[index:])
                    return tuple(result), cursor, True
                result.append(replace(operation, value=value))
                continue
            result.extend(operations[index:])
            return tuple(result), cursor, True
        return tuple(result), cursor, False

    def _partial_evaluate_bound_value(
        self,
        value,
        facts: tuple[DecisionPathFact, ...],
        cursor: int,
    ):
        if isinstance(value, ParseSymbol):
            known = self._known_consume(
                value.symbol,
                True,
                value.source_span,
                facts,
                cursor,
            )
            if known is None:
                return value, cursor, True
            return known, cursor + 1, False
        if isinstance(value, ConsumeKnownSymbol):
            return value, cursor + 1, False
        if isinstance(value, (UndefinedValue,)):
            return value, cursor, False
        if isinstance(value, ParseBranchValue):
            operations, cursor, stopped = self._partial_evaluate_operations(
                value.operations,
                value.result_index,
                facts,
                cursor,
            )
            return (
                replace(value, operations=operations),
                cursor,
                stopped,
            )
        return value, cursor, True

    def _known_consume(
        self,
        symbol: SyntaxSymbol,
        capture_value: bool,
        source_span,
        facts: tuple[DecisionPathFact, ...],
        cursor: int,
    ) -> ConsumeKnownSymbol | None:
        accepted = self._accepted_token_types(symbol)
        if accepted is None:
            return None
        fact = next((item for item in facts if item.offset == cursor), None)
        if fact is None or not set(fact.predicate.token_types).issubset(accepted):
            return None
        return ConsumeKnownSymbol(
            symbol,
            capture_value,
            fact.predicate.token_types,
            source_span,
        )

    def _accepted_token_types(
        self,
        symbol: SyntaxSymbol,
    ) -> frozenset[str] | None:
        if isinstance(symbol, Terminal):
            return frozenset({symbol.token_type})
        if isinstance(symbol, Lexeme):
            return frozenset({symbol.text})
        if isinstance(symbol, Constant):
            return frozenset({symbol.token_type})
        if isinstance(symbol, IdentifierRef):
            return self.identifier_token_types.get(symbol.name)
        return None

    def _resolve_region(
        self,
        operation: Dispatch | OptionalBranch,
        facts: tuple[DecisionPathFact, ...],
        cursor: int,
    ) -> tuple[tuple[Operation, ...], int | None, int, bool] | None:
        matching = tuple(
            path
            for path in decision_paths(operation.decision.dag)
            if _path_is_proven(path, facts, cursor)
        )
        if len(matching) != 1:
            return None
        leaf = matching[0].leaf
        if isinstance(leaf, CommitAlternative):
            branches = tuple(
                branch
                for branch in operation.branches
                if branch.outcome == leaf.outcome
            )
            if len(branches) != 1:
                return None
            branch = branches[0]
            operations, cursor, stopped = self._partial_evaluate_operations(
                branch.operations,
                branch.result_index,
                facts,
                cursor,
            )
            return operations, branch.result_index, cursor, stopped
        if isinstance(operation, OptionalBranch) and isinstance(
            leaf,
            ExitDecision,
        ):
            operations, cursor, stopped = self._partial_evaluate_operations(
                operation.exit_operations,
                _result_index(operation.exit_operations),
                facts,
                cursor,
            )
            return (
                operations,
                _result_index(operations),
                cursor,
                stopped,
            )
        return None

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
    if isinstance(operation, ConsumeKnownSymbol):
        return operation.capture_value
    if isinstance(operation, ResolvedRegion):
        return operation.result_index is not None
    if isinstance(operation, (Dispatch, OptionalBranch)):
        return bool(operation.branches) and all(
            branch.result_index is not None
            for branch in operation.branches
        )
    return False


def _path_is_proven(
    path: DecisionPath,
    facts: tuple[DecisionPathFact, ...],
    cursor: int,
) -> bool:
    facts_by_offset = {fact.offset: fact for fact in facts}
    return all(
        (outer := facts_by_offset.get(cursor + inner.offset)) is not None
        and set(outer.predicate.token_types).issubset(
            inner.predicate.token_types
        )
        for inner in path.facts
    )


def _branches_operation_tree_cost(
    branches: tuple[BranchIr, ...],
) -> int:
    return sum(
        _operations_tree_cost(branch.operations)
        for branch in branches
    )


def _operations_tree_cost(operations: tuple[Operation, ...]) -> int:
    return sum(_operation_tree_cost(operation) for operation in operations)


def _operation_tree_cost(operation: Operation) -> int:
    if isinstance(operation, ResolvedRegion):
        return 1 + _operations_tree_cost(operation.operations)
    if isinstance(operation, (Dispatch, RepeatLoop)):
        return 1 + _branches_operation_tree_cost(operation.branches)
    if isinstance(operation, OptionalBranch):
        return (
            1
            + _branches_operation_tree_cost(operation.branches)
            + _operations_tree_cost(operation.exit_operations)
        )
    if isinstance(operation, WrapOptional):
        return (
            1
            + _operation_tree_cost(operation.seed)
            + _branches_operation_tree_cost(operation.branches)
        )
    if isinstance(operation, WrapValue):
        return (
            1
            + _operation_tree_cost(operation.seed)
            + _bound_value_tree_cost(operation.value)
        )
    if isinstance(operation, LeftFold):
        return (
            1
            + _branches_operation_tree_cost(operation.base_branches)
            + _branches_operation_tree_cost(operation.recursive_branches)
        )
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
        return 1 + _bound_value_tree_cost(operation.value)
    return 1


def _bound_value_tree_cost(value) -> int:
    if isinstance(value, ParseBranchValue):
        return 1 + _operations_tree_cost(value.operations)
    if isinstance(value, DispatchValue):
        return 1 + sum(
            _bound_value_tree_cost(branch.value)
            for branch in value.branches
        )
    if isinstance(value, (ParseSymbol, ConsumeKnownSymbol)):
        return 1
    return 0


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
