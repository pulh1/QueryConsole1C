from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from .binding_validation import validate_bindings
from .diagnostics import Diagnostic, DiagnosticBag, SourceSpan
from .model import (
    Action,
    Alternative,
    Grammar,
    NonterminalCall,
    Production,
    SyntaxSymbol,
)
from .left_recursion import DirectLeftRecursion
from .source_model import (
    BindingMode,
    QuantifierKind,
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
from .source_validation import validate_source_grammar


_SYNTHETIC_PREFIX = "__parsergen_ebnf__"


def _binding_origin_kind(mode: BindingMode) -> BindingOriginKind:
    if mode is BindingMode.APPEND:
        return BindingOriginKind.APPEND
    if mode is BindingMode.EXTEND:
        return BindingOriginKind.EXTEND
    if mode is BindingMode.CONCAT:
        return BindingOriginKind.CONCAT
    if mode is BindingMode.INCREMENT:
        return BindingOriginKind.INCREMENT
    if mode is BindingMode.DISCARD:
        return BindingOriginKind.DISCARD
    if mode is BindingMode.WRAP:
        return BindingOriginKind.WRAP
    return BindingOriginKind.SCALAR


class LoweredConstructKind(StrEnum):
    GROUP = "group"
    STAR = "star"
    PLUS = "plus"
    OPTIONAL = "optional"


class BindingOriginKind(StrEnum):
    CONSTRUCTOR = "constructor"
    SCALAR = "scalar"
    APPEND = "append"
    EXTEND = "extend"
    CONCAT = "concat"
    INCREMENT = "increment"
    DISCARD = "discard"
    WRAP = "wrap"
    CONSTANT = "constant"


@dataclass(frozen=True, slots=True)
class BindingOrigin:
    kind: BindingOriginKind
    property: str | None
    value: str | None
    path: str
    source_span: SourceSpan
    source_production: str
    source_alternative: int


@dataclass(frozen=True, slots=True)
class LoweredConstruct:
    kind: LoweredConstructKind
    production: str
    tail_production: str | None
    source_span: SourceSpan
    operator_span: SourceSpan
    source_production: str
    source_alternative: int


@dataclass(frozen=True, slots=True)
class LoweredLeftRecursion:
    production: str
    tail_production: str
    base_alternatives: tuple[int, ...]
    recursive_alternatives: tuple[int, ...]
    source_span: SourceSpan


@dataclass(frozen=True, slots=True)
class LoweringResult:
    grammar: Grammar
    constructs: tuple[LoweredConstruct, ...]
    production_origins: Mapping[str, SourceSpan]
    alternative_origins: Mapping[tuple[str, int], SourceSpan]
    diagnostics: tuple[Diagnostic, ...] = ()
    bindings: tuple[BindingOrigin, ...] = ()
    left_recursions: tuple[LoweredLeftRecursion, ...] = ()


def lower_source_grammar(grammar: SourceGrammar) -> LoweringResult:
    source_validation = validate_source_grammar(grammar)
    diagnostics = DiagnosticBag(source_validation.diagnostics)
    diagnostics.extend(validate_bindings(grammar).diagnostics)
    left_recursions = (
        {}
        if any(
            item.code.startswith("LR")
            for item in source_validation.diagnostics
        )
        else source_validation.left_recursions
    )
    return _Lowerer(
        grammar,
        diagnostics,
        left_recursions,
    ).lower()


class _Lowerer:
    def __init__(
        self,
        grammar: SourceGrammar,
        diagnostics: DiagnosticBag,
        left_recursions: Mapping[str, DirectLeftRecursion],
    ) -> None:
        self._source = grammar
        self._diagnostics = diagnostics.sorted()
        self._synthetic: list[Production] = []
        self._constructs: list[LoweredConstruct] = []
        self._production_origins: dict[str, SourceSpan] = {}
        self._alternative_origins: dict[tuple[str, int], SourceSpan] = {}
        self._bindings: list[BindingOrigin] = []
        self._source_left_recursions = left_recursions
        self._left_recursions: list[LoweredLeftRecursion] = []

    def lower(self) -> LoweringResult:
        public: list[Production] = []
        for production in self._source.productions:
            left_recursion = self._source_left_recursions.get(
                production.name
            )
            if left_recursion is not None:
                public.append(
                    self._lower_left_recursive_production(
                        production,
                        left_recursion,
                    )
                )
                continue
            alternatives: list[Alternative] = []
            for alternative in production.alternatives:
                elements = self._lower_sequence(
                    alternative.body,
                    production,
                    alternative.index,
                    f"p{production.order}_a{alternative.index}",
                )
                alternatives.append(
                    Alternative(
                        alternative.index,
                        elements,
                        alternative.span,
                    )
                )
                self._alternative_origins[
                    (production.name, alternative.index)
                ] = alternative.span
            public.append(
                Production(
                    production.name,
                    production.parameters,
                    tuple(alternatives),
                    production.order,
                    production.span,
                )
            )
            self._production_origins[production.name] = production.span

        return LoweringResult(
            Grammar(
                (*public, *self._synthetic),
                self._source.identifier_definitions,
                self._source.path,
            ),
            tuple(self._constructs),
            MappingProxyType(dict(self._production_origins)),
            MappingProxyType(dict(self._alternative_origins)),
            self._diagnostics,
            tuple(self._bindings),
            tuple(self._left_recursions),
        )

    def _lower_left_recursive_production(
        self,
        production: SourceProduction,
        recursion: DirectLeftRecursion,
    ) -> Production:
        lowered_by_source: dict[int, tuple[SyntaxSymbol | Action, ...]] = {}
        for alternative in production.alternatives:
            lowered_by_source[alternative.index] = self._lower_sequence(
                alternative.body,
                production,
                alternative.index,
                f"p{production.order}_a{alternative.index}",
            )

        tail_name = (
            f"{_SYNTHETIC_PREFIX}p{production.order}_left_fold_tail"
        )
        public_alternatives: list[Alternative] = []
        for index, source_index in enumerate(recursion.base_alternatives):
            source = production.alternatives[source_index]
            public_alternatives.append(
                Alternative(
                    index,
                    (
                        *lowered_by_source[source_index],
                        _synthetic_call(
                            tail_name,
                            production.parameters,
                            source.span,
                        ),
                    ),
                    source.span,
                )
            )
            self._alternative_origins[(production.name, index)] = source.span

        tail_alternatives: list[Alternative] = []
        for index, recursive in enumerate(recursion.recursive_alternatives):
            source = production.alternatives[recursive.alternative]
            elements = lowered_by_source[recursive.alternative]
            if (
                not elements
                or not isinstance(elements[0], NonterminalCall)
                or elements[0].name != production.name
            ):
                raise ValueError(
                    "direct-LR lowering lost the classified self-call"
                )
            tail_alternatives.append(
                Alternative(
                    index,
                    (
                        *elements[1:],
                        _synthetic_call(
                            tail_name,
                            production.parameters,
                            source.span,
                        ),
                    ),
                    source.span,
                )
            )
            self._alternative_origins[(tail_name, index)] = source.span
        exit_index = len(tail_alternatives)
        tail_alternatives.append(
            Alternative(exit_index, (), production.span)
        )
        self._alternative_origins[(tail_name, exit_index)] = production.span
        self._add_synthetic(
            tail_name,
            production.parameters,
            tuple(tail_alternatives),
            production.span,
        )
        self._left_recursions.append(
            LoweredLeftRecursion(
                production.name,
                tail_name,
                recursion.base_alternatives,
                tuple(
                    item.alternative
                    for item in recursion.recursive_alternatives
                ),
                production.span,
            )
        )
        self._production_origins[production.name] = production.span
        return Production(
            production.name,
            production.parameters,
            tuple(public_alternatives),
            production.order,
            production.span,
        )

    def _lower_sequence(
        self,
        sequence: SourceSequence,
        owner: SourceProduction,
        source_alternative: int,
        path: str,
    ) -> tuple[SyntaxSymbol | Action, ...]:
        production = owner
        result: list[SyntaxSymbol | Action] = []
        for index, item in enumerate(sequence.items):
            item_path = f"{path}_n{index}"
            if isinstance(item, SourceConstructor):
                self._bindings.append(
                    BindingOrigin(
                        BindingOriginKind.CONSTRUCTOR,
                        None,
                        item.name,
                        item_path,
                        item.span,
                        production.name,
                        source_alternative,
                    )
                )
                continue
            if isinstance(item, SourceConstantBinding):
                self._bindings.append(
                    BindingOrigin(
                        BindingOriginKind.CONSTANT,
                        item.property,
                        item.value,
                        item_path,
                        item.span,
                        production.name,
                        source_alternative,
                    )
                )
                continue
            if isinstance(item, SourceBinding):
                self._bindings.append(
                    BindingOrigin(
                        _binding_origin_kind(item.mode),
                        item.property,
                        None,
                        item_path,
                        item.span,
                        production.name,
                        source_alternative,
                    )
                )
                item = item.value
            if isinstance(item, SourceGroup):
                result.append(
                    self._lower_group(
                        item,
                        production,
                        source_alternative,
                        item_path,
                    )
                )
            elif isinstance(item, SourceRepeat):
                result.append(
                    self._lower_repeat(
                        item,
                        production,
                        source_alternative,
                        item_path,
                    )
                )
            elif isinstance(item, SourceOptional):
                result.append(
                    self._lower_optional(
                        item,
                        production,
                        source_alternative,
                        item_path,
                    )
                )
            else:
                result.append(item)
        return tuple(result)

    def _lower_group(
        self,
        group: SourceGroup,
        owner: SourceProduction,
        source_alternative: int,
        path: str,
    ) -> NonterminalCall:
        production = owner
        name = f"{_SYNTHETIC_PREFIX}{path}_group"
        bodies = self._lower_body_alternatives(
            group,
            production,
            source_alternative,
            path,
        )
        alternatives = tuple(
            Alternative(index, elements, origin)
            for index, (elements, origin) in enumerate(bodies)
        )
        self._add_synthetic(name, production.parameters, alternatives, group.span)
        self._record_alternative_origins(name, bodies)
        self._constructs.append(
            LoweredConstruct(
                LoweredConstructKind.GROUP,
                name,
                None,
                group.span,
                group.span,
                production.name,
                source_alternative,
            )
        )
        return _synthetic_call(name, production.parameters, group.span)

    def _lower_repeat(
        self,
        repeat: SourceRepeat,
        owner: SourceProduction,
        source_alternative: int,
        path: str,
    ) -> NonterminalCall:
        production = owner
        kind = (
            LoweredConstructKind.STAR
            if repeat.kind is QuantifierKind.ZERO_OR_MORE
            else LoweredConstructKind.PLUS
        )
        suffix = kind.value
        name = f"{_SYNTHETIC_PREFIX}{path}_{suffix}"
        bodies = self._lower_body_alternatives(
            repeat.body,
            production,
            source_alternative,
            path,
        )
        tail_name: str | None = None
        if kind is LoweredConstructKind.STAR:
            recursive = tuple(
                Alternative(
                    index,
                    (
                        *elements,
                        _synthetic_call(
                            name,
                            production.parameters,
                            repeat.operator_span,
                        ),
                    ),
                    origin,
                )
                for index, (elements, origin) in enumerate(bodies)
            )
            alternatives = (
                *recursive,
                Alternative(len(recursive), (), repeat.operator_span),
            )
            self._add_synthetic(
                name,
                production.parameters,
                alternatives,
                repeat.span,
            )
            self._record_alternative_origins(name, bodies)
            self._alternative_origins[(name, len(recursive))] = (
                repeat.operator_span
            )
        else:
            tail_name = f"{name}_tail"
            head_alternatives = tuple(
                Alternative(
                    index,
                    (
                        *elements,
                        _synthetic_call(
                            tail_name,
                            production.parameters,
                            repeat.operator_span,
                        ),
                    ),
                    origin,
                )
                for index, (elements, origin) in enumerate(bodies)
            )
            tail_recursive = tuple(
                Alternative(
                    index,
                    (
                        *elements,
                        _synthetic_call(
                            tail_name,
                            production.parameters,
                            repeat.operator_span,
                        ),
                    ),
                    origin,
                )
                for index, (elements, origin) in enumerate(bodies)
            )
            tail_alternatives = (
                *tail_recursive,
                Alternative(
                    len(tail_recursive),
                    (),
                    repeat.operator_span,
                ),
            )
            self._add_synthetic(
                name,
                production.parameters,
                head_alternatives,
                repeat.span,
            )
            self._add_synthetic(
                tail_name,
                production.parameters,
                tail_alternatives,
                repeat.span,
            )
            self._record_alternative_origins(name, bodies)
            self._record_alternative_origins(tail_name, bodies)
            self._alternative_origins[
                (tail_name, len(tail_recursive))
            ] = repeat.operator_span

        self._constructs.append(
            LoweredConstruct(
                kind,
                name,
                tail_name,
                repeat.span,
                repeat.operator_span,
                production.name,
                source_alternative,
            )
        )
        return _synthetic_call(name, production.parameters, repeat.span)

    def _lower_optional(
        self,
        optional: SourceOptional,
        owner: SourceProduction,
        source_alternative: int,
        path: str,
    ) -> NonterminalCall:
        production = owner
        name = f"{_SYNTHETIC_PREFIX}{path}_optional"
        bodies = self._lower_body_alternatives(
            optional.body,
            production,
            source_alternative,
            path,
        )
        alternatives = tuple(
            Alternative(index, elements, origin)
            for index, (elements, origin) in enumerate(bodies)
        )
        alternatives = (
            *alternatives,
            Alternative(len(alternatives), (), optional.operator_span),
        )
        self._add_synthetic(
            name,
            production.parameters,
            alternatives,
            optional.span,
        )
        self._record_alternative_origins(name, bodies)
        self._alternative_origins[(name, len(bodies))] = (
            optional.operator_span
        )
        self._constructs.append(
            LoweredConstruct(
                LoweredConstructKind.OPTIONAL,
                name,
                None,
                optional.span,
                optional.operator_span,
                production.name,
                source_alternative,
            )
        )
        return _synthetic_call(name, production.parameters, optional.span)

    def _lower_body_alternatives(
        self,
        body: SourcePrimary,
        owner: SourceProduction,
        source_alternative: int,
        path: str,
    ) -> tuple[tuple[tuple[SyntaxSymbol | Action, ...], SourceSpan], ...]:
        production = owner
        if isinstance(body, SourceGroup):
            return tuple(
                (
                    self._lower_sequence(
                        alternative.body,
                        production,
                        source_alternative,
                        f"{path}_g{alternative.index}",
                    ),
                    alternative.span,
                )
                for alternative in body.alternatives
            )
        return (((body,), body.span),)

    def _add_synthetic(
        self,
        name: str,
        parameters: tuple[str, ...],
        alternatives: tuple[Alternative, ...],
        span: SourceSpan,
    ) -> None:
        order = len(self._source.productions) + len(self._synthetic)
        self._synthetic.append(
            Production(name, parameters, alternatives, order, span)
        )
        self._production_origins[name] = span

    def _record_alternative_origins(
        self,
        production: str,
        bodies: tuple[
            tuple[tuple[SyntaxSymbol | Action, ...], SourceSpan],
            ...,
        ],
    ) -> None:
        for index, (_, origin) in enumerate(bodies):
            self._alternative_origins[(production, index)] = origin


def _synthetic_call(
    name: str,
    parameters: tuple[str, ...],
    span: SourceSpan,
) -> NonterminalCall:
    return NonterminalCall(name, parameters, span)
