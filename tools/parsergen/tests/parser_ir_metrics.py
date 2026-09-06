"""Target-neutral ParserIr regression metrics used by repository grammar tests."""

from __future__ import annotations

from dataclasses import fields, is_dataclass

from parsergen.decision_dag import CommitAlternative, decision_paths
from parsergen.model import Constant, IdentifierRef, Lexeme, Terminal
from parsergen.parser_ir import (
    AppendCollection,
    BindScalar,
    BranchIr,
    CanonicalDecision,
    ConcatScalar,
    ConsumeKnownSymbol,
    DiscardSymbol,
    Dispatch,
    DispatchValue,
    ExtendCollection,
    IncrementScalar,
    LeftFold,
    OptionalBranch,
    ParseBranchValue,
    ParseSymbol,
    RepeatLoop,
    ResolvedRegion,
    WrapOptional,
    WrapValue,
)


def parser_ir_decisions(
    parser_ir,
    *,
    unique: bool = False,
) -> tuple[CanonicalDecision, ...]:
    """Return the canonical decisions reachable from the ParserIr."""
    decisions: list[CanonicalDecision] = []
    seen: set[int] = set()

    def visit(value) -> None:
        if isinstance(value, CanonicalDecision):
            if unique and id(value) in seen:
                return
            seen.add(id(value))
            decisions.append(value)
            return
        if isinstance(value, (str, bytes, int, bool, type(None))):
            return
        if isinstance(value, (tuple, list, frozenset)):
            for item in value:
                visit(item)
            return
        if is_dataclass(value):
            for field in fields(value):
                if field.name not in {"source_span", "span"}:
                    visit(getattr(value, field.name))

    for production in parser_ir.productions:
        visit(production)
    return tuple(decisions)


def decision_path_metrics(parser_ir) -> dict[str, int]:
    """Measure specialized ParserIr paths without assuming a codegen target."""
    counts = {
        "specialized_paths": 0,
        "known_symbol_consumes": 0,
        "redundant_validations": 0,
    }
    identifier_token_types = {
        definition.label: frozenset(definition.token_types)
        for definition in parser_ir.matcher_definitions
    }

    def accepted_token_types(symbol):
        if isinstance(symbol, Terminal):
            return frozenset({symbol.token_type})
        if isinstance(symbol, Lexeme):
            return frozenset({symbol.text})
        if isinstance(symbol, Constant):
            return frozenset({symbol.token_type})
        if isinstance(symbol, IdentifierRef):
            return identifier_token_types.get(symbol.name)
        return None

    def redundant_in_operations(operations, facts) -> int:
        facts_by_offset = {fact.offset: fact for fact in facts}

        def scan_bound_value(value, cursor):
            if isinstance(value, ConsumeKnownSymbol):
                return cursor + 1, True, 0
            if isinstance(value, ParseSymbol):
                return scan_symbol(value.symbol, cursor)
            if isinstance(value, ParseBranchValue):
                return scan_operations(value.operations, cursor)
            if isinstance(value, DispatchValue):
                return cursor, False, 0
            return cursor, True, 0

        def scan_symbol(symbol, cursor):
            accepted = accepted_token_types(symbol)
            if accepted is None:
                return cursor, False, 0
            fact = facts_by_offset.get(cursor)
            redundant = int(
                fact is not None
                and set(fact.predicate.token_types).issubset(accepted)
            )
            return cursor + 1, True, redundant

        def scan_operation(operation, cursor):
            if isinstance(operation, ConsumeKnownSymbol):
                return cursor + 1, True, 0
            if isinstance(operation, (ParseSymbol, DiscardSymbol)):
                return scan_symbol(operation.symbol, cursor)
            if isinstance(operation, ResolvedRegion):
                return scan_operations(operation.operations, cursor)
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
                return scan_bound_value(operation.value, cursor)
            if isinstance(operation, WrapValue):
                cursor, active, redundant = scan_operation(operation.seed, cursor)
                if not active:
                    return cursor, active, redundant
                cursor, active, nested = scan_bound_value(operation.value, cursor)
                return cursor, active, redundant + nested
            if isinstance(
                operation,
                (Dispatch, OptionalBranch, RepeatLoop, WrapOptional, LeftFold),
            ):
                return cursor, False, 0
            return cursor, True, 0

        def scan_operations(nested_operations, cursor=0):
            redundant = 0
            active = True
            for operation in nested_operations:
                cursor, active, nested = scan_operation(operation, cursor)
                redundant += nested
                if not active:
                    break
            return cursor, active, redundant

        return scan_operations(operations)[2]

    def visit_bound_value(value) -> None:
        if isinstance(value, ConsumeKnownSymbol):
            counts["known_symbol_consumes"] += 1
        elif isinstance(value, ParseBranchValue):
            visit_operations(value.operations)
        elif isinstance(value, DispatchValue):
            for branch in value.branches:
                visit_bound_value(branch.value)

    def visit_branch(
        branch: BranchIr,
        decision: CanonicalDecision | None,
    ) -> None:
        if branch.path_facts is not None:
            counts["specialized_paths"] += 1
            counts["redundant_validations"] += redundant_in_operations(
                branch.operations,
                branch.path_facts,
            )
        elif decision is not None:
            for path in decision_paths(decision.dag):
                if (
                    isinstance(path.leaf, CommitAlternative)
                    and path.leaf.outcome == branch.outcome
                ):
                    counts["redundant_validations"] += redundant_in_operations(
                        branch.operations,
                        path.facts,
                    )
        visit_operations(branch.operations)

    def visit_control_branches(branches, decision) -> None:
        fallback_decision = (
            decision
            if decision is not None
            and (
                decision.caller_callee_composed
                or any(branch.path_facts is not None for branch in branches)
            )
            else None
        )
        for branch in branches:
            visit_branch(branch, fallback_decision)

    def visit_operations(operations) -> None:
        for operation in operations:
            if isinstance(operation, ConsumeKnownSymbol):
                counts["known_symbol_consumes"] += 1
            elif isinstance(operation, ResolvedRegion):
                visit_operations(operation.operations)
            elif isinstance(operation, (Dispatch, RepeatLoop)):
                visit_control_branches(operation.branches, operation.decision)
            elif isinstance(operation, OptionalBranch):
                visit_control_branches(operation.branches, operation.decision)
                visit_operations(operation.exit_operations)
            elif isinstance(operation, WrapOptional):
                visit_operations((operation.seed,))
                visit_control_branches(operation.branches, operation.decision)
            elif isinstance(operation, WrapValue):
                visit_operations((operation.seed,))
                visit_bound_value(operation.value)
            elif isinstance(operation, LeftFold):
                visit_control_branches(
                    operation.base_branches,
                    operation.base_decision,
                )
                visit_control_branches(
                    operation.recursive_branches,
                    operation.recursive_decision,
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
                visit_bound_value(operation.value)

    for production in parser_ir.productions:
        for alternative in production.alternatives:
            visit_operations(alternative.operations)
    return counts
