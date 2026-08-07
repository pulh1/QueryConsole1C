from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .diagnostics import Diagnostic, DiagnosticBag, Severity
from .model import (
    Action,
    Constant,
    IdentifierRef,
    Lexeme,
    NonterminalCall,
    Terminal,
)
from .source_model import (
    SourceBinding,
    SourceConstantBinding,
    SourceConstructor,
    SourceAlternative,
    SourceGrammar,
    SourceGroup,
    SourceItem,
    SourceOptional,
    SourcePrimary,
    SourceRepeat,
    SourceSequence,
)


_SYNTHETIC_PREFIX = "__parsergen_ebnf__"


@dataclass(frozen=True, slots=True)
class SourceFacts:
    productive: bool
    nullable: bool
    min_consumed_tokens: int | None


@dataclass(frozen=True, slots=True)
class SourceValidationReport:
    diagnostics: tuple[Diagnostic, ...]
    production_facts: Mapping[str, SourceFacts]
    node_facts: Mapping[object, SourceFacts]


_NONPRODUCTIVE = SourceFacts(False, False, None)
_EPSILON = SourceFacts(True, True, 0)
_TOKEN = SourceFacts(True, False, 1)


def validate_source_grammar(grammar: SourceGrammar) -> SourceValidationReport:
    production_facts = _compute_production_facts(grammar)
    node_facts: dict[object, SourceFacts] = {}
    for production in grammar.productions:
        for alternative in production.alternatives:
            _record_alternative_facts(
                alternative,
                production_facts,
                node_facts,
            )

    bag = DiagnosticBag()
    for production in grammar.productions:
        if production.name.casefold().startswith(
            _SYNTHETIC_PREFIX.casefold()
        ):
            bag.add(
                Diagnostic(
                    "GR005",
                    Severity.ERROR,
                    "production name uses the reserved EBNF prefix",
                    production.span,
                )
            )
        for alternative in production.alternatives:
            _validate_sequence(
                alternative.body,
                production_facts,
                bag,
                inside_construct=False,
            )

    return SourceValidationReport(
        bag.sorted(),
        MappingProxyType(dict(production_facts)),
        MappingProxyType(node_facts),
    )


def _compute_production_facts(
    grammar: SourceGrammar,
) -> dict[str, SourceFacts]:
    facts = {
        production.name: _NONPRODUCTIVE
        for production in grammar.productions
    }
    while True:
        changed = False
        updated = dict(facts)
        for production in grammar.productions:
            computed = _choice_facts(
                tuple(
                    _sequence_facts(alternative.body, facts)
                    for alternative in production.alternatives
                )
            )
            if computed != facts[production.name]:
                updated[production.name] = computed
                changed = True
        facts = updated
        if not changed:
            return facts


def _record_alternative_facts(
    alternative: SourceAlternative,
    production_facts: Mapping[str, SourceFacts],
    node_facts: dict[object, SourceFacts],
) -> None:
    node_facts[alternative] = _sequence_facts(
        alternative.body,
        production_facts,
    )
    _record_sequence_facts(
        alternative.body,
        production_facts,
        node_facts,
    )


def _record_sequence_facts(
    sequence: SourceSequence,
    production_facts: Mapping[str, SourceFacts],
    node_facts: dict[object, SourceFacts],
) -> None:
    node_facts[sequence] = _sequence_facts(sequence, production_facts)
    for item in sequence.items:
        node_facts[item] = _item_facts(item, production_facts)
        if isinstance(item, SourceGroup):
            for alternative in item.alternatives:
                _record_alternative_facts(
                    alternative,
                    production_facts,
                    node_facts,
                )
        elif isinstance(item, (SourceRepeat, SourceOptional)):
            _record_primary_facts(
                item.body,
                production_facts,
                node_facts,
            )


def _record_primary_facts(
    primary: SourcePrimary,
    production_facts: Mapping[str, SourceFacts],
    node_facts: dict[object, SourceFacts],
) -> None:
    node_facts[primary] = _item_facts(primary, production_facts)
    if isinstance(primary, SourceGroup):
        for alternative in primary.alternatives:
            _record_alternative_facts(
                alternative,
                production_facts,
                node_facts,
            )


def _choice_facts(alternatives: tuple[SourceFacts, ...]) -> SourceFacts:
    productive = [item for item in alternatives if item.productive]
    if not productive:
        return _NONPRODUCTIVE
    return SourceFacts(
        True,
        any(item.nullable for item in productive),
        min(
            item.min_consumed_tokens
            for item in productive
            if item.min_consumed_tokens is not None
        ),
    )


def _sequence_facts(
    sequence: SourceSequence,
    production_facts: Mapping[str, SourceFacts],
) -> SourceFacts:
    item_facts = tuple(
        _item_facts(item, production_facts)
        for item in sequence.items
    )
    if any(not item.productive for item in item_facts):
        return _NONPRODUCTIVE
    return SourceFacts(
        True,
        all(item.nullable for item in item_facts),
        sum(item.min_consumed_tokens or 0 for item in item_facts),
    )


def _item_facts(
    item: SourceItem | SourcePrimary,
    production_facts: Mapping[str, SourceFacts],
) -> SourceFacts:
    if isinstance(item, (Terminal, Lexeme, Constant, IdentifierRef)):
        return _TOKEN
    if isinstance(item, NonterminalCall):
        # Resolution owns unknown-reference diagnostics. Treat an unresolved
        # call as consuming here so a derived progress error cannot mask the
        # primary resolver error once canonical lowering is available.
        return production_facts.get(item.name, _TOKEN)
    if isinstance(item, SourceBinding):
        return _item_facts(item.value, production_facts)
    if isinstance(item, (SourceConstructor, SourceConstantBinding)):
        return _EPSILON
    if isinstance(item, Action):
        return _EPSILON
    if isinstance(item, SourceGroup):
        return _choice_facts(
            tuple(
                _sequence_facts(alternative.body, production_facts)
                for alternative in item.alternatives
            )
        )
    if isinstance(item, SourceRepeat):
        if item.kind.value == "star":
            return _EPSILON
        return _item_facts(item.body, production_facts)
    if isinstance(item, SourceOptional):
        return _EPSILON
    raise TypeError(type(item))


def _validate_sequence(
    sequence: SourceSequence,
    production_facts: Mapping[str, SourceFacts],
    bag: DiagnosticBag,
    *,
    inside_construct: bool,
) -> None:
    for item in sequence.items:
        if isinstance(item, Action):
            if inside_construct:
                bag.add(
                    Diagnostic(
                        "EBNF204",
                        Severity.ERROR,
                        "arbitrary action inside an EBNF construct is unsupported",
                        item.span,
                    )
                )
            continue
        if isinstance(item, SourceBinding):
            _validate_sequence(
                SourceSequence((item.value,), item.value.span),
                production_facts,
                bag,
                inside_construct=inside_construct,
            )
            continue
        if isinstance(item, SourceGroup):
            _validate_group(
                item,
                production_facts,
                bag,
            )
            continue
        if isinstance(item, SourceRepeat):
            facts = _item_facts(item.body, production_facts)
            if not facts.productive:
                _add_body_error(
                    bag,
                    "EBNF200",
                    "repetition body is not productive",
                    item,
                )
            elif facts.nullable or (facts.min_consumed_tokens or 0) < 1:
                _add_body_error(
                    bag,
                    "EBNF201",
                    "repetition body does not guarantee input consumption",
                    item,
                )
            _validate_primary(item.body, production_facts, bag)
            continue
        if isinstance(item, SourceOptional):
            facts = _item_facts(item.body, production_facts)
            if not facts.productive:
                _add_body_error(
                    bag,
                    "EBNF200",
                    "optional body is not productive",
                    item,
                )
            elif facts.nullable:
                _add_body_error(
                    bag,
                    "EBNF202",
                    "optional body is already nullable",
                    item,
                )
            _validate_primary(item.body, production_facts, bag)


def _validate_group(
    group: SourceGroup,
    production_facts: Mapping[str, SourceFacts],
    bag: DiagnosticBag,
) -> None:
    for alternative in group.alternatives:
        _validate_sequence(
            alternative.body,
            production_facts,
            bag,
            inside_construct=True,
        )


def _validate_primary(
    primary: SourcePrimary,
    production_facts: Mapping[str, SourceFacts],
    bag: DiagnosticBag,
) -> None:
    if isinstance(primary, SourceGroup):
        _validate_group(primary, production_facts, bag)


def _add_body_error(
    bag: DiagnosticBag,
    code: str,
    message: str,
    item: SourceRepeat | SourceOptional,
) -> None:
    bag.add(
        Diagnostic(
            code,
            Severity.ERROR,
            message,
            item.operator_span,
        )
    )
