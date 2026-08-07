from __future__ import annotations

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
    LoweredConstruct,
    LoweredConstructKind,
    LoweringResult,
    lower_source_grammar,
)
from .model import Action, SyntaxSymbol
from .resolver import ResolvedGrammar, resolve_grammar
from .source_model import (
    SourceAlternative,
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
class BranchIr:
    alternative: int
    operations: tuple[Operation, ...]
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
    source_span: SourceSpan


Operation = ParseSymbol | Dispatch | RepeatLoop | OptionalBranch


@dataclass(frozen=True, slots=True)
class AlternativeIr:
    index: int
    operations: tuple[Operation, ...]
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


def build_parser_ir(
    source: SourceGrammar,
    lowering: LoweringResult,
    resolved: ResolvedGrammar,
    analysis: AnalysisResult,
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
    conflicts = find_canonical_select_conflicts(resolved, analysis)
    if conflicts:
        raise ValueError("overlapping canonical SELECT prevents Parser IR")
    artifact = build_canonical_decision_artifact(analysis)
    return _ParserIrBuilder(
        source,
        lowering,
        artifact.rows,
        artifact.matcher_definitions,
        analysis.k,
    ).build()


class _ParserIrBuilder:
    def __init__(
        self,
        source: SourceGrammar,
        lowering: LoweringResult,
        rows: tuple[CanonicalDecisionRow, ...],
        matcher_definitions: tuple[MatcherDefinition, ...],
        lookahead: int,
    ) -> None:
        self._source = source
        self._lowering = lowering
        self._rows = rows
        self._matcher_definitions = matcher_definitions
        self._lookahead = lookahead

    def build(self) -> ParserIr:
        productions = tuple(
            self._production(production)
            for production in self._source.productions
        )
        return ParserIr(
            productions,
            self._matcher_definitions,
            self._lookahead,
        )

    def _production(self, production: SourceProduction) -> ProductionIr:
        alternatives = tuple(
            AlternativeIr(
                alternative.index,
                self._sequence(alternative.body),
                alternative.span,
            )
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

    def _sequence(self, sequence: SourceSequence) -> tuple[Operation, ...]:
        result: list[Operation] = []
        for item in sequence.items:
            if isinstance(item, Action):
                raise ValueError(
                    "arbitrary source actions require declarative bindings"
                )
            if isinstance(item, SourceGroup):
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
                        item.span,
                    )
                )
            else:
                result.append(ParseSymbol(item, item.span))
        return tuple(result)

    def _repeat(self, repeat: SourceRepeat) -> tuple[Operation, ...]:
        kind = (
            LoweredConstructKind.STAR
            if repeat.kind.value == "star"
            else LoweredConstructKind.PLUS
        )
        construct = self._construct(repeat.span, kind)
        branches = self._primary_branches(repeat.body)
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
            BranchIr(
                1,
                (ParseSymbol(primary, primary.span),),
                primary.span,
            ),
        )

    def _alternative_branch(
        self,
        alternative: SourceAlternative,
    ) -> BranchIr:
        return BranchIr(
            alternative.index + 1,
            self._sequence(alternative.body),
            alternative.span,
        )

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

    def _decision(self, production: str) -> CanonicalDecision:
        return CanonicalDecision(
            production,
            tuple(
                row for row in self._rows if row.production == production
            ),
            self._matcher_definitions,
        )
