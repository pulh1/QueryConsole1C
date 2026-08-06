from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
import re

from .analysis import (
    AnalysisResult,
    SelectMatcherArtifact,
    build_select_matcher_artifact,
)
from .model import (
    Action,
    Alternative,
    Constant,
    Grammar,
    IdentifierRef,
    Lexeme,
    NonterminalCall,
    Production,
    SyntaxSymbol,
    Terminal,
)
from .resolver import ResolvedGrammar, ResolvedToken, resolve_grammar
from .semantic_actions import ActionCompiler
from .value_table_codec import (
    ColumnKind,
    ValueColumn,
    ValueTable,
)


MAX_MATCHER_ROWS = 100_000
_ENTRYPOINTS_MARKER = "// <parsergen:entrypoints>"
_ENTRY_RESULTS_MARKER = "// <parsergen:entry-results>"
_PRODUCTIONS_MARKER = "// <parsergen:productions>"
_END_TOKEN = "$"

# Legacy compatibility: the checked-in 1C reference snapshot was produced
# with this historical numbering for one repeatedly declared production.
# Canonical numbering is source order (1, 2, 3); keep this isolated so the
# exception can be removed when the reference artifacts are regenerated.
_LEGACY_ALTERNATIVE_NUMBERING = {
    "ПервыеРазличныеОпционально": (3, 1, 2),
}

_BSL_IDENTIFIER = re.compile(
    r"[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*\Z"
)
_BSL_DECLARATION = re.compile(
    r"^(?:Функция|Процедура)\s+"
    r"([A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*)\s*\(",
    re.MULTILINE | re.IGNORECASE,
)

# 1C:Enterprise Developer Guide, "Reserved words", defines the classic
# bilingual language core. The grouped additions below cover the current
# exception, handler, async, literal, and preprocessor constructs which may
# also occur in generated modules. Keep the categories explicit: this is a
# code-generation safety boundary, not a convenient sample of common words.
_BSL_CONTROL_KEYWORDS = (
    "Если", "If",
    "Тогда", "Then",
    "ИначеЕсли", "ElsIf",
    "Иначе", "Else",
    "КонецЕсли", "EndIf",
    "Для", "For",
    "Каждого", "Each",
    "Из", "In",
    "По", "To",
    "Пока", "While",
    "Цикл", "Do",
    "КонецЦикла", "EndDo",
    "Попытка", "Try",
    "Исключение", "Except",
    "КонецПопытки", "EndTry",
    "ВызватьИсключение", "Raise",
    "Перейти", "Goto",
    "Возврат", "Return",
    "Продолжить", "Continue",
    "Прервать", "Break",
)
_BSL_DECLARATION_KEYWORDS = (
    "Процедура", "Procedure",
    "КонецПроцедуры", "EndProcedure",
    "Функция", "Function",
    "КонецФункции", "EndFunction",
    "Перем", "Var",
    "Экспорт", "Export",
    "Знач", "Val",
    "Асинх", "Async",
)
_BSL_OPERATOR_AND_LITERAL_KEYWORDS = (
    "И", "And",
    "Или", "Or",
    "Не", "Not",
    "Новый", "New",
    "Выполнить", "Execute",
    "Ждать", "Await",
    "ДобавитьОбработчик", "AddHandler",
    "УдалитьОбработчик", "RemoveHandler",
    "Истина", "True",
    "Ложь", "False",
    "Неопределено", "Undefined",
    "Null",
)
_BSL_PREPROCESSOR_KEYWORDS = (
    "Область", "Region",
    "КонецОбласти", "EndRegion",
)
_BSL_RESERVED_KEYWORDS = frozenset(
    keyword.casefold()
    for category in (
        _BSL_CONTROL_KEYWORDS,
        _BSL_DECLARATION_KEYWORDS,
        _BSL_OPERATOR_AND_LITERAL_KEYWORDS,
        _BSL_PREPROCESSOR_KEYWORDS,
    )
    for keyword in category
)
_IMPLICIT_PRODUCTION_PARAMETERS = ("Родитель", "ЛевыйЭлемент")
_GENERATED_PRODUCTION_LOCALS = (
    "ЭтотУзел",
    "ТекущийЭлемент",
    "НомерВариантаПродукции",
)
_GENERATED_PRODUCTION_RUNTIME_NAMES = (
    "ТекущийТокен",
    "ЭлементыМоделиЗапроса",
    "ПоследняяПродукция",
)


def _validate_bsl_identifier(name: str, origin: str) -> None:
    if _BSL_IDENTIFIER.fullmatch(name) is None:
        raise ValueError(
            f"{origin} {name!r} is not a valid BSL identifier"
        )
    if name.casefold() in _BSL_RESERVED_KEYWORDS:
        raise ValueError(
            f"{origin} {name!r} is a reserved BSL keyword"
        )


@dataclass(frozen=True, slots=True)
class GeneratedParser:
    module_text: str
    select_table: ValueTable
    identifier_table: ValueTable
    constructor_names: tuple[str, ...]


class BslGenerator:
    def __init__(
        self,
        grammar: Grammar,
        resolved: ResolvedGrammar,
        analysis: AnalysisResult,
        entrypoints: Mapping[str, str],
    ) -> None:
        self._grammar = grammar
        self._resolved = resolved
        self._analysis = analysis
        self._entrypoints = entrypoints
        self._constructors: list[str] = []
        self._seen_constructors: set[str] = set()

    def generate(self) -> GeneratedParser:
        self._validate_inputs()
        artifact = build_select_matcher_artifact(
            self._analysis,
            max_rows=MAX_MATCHER_ROWS,
        )
        select_table = _select_table(
            artifact,
            self._resolved.production_order,
            self._analysis.k,
            {
                production.name: _alternative_numbers(production)
                for production in self._grammar.productions
            },
        )
        identifier_table = _identifier_table(self._grammar, artifact)
        module = _substitute_markers(
            _load_template(),
            self._render_entrypoints(),
            self._render_entry_results(),
            self._render_productions_and_ending(),
        )
        return GeneratedParser(
            module,
            select_table,
            identifier_table,
            tuple(self._constructors),
        )

    def _validate_inputs(self) -> None:
        if _contains_reserved_end(self._grammar, self._resolved):
            raise ValueError(
                "reserved END token '$' cannot be produced by grammar"
            )
        if self._analysis.k < 1:
            raise ValueError("analysis lookahead must be at least 1")
        if not self._entrypoints:
            raise ValueError("entrypoint mapping must not be empty")
        known = set(self._resolved.production_order)
        for entrypoint, production in self._entrypoints.items():
            if not entrypoint:
                raise ValueError("entrypoint name must not be empty")
            _validate_bsl_identifier(entrypoint, "entrypoint")
            if production not in known:
                raise ValueError(
                    f"entrypoint {entrypoint!r} references "
                    f"unknown production {production!r}"
                )
        reparsed_resolution = resolve_grammar(self._grammar)
        if (
            reparsed_resolution.grammar is None
            or reparsed_resolution.grammar != self._resolved
        ):
            raise ValueError(
                "parsed grammar does not match resolved grammar"
            )
        if self._analysis._resolved_grammar is not self._resolved:
            raise ValueError(
                "analysis is not bound to the supplied resolved grammar"
            )
        if (
            self._analysis._compressed is None
            or self._analysis._compressed.k != self._analysis.k
        ):
            raise ValueError(
                "analysis lookahead does not match its compressed solver"
            )
        seeded = set(self._analysis._start_productions)
        for production in self._entrypoints.values():
            if production not in seeded:
                raise ValueError(
                    f"entrypoint production {production!r} was not "
                    "END-seeded during analysis"
                )
        self._validate_production_parameters()
        self._validate_generated_symbols()

    def _validate_production_parameters(self) -> None:
        implicit = {
            name.casefold(): name
            for name in _IMPLICIT_PRODUCTION_PARAMETERS
        }
        generated_locals = {
            name.casefold(): name
            for name in _GENERATED_PRODUCTION_LOCALS
        }
        generated_runtime = {
            name.casefold(): name
            for name in _GENERATED_PRODUCTION_RUNTIME_NAMES
        }
        for production in self._grammar.productions:
            observed: dict[str, str] = {}
            origin = f"production {production.name!r} formal parameter"
            for parameter in production.parameters:
                _validate_bsl_identifier(parameter, origin)
                key = parameter.casefold()
                previous = observed.get(key)
                if previous is not None:
                    raise ValueError(
                        f"{origin} duplicate: "
                        f"{previous!r} and {parameter!r}"
                    )
                implicit_name = implicit.get(key)
                if implicit_name is not None:
                    raise ValueError(
                        f"{origin} {parameter!r} collides with "
                        f"implicit parameter {implicit_name!r}"
                    )
                local_name = generated_locals.get(key)
                if local_name is not None:
                    raise ValueError(
                        f"{origin} {parameter!r} collides with "
                        f"generated local {local_name!r}"
                    )
                runtime_name = generated_runtime.get(key)
                if runtime_name is not None:
                    raise ValueError(
                        f"{origin} {parameter!r} collides with "
                        f"generated runtime name {runtime_name!r}"
                    )
                observed[key] = parameter

    def _validate_generated_symbols(self) -> None:
        symbols: list[tuple[str, str]] = []
        template = _load_template()
        symbols.extend(
            (matched.group(1), "fixed template helper")
            for matched in _BSL_DECLARATION.finditer(template)
        )
        for production in self._grammar.productions:
            name = f"НеТерминал{production.name}"
            _validate_bsl_identifier(name, "generated production function")
            symbols.append((name, f"production {production.name!r}"))
        for entrypoint in self._entrypoints:
            result_name = _entry_result_name(entrypoint)
            _validate_bsl_identifier(result_name, "generated result function")
            symbols.append((entrypoint, "exported entrypoint"))
            symbols.append((result_name, "derived result function"))

        observed: dict[str, tuple[str, str]] = {}
        for name, origin in symbols:
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
        blocks = []
        for position, name in enumerate(self._entrypoints):
            # Legacy compatibility: preserve the reference text document's
            # otherwise insignificant trailing whitespace.
            ending_whitespace = "\t" if position == 0 else "  "
            blocks.append(
                f"Функция {name}(Текст) Экспорт\r\n"
                "\tЛексическийАнализатор."
                "УстановитьОбрабатываемыйТекст(Текст);\t\r\n"
                "\tУстановитьБуферТокенов();\r\n"
                "\t\r\n"
                f"\tВозврат {_entry_result_name(name)}();\r\n"
                f"КонецФункции{ending_whitespace}"
            )
        return "\r\n\r\n".join(blocks)

    def _render_entry_results(self) -> str:
        production_by_name = {
            production.name: production
            for production in self._grammar.productions
        }
        blocks: list[str] = []
        for position, (entrypoint, production_name) in enumerate(
            self._entrypoints.items()
        ):
            production = production_by_name[production_name]
            call_arguments = (
                "Неопределено, Неопределено"
                if production.parameters or position > 0
                else ""
            )
            # Legacy compatibility: the supplied module has asymmetric
            # whitespace and an explicit two-argument second entry call.
            ending_whitespace = "   " if position == 0 else ""
            blocks.append(
                f"Функция {_entry_result_name(entrypoint)}()\r\n"
                "\tУстановитьТекущийТокен();\r\n"
                "\r\n"
                f"\tРезультат = НеТерминал{production_name}"
                f"({call_arguments});\r\n"
                "\t\t\r\n"
                "\tЕсли ТекущийТокен.Тип <> Неопределено Тогда\r\n"
                "\t\tВызватьИсключениеНеУдалосьВыпполнитьРазбор("
                "ПоследняяПродукция);\r\n"
                "\tКонецЕсли;\r\n"
                "\t\r\n"
                "\tВозврат Результат;\t\r\n"
                f"КонецФункции{ending_whitespace}"
            )
        return "\r\n\r\n".join(blocks)

    def _render_productions_and_ending(self) -> str:
        functions = "\r\n\r\n".join(
            self._render_production(production)
            for production in self._grammar.productions
        )
        ending = (
            "#КонецОбласти\r\n"
            "\r\n"
            "#Область Инициализация\r\n"
            f"КоличествоПросматриваемыхСимволов = {self._analysis.k};\r\n"
            "Инициализировать();\r\n"
            "\r\n"
            "#КонецОбласти\r\n"
            "\r\n"
            "#Иначе\r\n"
            "ВызватьИсключение НСтр(\"ru = "
            "'Недопустимый вызов объекта на клиенте.'\");\r\n"
            # Legacy compatibility: retain the trailing CRLF from the
            # reference 1C text document.
            "#КонецЕсли\r\n"
        )
        if not functions:
            return ending
        return f"{functions}\r\n\r\n{ending}"

    def _render_production(self, production: Production) -> str:
        parameters = "".join(
            f", {parameter} = Неопределено"
            for parameter in production.parameters
        )
        lines = [
            f"Функция НеТерминал{production.name}("
            "Родитель = Неопределено, "
            f"ЛевыйЭлемент = Неопределено{parameters})",
            '\tЭтотУзел = "ПУСТО";',
        ]
        alternatives = production.alternatives
        if len(alternatives) == 1:
            body = self._render_alternative(alternatives[0], "\t")
            if body:
                lines.extend(body.rstrip("\r\n").split("\r\n"))
        else:
            lines.extend(self._render_dispatch(production))
        lines.extend(("", "\tВозврат ЭтотУзел;", "КонецФункции"))
        return "\r\n".join(lines)

    def _render_dispatch(self, production: Production) -> list[str]:
        result = [
            "\tНомерВариантаПродукции = "
            f'НомерВариантаПродукции({_bsl_string(production.name)});'
        ]
        alternative_numbers = _alternative_numbers(production)
        dispatchable = sorted(
            (
                (alternative_numbers[position], alternative)
                for position, alternative in enumerate(
                    production.alternatives
                )
                if alternative.elements
            ),
            key=lambda item: item[0],
        )
        for branch_position, (number, alternative) in enumerate(dispatchable):
            keyword = "Если" if branch_position == 0 else "ИначеЕсли"
            result.append(
                f"\t{keyword} НомерВариантаПродукции = {number} Тогда"
            )
            body = self._render_alternative(alternative, "\t\t")
            if body:
                result.extend(body.rstrip("\r\n").split("\r\n"))

        has_implicit_epsilon = any(
            not alternative.elements
            for alternative in production.alternatives
        )
        if dispatchable and not has_implicit_epsilon:
            result.extend(
                (
                    "\tИначе",
                    "\t\tВызватьИсключениеНеУдалосьВыпполнитьРазбор("
                    f"{_bsl_string(production.name)});",
                )
            )
        if dispatchable:
            result.append("\tКонецЕсли;")
        elif not has_implicit_epsilon:
            result.append(
                "\tВызватьИсключениеНеУдалосьВыпполнитьРазбор("
                f"{_bsl_string(production.name)});"
            )
        result.append(
            f"\tПоследняяПродукция = {_bsl_string(production.name)};"
        )
        return result

    def _render_alternative(
        self,
        alternative: Alternative,
        indent: str,
    ) -> str:
        if not alternative.elements:
            return ""
        parts = [
            f"{indent}ЭтотУзел = Неопределено;\r\n",
            f"{indent}ТекущийЭлемент = Неопределено;\r\n",
        ]
        rendered_action_boundaries: set[int] = set()
        for element in alternative.elements:
            if isinstance(element, Action):
                # Legacy compatibility: the reference generator searches its
                # action table with Найти and therefore executes only the first
                # action attached to a syntax boundary. Canonical semantics
                # would execute every adjacent action in source order.
                if element.boundary in rendered_action_boundaries:
                    continue
                rendered_action_boundaries.add(element.boundary)
                compiler = ActionCompiler(
                    indent=indent,
                    guard=element.boundary > 0,
                )
                parts.append(compiler.compile(element))
                self._record_constructors(compiler.constructor_names)
            else:
                parts.append(
                    f"{indent}ТекущийЭлемент = "
                    f"{_symbol_call(element)};\r\n"
                )
        return "".join(parts)

    def _record_constructors(self, names: tuple[str, ...]) -> None:
        for name in names:
            if name in self._seen_constructors:
                continue
            self._seen_constructors.add(name)
            self._constructors.append(name)


def generate_parser(
    grammar: Grammar,
    resolved: ResolvedGrammar,
    analysis: AnalysisResult,
    entrypoints: Mapping[str, str],
) -> GeneratedParser:
    return BslGenerator(
        grammar,
        resolved,
        analysis,
        entrypoints,
    ).generate()


def _load_template() -> str:
    text = (
        resources.files("parsergen")
        .joinpath("templates/parser_module.bsl")
        .read_text(encoding="utf-8")
    )
    return _normalize_newlines(text)


def _substitute_markers(
    template: str,
    entrypoints: str,
    entry_results: str,
    productions: str,
) -> str:
    replacements = (
        (_ENTRYPOINTS_MARKER, entrypoints),
        (_ENTRY_RESULTS_MARKER, entry_results),
        (_PRODUCTIONS_MARKER, productions),
    )
    for marker, _ in replacements:
        count = template.count(marker)
        if count != 1:
            raise ValueError(
                f"template marker {marker!r} must occur exactly once; "
                f"found {count}"
            )
    result = template
    for marker, replacement in replacements:
        result = result.replace(marker, replacement)
    return _normalize_newlines(result)


def _select_table(
    artifact: SelectMatcherArtifact,
    production_order: tuple[str, ...],
    k: int,
    alternative_numbers: Mapping[str, tuple[int, ...]],
) -> ValueTable:
    production_positions = {
        name: position for position, name in enumerate(production_order)
    }
    normalized: set[tuple[str, int, tuple[str, ...]]] = set()
    for row in artifact.select_rows:
        numbers = alternative_numbers[row.production]
        normalized.add(
            (
                row.production,
                numbers[row.alternative - 1],
                row.matchers,
            )
        )
    ordered = sorted(
        normalized,
        key=lambda item: (
            production_positions[item[0]],
            item[1],
            -len(item[2]),
            item[2],
        ),
    )
    rows = tuple(
        (
            len(matchers),
            *matchers,
            *([None] * (k - len(matchers))),
            production,
            alternative,
        )
        for production, alternative, matchers in ordered
    )
    columns = (
        ValueColumn("КоличествоЭлементов", ColumnKind.NUMBER),
        *(
            ValueColumn(f"Элемент{position}", ColumnKind.STRING)
            for position in range(1, k + 1)
        ),
        ValueColumn("Продукция", ColumnKind.STRING),
        ValueColumn("НомерВарианта", ColumnKind.NUMBER),
    )
    return ValueTable(columns, rows)


def _alternative_numbers(production: Production) -> tuple[int, ...]:
    legacy = _LEGACY_ALTERNATIVE_NUMBERING.get(production.name)
    if legacy is not None and len(legacy) == len(production.alternatives):
        return legacy
    return tuple(range(1, len(production.alternatives) + 1))


def _identifier_table(
    grammar: Grammar,
    artifact: SelectMatcherArtifact,
) -> ValueTable:
    # Legacy compatibility: a canonical symbol table would deduplicate equal
    # declarations. The reference artifact preserves source row order and even
    # duplicate rows, so reproduce the declarations verbatim.
    rows = [
        (definition.name, token)
        for definition in grammar.identifier_definitions
        for token in definition.token_types
    ]

    return ValueTable(
        (
            ValueColumn("Тип", ColumnKind.STRING),
            ValueColumn("Идентификатор", ColumnKind.STRING),
        ),
        tuple(rows),
    )


def _contains_reserved_end(
    grammar: Grammar,
    resolved: ResolvedGrammar,
) -> bool:
    if any(
        definition.name == _END_TOKEN
        or _END_TOKEN in definition.token_types
        for definition in grammar.identifier_definitions
    ):
        return True
    for production in grammar.productions:
        for alternative in production.alternatives:
            for symbol in alternative.syntax_symbols:
                if (
                    isinstance(symbol, Terminal)
                    and symbol.token_type == _END_TOKEN
                ):
                    return True
                if isinstance(symbol, Lexeme) and symbol.text == _END_TOKEN:
                    return True
                if (
                    isinstance(symbol, Constant)
                    and symbol.token_type == _END_TOKEN
                ):
                    return True
    if any(
        _END_TOKEN in tokens
        for tokens in resolved.identifier_tokens.values()
    ):
        return True
    return any(
        _END_TOKEN in symbol.token_types
        for alternatives in resolved.productions.values()
        for alternative in alternatives
        for symbol in alternative.symbols
        if isinstance(symbol, ResolvedToken)
    )


def _symbol_call(symbol: SyntaxSymbol) -> str:
    if isinstance(symbol, Terminal):
        return f"Терминал({_bsl_string(symbol.token_type)})"
    if isinstance(symbol, Lexeme):
        return f"Лексема({_bsl_string(symbol.text)})"
    if isinstance(symbol, Constant):
        return f"Константа({_bsl_string(symbol.token_type)})"
    if isinstance(symbol, IdentifierRef):
        return f"Идентификатор({_bsl_string(symbol.name)})"
    if isinstance(symbol, NonterminalCall):
        arguments = ["ЭтотУзел", "ТекущийЭлемент", *symbol.arguments]
        return f"НеТерминал{symbol.name}({', '.join(arguments)})"
    raise TypeError(type(symbol))


def _entry_result_name(entrypoint: str) -> str:
    established = {
        "Разобрать": "РезультатРазбора",
        "РазобратьВыражение": "РезультатРазбораВыражения",
    }
    return established.get(entrypoint, f"Результат{entrypoint}")


def _bsl_string(value: str) -> str:
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


def _normalize_newlines(text: str) -> str:
    return (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\r\n")
    )
