from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .binding_validation import validate_bindings
from .diagnostics import (
    Diagnostic,
    DiagnosticBag,
    RelatedLocation,
    Severity,
    SourcePosition,
    SourceSpan,
)
from .separated_model import (
    SemanticAlternative,
    SemanticAnchorBinding,
    SemanticBindingResult,
    SemanticProfile,
    SemanticScopedAppend,
    SyntaxAnchor,
    SyntaxGrammar,
)
from .source_model import (
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
    SourceScopedValue,
    SourceSequence,
    SourceValue,
)
from .scoped_append_validation import validate_scoped_appends
from .source_validation import validate_source_grammar


@dataclass(frozen=True, slots=True)
class _ResolvedAlternative:
    semantic: SemanticAlternative
    production: SourceProduction
    path: tuple[int, ...]
    source: SourceAlternative
    declaration_span: SourceSpan


def bind_semantic_profile(
    syntax: SyntaxGrammar,
    profile: SemanticProfile,
) -> SemanticBindingResult:
    bag = DiagnosticBag()
    productions = {
        production.name: production
        for production in syntax.source_grammar.productions
    }
    alternatives = _index_alternatives(syntax.source_grammar)
    named_alternatives = {
        (alternative.production, alternative.name): alternative
        for alternative in syntax.alternatives
    }
    names_by_path = {
        (alternative.production, alternative.path): alternative.name
        for alternative in syntax.alternatives
    }
    declaration_spans = {
        key: alternative.span
        for key, alternative in alternatives.items()
    }
    declaration_spans.update(
        {
            (alternative.production, alternative.path): alternative.span
            for alternative in syntax.alternatives
        }
    )
    anchors_by_production: dict[str, list[SyntaxAnchor]] = {}
    for anchor in syntax.anchors:
        anchors_by_production.setdefault(anchor.address.production, []).append(anchor)

    resolved: list[_ResolvedAlternative] = []
    resolved_by_selector: dict[tuple[str, tuple[int, ...]], _ResolvedAlternative] = {}
    bindings_by_production: dict[
        str,
        dict[tuple[int, ...], SemanticAnchorBinding],
    ] = {}
    scoped_by_production: dict[
        str,
        dict[tuple[int, ...], list[SemanticScopedAppend]],
    ] = {}
    current_fields_by_path: dict[
        tuple[str, tuple[int, ...]],
        tuple[SemanticScopedAppend, ...],
    ] = {}

    for semantic in profile.alternatives:
        production = productions.get(semantic.production)
        if production is None:
            _add_error(
                bag,
                "SPB200",
                "semantic profile references an unknown production",
                semantic.span,
                tuple(
                    RelatedLocation(
                        "available syntax production is declared here",
                        item.span,
                    )
                    for item in syntax.source_grammar.productions
                ),
            )
            continue

        selected_path = _resolve_alternative_path(
            semantic,
            production,
            named_alternatives,
            declaration_spans,
            bag,
        )
        if selected_path is None:
            continue
        source_alternative = alternatives.get((production.name, selected_path))
        if source_alternative is None:
            _add_error(
                bag,
                "SPB201",
                "semantic profile references an unknown alternative",
                semantic.span,
                (
                    RelatedLocation(
                        "syntax production is declared here",
                        production.span,
                    ),
                ),
            )
            continue

        declaration_span = declaration_spans[(production.name, selected_path)]
        selector = (production.name, selected_path)
        previous = resolved_by_selector.get(selector)
        if previous is not None:
            _add_error(
                bag,
                "SPB205",
                "semantic profile selector is duplicated",
                semantic.span,
                (
                    RelatedLocation(
                        "syntax alternative is declared here",
                        declaration_span,
                    ),
                    RelatedLocation(
                        "first profile selector is declared here",
                        previous.semantic.span,
                    ),
                ),
            )
            continue

        target = _ResolvedAlternative(
            semantic,
            production,
            selected_path,
            source_alternative,
            declaration_span,
        )
        resolved.append(target)
        resolved_by_selector[selector] = target
        production_bindings = bindings_by_production.setdefault(
            production.name,
            {},
        )
        _resolve_anchor_bindings(
            target,
            anchors_by_production.get(production.name, []),
            production_bindings,
            bag,
        )
        scoped = tuple(
            item
            for item in profile.scoped_appends
            if (item.production, item.alternative)
            == (semantic.production, semantic.alternative)
        )
        production_scoped = scoped_by_production.setdefault(
            production.name,
            {},
        )
        _resolve_scoped_appends(
            target,
            scoped,
            anchors_by_production.get(production.name, []),
            production_scoped,
            bag,
        )
        current_fields_by_path[(production.name, selected_path)] = tuple(
            item for item in scoped if item.current_field is not None
        )

    diagnostics = bag.sorted()
    if any(item.severity is Severity.ERROR for item in diagnostics):
        return SemanticBindingResult(None, diagnostics)

    semantic_by_path = {
        (item.production.name, item.path): item.semantic
        for item in resolved
    }
    bound = _rewrite_grammar(
        syntax.source_grammar,
        names_by_path,
        bindings_by_production,
        scoped_by_production,
        semantic_by_path,
        current_fields_by_path,
    )
    validation_diagnostics = (
        *validate_source_grammar(bound).diagnostics,
        *validate_bindings(bound).diagnostics,
        *validate_scoped_appends(bound).diagnostics,
    )
    if validation_diagnostics:
        converted = tuple(
            _convert_validation_diagnostic(diagnostic, profile, resolved)
            for diagnostic in validation_diagnostics
        )
        return SemanticBindingResult(
            None,
            tuple(sorted(converted, key=Diagnostic.sort_key)),
        )
    return SemanticBindingResult(bound, ())


def _resolve_alternative_path(
    semantic: SemanticAlternative,
    production: SourceProduction,
    named_alternatives,
    declaration_spans: Mapping[tuple[str, tuple[int, ...]], SourceSpan],
    bag: DiagnosticBag,
) -> tuple[int, ...] | None:
    if semantic.alternative is not None:
        named = named_alternatives.get(
            (semantic.production, semantic.alternative)
        )
        if named is not None:
            return named.path
        available = tuple(
            RelatedLocation(
                "available syntax alternative is declared here",
                span,
            )
            for (name, path), span in declaration_spans.items()
            if name == production.name
            and len(path) > 0
        )
        _add_error(
            bag,
            "SPB201",
            "semantic profile references an unknown alternative",
            semantic.span,
            available
            or (
                RelatedLocation(
                    "syntax production is declared here",
                    production.span,
                ),
            ),
        )
        return None

    if len(production.alternatives) != 1:
        related = tuple(
            RelatedLocation(
                "syntax alternative is declared here",
                declaration_spans[(production.name, (alternative.index,))],
            )
            for alternative in production.alternatives
        )
        _add_error(
            bag,
            "SPB202",
            "unnamed alternative selector is ambiguous",
            semantic.span,
            related,
        )
        return None
    return (production.alternatives[0].index,)


def _resolve_anchor_bindings(
    target: _ResolvedAlternative,
    production_anchors: list[SyntaxAnchor],
    bindings_by_path: dict[tuple[int, ...], SemanticAnchorBinding],
    bag: DiagnosticBag,
) -> None:
    for binding in target.semantic.anchor_bindings:
        matching_name = [
            anchor
            for anchor in production_anchors
            if anchor.name == binding.anchor
        ]
        in_scope = [
            anchor
            for anchor in matching_name
            if anchor.address.path[:-1] == target.path
        ]
        if not in_scope:
            if matching_name:
                _add_error(
                    bag,
                    "SPB204",
                    "semantic profile anchor is outside the selected alternative",
                    binding.span,
                    (
                        *(
                            RelatedLocation(
                                "syntax anchor is declared here",
                                anchor.span,
                            )
                            for anchor in matching_name
                        ),
                        RelatedLocation(
                            "selected syntax alternative is declared here",
                            target.declaration_span,
                        ),
                    ),
                )
            else:
                _add_error(
                    bag,
                    "SPB203",
                    "semantic profile references a missing anchor",
                    binding.span,
                    (
                        RelatedLocation(
                            "selected syntax alternative is declared here",
                            target.declaration_span,
                        ),
                    ),
                )
            continue

        anchor = in_scope[0]
        previous = bindings_by_path.get(anchor.address.path)
        if previous is None:
            bindings_by_path[anchor.address.path] = binding
            continue
        if (previous.property, previous.mode) == (binding.property, binding.mode):
            continue
        _add_error(
            bag,
            "SPB206",
            "semantic profile reuses an anchor incompatibly",
            binding.span,
            (
                RelatedLocation(
                    "syntax anchor is declared here",
                    anchor.span,
                ),
                RelatedLocation(
                    "first semantic binding is declared here",
                    previous.span,
                ),
            ),
        )


def _resolve_scoped_appends(
    target: _ResolvedAlternative,
    scoped_appends: tuple[SemanticScopedAppend, ...],
    production_anchors: list[SyntaxAnchor],
    scoped_by_path: dict[tuple[int, ...], list[SemanticScopedAppend]],
    bag: DiagnosticBag,
) -> None:
    for scoped in scoped_appends:
        if scoped.anchor is None:
            continue
        matching_name = [
            anchor
            for anchor in production_anchors
            if anchor.name == scoped.anchor
        ]
        in_scope = [
            anchor
            for anchor in matching_name
            if anchor.address.path[:-1] == target.path
        ]
        if not in_scope:
            code = "SPB204" if matching_name else "SPB203"
            message = (
                "semantic profile anchor is outside the selected alternative"
                if matching_name
                else "semantic profile references a missing anchor"
            )
            related = tuple(
                RelatedLocation(
                    "syntax anchor is declared here",
                    anchor.span,
                )
                for anchor in matching_name
            )
            _add_error(
                bag,
                code,
                message,
                scoped.span,
                (
                    *related,
                    RelatedLocation(
                        "selected syntax alternative is declared here",
                        target.declaration_span,
                    ),
                ),
            )
            continue
        scoped_by_path.setdefault(
            in_scope[0].address.path,
            [],
        ).append(scoped)


def _rewrite_grammar(
    grammar: SourceGrammar,
    names_by_path: Mapping[tuple[str, tuple[int, ...]], str],
    bindings_by_production: Mapping[
        str,
        Mapping[tuple[int, ...], SemanticAnchorBinding],
    ],
    scoped_by_production: Mapping[
        str,
        Mapping[tuple[int, ...], list[SemanticScopedAppend]],
    ],
    semantic_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        SemanticAlternative,
    ],
    current_fields_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        tuple[SemanticScopedAppend, ...],
    ],
) -> SourceGrammar:
    productions: list[SourceProduction] = []
    for production in grammar.productions:
        bindings = bindings_by_production.get(production.name, {})
        scoped = scoped_by_production.get(production.name, {})
        alternatives: list[SourceAlternative] = []
        for alternative in production.alternatives:
            path = (alternative.index,)
            bound = _bind_sequence(
                alternative.body,
                production=production.name,
                alternative_name=names_by_path.get((production.name, path)),
                path=path,
                bindings_by_path=bindings,
                scoped_by_path=scoped,
            )
            decorated = _decorate_sequence(
                bound,
                production=production.name,
                path=path,
                semantic_by_path=semantic_by_path,
                current_fields_by_path=current_fields_by_path,
            )
            alternatives.append(
                SourceAlternative(
                    alternative.index,
                    decorated,
                    alternative.span,
                )
            )
        productions.append(
            SourceProduction(
                production.name,
                production.parameters,
                tuple(alternatives),
                production.order,
                production.span,
            )
        )
    return SourceGrammar(
        tuple(productions),
        grammar.identifier_definitions,
        grammar.path,
    )


def _bind_sequence(
    sequence: SourceSequence,
    *,
    production: str,
    alternative_name: str | None,
    path: tuple[int, ...],
    bindings_by_path: Mapping[tuple[int, ...], SemanticAnchorBinding],
    scoped_by_path: Mapping[
        tuple[int, ...],
        list[SemanticScopedAppend],
    ],
) -> SourceSequence:
    """Return a new sequence; never mutate syntax.source_grammar."""
    items: list[SourceItem] = []
    for index, item in enumerate(sequence.items):
        item_path = (*path, index)
        value = _bind_value(
            item,
            production=production,
            alternative_name=alternative_name,
            path=item_path,
            bindings_by_path=bindings_by_path,
            scoped_by_path=scoped_by_path,
        )
        for scoped in scoped_by_path.get(item_path, ()):
            value = SourceScopedValue(
                scoped.owner,
                scoped.property,
                value,
                None,
                scoped.span,
            )
        binding = bindings_by_path.get(item_path)
        if binding is not None:
            value = SourceBinding(
                binding.property,
                binding.mode,
                value,
                binding.span,
                binding.operator_span,
            )
        items.append(value)
    return SourceSequence(tuple(items), sequence.span)


def _bind_value(
    value: SourceValue,
    *,
    production: str,
    alternative_name: str | None,
    path: tuple[int, ...],
    bindings_by_path: Mapping[tuple[int, ...], SemanticAnchorBinding],
    scoped_by_path: Mapping[
        tuple[int, ...],
        list[SemanticScopedAppend],
    ],
) -> SourceValue:
    if isinstance(value, SourceGroup):
        alternatives = tuple(
            SourceAlternative(
                alternative.index,
                _bind_sequence(
                    alternative.body,
                    production=production,
                    alternative_name=alternative_name,
                    path=(*path, alternative.index),
                    bindings_by_path=bindings_by_path,
                    scoped_by_path=scoped_by_path,
                ),
                alternative.span,
            )
            for alternative in value.alternatives
        )
        return SourceGroup(alternatives, value.span)
    if isinstance(value, SourceRepeat):
        return SourceRepeat(
            _bind_primary(
                value.body,
                production=production,
                alternative_name=alternative_name,
                path=path,
                bindings_by_path=bindings_by_path,
                scoped_by_path=scoped_by_path,
            ),
            value.kind,
            value.span,
            value.operator_span,
        )
    if isinstance(value, SourceOptional):
        return SourceOptional(
            _bind_primary(
                value.body,
                production=production,
                alternative_name=alternative_name,
                path=path,
                bindings_by_path=bindings_by_path,
                scoped_by_path=scoped_by_path,
            ),
            value.span,
            value.operator_span,
        )
    return value


def _bind_primary(
    primary: SourcePrimary,
    *,
    production: str,
    alternative_name: str | None,
    path: tuple[int, ...],
    bindings_by_path: Mapping[tuple[int, ...], SemanticAnchorBinding],
    scoped_by_path: Mapping[
        tuple[int, ...],
        list[SemanticScopedAppend],
    ],
) -> SourcePrimary:
    if not isinstance(primary, SourceGroup):
        return primary
    return _bind_value(
        primary,
        production=production,
        alternative_name=alternative_name,
        path=path,
        bindings_by_path=bindings_by_path,
        scoped_by_path=scoped_by_path,
    )


def _decorate_sequence(
    sequence: SourceSequence,
    *,
    production: str,
    path: tuple[int, ...],
    semantic_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        SemanticAlternative,
    ],
    current_fields_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        tuple[SemanticScopedAppend, ...],
    ],
) -> SourceSequence:
    items = tuple(
        _decorate_item(
            item,
            production=production,
            path=(*path, index),
            semantic_by_path=semantic_by_path,
            current_fields_by_path=current_fields_by_path,
        )
        for index, item in enumerate(sequence.items)
    )
    semantic = semantic_by_path.get((production, path))
    if semantic is None:
        return SourceSequence(items, sequence.span)
    prefix: tuple[SourceItem, ...] = ()
    if semantic.constructor is not None:
        prefix = (
            SourceConstructor(
                semantic.constructor,
                semantic.constructor_span or semantic.span,
            ),
        )
    constants: tuple[SourceItem, ...] = tuple(
        SourceConstantBinding(
            constant.property,
            constant.value,
            constant.span,
            constant.operator_span,
        )
        for constant in semantic.constants
    )
    current_fields: tuple[SourceItem, ...] = tuple(
        SourceScopedValue(
            scoped.owner,
            scoped.property,
            None,
            scoped.current_field,
            scoped.span,
        )
        for scoped in current_fields_by_path.get((production, path), ())
    )
    suffix = tuple(
        sorted(
            (*constants, *current_fields),
            key=lambda item: item.span.start.offset,
        )
    )
    return SourceSequence((*prefix, *items, *suffix), sequence.span)


def _decorate_item(
    item: SourceItem,
    *,
    production: str,
    path: tuple[int, ...],
    semantic_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        SemanticAlternative,
    ],
    current_fields_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        tuple[SemanticScopedAppend, ...],
    ],
) -> SourceItem:
    if isinstance(item, SourceBinding):
        return SourceBinding(
            item.property,
            item.mode,
            _decorate_value(
                item.value,
                production=production,
                path=path,
                semantic_by_path=semantic_by_path,
                current_fields_by_path=current_fields_by_path,
            ),
            item.span,
            item.operator_span,
        )
    if isinstance(
        item,
        (SourceGroup, SourceRepeat, SourceOptional, SourceScopedValue),
    ):
        return _decorate_value(
            item,
            production=production,
            path=path,
            semantic_by_path=semantic_by_path,
            current_fields_by_path=current_fields_by_path,
        )
    return item


def _decorate_value(
    value: SourceValue,
    *,
    production: str,
    path: tuple[int, ...],
    semantic_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        SemanticAlternative,
    ],
    current_fields_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        tuple[SemanticScopedAppend, ...],
    ],
) -> SourceValue:
    if isinstance(value, SourceScopedValue):
        return SourceScopedValue(
            value.owner,
            value.property,
            (
                _decorate_value(
                    value.value,
                    production=production,
                    path=path,
                    semantic_by_path=semantic_by_path,
                    current_fields_by_path=current_fields_by_path,
                )
                if value.value is not None
                else None
            ),
            value.current_field,
            value.span,
        )
    if isinstance(value, SourceGroup):
        alternatives = tuple(
            SourceAlternative(
                alternative.index,
                _decorate_sequence(
                    alternative.body,
                    production=production,
                    path=(*path, alternative.index),
                    semantic_by_path=semantic_by_path,
                    current_fields_by_path=current_fields_by_path,
                ),
                alternative.span,
            )
            for alternative in value.alternatives
        )
        return SourceGroup(alternatives, value.span)
    if isinstance(value, SourceRepeat):
        return SourceRepeat(
            _decorate_primary(
                value.body,
                production=production,
                path=path,
                semantic_by_path=semantic_by_path,
                current_fields_by_path=current_fields_by_path,
            ),
            value.kind,
            value.span,
            value.operator_span,
        )
    if isinstance(value, SourceOptional):
        return SourceOptional(
            _decorate_primary(
                value.body,
                production=production,
                path=path,
                semantic_by_path=semantic_by_path,
                current_fields_by_path=current_fields_by_path,
            ),
            value.span,
            value.operator_span,
        )
    return value


def _decorate_primary(
    primary: SourcePrimary,
    *,
    production: str,
    path: tuple[int, ...],
    semantic_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        SemanticAlternative,
    ],
    current_fields_by_path: Mapping[
        tuple[str, tuple[int, ...]],
        tuple[SemanticScopedAppend, ...],
    ],
) -> SourcePrimary:
    if not isinstance(primary, SourceGroup):
        return primary
    return _decorate_value(
        primary,
        production=production,
        path=path,
        semantic_by_path=semantic_by_path,
        current_fields_by_path=current_fields_by_path,
    )


def _index_alternatives(
    grammar: SourceGrammar,
) -> dict[tuple[str, tuple[int, ...]], SourceAlternative]:
    result: dict[tuple[str, tuple[int, ...]], SourceAlternative] = {}
    for production in grammar.productions:
        for alternative in production.alternatives:
            path = (alternative.index,)
            result[(production.name, path)] = alternative
            _index_sequence_alternatives(
                production.name,
                path,
                alternative.body,
                result,
            )
    return result


def _index_sequence_alternatives(
    production: str,
    path: tuple[int, ...],
    sequence: SourceSequence,
    result: dict[tuple[str, tuple[int, ...]], SourceAlternative],
) -> None:
    for index, item in enumerate(sequence.items):
        item_path = (*path, index)
        group = _item_group(item)
        if group is None:
            continue
        for alternative in group.alternatives:
            alternative_path = (*item_path, alternative.index)
            result[(production, alternative_path)] = alternative
            _index_sequence_alternatives(
                production,
                alternative_path,
                alternative.body,
                result,
            )


def _item_group(item: SourceItem) -> SourceGroup | None:
    if isinstance(item, SourceGroup):
        return item
    if isinstance(item, (SourceRepeat, SourceOptional)) and isinstance(
        item.body,
        SourceGroup,
    ):
        return item.body
    return None


def _convert_validation_diagnostic(
    diagnostic: Diagnostic,
    profile: SemanticProfile,
    resolved: list[_ResolvedAlternative],
) -> Diagnostic:
    semantic_provenance = _has_semantic_provenance(
        diagnostic.span,
        profile,
    )
    target = _validation_target(
        diagnostic.span,
        resolved,
        semantic_provenance=semantic_provenance,
    )
    if semantic_provenance:
        primary = diagnostic.span
    elif target is not None:
        primary = target.semantic.span
    elif profile.alternatives:
        primary = profile.alternatives[0].span
    else:
        position = SourcePosition(1, 1, 0)
        primary = SourceSpan(profile.path, position, position)

    related = [
        RelatedLocation(
            f"{diagnostic.code}: {diagnostic.message}",
            diagnostic.span,
        )
    ]
    if target is not None and diagnostic.span is not target.declaration_span:
        related.append(
            RelatedLocation(
                "selected syntax alternative is declared here",
                target.declaration_span,
            )
        )
    return Diagnostic(
        "SPB207",
        Severity.ERROR,
        "bound grammar failed semantic validation",
        primary,
        tuple(related),
        {"original_code": diagnostic.code},
    )


def _validation_target(
    span: SourceSpan,
    resolved: list[_ResolvedAlternative],
    *,
    semantic_provenance: bool,
) -> _ResolvedAlternative | None:
    if not resolved:
        return None
    if semantic_provenance:
        matches = [
            item
            for item in resolved
            if item.semantic.span.path == span.path
            and item.semantic.span.start.offset <= span.start.offset
            <= item.semantic.span.end.offset
        ]
    else:
        matches = [
            item
            for item in resolved
            if item.source.span.path == span.path
            and item.source.span.start.offset <= span.start.offset
            <= item.source.span.end.offset
        ]
    if matches:
        return min(
            matches,
            key=lambda item: item.source.span.end.offset
            - item.source.span.start.offset,
        )
    if span.path == resolved[0].production.span.path:
        preceding = [
            item
            for item in resolved
            if item.production.span.path == span.path
            and item.production.span.start.offset <= span.start.offset
        ]
        if preceding:
            production_start = max(
                item.production.span.start.offset
                for item in preceding
            )
            return next(
                item
                for item in preceding
                if item.production.span.start.offset == production_start
            )
    return resolved[0]


def _has_semantic_provenance(
    span: SourceSpan,
    profile: SemanticProfile,
) -> bool:
    for alternative in profile.alternatives:
        if span is alternative.span or span is alternative.constructor_span:
            return True
        for binding in alternative.anchor_bindings:
            if span is binding.span or span is binding.operator_span:
                return True
        for constant in alternative.constants:
            if span is constant.span or span is constant.operator_span:
                return True
    for scoped in profile.scoped_appends:
        if span is scoped.span or span is scoped.operator_span:
            return True
    return False


def _add_error(
    bag: DiagnosticBag,
    code: str,
    message: str,
    span: SourceSpan,
    related: tuple[RelatedLocation, ...] = (),
) -> None:
    bag.add(Diagnostic(code, Severity.ERROR, message, span, related))
