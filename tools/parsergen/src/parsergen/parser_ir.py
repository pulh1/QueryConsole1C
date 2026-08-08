from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from .analysis import (
    AnalysisResult,
    CanonicalDecisionRow,
    MatcherDefinition,
    build_canonical_decision_artifact,
    find_canonical_select_conflicts,
)
from .diagnostics import Severity, SourceSpan
from .lowering import (
    BindingOrigin,
    BindingOriginKind,
    LoweredConstruct,
    LoweredConstructKind,
    LoweredLeftRecursion,
    LoweringResult,
    lower_source_grammar,
)
from .left_recursion import (
    DirectRecursiveAlternative,
    classify_direct_left_recursion,
)
from .model import (
    Action,
    Constant,
    IdentifierRef,
    NonterminalCall,
    SyntaxSymbol,
)
from .resolver import ResolvedGrammar, resolve_grammar
from .source_model import (
    BindingMode,
    SourceAlternative,
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
    SourceGrammar,
    SourceGroup,
    SourceItem,
    SourceOptional,
    SourcePrimary,
    SourceProduction,
    SourceRepeat,
    SourceSequence,
)


@dataclass(frozen=True, slots=True)
class CanonicalDecision:
    production: str
    rows: tuple[CanonicalDecisionRow, ...]
    matcher_definitions: tuple[MatcherDefinition, ...]


@dataclass(frozen=True, slots=True)
class ParseSymbol:
    symbol: SyntaxSymbol
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class UndefinedValue:
    value: str
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class FoldLeftValue:
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class ParseBranchValue:
    operations: tuple[Operation, ...]
    result_index: int
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class ValueBranchIr:
    alternative: int
    value: ParseBranchValue
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class DispatchValue:
    decision: CanonicalDecision
    branches: tuple[ValueBranchIr, ...]
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class BranchIr:
    alternative: int
    operations: tuple[Operation, ...]
    result_index: int | None
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class Dispatch:
    decision: CanonicalDecision
    branches: tuple[BranchIr, ...]
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class RepeatLoop:
    decision: CanonicalDecision
    branches: tuple[BranchIr, ...]
    exit_alternative: int
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class OptionalBranch:
    decision: CanonicalDecision
    branches: tuple[BranchIr, ...]
    exit_alternative: int
    exit_operations: tuple[Operation, ...]
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class LeftFold:
    base_decision: CanonicalDecision | None
    base_branches: tuple[BranchIr, ...]
    recursive_decision: CanonicalDecision
    recursive_branches: tuple[BranchIr, ...]
    exit_alternative: int
    source_span: SourceSpan


BoundValue = (
    ParseSymbol
    | DispatchValue
    | ParseBranchValue
    | UndefinedValue
    | FoldLeftValue
)


@dataclass(frozen=True, slots=True)
class ConstructNode:
    constructor: str
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class BindScalar:
    property: str
    value: BoundValue
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class AppendCollection:
    property: str | None
    value: BoundValue
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class ConcatScalar:
    property: str
    value: BoundValue
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class IncrementScalar:
    property: str
    value: BoundValue
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class AssignConstant:
    property: str
    value: str
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class ReturnConstant:
    value: str
    source_span: SourceSpan


Operation = (
    ParseSymbol
    | Dispatch
    | RepeatLoop
    | OptionalBranch
    | ConstructNode
    | BindScalar
    | AppendCollection
    | ConcatScalar
    | IncrementScalar
    | AssignConstant
    | ReturnConstant
    | LeftFold
)


@dataclass(frozen=True, slots=True)
class AlternativeIr:
    index: int
    operations: tuple[Operation, ...]
    result_index: int | None
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class ProductionIr:
    name: str
    parameters: tuple[str, ...]
    alternatives: tuple[AlternativeIr, ...]
    decision: CanonicalDecision | None
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class ParserIr:
    productions: tuple[ProductionIr, ...]
    matcher_definitions: tuple[MatcherDefinition, ...]
    lookahead: int
    source_grammar: SourceGrammar


def build_parser_ir(
    source: SourceGrammar,
    lowering: LoweringResult,
    resolved: ResolvedGrammar,
    analysis: AnalysisResult,
    *,
    production_names: Collection[str] | None = None,
) -> ParserIr:
    if any(
        item.severity is Severity.ERROR
        for item in lowering.diagnostics
    ):
        raise ValueError("source grammar has EBNF validation errors")
    if lower_source_grammar(source) != lowering:
        raise ValueError("source grammar does not match lowering result")
    reparsed = resolve_grammar(lowering.grammar)
    if reparsed.grammar is None or reparsed.grammar != resolved:
        raise ValueError("lowered grammar does not match resolved grammar")
    if analysis._resolved_grammar is not resolved:
        raise ValueError("analysis is not bound to the resolved grammar")
    selected_names = _selected_production_names(source, production_names)
    required_decisions = _required_decision_productions(
        lowering,
        frozenset(selected_names),
    )
    conflicts = tuple(
        conflict
        for conflict in find_canonical_select_conflicts(resolved, analysis)
        if conflict.production in required_decisions
    )
    if conflicts:
        raise ValueError("overlapping canonical SELECT prevents Parser IR")
    artifact = build_canonical_decision_artifact(analysis)
    return _ParserIrBuilder(
        source,
        lowering,
        artifact.rows,
        artifact.matcher_definitions,
        analysis.k,
        frozenset(selected_names),
    ).build()


def _selected_production_names(
    source: SourceGrammar,
    production_names: Collection[str] | None,
) -> tuple[str, ...]:
    source_order = tuple(production.name for production in source.productions)
    if production_names is None:
        return source_order
    requested_values = tuple(production_names)
    requested = frozenset(requested_values)
    if len(requested) != len(requested_values):
        raise ValueError("duplicate Parser IR production")
    unknown = requested.difference(source_order)
    if unknown:
        formatted = ", ".join(repr(item) for item in sorted(unknown))
        raise ValueError(f"unknown Parser IR production: {formatted}")
    return tuple(name for name in source_order if name in requested)


def _required_decision_productions(
    lowering: LoweringResult,
    selected_names: frozenset[str],
) -> frozenset[str]:
    required = set(selected_names)
    for construct in lowering.constructs:
        if construct.source_production not in selected_names:
            continue
        required.add(construct.production)
        if construct.tail_production is not None:
            required.add(construct.tail_production)
    for recursion in lowering.left_recursions:
        if recursion.production in selected_names:
            required.add(recursion.tail_production)
    return frozenset(required)


class _ParserIrBuilder:
    def __init__(
        self,
        source: SourceGrammar,
        lowering: LoweringResult,
        rows: tuple[CanonicalDecisionRow, ...],
        matcher_definitions: tuple[MatcherDefinition, ...],
        lookahead: int,
        selected_names: frozenset[str],
    ) -> None:
        self._source = source
        self._lowering = lowering
        self._rows = rows
        self._matcher_definitions = matcher_definitions
        self._lookahead = lookahead
        self._selected_names = selected_names
        self._lowered_left_recursions = {
            item.production: item
            for item in lowering.left_recursions
        }
        self._source_left_recursions = classify_direct_left_recursion(source)

    def build(self) -> ParserIr:
        productions = tuple(
            self._production(production)
            for production in self._source.productions
            if production.name in self._selected_names
        )
        return ParserIr(
            productions,
            self._matcher_definitions,
            self._lookahead,
            self._source,
        )

    def _production(self, production: SourceProduction) -> ProductionIr:
        left_recursion = self._lowered_left_recursions.get(production.name)
        if left_recursion is not None:
            return self._left_fold_production(production, left_recursion)
        alternatives = tuple(
            self._alternative_ir(alternative)
            for alternative in production.alternatives
        )
        decision = (
            self._decision(production.name)
            if len(alternatives) > 1
            else None
        )
        return ProductionIr(
            production.name,
            production.parameters,
            alternatives,
            decision,
            production.span,
        )

    def _left_fold_production(
        self,
        production: SourceProduction,
        lowered: LoweredLeftRecursion,
    ) -> ProductionIr:
        source = self._source_left_recursions.get(production.name)
        if source is None:
            raise ValueError(
                "left-recursion lowering has no matching source descriptor"
            )
        if (
            source.base_alternatives != lowered.base_alternatives
            or tuple(
                item.alternative for item in source.recursive_alternatives
            )
            != lowered.recursive_alternatives
        ):
            raise ValueError(
                "left-recursion source and lowering alternatives differ"
            )

        base_branches = tuple(
            self._source_branch(
                production.alternatives[source_index],
                canonical_index + 1,
            )
            for canonical_index, source_index in enumerate(
                lowered.base_alternatives
            )
        )
        recursive_by_index = {
            item.alternative: item
            for item in source.recursive_alternatives
        }
        recursive_branches = tuple(
            self._recursive_left_fold_branch(
                production,
                production.alternatives[source_index],
                recursive_by_index[source_index],
                canonical_index + 1,
            )
            for canonical_index, source_index in enumerate(
                lowered.recursive_alternatives
            )
        )
        operation = LeftFold(
            (
                self._decision(production.name)
                if len(base_branches) > 1
                else None
            ),
            base_branches,
            self._decision(lowered.tail_production),
            recursive_branches,
            len(recursive_branches) + 1,
            production.span,
        )
        alternative = AlternativeIr(
            0,
            (operation,),
            0,
            production.span,
        )
        return ProductionIr(
            production.name,
            production.parameters,
            (alternative,),
            None,
            production.span,
        )

    def _source_branch(
        self,
        alternative: SourceAlternative,
        canonical_alternative: int,
    ) -> BranchIr:
        operations = self._sequence(alternative.body)
        return BranchIr(
            canonical_alternative,
            operations,
            self._result_index(operations),
            alternative.span,
        )

    def _recursive_left_fold_branch(
        self,
        production: SourceProduction,
        alternative: SourceAlternative,
        recursive: DirectRecursiveAlternative,
        canonical_alternative: int,
    ) -> BranchIr:
        operations = list(self._sequence(alternative.body))
        reference = recursive.self_reference
        if reference.property is None:
            matching = tuple(
                index
                for index, operation in enumerate(operations)
                if isinstance(operation, ParseSymbol)
                and isinstance(operation.symbol, NonterminalCall)
                and operation.symbol.name == production.name
                and operation.source_span == reference.call.span
            )
            if len(matching) != 1:
                raise ValueError(
                    "left-fold operations do not identify the self-call"
                )
            del operations[matching[0]]
        else:
            matching = tuple(
                index
                for index, operation in enumerate(operations)
                if isinstance(operation, BindScalar)
                and operation.property == reference.property
                and operation.source_span == reference.source_span
            )
            if len(matching) != 1:
                raise ValueError(
                    "left-fold operations do not identify the accumulator binding"
                )
            index = matching[0]
            binding = operations[index]
            assert isinstance(binding, BindScalar)
            if (
                not isinstance(binding.value, ParseSymbol)
                or not isinstance(binding.value.symbol, NonterminalCall)
                or binding.value.symbol.name != production.name
            ):
                raise ValueError(
                    "left-fold accumulator binding does not contain self-call"
                )
            operations[index] = BindScalar(
                binding.property,
                FoldLeftValue(reference.call.span),
                binding.source_span,
            )
        result = tuple(operations)
        return BranchIr(
            canonical_alternative,
            result,
            self._result_index(result),
            alternative.span,
        )

    def _alternative_ir(
        self,
        alternative: SourceAlternative,
    ) -> AlternativeIr:
        operations = self._sequence(alternative.body)
        return AlternativeIr(
            alternative.index,
            operations,
            self._result_index(operations),
            alternative.span,
        )

    def _sequence(self, sequence: SourceSequence) -> tuple[Operation, ...]:
        result: list[Operation] = []
        for item in sequence.items:
            if isinstance(item, Action):
                raise ValueError(
                    "arbitrary source actions require declarative bindings"
                )
            if isinstance(item, SourceConstructor):
                origin = self._binding_origin(
                    item.span,
                    BindingOriginKind.CONSTRUCTOR,
                )
                result.append(ConstructNode(item.name, origin.source_span))
            elif isinstance(item, SourceConstantBinding):
                origin = self._binding_origin(
                    item.span,
                    BindingOriginKind.CONSTANT,
                )
                if item.property is None:
                    result.append(
                        ReturnConstant(
                            item.value,
                            origin.source_span,
                        )
                    )
                else:
                    result.append(
                        AssignConstant(
                            item.property,
                            item.value,
                            origin.source_span,
                        )
                    )
            elif isinstance(item, SourceBinding):
                result.extend(self._binding(item))
            elif isinstance(item, SourceGroup):
                branches = self._group_branches(item)
                construct = self._construct(
                    item.span,
                    LoweredConstructKind.GROUP,
                )
                result.append(
                    Dispatch(
                        self._decision(construct.production),
                        branches,
                        item.span,
                    )
                )
            elif isinstance(item, SourceRepeat):
                result.extend(self._repeat(item))
            elif isinstance(item, SourceOptional):
                construct = self._construct(
                    item.span,
                    LoweredConstructKind.OPTIONAL,
                )
                branches = self._primary_branches(item.body)
                result.append(
                    OptionalBranch(
                        self._decision(construct.production),
                        branches,
                        len(branches) + 1,
                        (),
                        item.span,
                    )
                )
            else:
                result.append(ParseSymbol(item, item.span))
        return tuple(result)

    def _binding(self, binding: SourceBinding) -> tuple[Operation, ...]:
        kind = _binding_origin_kind(binding.mode)
        origin = self._binding_origin(binding.span, kind)
        if isinstance(binding.value, SourceOptional):
            optional = binding.value
            construct = self._construct(
                optional.span,
                LoweredConstructKind.OPTIONAL,
            )
            branches = self._bound_primary_branches(optional.body, binding)
            exit_operations: tuple[Operation, ...] = ()
            if binding.mode is BindingMode.SCALAR:
                exit_operations = (
                    BindScalar(
                        binding.property,
                        UndefinedValue("Неопределено", origin.source_span),
                        origin.source_span,
                    ),
                )
            return (
                OptionalBranch(
                    self._decision(construct.production),
                    branches,
                    len(branches) + 1,
                    exit_operations,
                    optional.span,
                ),
            )
        if isinstance(binding.value, SourceRepeat):
            return self._repeat(binding.value, binding)
        return (
            self._binding_operation(
                binding,
                self._bound_value(binding.value),
            ),
        )

    def _repeat(
        self,
        repeat: SourceRepeat,
        binding: SourceBinding | None = None,
    ) -> tuple[Operation, ...]:
        kind = (
            LoweredConstructKind.STAR
            if repeat.kind.value == "star"
            else LoweredConstructKind.PLUS
        )
        construct = self._construct(repeat.span, kind)
        branches = (
            self._bound_primary_branches(repeat.body, binding)
            if binding is not None
            else self._primary_branches(repeat.body)
        )
        if binding is None and any(
            branch.result_index is not None
            for branch in branches
        ):
            raise ValueError(
                "repeated semantic value requires collection binding"
            )
        result: list[Operation] = []
        decision_production = construct.production
        if kind is LoweredConstructKind.PLUS:
            if len(branches) == 1:
                result.extend(branches[0].operations)
            else:
                result.append(
                    Dispatch(
                        self._decision(construct.production),
                        branches,
                        repeat.span,
                    )
                )
            assert construct.tail_production is not None
            decision_production = construct.tail_production
        result.append(
            RepeatLoop(
                self._decision(decision_production),
                branches,
                len(branches) + 1,
                repeat.span,
            )
        )
        return tuple(result)

    def _bound_primary_branches(
        self,
        primary: SourcePrimary,
        binding: SourceBinding,
    ) -> tuple[BranchIr, ...]:
        if isinstance(primary, SourceGroup):
            return tuple(
                BranchIr(
                    alternative.index + 1,
                    (
                        self._binding_operation(
                            binding,
                            self._branch_value(alternative),
                        ),
                    ),
                    None,
                    alternative.span,
                )
                for alternative in primary.alternatives
            )
        return (
            BranchIr(
                1,
                (
                    self._binding_operation(
                        binding,
                        ParseSymbol(primary, primary.span),
                    ),
                ),
                None,
                primary.span,
            ),
        )

    def _bound_value(self, value: SourcePrimary) -> BoundValue:
        if isinstance(value, SourceGroup):
            construct = self._construct(
                value.span,
                LoweredConstructKind.GROUP,
            )
            return DispatchValue(
                self._decision(construct.production),
                tuple(
                    ValueBranchIr(
                        alternative.index + 1,
                        self._branch_value(alternative),
                        alternative.span,
                    )
                    for alternative in value.alternatives
                ),
                value.span,
            )
        return ParseSymbol(value, value.span)

    def _branch_value(
        self,
        alternative: SourceAlternative,
    ) -> ParseBranchValue:
        operations = self._sequence(alternative.body)
        semantic_indices = tuple(
            index
            for index, operation in enumerate(operations)
            if _produces_transparent_value(operation)
        )
        if not semantic_indices:
            semantic_indices = tuple(
                index
                for index, operation in enumerate(operations)
                if isinstance(operation, ParseSymbol)
            )
        if len(semantic_indices) != 1:
            raise ValueError(
                "bound branch does not identify exactly one semantic value"
            )
        return ParseBranchValue(
            operations,
            semantic_indices[0],
            alternative.span,
        )

    def _binding_operation(
        self,
        binding: SourceBinding,
        value: BoundValue,
    ) -> BindScalar | AppendCollection | ConcatScalar | IncrementScalar:
        kind = _binding_origin_kind(binding.mode)
        origin = self._binding_origin(binding.span, kind)
        if binding.mode is BindingMode.APPEND:
            operation = AppendCollection
        elif binding.mode is BindingMode.CONCAT:
            assert binding.property is not None
            operation = ConcatScalar
        elif binding.mode is BindingMode.INCREMENT:
            assert binding.property is not None
            operation = IncrementScalar
        else:
            operation = BindScalar
        return operation(binding.property, value, origin.source_span)

    def _group_branches(self, group: SourceGroup) -> tuple[BranchIr, ...]:
        return tuple(
            self._alternative_branch(alternative)
            for alternative in group.alternatives
        )

    def _primary_branches(
        self,
        primary: SourcePrimary,
    ) -> tuple[BranchIr, ...]:
        if isinstance(primary, SourceGroup):
            return self._group_branches(primary)
        return (
            self._branch_ir(
                1,
                (ParseSymbol(primary, primary.span),),
                primary.span,
            ),
        )

    def _alternative_branch(
        self,
        alternative: SourceAlternative,
    ) -> BranchIr:
        operations = self._sequence(alternative.body)
        return self._branch_ir(
            alternative.index + 1,
            operations,
            alternative.span,
        )

    def _branch_ir(
        self,
        alternative: int,
        operations: tuple[Operation, ...],
        source_span: SourceSpan,
    ) -> BranchIr:
        return BranchIr(
            alternative,
            operations,
            self._result_index(operations),
            source_span,
        )

    def _result_index(
        self,
        operations: tuple[Operation, ...],
    ) -> int | None:
        if any(isinstance(item, ConstructNode) for item in operations):
            return None
        semantic_indices = tuple(
            index
            for index, operation in enumerate(operations)
            if _produces_transparent_value(operation)
        )
        if len(semantic_indices) > 1:
            raise ValueError(
                "alternative has multiple transparent semantic values"
            )
        return semantic_indices[0] if semantic_indices else None

    def _construct(
        self,
        span: SourceSpan,
        kind: LoweredConstructKind,
    ) -> LoweredConstruct:
        matches = tuple(
            construct
            for construct in self._lowering.constructs
            if construct.kind is kind and construct.source_span == span
        )
        if len(matches) != 1:
            raise ValueError(
                "lowering origin does not identify exactly one construct"
            )
        return matches[0]

    def _binding_origin(
        self,
        span: SourceSpan,
        kind: BindingOriginKind,
    ) -> BindingOrigin:
        matches = tuple(
            origin
            for origin in self._lowering.bindings
            if origin.kind is kind and origin.source_span == span
        )
        if len(matches) != 1:
            raise ValueError(
                "lowering origin does not identify exactly one binding"
            )
        return matches[0]

    def _decision(self, production: str) -> CanonicalDecision:
        return CanonicalDecision(
            production,
            tuple(
                row for row in self._rows if row.production == production
            ),
            self._matcher_definitions,
        )


def _produces_transparent_value(operation: Operation) -> bool:
    if isinstance(operation, (LeftFold, ReturnConstant)):
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


def _binding_origin_kind(mode: BindingMode) -> BindingOriginKind:
    if mode is BindingMode.APPEND:
        return BindingOriginKind.APPEND
    if mode is BindingMode.CONCAT:
        return BindingOriginKind.CONCAT
    if mode is BindingMode.INCREMENT:
        return BindingOriginKind.INCREMENT
    return BindingOriginKind.SCALAR
