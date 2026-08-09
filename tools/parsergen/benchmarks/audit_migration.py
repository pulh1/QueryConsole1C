from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass
import json
from pathlib import Path
import re
import sys
from time import perf_counter


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SRC = PACKAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from parsergen.model import (
    Action,
    Constant,
    Grammar,
    IdentifierRef,
    Lexeme,
    NonterminalCall,
    Terminal,
)
from parsergen.analysis import (
    build_legacy_matcher_artifact,
    find_canonical_select_conflicts,
)
from parsergen.artifacts import compare_artifacts, render_artifacts
from parsergen.cli import compile_from_config, generate_from_compilation
from parsergen.config import load_config
from parsergen.decision_dag import (
    CommitAlternative,
    aggregate_decision_dag_metrics,
    decision_paths,
    emitted_predicate_token_sets,
)
from parsergen.hybrid_bsl_codegen import generate_hybrid_parser
from parsergen.parser_ir import (
    AppendCollection,
    BindScalar,
    BranchIr,
    CanonicalDecision,
    ConcatScalar,
    ConsumeKnownSymbol,
    DiscardSymbol,
    Dispatch,
    DispatchValue,
    ExtendCollection,
    IncrementScalar,
    LeftFold,
    OptionalBranch,
    ParseBranchValue,
    ParseSymbol,
    RepeatLoop,
    ResolvedRegion,
    WrapOptional,
    WrapValue,
    build_parser_ir,
)
from parsergen.semantic_actions import (
    CONSTRUCTOR,
    _normalize_newlines,
    _split_statements,
    _top_level_assignment,
)


CONSTANT = re.compile(
    r'^(?:Истина|Ложь|Неопределено|Null|-?\d+(?:\.\d+)?|"(?:[^"]|"")*")$',
    re.IGNORECASE,
)
STRUCTURAL_NAMES = (
    "ЭтотУзел",
    "ТекущийЭлемент",
    "Родитель",
    "ЛевыйЭлемент",
)
DECISION_LINE = re.compile(r"^\s*(?:Если|ИначеЕсли|Пока)\b", re.IGNORECASE)
NONTERMINAL_FUNCTION = re.compile(
    r"^\s*Функция\s+НеТерминал", re.IGNORECASE
)
NONTERMINAL_REFERENCE = re.compile(
    r"\bНеТерминал[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*\s*\(",
    re.IGNORECASE,
)
PREDICATE_ATOM = re.compile(
    r"(?:ТипТокенаПросмотра\(\d+\)|ТокенРешения\d+)\s*(?:=|<>)",
    re.IGNORECASE,
)


def _parenthesis_depth(value: str) -> int:
    depth = 0
    maximum = 0
    for char in value:
        if char == "(":
            depth += 1
            maximum = max(maximum, depth)
        elif char == ")":
            depth = max(0, depth - 1)
    return maximum


def generated_bsl_metrics(module_text: str) -> dict[str, int]:
    lines = module_text.splitlines()
    decisions = [line.strip() for line in lines if DECISION_LINE.match(line)]
    return {
        "lookahead_calls": module_text.count("ТипТокенаПросмотра("),
        "decision_lines": len(decisions),
        "predicate_atoms": sum(
            len(PREDICATE_ATOM.findall(line)) for line in decisions
        ),
        "nonterminal_functions": sum(
            NONTERMINAL_FUNCTION.match(line) is not None for line in lines
        ),
        "nonterminal_call_sites": max(
            0,
            len(NONTERMINAL_REFERENCE.findall(module_text))
            - sum(NONTERMINAL_FUNCTION.match(line) is not None for line in lines),
        ),
        "max_condition_chars": max(map(len, decisions), default=0),
        "max_condition_predicate_atoms": max(
            (len(PREDICATE_ATOM.findall(line)) for line in decisions),
            default=0,
        ),
        "max_condition_lookahead_calls": max(
            (line.count("ТипТокенаПросмотра(") for line in decisions),
            default=0,
        ),
        "max_condition_nesting": max(
            (_parenthesis_depth(line) for line in decisions),
            default=0,
        ),
    }


def classify_semantic_actions(grammar: Grammar) -> dict[str, int]:
    counts = {
        "action_blocks": 0,
        "statements": 0,
        "constructor_statements": 0,
        "collection_statements": 0,
        "constant_statements": 0,
        "structural_statements": 0,
        "other_assignment_statements": 0,
        "other_statements": 0,
    }
    for production in grammar.productions:
        for alternative in production.alternatives:
            for element in alternative.elements:
                if not isinstance(element, Action):
                    continue
                counts["action_blocks"] += 1
                statements = _split_statements(
                    _normalize_newlines(element.text)
                )
                counts["statements"] += len(statements)
                for statement in statements:
                    assignment = _top_level_assignment(statement)
                    if assignment is not None:
                        right = statement[assignment + 1 :].strip()
                        if CONSTRUCTOR.fullmatch(right):
                            counts["constructor_statements"] += 1
                        elif CONSTANT.fullmatch(right):
                            counts["constant_statements"] += 1
                        elif any(name in statement for name in STRUCTURAL_NAMES):
                            counts["structural_statements"] += 1
                        else:
                            counts["other_assignment_statements"] += 1
                    elif ".Добавить(" in statement:
                        counts["collection_statements"] += 1
                    else:
                        counts["other_statements"] += 1
    return counts


def _conflict_rows(conflicts) -> list[dict[str, object]]:
    return [
        {
            "production": item.production,
            "left_alternative": item.left_alternative,
            "right_alternative": item.right_alternative,
            "witness": list(item.witness),
        }
        for item in conflicts
    ]


def _legacy_runtime_conflict_rows(select_rows) -> list[dict[str, object]]:
    alternatives_by_word: dict[tuple[str, tuple[str, ...]], set[int]] = {}
    production_order: dict[str, int] = {}
    for row in select_rows:
        production_order.setdefault(row.production, len(production_order))
        alternatives_by_word.setdefault(
            (row.production, row.matchers), set()
        ).add(row.alternative)

    witnesses_by_pair: dict[tuple[str, int, int], tuple[str, ...]] = {}
    for (production, word), alternatives in alternatives_by_word.items():
        ordered_alternatives = sorted(alternatives)
        for left_index, left_alternative in enumerate(ordered_alternatives):
            for right_alternative in ordered_alternatives[left_index + 1 :]:
                key = (production, left_alternative, right_alternative)
                previous = witnesses_by_pair.get(key)
                if previous is None or (len(word), word) < (
                    len(previous), previous
                ):
                    witnesses_by_pair[key] = word
    return [
        {
            "production": production,
            "left_alternative": left_alternative,
            "right_alternative": right_alternative,
            "witness": list(witness),
        }
        for (production, left_alternative, right_alternative), witness in sorted(
            witnesses_by_pair.items(),
            key=lambda item: (
                production_order[item[0][0]],
                item[0][1],
                item[0][2],
            ),
        )
    ]


def _decision_dag_metrics(parser_ir) -> dict[str, int]:
    return aggregate_decision_dag_metrics(
        decision.dag
        for decision in _parser_ir_decisions(parser_ir, unique=True)
    )


def decision_path_metrics(parser_ir) -> dict[str, int]:
    counts = {
        "specialized_paths": 0,
        "known_symbol_consumes": 0,
        "redundant_validations": 0,
    }
    identifier_token_types = {
        definition.label: frozenset(definition.token_types)
        for definition in parser_ir.matcher_definitions
    }

    def accepted_token_types(symbol):
        if isinstance(symbol, Terminal):
            return frozenset({symbol.token_type})
        if isinstance(symbol, Lexeme):
            return frozenset({symbol.text})
        if isinstance(symbol, Constant):
            return frozenset({symbol.token_type})
        if isinstance(symbol, IdentifierRef):
            return identifier_token_types.get(symbol.name)
        return None

    def redundant_in_operations(operations, facts) -> int:
        facts_by_offset = {fact.offset: fact for fact in facts}

        def scan_bound_value(value, cursor):
            if isinstance(value, ConsumeKnownSymbol):
                return cursor + 1, True, 0
            if isinstance(value, ParseSymbol):
                return scan_symbol(value.symbol, cursor)
            if isinstance(value, ParseBranchValue):
                return scan_operations(value.operations, cursor)
            if isinstance(value, DispatchValue):
                return cursor, False, 0
            return cursor, True, 0

        def scan_symbol(symbol, cursor):
            accepted = accepted_token_types(symbol)
            if accepted is None:
                return cursor, False, 0
            fact = facts_by_offset.get(cursor)
            redundant = int(
                fact is not None
                and set(fact.predicate.token_types).issubset(accepted)
            )
            return cursor + 1, True, redundant

        def scan_operation(operation, cursor):
            if isinstance(operation, ConsumeKnownSymbol):
                return cursor + 1, True, 0
            if isinstance(operation, (ParseSymbol, DiscardSymbol)):
                return scan_symbol(operation.symbol, cursor)
            if isinstance(operation, ResolvedRegion):
                return scan_operations(operation.operations, cursor)
            if isinstance(
                operation,
                (
                    BindScalar,
                    AppendCollection,
                    ExtendCollection,
                    ConcatScalar,
                    IncrementScalar,
                ),
            ):
                return scan_bound_value(operation.value, cursor)
            if isinstance(operation, WrapValue):
                cursor, active, redundant = scan_operation(
                    operation.seed,
                    cursor,
                )
                if not active:
                    return cursor, active, redundant
                cursor, active, nested = scan_bound_value(
                    operation.value,
                    cursor,
                )
                return cursor, active, redundant + nested
            if isinstance(
                operation,
                (Dispatch, OptionalBranch, RepeatLoop, WrapOptional, LeftFold),
            ):
                return cursor, False, 0
            return cursor, True, 0

        def scan_operations(nested_operations, cursor=0):
            redundant = 0
            active = True
            for operation in nested_operations:
                cursor, active, nested = scan_operation(operation, cursor)
                redundant += nested
                if not active:
                    break
            return cursor, active, redundant

        return scan_operations(operations)[2]

    def visit_bound_value(value) -> None:
        if isinstance(value, ConsumeKnownSymbol):
            counts["known_symbol_consumes"] += 1
        elif isinstance(value, ParseBranchValue):
            visit_operations(value.operations)
        elif isinstance(value, DispatchValue):
            for branch in value.branches:
                visit_bound_value(branch.value)

    def visit_branch(
        branch: BranchIr,
        decision: CanonicalDecision | None,
    ) -> None:
        if branch.path_facts is not None:
            counts["specialized_paths"] += 1
            counts["redundant_validations"] += redundant_in_operations(
                branch.operations,
                branch.path_facts,
            )
        elif decision is not None:
            for path in decision_paths(decision.dag):
                if (
                    isinstance(path.leaf, CommitAlternative)
                    and path.leaf.outcome == branch.outcome
                ):
                    counts["redundant_validations"] += redundant_in_operations(
                        branch.operations,
                        path.facts,
                    )
        visit_operations(branch.operations)

    def visit_control_branches(branches, decision) -> None:
        fallback_decision = (
            decision
            if decision is not None
            and (
                decision.caller_callee_composed
                or any(branch.path_facts is not None for branch in branches)
            )
            else None
        )
        for branch in branches:
            visit_branch(branch, fallback_decision)

    def visit_operations(operations) -> None:
        for operation in operations:
            if isinstance(operation, ConsumeKnownSymbol):
                counts["known_symbol_consumes"] += 1
            elif isinstance(operation, ResolvedRegion):
                visit_operations(operation.operations)
            elif isinstance(operation, (Dispatch, RepeatLoop)):
                visit_control_branches(
                    operation.branches,
                    operation.decision,
                )
            elif isinstance(operation, OptionalBranch):
                visit_control_branches(
                    operation.branches,
                    operation.decision,
                )
                visit_operations(operation.exit_operations)
            elif isinstance(operation, WrapOptional):
                visit_operations((operation.seed,))
                visit_control_branches(
                    operation.branches,
                    operation.decision,
                )
            elif isinstance(operation, WrapValue):
                visit_operations((operation.seed,))
                visit_bound_value(operation.value)
            elif isinstance(operation, LeftFold):
                visit_control_branches(
                    operation.base_branches,
                    operation.base_decision,
                )
                visit_control_branches(
                    operation.recursive_branches,
                    operation.recursive_decision,
                )
            elif isinstance(
                operation,
                (
                    BindScalar,
                    AppendCollection,
                    ExtendCollection,
                    ConcatScalar,
                    IncrementScalar,
                ),
            ):
                visit_bound_value(operation.value)

    for production in parser_ir.productions:
        for alternative in production.alternatives:
            visit_operations(alternative.operations)
    return counts


def _parser_ir_decisions(
    parser_ir,
    *,
    unique: bool = False,
) -> tuple[CanonicalDecision, ...]:
    decisions: list[CanonicalDecision] = []
    seen: set[int] = set()

    def visit(value) -> None:
        if isinstance(value, CanonicalDecision):
            if unique and id(value) in seen:
                return
            seen.add(id(value))
            decisions.append(value)
            return
        if isinstance(value, (str, bytes, int, bool, type(None))):
            return
        if isinstance(value, (tuple, list, frozenset)):
            for item in value:
                visit(item)
            return
        if is_dataclass(value):
            for field in fields(value):
                if field.name in {"source_span", "span"}:
                    continue
                visit(getattr(value, field.name))

    for production in parser_ir.productions:
        visit(production)
    return tuple(decisions)


def _named_predicate_candidates(parser_ir) -> dict[tuple[str, ...], str]:
    usage: dict[tuple[str, ...], int] = {}
    for decision in _parser_ir_decisions(parser_ir):
        for token_types in emitted_predicate_token_sets(decision.dag):
            usage[token_types] = usage.get(token_types, 0) + 1
    labels: dict[tuple[str, ...], list[str]] = {}
    for definition in parser_ir.matcher_definitions:
        labels.setdefault(definition.token_types, []).append(
            definition.label
        )
    return {
        token_types: sorted(labels[token_types])[0]
        for token_types, count in usage.items()
        if len(token_types) > 8
        and count >= 3
        and token_types in labels
    }


def _generate_strategy(config, compilation, parser_ir, named_predicates):
    assert compilation.source_grammar is not None
    assert compilation.lowering is not None
    assert compilation.grammar is not None
    assert compilation.resolved is not None
    assert compilation.analysis is not None
    started = perf_counter()
    generated = generate_hybrid_parser(
        compilation.source_grammar,
        compilation.lowering,
        compilation.grammar,
        compilation.resolved,
        compilation.analysis,
        parser_ir,
        canonical_productions=config.canonical_productions,
        entrypoints=config.entrypoints,
        named_predicates=named_predicates,
    )
    elapsed = perf_counter() - started
    metrics = generated_bsl_metrics(generated.module_text)
    helper_occurrences = generated.module_text.count(
        "ТокенПринадлежитКлассу("
    )
    return {
        "bsl_loc": len(generated.module_text.splitlines()),
        "max_condition_chars": metrics["max_condition_chars"],
        "helper_calls": max(
            0,
            helper_occurrences - (1 if named_predicates else 0),
        ),
        "generation_seconds": elapsed,
    }


def benchmark_predicate_strategies(
    config_path: Path,
) -> dict[str, object]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    compilation = compile_from_config(config)
    if (
        compilation.source_grammar is None
        or compilation.lowering is None
        or compilation.resolved is None
        or compilation.analysis is None
    ):
        raise ValueError("predicate benchmark requires canonical Parser IR")
    parser_ir = build_parser_ir(
        compilation.source_grammar,
        compilation.lowering,
        compilation.resolved,
        compilation.analysis,
        production_names=config.canonical_productions,
        entrypoint_productions=config.entrypoints.values(),
    )
    named_predicates = _named_predicate_candidates(parser_ir)
    inline = _generate_strategy(config, compilation, parser_ir, {})
    named = _generate_strategy(
        config,
        compilation,
        parser_ir,
        named_predicates,
    )
    selected = (
        "named"
        if named_predicates and named["bsl_loc"] < inline["bsl_loc"]
        else "inline"
    )
    return {
        "inline": inline,
        "named": named,
        "eligible_named_sets": len(named_predicates),
        "selected": selected,
    }


def build_migration_audit(
    config_path: Path,
    *,
    max_matcher_rows: int = 100_000,
) -> dict[str, object]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    compilation = compile_from_config(config)
    if (
        compilation.grammar is None
        or compilation.resolved is None
        or compilation.analysis is None
        or compilation.source_grammar is None
    ):
        raise ValueError("production grammar did not produce a complete analysis")

    grammar = compilation.grammar
    source_grammar = compilation.source_grammar
    resolved = compilation.resolved
    analysis = compilation.analysis
    legacy_artifact = build_legacy_matcher_artifact(
        analysis,
        max_rows=max_matcher_rows,
    )
    generated = generate_from_compilation(config, compilation)
    parser_ir = (
        build_parser_ir(
            compilation.source_grammar,
            compilation.lowering,
            resolved,
            analysis,
            production_names=config.canonical_productions,
            entrypoint_productions=config.entrypoints.values(),
        )
        if config.canonical_productions
        and compilation.source_grammar is not None
        and compilation.lowering is not None
        else None
    )
    rendered = render_artifacts(generated)
    comparison = compare_artifacts(config.target, rendered)
    actions = classify_semantic_actions(grammar)
    actual_arguments = sum(
        len(element.arguments)
        for production in grammar.productions
        for alternative in production.alternatives
        for element in alternative.elements
        if isinstance(element, NonterminalCall)
    )
    compressed = analysis._compressed
    assert compressed is not None
    stats = compressed.stats
    return {
        "schema_version": 1,
        "config": {
            "grammar": str(config.grammar.relative_to(config_path.parent)),
            "target": str(config.target.relative_to(config_path.parent)),
            "lookahead": config.lookahead,
            "entrypoints": dict(config.entrypoints),
            "canonical_productions": list(config.canonical_productions),
        },
        "structural": {
            "source_productions": len(source_grammar.productions),
            "source_alternatives": sum(
                len(item.alternatives) for item in source_grammar.productions
            ),
            "productions": len(grammar.productions),
            "alternatives": sum(
                len(item.alternatives) for item in grammar.productions
            ),
            "epsilon_alternatives": sum(
                not alternative.syntax_symbols
                for production in grammar.productions
                for alternative in production.alternatives
            ),
            "formal_parameters": sum(
                len(item.parameters) for item in grammar.productions
            ),
            "actual_arguments": actual_arguments,
            **actions,
        },
        "canonical": {
            "conflicts": _conflict_rows(
                find_canonical_select_conflicts(resolved, analysis)
            ),
            "diagnostics": [
                {
                    "code": item.code,
                    "severity": item.severity.value,
                    "message": item.message,
                }
                for item in compilation.report.diagnostics
            ],
            "stats": {
                "packed_first_rows": sum(
                    len(value) for value in compressed.first
                ),
                "packed_follow_rows": sum(
                    len(value) for value in compressed.follow
                ),
                "select_descriptors": stats["select_descriptors"],
                "select_direct_facts": stats["select_direct_facts"],
                "select_short_complete_prefixes": stats[
                    "select_short_complete_prefixes"
                ],
                "packed_select_upper_bound": (
                    compressed.packed_select_upper_bound()
                ),
                "conflict_work_items": stats["conflict_work_items"],
                "public_select_expansions": stats["public_select_expansions"],
                "select_cartesian_materializations": stats[
                    "select_cartesian_materializations"
                ],
            },
        },
        "decision_dag": (
            _decision_dag_metrics(parser_ir)
            if parser_ir is not None
            else aggregate_decision_dag_metrics(())
        ),
        "decision_path": (
            decision_path_metrics(parser_ir)
            if parser_ir is not None
            else {
                "specialized_paths": 0,
                "known_symbol_consumes": 0,
                "redundant_validations": 0,
            }
        ),
        "legacy": {
            "matcher_rows": len(legacy_artifact.select_rows),
            "matcher_definitions": len(legacy_artifact.matcher_definitions),
            "runtime_conflicts": _legacy_runtime_conflict_rows(
                legacy_artifact.select_rows
            ),
        },
        "generated": {
            "bsl_functions": sum(
                line.strip().casefold().startswith("функция ")
                for line in generated.module_text.splitlines()
            ),
            "bsl_loc": len(generated.module_text.splitlines()),
            "constructor_names": len(generated.constructor_names),
            "select_rows": len(generated.select_table.rows),
            "identifier_rows": len(generated.identifier_table.rows),
            **generated_bsl_metrics(generated.module_text),
        },
        "artifacts": {
            "changed": [
                str(path.relative_to(config_path.parent))
                for path in comparison.changed
            ],
        },
    }


def _write_json(value: object) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(payload.decode("utf-8"))
    else:
        buffer.write(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only grammar/query-model migration audit",
    )
    parser.add_argument("--config", type=Path, default=Path("parsergen.toml"))
    parser.add_argument("--max-matcher-rows", type=int, default=100_000)
    arguments = parser.parse_args(argv)
    try:
        report = build_migration_audit(
            arguments.config,
            max_matcher_rows=arguments.max_matcher_rows,
        )
    except (OSError, ValueError) as error:
        _write_json({
            "schema_version": 1,
            "status": "error",
            "type": type(error).__name__,
            "message": str(error),
        })
        return 2
    _write_json(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
