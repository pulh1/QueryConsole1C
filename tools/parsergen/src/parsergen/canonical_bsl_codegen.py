from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
import re

from .bsl_rendering import (
    bsl_string,
    normalize_newlines,
    validate_bsl_identifier,
    validate_bsl_member_name,
    validate_bsl_member_path,
)
from .canonical_bsl_decisions import CanonicalDecisionRenderer
from .canonical_select import AlternativeOutcome
from .decision_dag import CommitAlternative, ExitDecision, ImmediateError
from .model import (
    Constant,
    IdentifierRef,
    Lexeme,
    NonterminalCall,
    SyntaxSymbol,
    Terminal,
)
from .parser_ir import (
    AlternativeIr,
    AppendCollection,
    AssignConstant,
    BindScalar,
    ConcatScalar,
    BoundValue,
    BranchIr,
    ConstructNode,
    Dispatch,
    DispatchValue,
    ExtendCollection,
    DiscardSymbol,
    FoldLeftValue,
    IncrementScalar,
    LeftFold,
    Operation,
    OptionalBranch,
    ParseBranchValue,
    ParseSymbol,
    ParserIr,
    ProductionIr,
    RepeatLoop,
    ReturnConstant,
    WrapOptional,
    WrapValue,
    UndefinedValue,
)
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
_DECISION_TOKEN = re.compile(r"ТокенРешения[0-9]+\Z", re.IGNORECASE)
_TOKEN_CLASS_HELPER_NAME = "ТокенПринадлежитКлассу"
_TOKEN_CLASS_HELPER = """Функция ТокенПринадлежитКлассу(ТипТокена, ИмяКласса)
	СтруктураПоиска = Новый Структура("Тип, Идентификатор", ИмяКласса, ТипТокена);
	Возврат ОпределенияИдентификаторов.НайтиСтроки(СтруктураПоиска).Количество() > 0;
КонецФункции"""
_GENERATED_LOCALS = frozenset(
    item.casefold()
    for item in ("РезультатПродукции", "ЭтотУзел")
)


@dataclass(frozen=True, slots=True)
class CanonicalGeneratedParser:
    module_text: str
    identifier_table: ValueTable
    constructor_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanonicalGeneratedFunctions:
    module_fragment: str
    constructor_names: tuple[str, ...]


def generate_canonical_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
    *,
    named_predicates: Mapping[tuple[str, ...], str] | None = None,
) -> CanonicalGeneratedParser:
    return _CanonicalBslGenerator(
        source,
        parser_ir,
        entrypoints,
        named_predicates=named_predicates,
    ).generate()


def generate_canonical_functions(
    source: SourceGrammar,
    parser_ir: ParserIr,
    *,
    abi_parameters: tuple[str, ...] = (),
    call_argument_prefix: tuple[str, ...] = (),
    named_predicates: Mapping[tuple[str, ...], str] | None = None,
) -> CanonicalGeneratedFunctions:
    return _CanonicalBslGenerator(
        source,
        parser_ir,
        {},
        named_predicates=named_predicates,
    ).generate_functions(
        abi_parameters,
        call_argument_prefix,
    )


class _CanonicalBslGenerator:
    def __init__(
        self,
        source: SourceGrammar,
        parser_ir: ParserIr,
        entrypoints: Mapping[str, str],
        *,
        named_predicates: Mapping[tuple[str, ...], str] | None = None,
    ) -> None:
        self._source = source
        self._ir = parser_ir
        self._entrypoints = entrypoints
        self._named_predicates = dict(named_predicates or {})
        self._decisions = CanonicalDecisionRenderer(
            parser_ir.matcher_definitions,
            named_predicates=self._named_predicates,
        )
        self._temporary = 0
        self._constructors: list[str] = []
        self._seen_constructors: set[str] = set()
        self._fold_left_values: list[str] = []
        self._abi_parameters: tuple[str, ...] = ()
        self._call_argument_prefix: tuple[str, ...] = ()

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
            tuple(self._constructors),
        )

    def generate_functions(
        self,
        abi_parameters: tuple[str, ...],
        call_argument_prefix: tuple[str, ...],
    ) -> CanonicalGeneratedFunctions:
        self._abi_parameters = tuple(abi_parameters)
        self._call_argument_prefix = tuple(call_argument_prefix)
        self._validate_common_inputs()
        self._validate_abi_parameters()
        if (
            self._call_argument_prefix
            and len(self._call_argument_prefix) != len(self._abi_parameters)
        ):
            raise ValueError(
                "call argument prefix must match ABI parameter count"
            )
        self._validate_generated_symbols(
            include_template=False,
            include_entrypoints=False,
        )
        return CanonicalGeneratedFunctions(
            self._render_productions(),
            tuple(self._constructors),
        )

    def _validate_inputs(self) -> None:
        self._validate_common_inputs()
        if not self._entrypoints:
            raise ValueError("entrypoint mapping must not be empty")
        production_names = {
            production.name
            for production in self._ir.productions
        }
        for entrypoint, production in self._entrypoints.items():
            validate_bsl_identifier(entrypoint, "entrypoint")
            if production not in production_names:
                raise ValueError(
                    f"entrypoint {entrypoint!r} references unknown "
                    f"production {production!r}"
                )
        self._validate_generated_symbols(
            include_template=True,
            include_entrypoints=True,
        )

    def _validate_common_inputs(self) -> None:
        if self._source != self._ir.source_grammar:
            raise ValueError("source grammar does not match Parser IR")
        if self._ir.lookahead < 1:
            raise ValueError("Parser IR lookahead must be at least 1")
        for definition in self._source.identifier_definitions:
            if (
                definition.name == _END_TOKEN
                or _END_TOKEN in definition.token_types
            ):
                raise ValueError("reserved END token '$' cannot be generated")
        for production in self._ir.productions:
            validate_bsl_identifier(
                f"НеТерминал{production.name}",
                "generated production function",
            )
            self._validate_parameters(production)
            if production.decision is not None:
                self._validate_decision(production.decision)

    def _validate_abi_parameters(self) -> None:
        observed: set[str] = set()
        declared = {
            parameter.casefold()
            for production in self._ir.productions
            for parameter in production.parameters
        }
        for parameter in self._abi_parameters:
            validate_bsl_identifier(parameter, "production ABI parameter")
            key = parameter.casefold()
            if key in observed:
                raise ValueError(f"duplicate ABI parameter {parameter!r}")
            if key in declared:
                raise ValueError(
                    f"ABI parameter {parameter!r} collides with declared parameter"
                )
            if (
                key in _GENERATED_LOCALS
                or _TEMPORARY.fullmatch(parameter)
                or _DECISION_TOKEN.fullmatch(parameter)
            ):
                raise ValueError(
                    f"ABI parameter {parameter!r} collides with generated local"
                )
            observed.add(key)

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
            if (
                key in _GENERATED_LOCALS
                or _TEMPORARY.fullmatch(parameter)
                or _DECISION_TOKEN.fullmatch(parameter)
            ):
                raise ValueError(
                    f"production {production.name!r} formal parameter "
                    f"{parameter!r} collides with generated local"
                )
            observed.add(key)

    def _validate_decision(self, decision) -> None:
        if decision.source.lookahead > self._ir.lookahead:
            raise ValueError(
                "canonical decision exceeds Parser IR lookahead"
            )
        if decision.dag.lookahead != decision.source.lookahead:
            raise ValueError("canonical decision DAG lookahead differs")

    def _validate_generated_symbols(
        self,
        *,
        include_template: bool,
        include_entrypoints: bool,
    ) -> None:
        symbols: list[tuple[str, str]] = []
        if self._named_predicates:
            symbols.append(
                (_TOKEN_CLASS_HELPER_NAME, "named token-set helper")
            )
        if include_template:
            symbols.extend(
                (matched.group(1), "canonical template helper")
                for matched in _BSL_DECLARATION.finditer(_load_template())
            )
        symbols.extend(
            (f"НеТерминал{item.name}", f"production {item.name!r}")
            for item in self._ir.productions
        )
        if include_entrypoints:
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
        productions = "\r\n\r\n".join(
            self._render_production(production)
            for production in self._ir.productions
        )
        if not self._named_predicates:
            return productions
        return normalize_newlines(_TOKEN_CLASS_HELPER) + "\r\n\r\n" + productions

    def _render_production(self, production: ProductionIr) -> str:
        self._temporary = 0
        parameters = ", ".join(
            f"{item} = Неопределено"
            for item in (*self._abi_parameters, *production.parameters)
        )
        lines = [
            f"Функция НеТерминал{production.name}({parameters})",
            "\tРезультатПродукции = Неопределено;",
        ]
        if production.decision is None:
            lines.extend(
                self._render_alternative(
                    production.alternatives[0],
                    "\t",
                    production.name,
                )
            )
        else:
            alternatives_by_outcome = {
                AlternativeOutcome(production.name, alternative.index + 1):
                    alternative
                for alternative in production.alternatives
            }

            def render_leaf(leaf, indent: str) -> list[str]:
                if isinstance(leaf, ImmediateError):
                    return [
                        self._syntax_error_line(
                            indent,
                            production.name,
                            leaf.expected,
                        )
                    ]
                if isinstance(leaf, ExitDecision):
                    raise ValueError("production decision must not exit")
                assert isinstance(leaf, CommitAlternative)
                alternative = alternatives_by_outcome.get(leaf.outcome)
                if alternative is None:
                    raise ValueError(
                        "production decision references unknown outcome"
                    )
                return self._render_alternative(
                    alternative,
                    indent,
                    production.name,
                )

            lines.extend(
                self._decisions.render(
                    production.decision,
                    indent="\t",
                    token_prefix="ТокенРешения",
                    render_leaf=render_leaf,
                )
            )
        lines.extend(("\tВозврат РезультатПродукции;", "КонецФункции"))
        return "\r\n".join(lines)

    def _render_alternative(
        self,
        alternative: AlternativeIr,
        indent: str,
        error_label: str,
    ) -> list[str]:
        has_constructor = any(
            isinstance(operation, ConstructNode)
            for operation in alternative.operations
        )
        lines, values = self._render_operations(
            alternative.operations,
            indent,
            error_label,
            required_result_index=(
                None if has_constructor else alternative.result_index
            ),
        )
        if has_constructor:
            lines.append(f"{indent}РезультатПродукции = ЭтотУзел;")
        elif alternative.result_index is not None:
            value = values[alternative.result_index]
            if value is None:
                raise ValueError("transparent result operation has no value")
            lines.append(f"{indent}РезультатПродукции = {value};")
        return lines

    def _render_operations(
        self,
        operations: tuple[Operation, ...],
        indent: str,
        error_label: str,
        *,
        required_result_index: int | None = None,
    ) -> tuple[list[str], list[str | None]]:
        lines: list[str] = []
        values: list[str | None] = []
        for index, operation in enumerate(operations):
            if isinstance(operation, DiscardSymbol):
                rendered = [
                    f"{indent}{self._symbol_call(operation.symbol)};"
                ]
                value = None
            elif (
                isinstance(operation, ParseSymbol)
                and index != required_result_index
            ):
                rendered = [
                    f"{indent}{self._symbol_call(operation.symbol)};"
                ]
                value = None
            else:
                rendered, value = self._render_operation(
                    operation,
                    indent,
                    error_label,
                )
            lines.extend(rendered)
            values.append(value)
        return lines, values

    def _render_operation(
        self,
        operation: Operation,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str | None]:
        if isinstance(operation, ParseSymbol):
            temporary = self._new_temporary()
            return (
                [
                    f"{indent}{temporary} = "
                    f"{self._symbol_call(operation.symbol)};"
                ],
                temporary,
            )
        if isinstance(operation, ConstructNode):
            validate_bsl_identifier(operation.constructor, "constructor")
            self._record_constructor(operation.constructor)
            return (
                [
                    f"{indent}ЭтотУзел = ЭлементыМоделиЗапроса."
                    f"{operation.constructor}(ТекущийТокен);"
                ],
                None,
            )
        if isinstance(operation, BindScalar):
            return self._render_binding(
                operation.property,
                operation.value,
                indent,
                error_label,
                append=False,
            )
        if isinstance(operation, AppendCollection):
            return self._render_binding(
                operation.property,
                operation.value,
                indent,
                error_label,
                append=True,
            )
        if isinstance(operation, ExtendCollection):
            lines, collection = self._render_bound_value(
                operation.value,
                indent,
                error_label,
            )
            validate_bsl_member_path(operation.property, "bound property")
            item = "ЭлементКоллекции"
            lines.extend(
                (
                    f"{indent}Если {collection} <> Неопределено Тогда",
                    f"{indent}\tДля Каждого {item} Из {collection} Цикл",
                    f"{indent}\t\tЭтотУзел.{operation.property}."
                    f"Добавить({item});",
                    f"{indent}\tКонецЦикла;",
                    f"{indent}КонецЕсли;",
                )
            )
            return lines, None
        if isinstance(operation, ConcatScalar):
            lines, expression = self._render_bound_value(
                operation.value,
                indent,
                error_label,
            )
            validate_bsl_member_name(operation.property, "bound property")
            lines.append(
                f"{indent}ЭтотУзел.{operation.property} = "
                f"ЭтотУзел.{operation.property} + {expression};"
            )
            return lines, None
        if isinstance(operation, IncrementScalar):
            if not isinstance(operation.value, ParseSymbol):
                raise ValueError(
                    "increment binding requires a direct parse symbol"
                )
            validate_bsl_member_name(operation.property, "bound property")
            return (
                [
                    f"{indent}{self._symbol_call(operation.value.symbol)};",
                    f"{indent}ЭтотУзел.{operation.property} = "
                    f"ЭтотУзел.{operation.property} + 1;",
                ],
                None,
            )
        if isinstance(operation, AssignConstant):
            validate_bsl_member_name(operation.property, "bound property")
            return (
                [
                    f"{indent}ЭтотУзел.{operation.property} = "
                    f"{operation.value};"
                ],
                None,
            )
        if isinstance(operation, ReturnConstant):
            return [], operation.value
        if isinstance(operation, Dispatch):
            return self._render_dispatch(
                operation,
                indent,
                error_label,
            )
        if isinstance(operation, OptionalBranch):
            return self._render_optional(
                operation,
                indent,
                error_label,
            )
        if isinstance(operation, WrapOptional):
            return self._render_wrap_optional(
                operation,
                indent,
                error_label,
            )
        if isinstance(operation, WrapValue):
            return self._render_wrap_value(
                operation,
                indent,
                error_label,
            )
        if isinstance(operation, RepeatLoop):
            return self._render_repeat(
                operation,
                indent,
                error_label,
            )
        if isinstance(operation, LeftFold):
            return self._render_left_fold(
                operation,
                indent,
                error_label,
            )
        raise ValueError(
            f"unsupported canonical operation {type(operation).__name__}"
        )

    def _symbol_call(self, symbol: SyntaxSymbol) -> str:
        if not isinstance(symbol, NonterminalCall):
            return _symbol_call(symbol)
        arguments = (
            (*self._call_argument_prefix, *symbol.arguments)
            if symbol.arguments
            else ()
        )
        return f"НеТерминал{symbol.name}({', '.join(arguments)})"

    def _render_binding(
        self,
        property_name: str | None,
        value: BoundValue,
        indent: str,
        error_label: str,
        *,
        append: bool,
    ) -> tuple[list[str], None]:
        lines, expression = self._render_bound_value(
            value,
            indent,
            error_label,
        )
        if append:
            if property_name is None:
                lines.append(f"{indent}ЭтотУзел.Добавить({expression});")
            else:
                validate_bsl_member_name(property_name, "bound property")
                lines.append(
                    f"{indent}ЭтотУзел.{property_name}."
                    f"Добавить({expression});"
                )
        else:
            if property_name is None:
                raise ValueError("scalar root binding is not supported")
            validate_bsl_member_name(property_name, "bound property")
            lines.append(
                f"{indent}ЭтотУзел.{property_name} = {expression};"
            )
        return lines, None

    def _render_bound_value(
        self,
        value: BoundValue,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str]:
        if isinstance(value, ParseSymbol):
            lines, result = self._render_operation(
                value,
                indent,
                error_label,
            )
            assert result is not None
            return lines, result
        if isinstance(value, UndefinedValue):
            return [], value.value
        if isinstance(value, FoldLeftValue):
            if not self._fold_left_values:
                raise ValueError("fold-left value used outside LeftFold")
            return [], self._fold_left_values[-1]
        if isinstance(value, ParseBranchValue):
            lines, values = self._render_operations(
                value.operations,
                indent,
                error_label,
                required_result_index=value.result_index,
            )
            result = values[value.result_index]
            if result is None:
                raise ValueError("bound branch result has no value")
            return lines, result
        if isinstance(value, DispatchValue):
            return self._render_dispatch_value(
                value,
                indent,
                error_label,
            )
        raise TypeError(type(value))

    def _render_dispatch_value(
        self,
        dispatch: DispatchValue,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str]:
        if not dispatch.branches:
            raise ValueError("value dispatch must have at least one branch")
        result = self._new_temporary()
        branches_by_outcome = {
            branch.outcome: branch for branch in dispatch.branches
        }

        def render_leaf(leaf, leaf_indent: str) -> list[str]:
            if isinstance(leaf, ImmediateError):
                return [
                    self._syntax_error_line(
                        leaf_indent,
                        error_label,
                        leaf.expected,
                    )
                ]
            if isinstance(leaf, ExitDecision):
                raise ValueError("value dispatch must not exit")
            assert isinstance(leaf, CommitAlternative)
            branch = branches_by_outcome.get(leaf.outcome)
            if branch is None:
                raise ValueError("value dispatch references unknown outcome")
            branch_lines, branch_result = self._render_bound_value(
                branch.value,
                leaf_indent,
                error_label,
            )
            branch_lines.append(
                f"{leaf_indent}{result} = {branch_result};"
            )
            return branch_lines

        lines = self._decisions.render(
            dispatch.decision,
            indent=indent,
            token_prefix="ТокенРешения",
            render_leaf=render_leaf,
        )
        return lines, result

    def _render_left_fold(
        self,
        fold: LeftFold,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str]:
        accumulator = self._new_temporary()
        lines = self._render_left_fold_base(
            fold,
            accumulator,
            indent,
            error_label,
        )
        branches_by_outcome = {
            branch.outcome: branch for branch in fold.recursive_branches
        }

        def render_leaf(leaf, leaf_indent: str) -> list[str]:
            if isinstance(leaf, ImmediateError):
                return [
                    self._syntax_error_line(
                        leaf_indent,
                        error_label,
                        leaf.expected,
                    )
                ]
            if isinstance(leaf, ExitDecision):
                return [f"{leaf_indent}Прервать;"]
            assert isinstance(leaf, CommitAlternative)
            branch = branches_by_outcome.get(leaf.outcome)
            if branch is None:
                raise ValueError("left fold references unknown outcome")
            self._fold_left_values.append(accumulator)
            try:
                return self._render_left_fold_recursive_branch(
                    branch,
                    accumulator,
                    leaf_indent,
                    error_label,
                )
            finally:
                self._fold_left_values.pop()

        lines.append(f"{indent}Пока Истина Цикл")
        lines.extend(
            self._decisions.render(
                fold.recursive_decision,
                indent=indent + "\t",
                token_prefix="ТокенРешения",
                render_leaf=render_leaf,
            )
        )
        lines.append(f"{indent}КонецЦикла;")
        return lines, accumulator

    def _render_left_fold_base(
        self,
        fold: LeftFold,
        accumulator: str,
        indent: str,
        error_label: str,
    ) -> list[str]:
        if fold.base_decision is None:
            if len(fold.base_branches) != 1:
                raise ValueError(
                    "left fold without base decision must have one branch"
                )
            return self._render_left_fold_base_branch(
                fold.base_branches[0],
                accumulator,
                indent,
                error_label,
            )

        branches_by_outcome = {
            branch.outcome: branch for branch in fold.base_branches
        }

        def render_leaf(leaf, leaf_indent: str) -> list[str]:
            if isinstance(leaf, ImmediateError):
                return [
                    self._syntax_error_line(
                        leaf_indent,
                        error_label,
                        leaf.expected,
                    )
                ]
            if isinstance(leaf, ExitDecision):
                raise ValueError("left-fold base decision must not exit")
            assert isinstance(leaf, CommitAlternative)
            branch = branches_by_outcome.get(leaf.outcome)
            if branch is None:
                raise ValueError("left-fold base references unknown outcome")
            return self._render_left_fold_base_branch(
                branch,
                accumulator,
                leaf_indent,
                error_label,
            )

        return self._decisions.render(
            fold.base_decision,
            indent=indent,
            token_prefix="ТокенРешения",
            render_leaf=render_leaf,
        )

    def _render_left_fold_base_branch(
        self,
        branch: BranchIr,
        accumulator: str,
        indent: str,
        error_label: str,
    ) -> list[str]:
        lines, values = self._render_operations(
            branch.operations,
            indent,
            error_label,
            required_result_index=(
                None
                if any(
                    isinstance(operation, ConstructNode)
                    for operation in branch.operations
                )
                else branch.result_index
            ),
        )
        value = self._left_fold_branch_value(branch, values)
        lines.append(
            f"{indent}{accumulator} = "
            f"{value if value is not None else 'Неопределено'};"
        )
        return lines

    def _render_left_fold_recursive_branch(
        self,
        branch: BranchIr,
        accumulator: str,
        indent: str,
        error_label: str,
    ) -> list[str]:
        lines, _ = self._render_operations(
            branch.operations,
            indent,
            error_label,
        )
        if any(
            isinstance(operation, ConstructNode)
            for operation in branch.operations
        ):
            lines.append(f"{indent}{accumulator} = ЭтотУзел;")
        return lines

    def _left_fold_branch_value(
        self,
        branch: BranchIr,
        values: list[str | None],
    ) -> str | None:
        if any(
            isinstance(operation, ConstructNode)
            for operation in branch.operations
        ):
            return "ЭтотУзел"
        if branch.result_index is None:
            return None
        value = values[branch.result_index]
        if value is None:
            raise ValueError("left-fold branch result has no value")
        return value

    def _render_dispatch(
        self,
        dispatch: Dispatch,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str | None]:
        result = self._branch_result_temporary(dispatch.branches)
        branches_by_outcome = {
            branch.outcome: branch for branch in dispatch.branches
        }

        def render_leaf(leaf, leaf_indent: str) -> list[str]:
            if isinstance(leaf, ImmediateError):
                return [
                    self._syntax_error_line(
                        leaf_indent,
                        error_label,
                        leaf.expected,
                    )
                ]
            if isinstance(leaf, ExitDecision):
                raise ValueError("dispatch must not exit")
            assert isinstance(leaf, CommitAlternative)
            branch = branches_by_outcome.get(leaf.outcome)
            if branch is None:
                raise ValueError("dispatch references unknown outcome")
            branch_lines, values = self._render_operations(
                branch.operations,
                leaf_indent,
                error_label,
                required_result_index=(
                    branch.result_index if result is not None else None
                ),
            )
            if result is not None:
                assert branch.result_index is not None
                value = values[branch.result_index]
                if value is None:
                    raise ValueError("dispatch branch result has no value")
                branch_lines.append(f"{leaf_indent}{result} = {value};")
            return branch_lines

        lines = self._decisions.render(
            dispatch.decision,
            indent=indent,
            token_prefix="ТокенРешения",
            render_leaf=render_leaf,
        )
        return lines, result

    def _render_optional(
        self,
        optional: OptionalBranch,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str | None]:
        result = self._branch_result_temporary(optional.branches)
        branches_by_outcome = {
            branch.outcome: branch for branch in optional.branches
        }

        def render_leaf(leaf, leaf_indent: str) -> list[str]:
            if isinstance(leaf, ImmediateError):
                return [
                    self._syntax_error_line(
                        leaf_indent,
                        error_label,
                        leaf.expected,
                    )
                ]
            if isinstance(leaf, ExitDecision):
                exit_lines, _ = self._render_operations(
                    optional.exit_operations,
                    leaf_indent,
                    error_label,
                )
                if result is not None:
                    exit_lines.append(
                        f"{leaf_indent}{result} = Неопределено;"
                    )
                return exit_lines
            assert isinstance(leaf, CommitAlternative)
            branch = branches_by_outcome.get(leaf.outcome)
            if branch is None:
                raise ValueError("optional references unknown outcome")
            branch_lines, values = self._render_operations(
                branch.operations,
                leaf_indent,
                error_label,
                required_result_index=(
                    branch.result_index if result is not None else None
                ),
            )
            if result is not None:
                assert branch.result_index is not None
                value = values[branch.result_index]
                if value is None:
                    raise ValueError("optional branch result has no value")
                branch_lines.append(f"{leaf_indent}{result} = {value};")
            return branch_lines

        lines = self._decisions.render(
            optional.decision,
            indent=indent,
            token_prefix="ТокенРешения",
            render_leaf=render_leaf,
        )
        return lines, result

    def _render_wrap_optional(
        self,
        optional: WrapOptional,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str]:
        if any(
            branch.outcome.production != optional.decision.source.production
            for branch in optional.branches
        ):
            return self._render_specialized_wrap_optional(
                optional,
                indent,
                error_label,
            )
        seed_lines, seed_value = self._render_operation(
            optional.seed,
            indent,
            error_label,
        )
        if seed_value is None:
            raise ValueError("returned-child decorator seed has no value")
        accumulator = self._new_temporary()
        lines = [*seed_lines, f"{indent}{accumulator} = {seed_value};"]
        validate_bsl_member_name(optional.property, "wrapped property")
        branches_by_outcome = {
            branch.outcome: branch for branch in optional.branches
        }

        def render_leaf(leaf, leaf_indent: str) -> list[str]:
            if isinstance(leaf, ImmediateError):
                return [
                    self._syntax_error_line(
                        leaf_indent,
                        error_label,
                        leaf.expected,
                    )
                ]
            if isinstance(leaf, ExitDecision):
                return []
            assert isinstance(leaf, CommitAlternative)
            branch = branches_by_outcome.get(leaf.outcome)
            if branch is None:
                raise ValueError("wrapped optional references unknown outcome")
            assert branch.result_index is not None
            branch_lines, values = self._render_operations(
                branch.operations,
                leaf_indent,
                error_label,
                required_result_index=branch.result_index,
            )
            wrapped = values[branch.result_index]
            if wrapped is None:
                raise ValueError(
                    "returned-child decorator branch has no value"
                )
            branch_lines.extend(
                (
                    (
                        f"{leaf_indent}{wrapped}.{optional.property}.Вставить(0, {accumulator});"
                        if optional.prepend
                        else f"{leaf_indent}{wrapped}.{optional.property} = {accumulator};"
                    ),
                    f"{leaf_indent}{accumulator} = {wrapped};",
                )
            )
            return branch_lines

        lines.extend(
            self._decisions.render(
                optional.decision,
                indent=indent,
                token_prefix="ТокенРешения",
                render_leaf=render_leaf,
            )
        )
        return lines, accumulator

    def _render_specialized_wrap_optional(
        self,
        optional: WrapOptional,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str]:
        seed_lines, seed_value = self._render_operation(
            optional.seed,
            indent,
            error_label,
        )
        if seed_value is None:
            raise ValueError("returned-child decorator seed has no value")
        accumulator = self._new_temporary()
        selected = self._new_temporary()
        branch_result = self._new_temporary()
        lines = [*seed_lines, f"{indent}{accumulator} = {seed_value};"]
        branches_by_outcome = {
            branch.outcome: branch for branch in optional.branches
        }
        outcome_codes = {
            branch.outcome: position
            for position, branch in enumerate(optional.branches, start=1)
        }

        def render_leaf(leaf, leaf_indent: str) -> list[str]:
            if isinstance(leaf, ImmediateError):
                return [
                    self._syntax_error_line(
                        leaf_indent,
                        error_label,
                        leaf.expected,
                    )
                ]
            if isinstance(leaf, ExitDecision):
                return [f"{leaf_indent}{selected} = 0;"]
            assert isinstance(leaf, CommitAlternative)
            code = outcome_codes.get(leaf.outcome)
            if code is None:
                raise ValueError(
                    "specialized wrapped optional references unknown outcome"
                )
            return [f"{leaf_indent}{selected} = {code};"]

        lines.extend(
            self._decisions.render(
                optional.decision,
                indent=indent,
                token_prefix="ТокенРешения",
                render_leaf=render_leaf,
            )
        )
        for position, branch in enumerate(optional.branches, start=1):
            keyword = "Если" if position == 1 else "ИначеЕсли"
            lines.append(f"{indent}{keyword} {selected} = {position} Тогда")
            branch_lines, values = self._render_operations(
                branch.operations,
                indent + "\t",
                error_label,
                required_result_index=branch.result_index,
            )
            lines.extend(branch_lines)
            value = self._specialized_branch_result(branch, values)
            lines.append(f"{indent}\t{branch_result} = {value};")
        lines.append(f"{indent}КонецЕсли;")

        validate_bsl_member_name(optional.property, "wrapped property")
        lines.append(f"{indent}Если {selected} <> 0 Тогда")
        binding = (
            f"{branch_result}.{optional.property}.Вставить(0, {accumulator});"
            if optional.prepend
            else f"{branch_result}.{optional.property} = {accumulator};"
        )
        lines.extend(
            (
                f"{indent}\t{binding}",
                f"{indent}\t{accumulator} = {branch_result};",
                f"{indent}КонецЕсли;",
            )
        )
        return lines, accumulator

    def _specialized_branch_result(
        self,
        branch: BranchIr,
        values: list[str | None],
    ) -> str:
        if branch.result_index is not None:
            value = values[branch.result_index]
            if value is None:
                raise ValueError("specialized branch result has no value")
            return value
        if any(
            isinstance(operation, ConstructNode)
            for operation in branch.operations
        ):
            return "ЭтотУзел"
        raise ValueError("specialized branch does not produce a value")

    def _render_wrap_value(
        self,
        wrapped: WrapValue,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], str]:
        seed_lines, seed_value = self._render_operation(
            wrapped.seed,
            indent,
            error_label,
        )
        if seed_value is None:
            raise ValueError("returned-child decorator seed has no value")
        child_lines, child_value = self._render_bound_value(
            wrapped.value,
            indent,
            error_label,
        )
        validate_bsl_member_name(wrapped.property, "wrapped property")
        binding = (
            f"{child_value}.{wrapped.property}.Вставить(0, {seed_value});"
            if wrapped.prepend
            else f"{child_value}.{wrapped.property} = {seed_value};"
        )
        return (
            [
                *seed_lines,
                *child_lines,
                f"{indent}{binding}",
            ],
            child_value,
        )

    def _render_repeat(
        self,
        repeat: RepeatLoop,
        indent: str,
        error_label: str,
    ) -> tuple[list[str], None]:
        branches_by_outcome = {
            branch.outcome: branch for branch in repeat.branches
        }

        def render_leaf(leaf, leaf_indent: str) -> list[str]:
            if isinstance(leaf, ImmediateError):
                return [
                    self._syntax_error_line(
                        leaf_indent,
                        error_label,
                        leaf.expected,
                    )
                ]
            if isinstance(leaf, ExitDecision):
                return [f"{leaf_indent}Прервать;"]
            assert isinstance(leaf, CommitAlternative)
            branch = branches_by_outcome.get(leaf.outcome)
            if branch is None:
                raise ValueError("repeat references unknown outcome")
            body, _ = self._render_operations(
                branch.operations,
                leaf_indent,
                error_label,
            )
            return body

        lines = [f"{indent}Пока Истина Цикл"]
        lines.extend(
            self._decisions.render(
                repeat.decision,
                indent=indent + "\t",
                token_prefix="ТокенРешения",
                render_leaf=render_leaf,
            )
        )
        lines.append(f"{indent}КонецЦикла;")
        return lines, None

    def _branch_result_temporary(
        self,
        branches: tuple[BranchIr, ...],
    ) -> str | None:
        has_result = tuple(
            branch.result_index is not None
            for branch in branches
        )
        if any(has_result) and not all(has_result):
            raise ValueError(
                "control-flow branches have inconsistent semantic results"
            )
        return self._new_temporary() if all(has_result) else None

    def _new_temporary(self) -> str:
        self._temporary += 1
        return f"Значение{self._temporary}"

    def _record_constructor(self, name: str) -> None:
        key = name.casefold()
        if key in self._seen_constructors:
            return
        self._seen_constructors.add(key)
        self._constructors.append(name)

    def _syntax_error_line(
        self,
        indent: str,
        label: str,
        expected: tuple[str, ...] = (),
    ) -> str:
        if len(expected) == 1:
            token = (
                "конец ввода"
                if expected[0] == _END_TOKEN
                else expected[0]
            )
            return (
                f"{indent}ВызватьИсключениеСинтаксическаяОшибка("
                f"{bsl_string(token)}, Истина);"
            )
        if 1 < len(expected) <= 3:
            rendered = ", ".join(
                "конец ввода"
                if token == _END_TOKEN
                else f'"{token}"'
                for token in expected
            )
            return (
                f"{indent}"
                "ВызватьИсключениеСинтаксическаяОшибкаОжидаемыеТокены("
                f"{bsl_string(rendered)});"
            )
        return (
            f"{indent}ВызватьИсключениеСинтаксическаяОшибка("
            f"{bsl_string(label)});"
        )


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
