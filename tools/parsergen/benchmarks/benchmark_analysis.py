from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from types import MappingProxyType


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from parsergen.analysis import (  # noqa: E402
    AnalysisResult,
    _CompressedAnalysis,
    _ContinuationFirst,
    _LazyPackedMapping,
    _LazySelectMapping,
    _compute_nullable,
    _compute_factorized_select,
    _compute_packed_follow,
    find_select_conflicts,
)
from parsergen.grammar_parser import parse_grammar  # noqa: E402
from parsergen.resolver import resolve_grammar  # noqa: E402
from parsergen.validation import validate_grammar  # noqa: E402


DEFAULT_GRAMMAR = ROOT / "grammar/query-language.grammar"


def _milliseconds(start: float) -> float:
    return round((perf_counter() - start) * 1000, 4)


def _write_json(value: object) -> None:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(payload)
    else:
        sys.stdout.write(payload.decode("utf-8"))


def _error_record(
    k: int,
    phase: str,
    exception_type: str,
    message: str,
) -> dict[str, object]:
    return {
        "status": "error",
        "k": k,
        "phase": phase,
        "type": exception_type,
        "message": message,
    }


def _diagnostic_rows(diagnostics) -> list[dict[str, object]]:
    return [
        {
            "code": item.code,
            "severity": item.severity.value,
            "message": item.message,
        }
        for item in diagnostics
    ]


def _measure_worker(
    grammar_path: Path,
    k: int,
    materialize_concrete: bool,
    max_expanded_rows: int | None,
    progress_path: Path | None = None,
) -> dict[str, object]:
    timing: dict[str, float] = {}
    partial_counts: dict[str, int] = {}

    def checkpoint() -> None:
        if progress_path is None:
            return
        temporary = progress_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "timing_ms": timing,
                    "counts": partial_counts,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temporary.replace(progress_path)

    started = perf_counter()
    text = grammar_path.read_text(encoding="utf-8")
    parsed = parse_grammar(text, path=str(grammar_path))
    timing["parse"] = _milliseconds(started)
    checkpoint()
    if parsed.grammar is None:
        record = _error_record(k, "parse", "GrammarDiagnostics", "parse failed")
        record["diagnostics"] = _diagnostic_rows(parsed.diagnostics)
        return record

    started = perf_counter()
    resolution = resolve_grammar(parsed.grammar)
    timing["resolve"] = _milliseconds(started)
    checkpoint()
    if resolution.grammar is None:
        record = _error_record(
            k,
            "resolve",
            "GrammarDiagnostics",
            "resolution failed",
        )
        record["diagnostics"] = _diagnostic_rows(resolution.diagnostics)
        return record
    grammar = resolution.grammar
    start_productions = (grammar.production_order[0],)

    started = perf_counter()
    solver = _ContinuationFirst(grammar, k)
    timing["packed_suffix_preparation"] = _milliseconds(started)
    partial_counts.update(
        {
            "alternatives": solver.stats["real_alternatives"],
            "occurrences": solver.stats["occurrences"],
            "suffix_fact_sets": solver.stats["suffix_fact_sets"],
            "matcher_classes": solver.stats["matcher_classes"],
        }
    )
    checkpoint()

    started = perf_counter()
    packed_first = solver.run_core()
    timing["packed_first"] = _milliseconds(started)
    partial_counts["packed_first_rows"] = sum(map(len, packed_first))
    partial_counts["first_work_items"] = solver.stats["work_items_processed"]
    checkpoint()

    started = perf_counter()
    packed_follow, follow_stats = _compute_packed_follow(
        solver,
        start_productions,
    )
    timing["packed_follow_propagation"] = _milliseconds(started)
    partial_counts["packed_follow_rows"] = sum(map(len, packed_follow))
    partial_counts["follow_transforms"] = follow_stats["follow_transforms"]
    partial_counts["follow_delta_facts"] = follow_stats["follow_delta_facts"]
    partial_counts["follow_work_items"] = follow_stats["follow_work_items"]
    checkpoint()

    started = perf_counter()
    select_keys, select_descriptors, select_stats = _compute_factorized_select(
        grammar,
        solver,
    )
    timing["packed_select_construction"] = _milliseconds(started)
    partial_counts["packed_select_rows"] = (
        select_stats["select_direct_facts"]
        + select_stats["select_short_complete_prefixes"]
    )
    checkpoint()

    compressed = _CompressedAnalysis(
        solver,
        packed_first,
        packed_follow,
        select_keys,
        select_descriptors,
        {**follow_stats, **select_stats},
    )
    analysis = AnalysisResult(
        k=k,
        nullable=_compute_nullable(grammar),
        first=_LazyPackedMapping(
            grammar.production_order,
            packed_first,
            compressed.expand_first,
            compressed.first_estimates,
            "first",
        ),
        follow=_LazyPackedMapping(
            grammar.production_order,
            packed_follow,
            compressed.expand_follow,
            compressed.follow_estimates,
            "follow",
        ),
        select=_LazySelectMapping(compressed),
        updates=MappingProxyType(solver.updates(packed_first)),
        _compressed=compressed,
    )

    started = perf_counter()
    conflicts = find_select_conflicts(grammar, analysis)
    timing["compressed_conflict_scan"] = _milliseconds(started)
    partial_counts["conflict_work_items"] = compressed.stats[
        "conflict_work_items"
    ]
    checkpoint()

    started = perf_counter()
    validation = validate_grammar(
        parsed.grammar,
        grammar,
        analysis,
        {"benchmark": start_productions[0]},
        (*parsed.diagnostics, *resolution.diagnostics),
    )
    timing["validation"] = _milliseconds(started)
    checkpoint()

    upper_bounds = compressed.expanded_row_upper_bounds()
    concrete_expansion: dict[str, dict[str, object]] = {}
    mappings = {
        "first": analysis.first,
        "follow": analysis.follow,
        "select": analysis.select,
    }
    for phase, mapping in mappings.items():
        upper_bound = upper_bounds[phase]
        if not materialize_concrete:
            concrete_expansion[phase] = {
                "status": "materialization-disabled",
                "upper_bound_rows": upper_bound,
            }
            continue
        assert max_expanded_rows is not None
        if upper_bound > max_expanded_rows:
            concrete_expansion[phase] = {
                "status": "expansion-skipped",
                "upper_bound_rows": upper_bound,
                "limit_rows": max_expanded_rows,
            }
            continue
        started = perf_counter()
        rows = sum(
            len(mapping.materialize(key, max_rows=max_expanded_rows))
            for key in mapping
        )
        concrete_expansion[phase] = {
            "status": "ok",
            "upper_bound_rows": upper_bound,
            "rows": rows,
            "timing_ms": _milliseconds(started),
        }

    stats = compressed.stats
    counts = {
        "productions": len(grammar.production_order),
        "alternatives": stats["real_alternatives"],
        "occurrences": stats["occurrences"],
        "suffix_fact_sets": stats["suffix_fact_sets"],
        "matcher_classes": stats["matcher_classes"],
        "packed_first_rows": sum(map(len, packed_first)),
        "packed_follow_rows": sum(map(len, packed_follow)),
        "packed_select_rows": (
            stats["select_direct_facts"]
            + stats["select_short_complete_prefixes"]
        ),
        "concrete_first_upper_bound": upper_bounds["first"],
        "concrete_follow_upper_bound": upper_bounds["follow"],
        "concrete_select_upper_bound": upper_bounds["select"],
        "follow_transforms": stats["follow_transforms"],
        "follow_delta_facts": stats["follow_delta_facts"],
        "follow_work_items": stats["follow_work_items"],
        "follow_projection_checks": stats["follow_projection_checks"],
        "duplicate_follow_projections": stats[
            "duplicate_follow_projections"
        ],
        "follow_transform_applications": stats[
            "follow_transform_applications"
        ],
        "conflict_work_items": stats["conflict_work_items"],
        "first_work_items": stats["work_items_processed"],
        "select_descriptors": stats["select_descriptors"],
        "select_cartesian_materializations": stats[
            "select_cartesian_materializations"
        ],
        "select_packed_product_rows": stats["select_packed_product_rows"],
    }
    return {
        "status": "ok",
        "k": k,
        "timing_ms": timing,
        "counts": counts,
        "conflicts": len(conflicts),
        "diagnostics": len(validation.diagnostics),
        "concrete_expansion": concrete_expansion,
    }


def _run_bounded_worker(
    grammar_path: Path,
    k: int,
    timeout: float,
    materialize_concrete: bool,
    max_expanded_rows: int | None,
) -> dict[str, object]:
    with TemporaryDirectory() as directory:
        progress_path = Path(directory) / "progress.json"
        arguments = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--grammar",
            str(grammar_path),
            "--worker-k",
            str(k),
            "--progress-file",
            str(progress_path),
        ]
        if materialize_concrete:
            arguments.append("--materialize-concrete")
            assert max_expanded_rows is not None
            arguments.extend(
                ("--max-expanded-rows", str(max_expanded_rows))
            )
        try:
            completed = subprocess.run(
                arguments,
                cwd=ROOT,
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            record = _error_record(
                k,
                "worker",
                "TimeoutExpired",
                f"compressed analysis exceeded {timeout:g} seconds",
            )
            record["status"] = "timeout"
            record["timeout_seconds"] = timeout
            if progress_path.exists():
                try:
                    record["partial"] = json.loads(
                        progress_path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError):
                    pass
            return record
    if completed.returncode != 0:
        return _error_record(
            k,
            "worker",
            "WorkerExit",
            f"worker exited with status {completed.returncode}",
        )
    try:
        return json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return _error_record(k, "worker", type(error).__name__, str(error))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bounded compressed FOLLOW/SELECT benchmark",
    )
    parser.add_argument("--grammar", type=Path, default=DEFAULT_GRAMMAR)
    parser.add_argument("--k", type=int, action="append")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--materialize-concrete", action="store_true")
    parser.add_argument("--max-expanded-rows", type=int)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-k", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--progress-file", type=Path, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    requested_k = arguments.k or [2, 3, 4]
    setup_error = (
        arguments.materialize_concrete
        and (
            arguments.max_expanded_rows is None
            or arguments.max_expanded_rows < 1
        )
    )
    if arguments.worker:
        if arguments.worker_k is None:
            _write_json(
                _error_record(
                    0,
                    "setup",
                    "ValueError",
                    "--worker-k is required in worker mode",
                )
            )
            return 0
        try:
            measurement = _measure_worker(
                arguments.grammar,
                arguments.worker_k,
                arguments.materialize_concrete,
                arguments.max_expanded_rows,
                arguments.progress_file,
            )
        except Exception as error:
            measurement = _error_record(
                arguments.worker_k,
                "worker",
                type(error).__name__,
                str(error),
            )
        _write_json(measurement)
        return 0

    if setup_error:
        measurements = [
            _error_record(
                k,
                "setup",
                "ValueError",
                "--materialize-concrete requires a positive "
                "--max-expanded-rows",
            )
            for k in requested_k
        ]
    else:
        measurements = [
            _run_bounded_worker(
                arguments.grammar,
                k,
                arguments.timeout,
                arguments.materialize_concrete,
                arguments.max_expanded_rows,
            )
            for k in requested_k
        ]
    _write_json(
        {
            "grammar": str(arguments.grammar),
            "requested_k": requested_k,
            "timeout_seconds": arguments.timeout,
            "materialize_concrete": arguments.materialize_concrete,
            "max_expanded_rows": arguments.max_expanded_rows,
            "measurements": measurements,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
