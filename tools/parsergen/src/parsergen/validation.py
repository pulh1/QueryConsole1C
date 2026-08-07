from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .analysis import AnalysisResult, find_select_conflicts
from .diagnostics import (
    Diagnostic,
    DiagnosticBag,
    RelatedLocation,
    Severity,
    SourcePosition,
    SourceSpan,
)
from .lowering import LoweredConstruct, LoweringResult
from .model import Grammar, IdentifierDefinition, IdentifierRef, NonterminalCall
from .resolver import (
    ResolvedAlternative,
    ResolvedGrammar,
    ResolvedNonterminal,
)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    diagnostics: tuple[Diagnostic, ...]

    @property
    def has_errors(self) -> bool:
        return any(
            item.severity is Severity.ERROR
            for item in self.diagnostics
        )


@dataclass(frozen=True, slots=True)
class _GraphEdge:
    target: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class _Cycle:
    path: tuple[str, ...]
    edges: tuple[_GraphEdge, ...]


def validate_grammar(
    grammar: Grammar,
    resolved: ResolvedGrammar | None,
    analysis: AnalysisResult | None,
    entrypoints: Mapping[str, str],
    prior_diagnostics: Iterable[Diagnostic] = (),
    *,
    lowering: LoweringResult | None = None,
) -> ValidationReport:
    return _Validator(
        grammar,
        resolved,
        analysis,
        entrypoints,
        prior_diagnostics,
        lowering,
    ).run()


class _Validator:
    def __init__(
        self,
        grammar: Grammar,
        resolved: ResolvedGrammar | None,
        analysis: AnalysisResult | None,
        entrypoints: Mapping[str, str],
        prior_diagnostics: Iterable[Diagnostic],
        lowering: LoweringResult | None,
    ) -> None:
        self.grammar = grammar
        self.resolved = resolved
        self.analysis = analysis
        self.entrypoints = entrypoints
        self.lowering = lowering
        self.bag = DiagnosticBag(prior_diagnostics)
        self.productions = {
            production.name: production
            for production in grammar.productions
        }
        self.production_order = {
            production.name: position
            for position, production in enumerate(grammar.productions)
        }

    def run(self) -> ValidationReport:
        if not self.grammar.productions:
            self.bag.add(
                self._diagnostic(
                    "VAL100",
                    Severity.ERROR,
                    "grammar has no productions",
                    self._fallback_span(),
                )
            )

        for entrypoint, production_name in sorted(
            self.entrypoints.items(),
            key=lambda item: (item[0], item[1]),
        ):
            if production_name in self.productions:
                continue
            self.bag.add(
                self._diagnostic(
                    "VAL101",
                    Severity.ERROR,
                    "entry point refers to a missing production",
                    self._fallback_span(),
                    details={
                        "entrypoint": entrypoint,
                        "production": production_name,
                    },
                )
            )

        reachable = self._reachable_productions()
        self._report_unreachable(reachable)
        self._report_unused_identifiers()

        productive = self._productive_productions()
        nonproductive = set(self.productions) - productive
        self._report_nonproductive(nonproductive)

        nullable = self._nullable_productions()
        zero_graph = self._zero_consumption_graph(nullable)
        zero_components = self._cyclic_components(zero_graph)
        self._report_cycles(
            "VAL201",
            "nullable productions form a zero-consumption cycle",
            zero_graph,
            zero_components,
        )

        left_graph = self._left_corner_graph(nullable)
        left_components = self._cyclic_components(left_graph)
        self._report_cycles(
            "VAL202",
            "left recursion is not supported",
            left_graph,
            left_components,
        )

        (
            invalid_empty_select_alternatives,
            invalid_conflict_alternatives,
        ) = self._invalid_lookahead_alternatives(
            productive,
            nullable,
            left_components,
        )
        self._report_lookahead(
            reachable,
            invalid_empty_select_alternatives,
            invalid_conflict_alternatives,
            nullable,
        )
        return ValidationReport(self.bag.sorted())

    def _fallback_span(self) -> SourceSpan:
        if self.grammar.productions:
            return self.grammar.productions[0].span
        if self.grammar.identifier_definitions:
            return self.grammar.identifier_definitions[0].span
        position = SourcePosition(1, 1, 0)
        return SourceSpan(
            self.grammar.path,
            position,
            position,
        )

    def _reachable_productions(self) -> set[str]:
        starts: list[str] = []
        seen_starts: set[str] = set()
        for production_name in self.entrypoints.values():
            if (
                production_name in self.productions
                and production_name not in seen_starts
            ):
                starts.append(production_name)
                seen_starts.add(production_name)
        if not starts and self.grammar.productions:
            starts.append(self.grammar.productions[0].name)

        reachable: set[str] = set()
        queue = deque(starts)
        while queue:
            name = queue.popleft()
            if name in reachable:
                continue
            reachable.add(name)
            production = self.productions[name]
            for alternative in production.alternatives:
                for symbol in alternative.syntax_symbols:
                    if (
                        isinstance(symbol, NonterminalCall)
                        and symbol.name in self.productions
                        and symbol.name not in reachable
                    ):
                        queue.append(symbol.name)
        return reachable

    def _report_unreachable(self, reachable: set[str]) -> None:
        for production in self.grammar.productions:
            if production.name in reachable:
                continue
            if self._lowered_construct(production.name) is not None:
                continue
            self.bag.add(
                self._diagnostic(
                    "VAL102",
                    Severity.WARNING,
                    "production is unreachable from every entry point",
                    production.span,
                    details={"production": production.name},
                )
            )

    def _report_unused_identifiers(self) -> None:
        references = {
            symbol.name
            for production in self.grammar.productions
            for alternative in production.alternatives
            for symbol in alternative.syntax_symbols
            if isinstance(symbol, IdentifierRef)
        }
        definitions_by_name: dict[str, list[IdentifierDefinition]] = {}
        for definition in self.grammar.identifier_definitions:
            definitions_by_name.setdefault(definition.name, []).append(definition)

        for name, definitions in definitions_by_name.items():
            first = definitions[0]
            token_types = {
                definition.token_types
                for definition in definitions
            }
            if (
                name in references
                or not first.token_types
                or len(token_types) != 1
            ):
                continue
            self.bag.add(
                self._diagnostic(
                    "VAL103",
                    Severity.WARNING,
                    "identifier class is never referenced",
                    first.span,
                    details={"identifier": name},
                )
            )

    def _productive_productions(self) -> set[str]:
        productive: set[str] = set()
        changed = True
        while changed:
            changed = False
            for production in self.grammar.productions:
                if production.name in productive:
                    continue
                if any(
                    self._alternative_productive(
                        alternative.syntax_symbols,
                        productive,
                    )
                    for alternative in production.alternatives
                ):
                    productive.add(production.name)
                    changed = True
        return productive

    def _alternative_productive(
        self,
        symbols: tuple[object, ...],
        productive: set[str],
    ) -> bool:
        return all(
            not isinstance(symbol, NonterminalCall)
            or symbol.name not in self.productions
            or symbol.name in productive
            for symbol in symbols
        )

    def _report_nonproductive(self, nonproductive: set[str]) -> None:
        if not nonproductive:
            return
        graph = self._dependency_graph(nonproductive)
        components = self._tarjan(graph)
        component_index = {
            name: index
            for index, component in enumerate(components)
            for name in component
        }
        sink_indexes = {
            index
            for index, component in enumerate(components)
            if not any(
                component_index[edge.target] != index
                for owner in component
                for edge in graph[owner]
            )
        }
        reverse: dict[str, list[str]] = {
            name: []
            for name in nonproductive
        }
        for owner, edges in graph.items():
            for edge in edges:
                reverse[edge.target].append(owner)

        for index, component in enumerate(components):
            if index not in sink_indexes:
                continue
            affected = set(component)
            queue = deque(component)
            while queue:
                name = queue.popleft()
                for parent in reverse[name]:
                    if parent not in affected:
                        affected.add(parent)
                        queue.append(parent)
            ordered = tuple(
                sorted(affected, key=self.production_order.__getitem__)
            )
            primary_name = min(
                component,
                key=self.production_order.__getitem__,
            )
            source_names = tuple(
                dict.fromkeys(
                    self._source_production_name(name)
                    for name in ordered
                )
            )
            primary_source_name = self._source_production_name(primary_name)
            related = tuple(
                RelatedLocation(
                    "this production is also nonproductive",
                    self.productions[name].span,
                )
                for name in source_names
                if name != primary_source_name
                if name in self.productions
            )
            self.bag.add(
                self._diagnostic(
                    "VAL200",
                    Severity.ERROR,
                    "production cannot derive a finite token sequence",
                    (
                        self.productions[primary_source_name].span
                        if primary_source_name in self.productions
                        else self.productions[primary_name].span
                    ),
                    related=related,
                    details={"productions": source_names},
                )
            )

    def _nullable_productions(self) -> set[str]:
        nullable: set[str] = set()
        changed = True
        while changed:
            changed = False
            for production in self.grammar.productions:
                if production.name in nullable:
                    continue
                if any(
                    all(
                        isinstance(symbol, NonterminalCall)
                        and symbol.name in nullable
                        for symbol in alternative.syntax_symbols
                    )
                    for alternative in production.alternatives
                ):
                    nullable.add(production.name)
                    changed = True
        return nullable

    def _dependency_graph(
        self,
        included: set[str] | None = None,
    ) -> dict[str, tuple[_GraphEdge, ...]]:
        graph: dict[str, tuple[_GraphEdge, ...]] = {}
        for production in self.grammar.productions:
            if included is not None and production.name not in included:
                continue
            edges: list[_GraphEdge] = []
            seen: set[str] = set()
            for alternative in production.alternatives:
                for symbol in alternative.syntax_symbols:
                    if not isinstance(symbol, NonterminalCall):
                        continue
                    if symbol.name not in self.productions:
                        continue
                    if included is not None and symbol.name not in included:
                        continue
                    if symbol.name not in seen:
                        edges.append(_GraphEdge(symbol.name, symbol.span))
                        seen.add(symbol.name)
            graph[production.name] = tuple(edges)
        return graph

    def _zero_consumption_graph(
        self,
        nullable: set[str],
    ) -> dict[str, tuple[_GraphEdge, ...]]:
        prefix_graph = self._prefix_call_graph(nullable)
        return {
            owner: tuple(
                edge
                for edge in prefix_graph[owner]
                if edge.target in nullable
            )
            for owner in prefix_graph
            if owner in nullable
        }

    def _left_corner_graph(
        self,
        nullable: set[str],
    ) -> dict[str, tuple[_GraphEdge, ...]]:
        return self._prefix_call_graph(nullable)

    def _prefix_call_graph(
        self,
        nullable: set[str],
    ) -> dict[str, tuple[_GraphEdge, ...]]:
        graph: dict[str, tuple[_GraphEdge, ...]] = {}
        for production in self.grammar.productions:
            edges: list[_GraphEdge] = []
            seen: set[str] = set()
            for alternative in production.alternatives:
                for symbol in alternative.syntax_symbols:
                    if not isinstance(symbol, NonterminalCall):
                        break
                    if (
                        symbol.name in self.productions
                        and symbol.name not in seen
                    ):
                        edges.append(_GraphEdge(symbol.name, symbol.span))
                        seen.add(symbol.name)
                    if symbol.name not in nullable:
                        break
            graph[production.name] = tuple(edges)
        return graph

    def _cyclic_components(
        self,
        graph: Mapping[str, tuple[_GraphEdge, ...]],
    ) -> tuple[tuple[str, ...], ...]:
        return tuple(
            component
            for component in self._tarjan(graph)
            if (
                len(component) > 1
                or any(
                    edge.target == component[0]
                    for edge in graph[component[0]]
                )
            )
        )

    def _tarjan(
        self,
        graph: Mapping[str, tuple[_GraphEdge, ...]],
    ) -> tuple[tuple[str, ...], ...]:
        next_index = 0
        indexes: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        components: list[tuple[str, ...]] = []

        def visit(name: str) -> None:
            nonlocal next_index
            indexes[name] = next_index
            lowlinks[name] = next_index
            next_index += 1
            stack.append(name)
            on_stack.add(name)

            for edge in graph[name]:
                target = edge.target
                if target not in indexes:
                    visit(target)
                    lowlinks[name] = min(
                        lowlinks[name],
                        lowlinks[target],
                    )
                elif target in on_stack:
                    lowlinks[name] = min(
                        lowlinks[name],
                        indexes[target],
                    )

            if lowlinks[name] != indexes[name]:
                return
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == name:
                    break
            components.append(
                tuple(
                    sorted(
                        component,
                        key=self.production_order.__getitem__,
                    )
                )
            )

        for production in self.grammar.productions:
            if production.name in graph and production.name not in indexes:
                visit(production.name)
        return tuple(
            sorted(
                components,
                key=lambda component: min(
                    self.production_order[name]
                    for name in component
                ),
            )
        )

    def _report_cycles(
        self,
        code: str,
        message: str,
        graph: Mapping[str, tuple[_GraphEdge, ...]],
        components: tuple[tuple[str, ...], ...],
    ) -> None:
        for component in components:
            cycle = self._shortest_cycle(graph, component)
            start = cycle.path[0]
            related = [
                RelatedLocation(
                    "cycle starts in this production",
                    self.productions[start].span,
                )
            ]
            related.extend(
                RelatedLocation(
                    "cycle continues through this call",
                    edge.span,
                )
                for edge in cycle.edges[1:]
            )
            self.bag.add(
                self._diagnostic(
                    code,
                    Severity.ERROR,
                    message,
                    cycle.edges[0].span,
                    related=tuple(related),
                    details={
                        "path": self._source_cycle_path(cycle.path)
                    },
                )
            )

    def _source_cycle_path(
        self,
        path: tuple[str, ...],
    ) -> tuple[str, ...]:
        collapsed: list[str] = []
        for name in path:
            source_name = self._source_production_name(name)
            if not collapsed or collapsed[-1] != source_name:
                collapsed.append(source_name)
        if not collapsed:
            return ()
        if len(collapsed) == 1:
            collapsed.append(collapsed[0])
        elif collapsed[-1] != collapsed[0]:
            collapsed.append(collapsed[0])
        return tuple(collapsed)

    def _shortest_cycle(
        self,
        graph: Mapping[str, tuple[_GraphEdge, ...]],
        component: tuple[str, ...],
    ) -> _Cycle:
        members = set(component)
        candidates: list[tuple[tuple[object, ...], _Cycle]] = []
        for start in component:
            queue = deque(
                [(start, (start,), (), frozenset({start}))]
            )
            found: _Cycle | None = None
            while queue and found is None:
                owner, node_path, edge_path, visited = queue.popleft()
                for edge in graph[owner]:
                    if edge.target not in members:
                        continue
                    if edge.target == start:
                        found = _Cycle(
                            (*node_path, start),
                            (*edge_path, edge),
                        )
                        break
                    if edge.target in visited:
                        continue
                    queue.append(
                        (
                            edge.target,
                            (*node_path, edge.target),
                            (*edge_path, edge),
                            visited | {edge.target},
                        )
                    )
            if found is None:
                continue
            key: tuple[object, ...] = (
                len(found.edges),
                tuple(
                    edge.span.start.offset
                    for edge in found.edges
                ),
                tuple(
                    self.production_order[name]
                    for name in found.path[:-1]
                ),
            )
            candidates.append((key, found))
        return min(candidates, key=lambda item: item[0])[1]

    def _report_lookahead(
        self,
        reachable: set[str],
        invalid_empty_select_alternatives: set[tuple[str, int]],
        invalid_conflict_alternatives: set[tuple[str, int]],
        nullable: set[str],
    ) -> None:
        if self.resolved is None or self.analysis is None:
            return

        for production_name in self.resolved.production_order:
            if production_name not in reachable:
                continue
            alternatives = self.resolved.productions[production_name]
            for number, alternative in enumerate(alternatives, start=1):
                if (
                    production_name,
                    number,
                ) in invalid_empty_select_alternatives:
                    continue
                key = (production_name, number)
                compressed = self.analysis._compressed
                if (
                    compressed.select_nonempty(key)
                    if compressed is not None
                    else bool(self.analysis.select.get(key))
                ):
                    continue
                self.bag.add(
                    self._diagnostic(
                        "LLK200",
                        Severity.ERROR,
                        "reachable alternative has an empty SELECT set",
                        alternative.source.span,
                        details={
                            "production": self._source_production_name(
                                production_name
                            ),
                            "alternative": number,
                            "k": self.analysis.k,
                        },
                    )
                )

            epsilon_alternatives = tuple(
                alternative
                for number, alternative in enumerate(alternatives, start=1)
                if (
                    production_name,
                    number,
                ) not in invalid_conflict_alternatives
                if self._resolved_alternative_nullable(
                    alternative,
                    nullable,
                )
            )
            if len(epsilon_alternatives) > 1:
                first, *others = epsilon_alternatives
                construct = self._lowered_construct(production_name)
                self.bag.add(
                    self._diagnostic(
                        "LLK201",
                        Severity.ERROR,
                        "production has multiple epsilon alternatives",
                        (
                            construct.source_span
                            if construct is not None
                            else first.source.span
                        ),
                        related=(
                            tuple(
                                RelatedLocation(
                                    "nullable source alternative",
                                    self._source_alternative_span(
                                        production_name,
                                        alternative.index,
                                        alternative.source.span,
                                    ),
                                )
                                for alternative in epsilon_alternatives
                            )
                            if construct is not None
                            else tuple(
                                RelatedLocation(
                                    "another epsilon alternative",
                                    alternative.source.span,
                                )
                                for alternative in others
                            )
                        ),
                        details={
                            "production": self._source_production_name(
                                production_name
                            ),
                            "alternatives": tuple(
                                alternative.index + 1
                                for alternative in epsilon_alternatives
                            ),
                        },
                    )
                )

        for conflict in find_select_conflicts(
            self.resolved,
            self.analysis,
        ):
            if (
                conflict.production not in reachable
                or (
                    conflict.production,
                    conflict.left_alternative,
                ) in invalid_conflict_alternatives
                or (
                    conflict.production,
                    conflict.right_alternative,
                ) in invalid_conflict_alternatives
            ):
                continue
            alternatives = self.resolved.productions[conflict.production]
            left = alternatives[conflict.left_alternative - 1]
            right = alternatives[conflict.right_alternative - 1]
            construct = self._lowered_construct(conflict.production)
            self.bag.add(
                self._diagnostic(
                    "LLK202",
                    Severity.ERROR,
                    "alternatives have overlapping SELECT sets",
                    (
                        construct.source_span
                        if construct is not None
                        else left.source.span
                    ),
                    related=(
                        (
                            RelatedLocation(
                                "first conflicting source alternative",
                                self._source_alternative_span(
                                    conflict.production,
                                    conflict.left_alternative - 1,
                                    left.source.span,
                                ),
                            ),
                            RelatedLocation(
                                "second conflicting source alternative",
                                self._source_alternative_span(
                                    conflict.production,
                                    conflict.right_alternative - 1,
                                    right.source.span,
                                ),
                            ),
                        )
                        if construct is not None
                        else (
                            RelatedLocation(
                                "conflicting alternative",
                                right.source.span,
                            ),
                        )
                    ),
                    details={
                        "witness": conflict.witness,
                        "k": self.analysis.k,
                    },
                )
            )

    def _lowered_construct(
        self,
        production: str,
    ) -> LoweredConstruct | None:
        if self.lowering is None:
            return None
        return next(
            (
                construct
                for construct in self.lowering.constructs
                if production
                in (construct.production, construct.tail_production)
            ),
            None,
        )

    def _source_production_name(self, production: str) -> str:
        construct = self._lowered_construct(production)
        return (
            construct.source_production
            if construct is not None
            else production
        )

    def _source_alternative_span(
        self,
        production: str,
        alternative: int,
        fallback: SourceSpan,
    ) -> SourceSpan:
        if self.lowering is None:
            return fallback
        return self.lowering.alternative_origins.get(
            (production, alternative),
            fallback,
        )

    def _invalid_lookahead_alternatives(
        self,
        productive: set[str],
        nullable: set[str],
        left_components: tuple[tuple[str, ...], ...],
    ) -> tuple[
        set[tuple[str, int]],
        set[tuple[str, int]],
    ]:
        component_by_name = {
            name: frozenset(component)
            for component in left_components
            for name in component
        }
        left_recursive: set[tuple[str, int]] = set()
        unproductive: set[tuple[str, int]] = set()
        nonproductive_owners: set[tuple[str, int]] = set()
        for production in self.grammar.productions:
            component = component_by_name.get(production.name)
            for number, alternative in enumerate(
                production.alternatives,
                start=1,
            ):
                key = (production.name, number)
                if not self._alternative_productive(
                    alternative.syntax_symbols,
                    productive,
                ):
                    unproductive.add(key)
                if production.name not in productive:
                    nonproductive_owners.add(key)
                if component is None:
                    continue
                for symbol in alternative.syntax_symbols:
                    if not isinstance(symbol, NonterminalCall):
                        break
                    if symbol.name in component:
                        left_recursive.add(key)
                        break
                    if symbol.name not in nullable:
                        break
        return (
            left_recursive | nonproductive_owners,
            left_recursive | unproductive,
        )

    def _resolved_alternative_nullable(
        self,
        alternative: ResolvedAlternative,
        nullable: set[str],
    ) -> bool:
        return all(
            isinstance(symbol, ResolvedNonterminal)
            and symbol.name in nullable
            for symbol in alternative.symbols
        )

    def _diagnostic(
        self,
        code: str,
        severity: Severity,
        message: str,
        span: SourceSpan,
        *,
        related: tuple[RelatedLocation, ...] = (),
        details: Mapping[str, object] | None = None,
    ) -> Diagnostic:
        return Diagnostic(
            code,
            severity,
            message,
            span,
            related,
            MappingProxyType(dict(details or {})),
        )
