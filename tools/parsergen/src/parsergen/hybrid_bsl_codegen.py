from __future__ import annotations

from collections.abc import Collection, Mapping

from .analysis import AnalysisResult
from .canonical_bsl_codegen import (
    generate_canonical_functions,
    generate_canonical_parser,
)
from .generated_parser import GeneratedParser, empty_select_table
from .lowering import LoweringResult
from .model import Grammar
from .parser_ir import ParserIr
from .resolver import ResolvedGrammar
from .source_model import SourceGrammar


_SYNTHETIC_PREFIX = "__parsergen_ebnf__"
_LEGACY_ABI = ("Родитель", "ЛевыйЭлемент")
_LEGACY_CALL_PREFIX = ("Неопределено", "Неопределено")
_CANONICAL_ERROR = "ВызватьИсключениеCanonicalСинтаксическаяОшибка"
_CANONICAL_SUPPORT = """Функция ТипТокенаПросмотра(Смещение)
	Индекс = БуферТокенов.ИндексТекущегоЭлемента + Смещение;
	Если Индекс < 0 Или Индекс >= БуферТокенов.Токены.Количество() Тогда
		Возврат Неопределено;
	КонецЕсли;
	Токен = БуферТокенов.Токены[Индекс];
	Если Токен = Неопределено Тогда
		Возврат Неопределено;
	КонецЕсли;
	Возврат Токен.Тип;
КонецФункции

Процедура ВызватьИсключениеCanonicalСинтаксическаяОшибка(Ожидаемое)
	Если ТекущийТокен = Неопределено Или ТипТокенаПросмотра(0) = Неопределено Тогда
		ВызватьИсключение "Синтаксическая ошибка. Ожидается " + Ожидаемое;
	Иначе
		ВызватьИсключение "Синтаксическая ошибка. Неожиданный токен " + ТекущийТокен.Лексема;
	КонецЕсли;
КонецПроцедуры"""


def generate_hybrid_parser(
    source: SourceGrammar,
    lowering: LoweringResult,
    grammar: Grammar,
    resolved: ResolvedGrammar,
    analysis: AnalysisResult,
    parser_ir: ParserIr,
    *,
    canonical_productions: Collection[str],
    entrypoints: Mapping[str, str],
) -> GeneratedParser:
    canonical_names = _canonical_names(canonical_productions)
    ir_names = tuple(production.name for production in parser_ir.productions)
    ir_name_set = frozenset(ir_names)
    if tuple(
        name for name in canonical_names if name in ir_name_set
    ) != ir_names:
        raise ValueError(
            "canonical production ownership does not match Parser IR"
        )
    removed_canonical = frozenset(canonical_names).difference(ir_name_set)
    if lowering.grammar != grammar:
        raise ValueError("lowering does not match hybrid grammar")

    source_names = frozenset(
        production.name for production in source.productions
    )
    full_canonical_ownership = (
        frozenset(canonical_names) == source_names
    )

    owned_synthetic = _owned_synthetic_productions(
        lowering,
        frozenset(canonical_names),
    )
    all_synthetic = frozenset(
        production.name
        for production in grammar.productions
        if production.name.casefold().startswith(_SYNTHETIC_PREFIX.casefold())
    )
    legacy_synthetic = all_synthetic.difference(owned_synthetic)
    if legacy_synthetic:
        formatted = ", ".join(sorted(legacy_synthetic))
        raise ValueError(
            "legacy island owns synthetic CFG production: " + formatted
        )

    if full_canonical_ownership:
        canonical = generate_canonical_parser(
            source,
            parser_ir,
            entrypoints,
        )
        return GeneratedParser(
            canonical.module_text,
            empty_select_table(analysis.k),
            canonical.identifier_table,
            canonical.constructor_names,
        )

    canonical = generate_canonical_functions(
        source,
        parser_ir,
        abi_parameters=_LEGACY_ABI,
        call_argument_prefix=_LEGACY_CALL_PREFIX,
    )
    overrides = _split_function_fragment(
        canonical.module_fragment.replace(
            "ВызватьИсключениеСинтаксическаяОшибка",
            _CANONICAL_ERROR,
        ),
        ir_names,
    )
    legacy_productions = frozenset(
        production.name
        for production in source.productions
        if production.name not in frozenset(canonical_names)
    )
    from .bsl_codegen import BslGenerator

    return BslGenerator(
        grammar,
        resolved,
        analysis,
        entrypoints,
        function_overrides=overrides,
        omitted_productions=owned_synthetic.union(removed_canonical),
        support_fragment=_CANONICAL_SUPPORT,
        matcher_productions=legacy_productions,
        additional_constructor_names=canonical.constructor_names,
        allow_synthetic_cfg=True,
    ).generate()


def _canonical_names(productions: Collection[str]) -> tuple[str, ...]:
    values = tuple(productions)
    if not values:
        raise ValueError("canonical production ownership must not be empty")
    if len(frozenset(values)) != len(values):
        raise ValueError("duplicate canonical production ownership")
    return values


def _owned_synthetic_productions(
    lowering: LoweringResult,
    canonical_names: frozenset[str],
) -> frozenset[str]:
    result: set[str] = set()
    for construct in lowering.constructs:
        if construct.source_production not in canonical_names:
            continue
        result.add(construct.production)
        if construct.tail_production is not None:
            result.add(construct.tail_production)
    for recursion in lowering.left_recursions:
        if recursion.production in canonical_names:
            result.add(recursion.tail_production)
    return frozenset(result)


def _split_function_fragment(
    fragment: str,
    production_names: tuple[str, ...],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in production_names:
        marker = f"Функция НеТерминал{name}("
        start = fragment.find(marker)
        if start < 0:
            raise ValueError(
                f"canonical function fragment is missing production {name!r}"
            )
        end = fragment.find("КонецФункции", start)
        if end < 0:
            raise ValueError(
                f"canonical function fragment is incomplete for {name!r}"
            )
        end += len("КонецФункции")
        result[name] = fragment[start:end]
    return result
