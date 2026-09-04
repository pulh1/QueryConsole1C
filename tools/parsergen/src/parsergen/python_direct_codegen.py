from __future__ import annotations

from dataclasses import dataclass
from pprint import pformat
from typing import TYPE_CHECKING, Mapping

from .decision_dag import CommitAlternative, ExitDecision, ImmediateError, LookaheadDecision
from .model import Constant, IdentifierRef, Lexeme, NonterminalCall, SyntaxSymbol, Terminal
from .parser_ir import (
    AppendCollection,
    AssignConstant,
    BindScalar,
    BranchIr,
    ConcatScalar,
    ConsumeKnownSymbol,
    ConstructNode,
    DiscardSymbol,
    Dispatch,
    DispatchValue,
    ExtendCollection,
    FoldLeftValue,
    IncrementScalar,
    LeftFold,
    Operation,
    OptionalBranch,
    ParseBranchValue,
    ParseSymbol,
    ParserIr,
    RepeatLoop,
    ResolvedRegion,
    ReturnConstant,
    UndefinedValue,
    WrapOptional,
    WrapValue,
)
from .source_model import SourceGrammar

if TYPE_CHECKING:
    from .direct_render_analysis import DirectRenderAnalysis
    from .python_semantic_codegen import AstNodeSchema


PYTHON_SEMANTIC_BACKEND_ID = "python-semantic-direct-v1"


@dataclass(frozen=True, slots=True)
class _ConstructorSite:
    name: str
    trail: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _LocalContinuationFinish:
    number: int
    layout: ContinuationLayout
    operation: Operation
    trail: tuple[int, ...]
    constructor_site: _ConstructorSite | None
    result_index: int | None
    operations: tuple[Operation, ...]


class _DirectPythonRenderer:
    def __init__(
        self,
        source: SourceGrammar,
        parser_ir: ParserIr,
        entrypoints: Mapping[str, str],
        schema: tuple[AstNodeSchema, ...],
        analysis: DirectRenderAnalysis,
    ) -> None:
        self.source = source
        self.parser_ir = parser_ir
        self.entrypoints = dict(entrypoints)
        self.schema = schema
        self.analysis = analysis
        self.production_names = {
            item.name: f"_p_{index:04d}"
            for index, item in enumerate(parser_ir.productions)
        }
        self.identifier_types = {
            item.name: item.token_types for item in source.identifier_definitions
        }
        self.schema_by_name = {item.name: item for item in schema}
        self.local_names: dict[tuple[tuple[int, ...], str], str] = {}
        self.used_local_names: set[str] = set()
        self._decision_facts_index = 0
        self._active_fold_accumulator: str | None = None
        self._rendering_production: str | None = None
        self._rendering_alternative: int | None = None
        self._safe_tail_sites = frozenset(
            (call.site.production, call.site.alternative, call.site.trail)
            for call in analysis.recursive_calls
            if call.kind == "safe_tail_loop"
        )
        self._local_continuation_sites = {
            (call.site.production, call.site.alternative, call.site.trail): call
            for call in analysis.recursive_calls
            if call.kind == "local_continuation"
        }
        self._continuation_finishes: dict[int, _LocalContinuationFinish] = {}
        self._continuation_site_numbers: dict[object, int] = {}
        self._rendering_operations: tuple[Operation, ...] = ()
        self._rendering_result_index: int | None = None
        self._has_local_continuations = False

    def render(self) -> str:
        return "\n\n".join((self._render_prelude(), self._render_parser())) + "\n"

    def _render_prelude(self) -> str:
        lines = [
            "from __future__ import annotations",
            "",
            "from dataclasses import dataclass, replace",
            "",
            "",
            "@dataclass(frozen=True, slots=True)",
            "class SourceSpan:",
            "    start: int",
            "    end: int",
        ]
        for node in self.schema:
            lines.extend(("", "", "@dataclass(frozen=True, slots=True)", f"class {node.name}:"))
            for field in node.fields:
                lines.append(f"    {field.name}: object")
            lines.append("    span: SourceSpan")
        lines.extend(("", "", "AST_CLASSES = {"))
        lines.extend(f'    "{node.name}": {node.name},' for node in self.schema)
        lines.append("}")
        defaults = {
            node.name: tuple((field.name, field.category) for field in node.fields)
            for node in self.schema
        }
        lines.extend(("", f"NODE_DEFAULTS = {pformat(defaults, width=100, sort_dicts=True)}"))
        return "\n".join(lines)

    def _render_productions(self) -> str:
        return "\n\n".join(self._render_production(item) for item in self.parser_ir.productions)

    def _render_production(self, production) -> str:
        self.local_names = {}
        self.used_local_names = {
            "start",
            "outcome",
            *(
                name
                for alternative in production.alternatives
                for name in self._value_names(alternative.operations, ())
            ),
        }
        self._rendering_production = production.name
        local_calls = [
            call
            for (site_production, _, _), call in self._local_continuation_sites.items()
            if site_production == production.name
        ]
        self._continuation_finishes = {}
        self._continuation_site_numbers = {
            call: index for index, call in enumerate(local_calls)
        }
        self._has_local_continuations = bool(local_calls)
        has_safe_tail_loop = any(
            site_production == production.name
            for site_production, _, _ in self._safe_tail_sites
        )
        has_iteration_loop = has_safe_tail_loop or self._has_local_continuations
        indent = "            " if has_iteration_loop else "        "
        body = [f"{indent}start = self._offset()"]
        if production.decision is None:
            if len(production.alternatives) != 1:
                raise ValueError("production alternatives require a canonical decision")
            self._rendering_alternative = production.alternatives[0].index
            body.extend(self._render_alternative(production.alternatives[0], indent))
            self._rendering_alternative = None
        else:
            body.extend(self._render_decision(production.decision, indent, "outcome"))
            for index, alternative in enumerate(production.alternatives):
                prefix = "if" if index == 0 else "elif"
                body.append(
                    f"{indent}{prefix} outcome == ({production.name!r}, {alternative.index + 1!r}):"
                )
                self._rendering_alternative = alternative.index
                body.extend(self._render_alternative(alternative, indent + "    "))
            body.extend(
                (
                    f"{indent}else:",
                    f"{indent}    raise RuntimeError(f\"decision outcome has no semantic branch: {{outcome!r}}\")",
                )
            )
        if self._has_local_continuations and len(self._continuation_finishes) != len(local_calls):
            raise ValueError("direct renderer did not render every local continuation site")
        lines = [f"    def {self.production_names[production.name]}(self):"]
        if self._has_local_continuations:
            lines.append("        continuations = []")
            if len(local_calls) > 1:
                lines.append("        continuation_sites = []")
            for finish in self._continuation_finishes.values():
                lines.extend(self._render_continuation_finish(finish, "        "))
        if has_iteration_loop:
            lines.append("        while True:")
        lines.extend(body)
        if self._has_local_continuations:
            lines.extend(self._render_continuation_unwind("        "))
        self._rendering_alternative = None
        self._rendering_production = None
        self._has_local_continuations = False
        return "\n".join(lines)

    def _render_alternative(self, alternative, indent: str) -> list[str]:
        previous_operations = self._rendering_operations
        previous_result_index = self._rendering_result_index
        self._rendering_operations = alternative.operations
        self._rendering_result_index = alternative.result_index
        try:
            body, constructor_site = self._render_sequence(
                alternative.operations,
                alternative.result_index,
                indent,
                (),
                None,
            )
        finally:
            self._rendering_operations = previous_operations
            self._rendering_result_index = previous_result_index
        result = (
            "None"
            if constructor_site is None and alternative.result_index is None
            else (
                self._value_name((alternative.result_index,))
                if constructor_site is None
                else self._freeze_expression(constructor_site, "start")
            )
        )
        if self._has_local_continuations:
            body.extend((f"{indent}result = {result}", f"{indent}break"))
            return body
        if constructor_site is None:
            body.append(f"{indent}return {result}")
        else:
            body.append(f"{indent}return {result}")
        return body

    def _render_decision(self, decision, indent: str, outcome: str) -> list[str]:
        facts = self._next_decision_facts(decision)
        if any(indegree > 1 for indegree in facts.node_indegrees):
            return self._render_shared_decision(decision, indent, outcome)
        return self._render_tree_decision(decision, decision.dag.root, indent, outcome)

    def _next_decision_facts(self, decision) -> object:
        try:
            facts = self.analysis.decisions[self._decision_facts_index]
        except IndexError as error:
            raise ValueError("direct render analysis is missing decision facts") from error
        self._decision_facts_index += 1
        if len(facts.node_indegrees) != len(decision.dag.nodes):
            raise ValueError("decision facts do not match canonical DAG")
        return facts

    def _render_tree_decision(
        self,
        decision,
        node_index: int,
        indent: str,
        outcome: str,
    ) -> list[str]:
        node = decision.dag.nodes[node_index]
        if isinstance(node, CommitAlternative):
            return [f"{indent}{outcome} = ({node.outcome.production!r}, {node.outcome.alternative!r})"]
        if isinstance(node, ExitDecision):
            return [f"{indent}{outcome} = ({node.outcome.production!r}, {node.outcome.alternative!r})"]
        if isinstance(node, ImmediateError):
            return [f"{indent}self._syntax_error({node.expected!r})"]
        if not isinstance(node, LookaheadDecision):
            raise TypeError(type(node))
        lines: list[str] = []
        for edge_index, edge in enumerate(node.edges):
            prefix = "if" if edge_index == 0 else "elif"
            lines.append(
                f"{indent}{prefix} self._type_at({node.offset!r}) in {edge.predicate.token_types!r}:"
            )
            lines.extend(
                self._render_tree_decision(
                    decision,
                    edge.target,
                    indent + "    ",
                    outcome,
                )
            )
        lines.extend((f"{indent}else:", f"{indent}    self._syntax_error({node.expected!r})"))
        return lines

    def _render_shared_decision(self, decision, indent: str, outcome: str) -> list[str]:
        state = "decision_state"
        lines = [f"{indent}{state} = {decision.dag.root!r}", f"{indent}while True:"]
        for node_index, node in enumerate(decision.dag.nodes):
            lines.append(f"{indent}    if {state} == {node_index!r}:")
            if isinstance(node, CommitAlternative):
                lines.extend(
                    (
                        f"{indent}        {outcome} = ({node.outcome.production!r}, {node.outcome.alternative!r})",
                        f"{indent}        break",
                    )
                )
                continue
            if isinstance(node, ExitDecision):
                lines.extend(
                    (
                        f"{indent}        {outcome} = ({node.outcome.production!r}, {node.outcome.alternative!r})",
                        f"{indent}        break",
                    )
                )
                continue
            if isinstance(node, ImmediateError):
                lines.append(f"{indent}        self._syntax_error({node.expected!r})")
                continue
            if not isinstance(node, LookaheadDecision):
                raise TypeError(type(node))
            for edge_index, edge in enumerate(node.edges):
                prefix = "if" if edge_index == 0 else "elif"
                lines.append(
                    f"{indent}        {prefix} self._type_at({node.offset!r}) in {edge.predicate.token_types!r}:"
                )
                lines.extend(
                    (
                        f"{indent}            {state} = {edge.target!r}",
                        f"{indent}            continue",
                    )
                )
            lines.extend(
                (
                    f"{indent}        else:",
                    f"{indent}            self._syntax_error({node.expected!r})",
                )
            )
        lines.append(f"{indent}    raise RuntimeError(f\"invalid decision state: {{{state}!r}}\")")
        return lines

    def _render_branch_selection(
        self,
        branches: tuple[BranchIr, ...],
        outcome: str,
        indent: str,
        render_branch,
    ) -> list[str]:
        """Render original-order outcome/path-fact matching for branch operations."""
        lines: list[str] = []
        for index, branch in enumerate(branches):
            facts = () if branch.path_facts is None else branch.path_facts
            conditions = [
                f"{outcome} == ({branch.outcome.production!r}, {branch.outcome.alternative!r})"
            ]
            conditions.extend(
                f"self._type_at({fact.offset!r}) in {fact.predicate.token_types!r}"
                for fact in facts
            )
            prefix = "if" if index == 0 else "elif"
            lines.append(f"{indent}{prefix} {' and '.join(conditions)}:")
            lines.extend(render_branch(branch, indent + "    "))
        lines.extend(
            (
                f"{indent}else:",
                f"{indent}    raise RuntimeError(f\"decision outcome has no semantic branch: {{{outcome}!r}}\")",
            )
        )
        return lines

    def _render_sequence(
        self,
        operations: tuple[Operation, ...],
        result_index: int | None,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> tuple[list[str], _ConstructorSite | None]:
        lines: list[str] = []
        for index, operation in enumerate(operations):
            operation_lines, constructor_site = self._render_operation(
                operation,
                indent,
                (*trail, index),
                constructor_site,
            )
            lines.extend(operation_lines)
        return lines, constructor_site

    def _render_operation(
        self,
        operation: Operation,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> tuple[list[str], _ConstructorSite | None]:
        value = self._value_name(trail)
        if self._is_safe_tail_call(trail):
            return [f"{indent}continue"], constructor_site
        continuation = self._local_continuation_site(trail, operation)
        if continuation is not None:
            return (
                self._render_local_continuation_push(
                    continuation,
                    operation,
                    trail,
                    constructor_site,
                    indent,
                ),
                constructor_site,
            )
        if isinstance(operation, ParseSymbol):
            if isinstance(operation.symbol, NonterminalCall):
                return [f"{indent}{value} = self.{self._production_name(operation.symbol.name)}()"], constructor_site
            expected, capture = self._terminal_parts(operation.symbol)
            return [f"{indent}{value} = self._consume({expected!r}, {capture!r})"], constructor_site
        if isinstance(operation, DiscardSymbol):
            if isinstance(operation.symbol, NonterminalCall):
                return [f"{indent}self.{self._production_name(operation.symbol.name)}()"], constructor_site
            expected, _ = self._terminal_parts(operation.symbol)
            return [f"{indent}self._consume({expected!r}, False)"], constructor_site
        if isinstance(operation, ConsumeKnownSymbol):
            expected, capture = self._terminal_parts(operation.symbol)
            if operation.capture_value:
                return [f"{indent}{value} = self._consume({expected!r}, {capture!r})"], constructor_site
            return [f"{indent}self._consume({expected!r}, False)"], constructor_site
        if isinstance(operation, ResolvedRegion):
            lines, _ = self._render_sequence(
                operation.operations,
                operation.result_index,
                indent,
                (*trail, 0),
                constructor_site,
            )
            if operation.result_index is None:
                lines.append(f"{indent}{value} = None")
            else:
                lines.append(
                    f"{indent}{value} = {self._value_name((*trail, 0, operation.result_index))}"
                )
            return lines, constructor_site
        if isinstance(operation, Dispatch):
            outcome = self._control_name("outcome", trail)
            lines = self._render_decision(operation.decision, indent, outcome)
            lines.extend(
                self._render_branch_selection(
                    operation.branches,
                    outcome,
                    indent,
                    lambda branch, branch_indent: self._render_branch_result(
                        branch,
                        value,
                        branch_indent,
                        (*trail, operation.branches.index(branch)),
                        constructor_site,
                    ),
                )
            )
            return lines, constructor_site
        if isinstance(operation, OptionalBranch):
            outcome = self._control_name("outcome", trail)
            lines = self._render_decision(operation.decision, indent, outcome)
            exit_conditions = self._exit_conditions(operation.decision, outcome)
            branch_indent = indent + "    " if exit_conditions else indent
            branch_lines = self._render_branch_selection(
                operation.branches,
                outcome,
                branch_indent,
                lambda branch, selected_indent: self._render_branch_result(
                    branch,
                    value,
                    selected_indent,
                    (*trail, operation.branches.index(branch)),
                    constructor_site,
                ),
            )
            if exit_conditions:
                lines.append(f"{indent}if {' or '.join(exit_conditions)}:")
                exit_lines = self._render_sequence_result(
                    operation.exit_operations,
                    None,
                    value,
                    indent + "    ",
                    (*trail, len(operation.branches)),
                    constructor_site,
                )
                lines.extend(exit_lines)
                lines.append(f"{indent}    {value} = None")
                lines.append(f"{indent}else:")
            lines.extend(branch_lines)
            return lines, constructor_site
        if isinstance(operation, RepeatLoop):
            outcome = self._control_name("outcome", trail)
            position = self._control_name("repeat_position", trail)
            exit_conditions = self._exit_conditions(operation.decision, outcome)
            lines = [f"{indent}while True:", f"{indent}    {position} = self._position"]
            lines.extend(self._render_decision(operation.decision, indent + "    ", outcome))
            if exit_conditions:
                lines.append(f"{indent}    if {' or '.join(exit_conditions)}:")
                lines.append(f"{indent}        break")
            lines.extend(
                self._render_branch_selection(
                    operation.branches,
                    outcome,
                    indent + "    ",
                    lambda branch, branch_indent: self._render_branch_operations(
                        branch,
                        branch_indent,
                        (*trail, operation.branches.index(branch)),
                        constructor_site,
                    ),
                )
            )
            lines.extend(
                (
                    f"{indent}    if self._position == {position}:",
                    f"{indent}        raise RuntimeError('repeat branch did not advance parser cursor')",
                    f"{indent}{value} = None",
                )
            )
            return lines, constructor_site
        if isinstance(operation, WrapValue):
            return self._render_wrap_value(
                operation,
                value,
                indent,
                trail,
                constructor_site,
            ), constructor_site
        if isinstance(operation, WrapOptional):
            return self._render_wrap_optional(
                operation,
                value,
                indent,
                trail,
                constructor_site,
            ), constructor_site
        if isinstance(operation, LeftFold):
            return self._render_left_fold(operation, value, indent, trail, constructor_site), constructor_site
        if isinstance(operation, (UndefinedValue, ReturnConstant)):
            return [f"{indent}{value} = {self._constant(operation.value)!r}"], constructor_site
        if isinstance(operation, ConstructNode):
            site = _ConstructorSite(operation.constructor, trail)
            return self._construct_locals(site, indent), site
        if isinstance(operation, BindScalar):
            return self._render_binding(
                operation.value,
                f"{self._field_local(constructor_site, operation.property)} = {value}",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, AppendCollection):
            property_name = "items" if operation.property is None else operation.property
            return self._render_binding(
                operation.value,
                f"{self._field_local(constructor_site, property_name)}.append({value})",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, ExtendCollection):
            target = self._field_local(constructor_site, operation.property)
            return self._render_binding(
                operation.value,
                f"{target}.extend({value}.items if hasattr({value}, 'items') else {value}) if {value} is not None else None",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, ConcatScalar):
            return self._render_binding(
                operation.value,
                f"{self._field_local(constructor_site, operation.property)} += {value}",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, IncrementScalar):
            return self._render_binding(
                operation.value,
                f"{self._field_local(constructor_site, operation.property)} += 1",
                indent,
                trail,
                constructor_site,
            )
        if isinstance(operation, AssignConstant):
            return [
                f"{indent}{self._field_local(constructor_site, operation.property)} = {self._constant(operation.value)!r}"
            ], constructor_site
        raise TypeError(
            f"direct renderer does not support {type(operation).__name__} before its task"
        )

    def _is_safe_tail_call(self, trail: tuple[int, ...]) -> bool:
        if (
            self._rendering_production is None
            or self._rendering_alternative is None
            or len(trail) != 1
        ):
            return False
        return (
            self._rendering_production,
            self._rendering_alternative,
            (("operation", trail[0]),),
        ) in self._safe_tail_sites

    def _local_continuation_site(self, trail: tuple[int, ...], operation: Operation):
        if (
            self._rendering_production is None
            or self._rendering_alternative is None
            or len(trail) != 1
        ):
            return None
        operation_site = (("operation", trail[0]),)
        key = (
            self._rendering_production,
            self._rendering_alternative,
            operation_site,
        )
        continuation = self._local_continuation_sites.get(key)
        if continuation is not None:
            return continuation
        return self._local_continuation_sites.get(
            (
                self._rendering_production,
                self._rendering_alternative,
                (*operation_site, ("value", 0)),
            )
        )

    def _render_local_continuation_push(
        self,
        continuation,
        operation: Operation,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
        indent: str,
    ) -> list[str]:
        if continuation.layout is None:
            raise ValueError("local continuation is missing its layout")
        number = self._continuation_site_numbers[continuation]
        existing = self._continuation_finishes.get(number)
        finish = _LocalContinuationFinish(
            number,
            continuation.layout,
            operation,
            trail,
            constructor_site,
            self._rendering_result_index,
            self._rendering_operations,
        )
        if existing is not None and existing != finish:
            raise ValueError("local continuation site was rendered inconsistently")
        self._continuation_finishes[number] = finish
        saved = ", ".join(
            self._continuation_slot_expression(slot, finish)
            for slot in continuation.layout.slots
        )
        if len(continuation.layout.slots) == 1:
            saved += ","
        lines = [f"{indent}continuations.append(({saved}))"]
        if len(self._continuation_site_numbers) > 1:
            lines.append(f"{indent}continuation_sites.append({number!r})")
        return [*lines, f"{indent}continue"]

    def _continuation_slot_expression(
        self,
        slot,
        finish: _LocalContinuationFinish,
    ) -> str:
        if slot.kind == "span_start":
            return "start"
        if slot.kind == "operation_result":
            if slot.index is None:
                raise ValueError("operation-result continuation slot has no index")
            return self._value_name((slot.index,))
        if slot.kind == "wrap_seed":
            if slot.index is None:
                raise ValueError("wrap-seed continuation slot has no index")
            return self._value_name((slot.index, 0))
        if slot.kind in {"builder_field", "collection_accumulator"}:
            if slot.index is None:
                raise ValueError("builder continuation slot has no index")
            try:
                operation = finish.operations[slot.index]
            except IndexError as error:
                raise ValueError("continuation slot is outside its sequence") from error
            if not isinstance(
                operation,
                (BindScalar, AppendCollection, ExtendCollection, ConcatScalar, IncrementScalar),
            ):
                raise ValueError("continuation slot does not name a builder operation")
            property_name = (
                "items"
                if isinstance(operation, AppendCollection) and operation.property is None
                else operation.property
            )
            return self._field_local(finish.constructor_site, property_name)
        if slot.kind == "fold_accumulator":
            raise ValueError("fold continuation is not supported by direct right recursion")
        raise TypeError(slot.kind)

    def _render_continuation_finish(
        self,
        finish: _LocalContinuationFinish,
        indent: str,
    ) -> list[str]:
        restored = [
            self._continuation_slot_expression(slot, finish)
            for slot in finish.layout.slots
        ]
        lines = [f"{indent}def finish_site_{finish.number}(saved, result):"]
        if len(restored) == 1:
            lines.append(f"{indent}    {restored[0]}, = saved")
        else:
            lines.append(f"{indent}    {', '.join(restored)} = saved")
        lines.extend(self._render_continuation_result_binding(finish, indent + "    "))
        lines.append(f"{indent}    {self._continuation_finish_return(finish)}")
        return lines

    def _render_continuation_result_binding(
        self,
        finish: _LocalContinuationFinish,
        indent: str,
    ) -> list[str]:
        operation = finish.operation
        if isinstance(operation, BindScalar):
            return [
                f"{indent}{self._field_local(finish.constructor_site, operation.property)} = result"
            ]
        if isinstance(operation, AppendCollection):
            property_name = "items" if operation.property is None else operation.property
            return [
                f"{indent}{self._field_local(finish.constructor_site, property_name)}.append(result)"
            ]
        if isinstance(operation, ExtendCollection):
            target = self._field_local(finish.constructor_site, operation.property)
            return [
                f"{indent}{target}.extend(result.items if hasattr(result, 'items') else result) if result is not None else None"
            ]
        if isinstance(operation, ConcatScalar):
            return [
                f"{indent}{self._field_local(finish.constructor_site, operation.property)} += result"
            ]
        if isinstance(operation, IncrementScalar):
            return [
                f"{indent}{self._field_local(finish.constructor_site, operation.property)} += 1"
            ]
        if isinstance(operation, WrapValue):
            target = self._value_name(finish.trail)
            seed = self._value_name((*finish.trail, 0))
            return [
                f"{indent}{target} = result",
                *self._render_wrap_apply(
                    target,
                    seed,
                    operation.property,
                    operation.prepend,
                    indent,
                ),
            ]
        if isinstance(operation, ParseSymbol):
            return [f"{indent}{self._value_name(finish.trail)} = result"]
        if isinstance(operation, DiscardSymbol):
            return []
        raise TypeError(
            f"direct renderer cannot finish {type(operation).__name__} local continuation"
        )

    def _continuation_finish_return(self, finish: _LocalContinuationFinish) -> str:
        if finish.constructor_site is not None:
            return f"return {self._freeze_expression(finish.constructor_site, 'start')}"
        if finish.result_index is None:
            return "return None"
        return f"return {self._value_name((finish.result_index,))}"

    def _render_continuation_unwind(self, indent: str) -> list[str]:
        finishes = tuple(self._continuation_finishes.values())
        lines = [f"{indent}while continuations:", f"{indent}    saved = continuations.pop()"]
        if len(finishes) == 1:
            lines.append(f"{indent}    result = finish_site_0(saved, result)")
        else:
            lines.append(f"{indent}    continuation_site = continuation_sites.pop()")
            for index, finish in enumerate(finishes):
                prefix = "if" if index == 0 else "elif"
                lines.append(f"{indent}    {prefix} continuation_site == {finish.number!r}:")
                lines.append(
                    f"{indent}        result = finish_site_{finish.number}(saved, result)"
                )
            lines.extend(
                (
                    f"{indent}    else:",
                    f"{indent}        raise RuntimeError('unknown local continuation site')",
                )
            )
        lines.append(f"{indent}return result")
        return lines

    def _render_binding(
        self,
        bound_value: object,
        apply: str,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> tuple[list[str], _ConstructorSite | None]:
        if constructor_site is None:
            raise RuntimeError("semantic binding has no active constructor")
        if not isinstance(
            bound_value,
            (
                ParseSymbol,
                ConsumeKnownSymbol,
                UndefinedValue,
                ParseBranchValue,
                DispatchValue,
                FoldLeftValue,
            ),
        ):
            raise TypeError(
                f"direct renderer does not support {type(bound_value).__name__} bound values before its task"
            )
        lines = self._render_bound_value(bound_value, indent, trail, constructor_site)
        lines.append(f"{indent}{apply}")
        return lines, constructor_site

    def _render_bound_value(
        self,
        bound_value: object,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> list[str]:
        value = self._value_name(trail)
        if isinstance(bound_value, (ParseSymbol, ConsumeKnownSymbol, UndefinedValue)):
            lines, _ = self._render_operation(bound_value, indent, trail, constructor_site)
            return lines
        if isinstance(bound_value, FoldLeftValue):
            if self._active_fold_accumulator is None:
                raise ValueError("fold-left value used outside LeftFold")
            return [f"{indent}{value} = {self._active_fold_accumulator}"]
        if isinstance(bound_value, ParseBranchValue):
            return self._render_parse_branch_value(
                bound_value,
                value,
                indent,
                (*trail, 0),
                constructor_site,
            )
        if isinstance(bound_value, DispatchValue):
            outcome = self._control_name("outcome", trail)
            lines = self._render_decision(bound_value.decision, indent, outcome)
            for index, branch in enumerate(bound_value.branches):
                prefix = "if" if index == 0 else "elif"
                lines.append(
                    f"{indent}{prefix} {outcome} == ({branch.outcome.production!r}, {branch.outcome.alternative!r}):"
                )
                lines.extend(
                    self._render_parse_branch_value(
                        branch.value,
                        value,
                        indent + "    ",
                        (*trail, index, 0),
                        constructor_site,
                    )
                )
            lines.extend(
                (
                    f"{indent}else:",
                    f"{indent}    raise RuntimeError(f\"value decision outcome has no branch: {{{outcome}!r}}\")",
                )
            )
            return lines
        raise TypeError(type(bound_value))

    def _render_parse_branch_value(
        self,
        branch_value: ParseBranchValue,
        target: str,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> list[str]:
        lines, _ = self._render_sequence(
            branch_value.operations,
            branch_value.result_index,
            indent,
            trail,
            constructor_site,
        )
        lines.append(f"{indent}{target} = {self._value_name((*trail, branch_value.result_index))}")
        return lines

    def _render_branch_result(
        self,
        branch: BranchIr,
        target: str,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
        *,
        start_override: str | None = None,
        none_result: str | None = None,
    ) -> list[str]:
        return self._render_sequence_result(
            branch.operations,
            branch.result_index,
            target,
            indent,
            trail,
            constructor_site,
            start_override=start_override,
            none_result=none_result,
        )

    def _render_sequence_result(
        self,
        operations: tuple[Operation, ...],
        result_index: int | None,
        target: str,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
        *,
        start_override: str | None = None,
        none_result: str | None = None,
    ) -> list[str]:
        has_construct = self._has_construct(operations)
        start = start_override or self._control_name("branch_start", trail)
        lines = (
            []
            if not has_construct or start_override is not None
            else [f"{indent}{start} = self._offset()"]
        )
        sequence_lines, branch_constructor = self._render_sequence(
            operations,
            result_index,
            indent,
            trail,
            constructor_site,
        )
        lines.extend(sequence_lines)
        if has_construct:
            if branch_constructor is None:
                raise RuntimeError("branch constructor is missing")
            lines.append(f"{indent}{target} = {self._freeze_expression(branch_constructor, start)}")
        elif result_index is None:
            lines.append(f"{indent}{target} = {none_result or 'None'}")
        else:
            lines.append(f"{indent}{target} = {self._value_name((*trail, result_index))}")
        return lines

    def _render_wrap_value(
        self,
        wrapped: WrapValue,
        target: str,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> list[str]:
        seed_trail = (*trail, 0)
        seed, _ = self._render_operation(
            wrapped.seed,
            indent,
            seed_trail,
            constructor_site,
        )
        lines = list(seed)
        seed_value = self._value_name(seed_trail)
        lines.extend(
            self._render_bound_value(
                wrapped.value,
                indent,
                trail,
                constructor_site,
            )
        )
        lines.extend(self._render_wrap_apply(target, seed_value, wrapped.property, wrapped.prepend, indent))
        return lines

    def _render_wrap_optional(
        self,
        wrapped: WrapOptional,
        target: str,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> list[str]:
        seed_trail = (*trail, 0)
        seed, _ = self._render_operation(
            wrapped.seed,
            indent,
            seed_trail,
            constructor_site,
        )
        lines = list(seed)
        seed_value = self._value_name(seed_trail)
        outcome = self._control_name("wrap_outcome", trail)
        lines.extend(self._render_decision(wrapped.decision, indent, outcome))
        exit_conditions = self._exit_conditions(wrapped.decision, outcome)

        def render_branch(branch: BranchIr, branch_indent: str) -> list[str]:
            branch_lines = self._render_branch_result(
                branch,
                target,
                branch_indent,
                (*trail, 1, wrapped.branches.index(branch)),
                constructor_site,
            )
            branch_lines.extend(
                self._render_wrap_apply(
                    target,
                    seed_value,
                    wrapped.property,
                    wrapped.prepend,
                    branch_indent,
                )
            )
            return branch_lines

        if exit_conditions:
            lines.extend(
                (
                    f"{indent}if {' or '.join(exit_conditions)}:",
                    f"{indent}    {target} = {seed_value}",
                    f"{indent}else:",
                )
            )
            lines.extend(
                self._render_branch_selection(
                    wrapped.branches,
                    outcome,
                    indent + "    ",
                    render_branch,
                )
            )
        else:
            lines.extend(
                self._render_branch_selection(wrapped.branches, outcome, indent, render_branch)
            )
        return lines

    @staticmethod
    def _render_wrap_apply(
        target: str,
        seed: str,
        property_name: str,
        prepend: bool,
        indent: str,
    ) -> list[str]:
        replacement = (
            f"({seed}, *(getattr({target}, {property_name!r}) or ()))"
            if prepend
            else seed
        )
        return [f"{indent}{target} = replace({target}, **{{{property_name!r}: {replacement}}})"]

    def _render_left_fold(
        self,
        fold: LeftFold,
        target: str,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> list[str]:
        accumulator = self._control_name("fold_accumulator", trail)
        lines: list[str] = []
        if fold.base_decision is None:
            if len(fold.base_branches) != 1:
                raise ValueError("left fold without a decision requires one base branch")
            lines.extend(
                self._render_branch_result(
                    fold.base_branches[0],
                    accumulator,
                    indent,
                    (*trail, 0),
                    constructor_site,
                    start_override="start",
                )
            )
        else:
            base_outcome = self._control_name("fold_base_outcome", trail)
            lines.extend(self._render_decision(fold.base_decision, indent, base_outcome))
            lines.extend(
                self._render_branch_selection(
                    fold.base_branches,
                    base_outcome,
                    indent,
                    lambda branch, branch_indent: self._render_branch_result(
                        branch,
                        accumulator,
                        branch_indent,
                        (*trail, 0, fold.base_branches.index(branch)),
                        constructor_site,
                        start_override="start",
                    ),
                )
            )

        recursive_outcome = self._control_name("fold_outcome", trail)
        exit_conditions = self._exit_conditions(fold.recursive_decision, recursive_outcome)
        lines.append(f"{indent}while True:")
        lines.extend(self._render_decision(fold.recursive_decision, indent + "    ", recursive_outcome))
        branch_indent = indent + "    "
        if exit_conditions:
            lines.extend(
                (
                    f"{indent}    if {' or '.join(exit_conditions)}:",
                    f"{indent}        break",
                    f"{indent}    else:",
                )
            )
            branch_indent += "    "
        previous = self._active_fold_accumulator
        self._active_fold_accumulator = accumulator
        try:
            lines.extend(
                self._render_branch_selection(
                    fold.recursive_branches,
                    recursive_outcome,
                    branch_indent,
                    lambda branch, selected_indent: self._render_branch_result(
                        branch,
                        accumulator,
                        selected_indent,
                        (*trail, 1, fold.recursive_branches.index(branch)),
                        constructor_site,
                        start_override="start",
                        none_result=accumulator,
                    ),
                )
            )
        finally:
            self._active_fold_accumulator = previous
        lines.append(f"{indent}{target} = {accumulator}")
        return lines

    def _render_branch_operations(
        self,
        branch: BranchIr,
        indent: str,
        trail: tuple[int, ...],
        constructor_site: _ConstructorSite | None,
    ) -> list[str]:
        lines, _ = self._render_sequence(
            branch.operations,
            branch.result_index,
            indent,
            trail,
            constructor_site,
        )
        return lines

    @staticmethod
    def _has_construct(operations: tuple[Operation, ...]) -> bool:
        return any(isinstance(operation, ConstructNode) for operation in operations)

    @staticmethod
    def _exit_conditions(decision, outcome: str) -> list[str]:
        return [
            f"{outcome} == ({node.outcome.production!r}, {node.outcome.alternative!r})"
            for node in decision.dag.nodes
            if isinstance(node, ExitDecision)
        ]

    @staticmethod
    def _control_name(kind: str, trail: tuple[int, ...]) -> str:
        return f"{kind}_" + "_".join(str(item) for item in trail)

    def _construct_locals(self, site: _ConstructorSite, indent: str) -> list[str]:
        try:
            fields = self.schema_by_name[site.name].fields
        except KeyError as error:
            raise ValueError(f"unknown constructor {site.name!r}") from error
        initial = {
            "scalar": "None",
            "collection": "[]",
            "concat": "\"\"",
            "increment": "0",
        }
        return [
            f"{indent}{self._field_local(site, field.name)} = {initial[field.category]}"
            for field in fields
        ]

    def _freeze_expression(self, site: _ConstructorSite, start: str) -> str:
        fields = self.schema_by_name[site.name].fields
        values = [
            (
                f"tuple({self._field_local(site, field.name)})"
                if field.category == "collection"
                else self._field_local(site, field.name)
            )
            for field in fields
        ]
        values.append(f"SourceSpan({start}, self._end_offset({start}))")
        return f"{site.name}({', '.join(values)})"

    def _field_local(self, site: _ConstructorSite | None, property_name: str) -> str:
        if site is None:
            raise RuntimeError("semantic binding has no active constructor")
        fields = self.schema_by_name[site.name].fields
        for field in fields:
            if field.name == property_name:
                return self._allocate_local(site, field.name)
        raise ValueError(f"unknown field {site.name}.{property_name}")

    def _allocate_local(self, site: _ConstructorSite, field_name: str) -> str:
        key = (site.trail, field_name)
        existing = self.local_names.get(key)
        if existing is not None:
            return existing
        base = "node_" + "_".join(str(item) for item in site.trail)
        base = f"{base}_{field_name.casefold()}"
        local = base
        suffix = 2
        while local in self.used_local_names:
            local = f"{base}_{suffix}"
            suffix += 1
        self.used_local_names.add(local)
        self.local_names[key] = local
        return local

    def _value_names(
        self,
        operations: tuple[Operation, ...],
        trail: tuple[int, ...],
    ) -> set[str]:
        names: set[str] = set()
        for index, operation in enumerate(operations):
            operation_trail = (*trail, index)
            names.add(self._value_name(operation_trail))
            if isinstance(operation, ResolvedRegion):
                names.update(self._value_names(operation.operations, (*operation_trail, 0)))
            elif isinstance(operation, (Dispatch, RepeatLoop)):
                for branch_index, branch in enumerate(operation.branches):
                    names.update(
                        self._value_names(branch.operations, (*operation_trail, branch_index))
                    )
            elif isinstance(operation, OptionalBranch):
                for branch_index, branch in enumerate(operation.branches):
                    names.update(
                        self._value_names(branch.operations, (*operation_trail, branch_index))
                    )
                names.update(
                    self._value_names(
                        operation.exit_operations,
                        (*operation_trail, len(operation.branches)),
                    )
                )
            elif isinstance(operation, WrapValue):
                names.update(self._value_names((operation.seed,), (*operation_trail, 0)))
                names.update(self._bound_value_names(operation.value, (*operation_trail, 1)))
            elif isinstance(operation, WrapOptional):
                names.update(self._value_names((operation.seed,), (*operation_trail, 0)))
                for branch_index, branch in enumerate(operation.branches):
                    names.update(
                        self._value_names(
                            branch.operations,
                            (*operation_trail, 1, branch_index),
                        )
                    )
            elif isinstance(operation, LeftFold):
                for branch_index, branch in enumerate(operation.base_branches):
                    names.update(
                        self._value_names(
                            branch.operations,
                            (*operation_trail, 0, branch_index),
                        )
                    )
                for branch_index, branch in enumerate(operation.recursive_branches):
                    names.update(
                        self._value_names(
                            branch.operations,
                            (*operation_trail, 1, branch_index),
                        )
                    )
            elif isinstance(
                operation,
                (BindScalar, AppendCollection, ExtendCollection, ConcatScalar, IncrementScalar),
            ):
                names.update(self._bound_value_names(operation.value, (*operation_trail, 0)))
        return names

    def _bound_value_names(self, value: object, trail: tuple[int, ...]) -> set[str]:
        if isinstance(value, ParseBranchValue):
            return self._value_names(value.operations, trail)
        if isinstance(value, DispatchValue):
            names: set[str] = set()
            for index, branch in enumerate(value.branches):
                names.update(self._value_names(branch.value.operations, (*trail, index, 0)))
            return names
        return set()

    def _render_parser(self) -> str:
        lines = [
            "class GeneratedParseError(ValueError):",
            "    def __init__(self, position, actual, expected):",
            "        self.position = position",
            "        self.actual = actual",
            "        self.expected = tuple(expected)",
            "        super().__init__(",
            "            f\"unexpected {actual!r} at token {position}; expected {self.expected!r}\"",
            "        )",
            "",
            "",
            "class GeneratedParser:",
            "    def parse(self, tokens, entrypoint):",
            "        self._tokens = tuple(tokens)",
            "        self._position = 0",
        ]
        for index, (entrypoint, production) in enumerate(self.entrypoints.items()):
            prefix = "if" if index == 0 else "elif"
            lines.extend(
                (
                    f"        {prefix} entrypoint == {entrypoint!r}:",
                    f"            result = self.{self._production_name(production)}()",
                )
            )
        lines.extend(
            (
                "        else:",
                "            raise ValueError(f\"unknown entrypoint {entrypoint!r}\")",
                "        if self._position != len(self._tokens):",
                "            self._raise(('$',))",
                "        return result",
                "",
                "    def _consume(self, expected, capture):",
                "        actual = self._lookahead(0)",
                "        if actual not in expected:",
                "            self._raise(expected)",
                "        token = self._tokens[self._position]",
                "        self._position += 1",
                "        if not capture:",
                "            return None",
                "        if capture == 'type':",
                "            return token.type",
                "        if capture == 'text':",
                "            return token.text",
                "        value = getattr(token, 'value', None)",
                "        return token.text if value is None else value",
                "",
                "    def _type_at(self, offset):",
                "        index = self._position + offset",
                "        if index >= len(self._tokens):",
                "            return '$'",
                "        return self._tokens[index].type",
                "",
                "    def _lookahead(self, offset):",
                "        return self._type_at(offset)",
                "",
                "    def _offset(self):",
                "        if self._position < len(self._tokens):",
                "            return self._tokens[self._position].start",
                "        if self._tokens:",
                "            return self._tokens[-1].end",
                "        return 0",
                "",
                "    def _end_offset(self, start):",
                "        if self._position:",
                "            end = self._tokens[self._position - 1].end",
                "            if end >= start:",
                "                return end",
                "        return start",
                "",
                "    def _syntax_error(self, expected):",
                "        raise GeneratedParseError(self._position, self._lookahead(0), expected)",
                "",
                "    def _raise(self, expected):",
                "        self._syntax_error(expected)",
            )
        )
        lines.extend(("", *self._render_productions().splitlines()))
        return "\n".join(lines)

    def _terminal_parts(self, symbol: SyntaxSymbol) -> tuple[tuple[str, ...], str]:
        if isinstance(symbol, Terminal):
            return (symbol.token_type,), "type"
        if isinstance(symbol, Lexeme):
            return (symbol.text,), "type"
        if isinstance(symbol, Constant):
            return (symbol.token_type,), "value"
        if isinstance(symbol, IdentifierRef):
            try:
                return self.identifier_types[symbol.name], "text"
            except KeyError as error:
                raise ValueError(
                    f"unknown identifier definition {symbol.name!r}"
                ) from error
        raise TypeError(type(symbol))

    def _production_name(self, production: str) -> str:
        try:
            return self.production_names[production]
        except KeyError as error:
            raise ValueError(f"unknown production {production!r}") from error

    @staticmethod
    def _value_name(trail: tuple[int, ...]) -> str:
        return "value_" + "_".join(str(item) for item in trail)

    @staticmethod
    def _constant(value: str) -> object:
        normalized = value.casefold()
        if normalized == "истина":
            return True
        if normalized == "ложь":
            return False
        if normalized == "неопределено":
            return None
        return value


def render_direct_python_module(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
    schema: tuple[AstNodeSchema, ...],
    analysis: DirectRenderAnalysis,
) -> str:
    return _DirectPythonRenderer(
        source,
        parser_ir,
        entrypoints,
        schema,
        analysis,
    ).render()
