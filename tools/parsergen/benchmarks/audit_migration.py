from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SRC = PACKAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from parsergen.model import Action, Grammar
from parsergen.analysis import (
    build_legacy_matcher_artifact,
    find_canonical_select_conflicts,
)
from parsergen.artifacts import compare_artifacts, render_artifacts
from parsergen.bsl_codegen import generate_parser
from parsergen.cli import compile_from_config
from parsergen.config import load_config
from parsergen.model import NonterminalCall
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
    ):
        raise ValueError("production grammar did not produce a complete analysis")

    grammar = compilation.grammar
    resolved = compilation.resolved
    analysis = compilation.analysis
    legacy_artifact = build_legacy_matcher_artifact(
        analysis,
        max_rows=max_matcher_rows,
    )
    generated = generate_parser(
        grammar,
        resolved,
        analysis,
        config.entrypoints,
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
        },
        "structural": {
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
                "conflict_work_items": stats["conflict_work_items"],
                "public_select_expansions": stats["public_select_expansions"],
                "select_cartesian_materializations": stats[
                    "select_cartesian_materializations"
                ],
            },
        },
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
