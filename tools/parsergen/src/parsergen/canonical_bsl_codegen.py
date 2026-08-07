from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
import re

from .bsl_rendering import (
    bsl_string,
    normalize_newlines,
    validate_bsl_identifier,
)
from .canonical_bsl_conditions import CanonicalConditionRenderer
from .model import (
    Constant,
    IdentifierRef,
    Lexeme,
    NonterminalCall,
    SyntaxSymbol,
    Terminal,
)
from .parser_ir import AlternativeIr, ParseSymbol, ParserIr, ProductionIr
from .source_model import SourceGrammar
from .value_table_codec import ColumnKind, ValueColumn, ValueTable


_ENTRYPOINTS_MARKER = "// <parsergen:entrypoints>"
_ENTRY_RESULTS_MARKER = "// <parsergen:entry-results>"
_PRODUCTIONS_MARKER = "// <parsergen:productions>"
_LOOKAHEAD_MARKER = "{{LOOKAHEAD}}"
_END_TOKEN = "$"
_BSL_DECLARATION = re.compile(
    r"^(?:Функция|Процедура)\s+"
    r"([A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*)\s*\(",
    re.MULTILINE | re.IGNORECASE,
)
_TEMPORARY = re.compile(r"Значение[1-9][0-9]*\Z", re.IGNORECASE)
_GENERATED_LOCALS = frozenset(
    item.casefold()
    for item in ("РезультатПродукции", "ЭтотУзел")
)


@dataclass(frozen=True, slots=True)
class CanonicalGeneratedParser:
    module_text: str
    identifier_table: ValueTable
    constructor_names: tuple[str, ...]


def generate_canonical_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> CanonicalGeneratedParser:
    return _CanonicalBslGenerator(source, parser_ir, entrypoints).generate()


class _CanonicalBslGenerator:
    def __init__(
        self,
        source: SourceGrammar,
        parser_ir: ParserIr,
        entrypoints: Mapping[str, str],
    ) -> None:
        self._source = source
        self._ir = parser_ir
        self._entrypoints = entrypoints
        self._conditions = CanonicalConditionRenderer(
            parser_ir.matcher_definitions
        )
        self._temporary = 0

    def generate(self) -> CanonicalGeneratedParser:
        self._validate_inputs()
        module = _substitute_template(
            _load_template(),
            self._render_entrypoints(),
            self._render_entry_results(),
            self._render_productions(),
            self._ir.lookahead,
        )
        return CanonicalGeneratedParser(
            module,
            _identifier_table(self._source),
            (),
        )

    def _validate_inputs(self) -> None:
        if self._source != self._ir.source_grammar:
            raise ValueError("source grammar does not match Parser IR")
        if self._ir.lookahead < 1:
            raise ValueError("Parser IR lookahead must be at least 1")
        if not self._entrypoints:
            raise ValueError("entrypoint mapping must not be empty")
        production_names = {
            production.name
            for production in self._ir.productions
        }
        for definition in self._source.identifier_definitions:
            if (
                definition.name == _END_TOKEN
                or _END_TOKEN in definition.token_types
            ):
                raise ValueError("reserved END token '$' cannot be generated")
        for entrypoint, production in self._entrypoints.items():
            validate_bsl_identifier(entrypoint, "entrypoint")
            if production not in production_names:
                raise ValueError(
                    f"entrypoint {entrypoint!r} references unknown "
                    f"production {production!r}"
                )
        for production in self._ir.productions:
            validate_bsl_identifier(
                f"НеТерминал{production.name}",
                "generated production function",
            )
            self._validate_parameters(production)
            if production.decision is not None:
                self._validate_decision(production.decision)
        self._validate_generated_symbols()

    def _validate_parameters(self, production: ProductionIr) -> None:
        observed: set[str] = set()
        for parameter in production.parameters:
            validate_bsl_identifier(
                parameter,
                f"production {production.name!r} formal parameter",
            )
            key = parameter.casefold()
            if key in observed:
                raise ValueError(
                    f"production {production.name!r} has duplicate "
                    f"formal parameter {parameter!r}"
                )
            if key in _GENERATED_LOCALS or _TEMPORARY.fullmatch(parameter):
                raise ValueError(
                    f"production {production.name!r} formal parameter "
                    f"{parameter!r} collides with generated local"
                )
            observed.add(key)

    def _validate_decision(self, decision) -> None:
        for row in decision.rows:
            if len(row.matchers) > self._ir.lookahead:
                raise ValueError(
                    "canonical decision exceeds Parser IR lookahead"
                )

    def _validate_generated_symbols(self) -> None:
        symbols: list[tuple[str, str]] = [
            (matched.group(1), "canonical template helper")
            for matched in _BSL_DECLARATION.finditer(_load_template())
        ]
        symbols.extend(
            (f"НеТерминал{item.name}", f"production {item.name!r}")
            for item in self._ir.productions
        )
        for entrypoint in self._entrypoints:
            symbols.append((entrypoint, "exported entrypoint"))
            symbols.append(
                (_entry_result_name(entrypoint), "derived result function")
            )
        observed: dict[str, tuple[str, str]] = {}
        for name, origin in symbols:
            validate_bsl_identifier(name, origin)
            key = name.casefold()
            previous = observed.get(key)
            if previous is not None:
                raise ValueError(
                    "generated BSL symbol collision: "
                    f"{previous[0]!r} ({previous[1]}) and "
                    f"{name!r} ({origin})"
                )
            observed[key] = (name, origin)

    def _render_entrypoints(self) -> str:
        return "\r\n\r\n".join(
            f"Функция {name}(Текст) Экспорт\r\n"
            "\tЛексическийАнализатор."
            "УстановитьОбрабатываемыйТекст(Текст);\r\n"
            "\tУстановитьБуферТокенов();\r\n"
            f"\tВозврат {_entry_result_name(name)}();\r\n"
            "КонецФункции"
            for name in self._entrypoints
        )

    def _render_entry_results(self) -> str:
        return "\r\n\r\n".join(
            f"Функция {_entry_result_name(entrypoint)}()\r\n"
            "\tУстановитьТекущийТокен();\r\n"
            f"\tРезультат = НеТерминал{production}();\r\n"
            "\tЕсли ТипТокенаПросмотра(0) <> Неопределено Тогда\r\n"
            f"\t\tВызватьИсключениеСинтаксическаяОшибка({bsl_string(production)});\r\n"
            "\tКонецЕсли;\r\n"
            "\tВозврат Результат;\r\n"
            "КонецФункции"
            for entrypoint, production in self._entrypoints.items()
        )

    def _render_productions(self) -> str:
        return "\r\n\r\n".join(
            self._render_production(production)
            for production in self._ir.productions
        )

    def _render_production(self, production: ProductionIr) -> str:
        self._temporary = 0
        parameters = ", ".join(
            f"{item} = Неопределено"
            for item in production.parameters
        )
        lines = [
            f"Функция НеТерминал{production.name}({parameters})",
            "\tРезультатПродукции = Неопределено;",
        ]
        if production.decision is None:
            lines.extend(
                self._render_alternative(production.alternatives[0], "\t")
            )
        else:
            for position, alternative in enumerate(production.alternatives):
                keyword = "Если" if position == 0 else "ИначеЕсли"
                condition = self._conditions.for_alternative(
                    production.decision,
                    alternative.index + 1,
                )
                lines.append(f"\t{keyword} {condition} Тогда")
                lines.extend(self._render_alternative(alternative, "\t\t"))
            lines.extend(
                (
                    "\tИначе",
                    "\t\tВызватьИсключениеСинтаксическаяОшибка("
                    f"{bsl_string(production.name)});",
                    "\tКонецЕсли;",
                )
            )
        lines.extend(("\tВозврат РезультатПродукции;", "КонецФункции"))
        return "\r\n".join(lines)

    def _render_alternative(
        self,
        alternative: AlternativeIr,
        indent: str,
    ) -> list[str]:
        values: list[str | None] = []
        lines: list[str] = []
        for operation in alternative.operations:
            if not isinstance(operation, ParseSymbol):
                raise ValueError(
                    f"unsupported canonical operation {type(operation).__name__}"
                )
            self._temporary += 1
            temporary = f"Значение{self._temporary}"
            lines.append(
                f"{indent}{temporary} = {_symbol_call(operation.symbol)};"
            )
            values.append(temporary)
        if alternative.result_index is not None:
            value = values[alternative.result_index]
            if value is None:
                raise ValueError("transparent result operation has no value")
            lines.append(f"{indent}РезультатПродукции = {value};")
        return lines


def _load_template() -> str:
    return normalize_newlines(
        resources.files("parsergen")
        .joinpath("templates/canonical_parser_module.bsl")
        .read_text(encoding="utf-8")
    )


def _substitute_template(
    template: str,
    entrypoints: str,
    entry_results: str,
    productions: str,
    lookahead: int,
) -> str:
    replacements = (
        (_ENTRYPOINTS_MARKER, entrypoints),
        (_ENTRY_RESULTS_MARKER, entry_results),
        (_PRODUCTIONS_MARKER, productions),
        (_LOOKAHEAD_MARKER, str(lookahead)),
    )
    result = template
    for marker, replacement in replacements:
        if result.count(marker) != 1:
            raise ValueError(
                f"canonical template marker {marker!r} must occur once"
            )
        result = result.replace(marker, replacement)
    return normalize_newlines(result)


def _identifier_table(source: SourceGrammar) -> ValueTable:
    rows = tuple(
        (definition.name, token)
        for definition in source.identifier_definitions
        for token in definition.token_types
    )
    return ValueTable(
        (
            ValueColumn("Тип", ColumnKind.STRING),
            ValueColumn("Идентификатор", ColumnKind.STRING),
        ),
        rows,
    )


def _symbol_call(symbol: SyntaxSymbol) -> str:
    if isinstance(symbol, Terminal):
        return f"Терминал({bsl_string(symbol.token_type)})"
    if isinstance(symbol, Lexeme):
        return f"Лексема({bsl_string(symbol.text)})"
    if isinstance(symbol, Constant):
        return f"Константа({bsl_string(symbol.token_type)})"
    if isinstance(symbol, IdentifierRef):
        return f"Идентификатор({bsl_string(symbol.name)})"
    if isinstance(symbol, NonterminalCall):
        return f"НеТерминал{symbol.name}({', '.join(symbol.arguments)})"
    raise TypeError(type(symbol))


def _entry_result_name(entrypoint: str) -> str:
    established = {
        "Разобрать": "РезультатРазбора",
        "РазобратьВыражение": "РезультатРазбораВыражения",
    }
    return established.get(entrypoint, f"Результат{entrypoint}")
