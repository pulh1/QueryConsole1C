from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from parsergen.analysis import (  # noqa: E402
    _ContinuationFirst,
    compute_analysis,
    compute_prefix_analysis,
)
from parsergen.grammar_parser import parse_grammar  # noqa: E402
from parsergen.resolver import resolve_grammar  # noqa: E402


DEFAULT_GRAMMAR = ROOT / "grammar/query-language.grammar"


def _error_record(
    k: int,
    phase: str,
    error_type: str,
    message: str,
    **details: object,
) -> dict[str, object]:
    return {
        "status": "error",
        "k": k,
        "phase": phase,
        "type": error_type,
        "message": message,
        **details,
    }


def _exception_record(
    k: int,
    phase: str,
    error: Exception,
) -> dict[str, object]:
    return _error_record(
        k,
        phase,
        type(error).__name__,
        str(error) or type(error).__name__,
    )


def _diagnostic_record(
    k: int,
    phase: str,
    diagnostics: tuple[Any, ...],
) -> dict[str, object]:
    return _error_record(
        k,
        phase,
        "GrammarDiagnostics",
        f"grammar {phase} reported diagnostics",
        diagnostics=_diagnostics_data(diagnostics),
    )


def _write_json(result: dict[str, object]) -> None:
    payload = (
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    binary_stdout = getattr(sys.stdout, "buffer", None)
    if binary_stdout is None:
        sys.stdout.write(payload.decode("utf-8"))
        sys.stdout.flush()
        return
    binary_stdout.write(payload)
    binary_stdout.flush()


def _diagnostics_data(diagnostics: tuple[Any, ...]) -> list[dict[str, object]]:
    return [
        {
            "code": diagnostic.code,
            "line": diagnostic.span.start.line,
            "column": diagnostic.span.start.column,
        }
        for diagnostic in diagnostics
    ]


def _full_analysis_worker(
    grammar_path: Path,
    k: int,
    materialize_concrete: bool = False,
    max_expanded_rows: int | None = None,
) -> dict[str, object]:
    if materialize_concrete and (
        max_expanded_rows is None or max_expanded_rows < 1
    ):
        return _error_record(
            k,
            "setup",
            "ValueError",
            "materialization requires a positive max_expanded_rows",
        )
    try:
        source = grammar_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return _error_record(
            k,
            "read",
            "FileNotFoundError",
            f"grammar file does not exist: {grammar_path}",
        )
    except Exception as error:
        return _exception_record(k, "read", error)
    try:
        parsed = parse_grammar(source, str(grammar_path))
    except Exception as error:
        return _exception_record(k, "parse", error)
    if parsed.grammar is None or parsed.diagnostics:
        return _diagnostic_record(k, "parse", parsed.diagnostics)
    try:
        resolution = resolve_grammar(parsed.grammar)
    except Exception as error:
        return _exception_record(k, "resolve", error)
    if resolution.grammar is None or resolution.diagnostics:
        return _diagnostic_record(k, "resolve", resolution.diagnostics)
    if not resolution.grammar.production_order:
        return _error_record(
            k,
            "full-analysis",
            "ValueError",
            "grammar has no productions",
        )

    starts = (resolution.grammar.production_order[0],)
    started = time.perf_counter_ns()
    try:
        analysis = compute_analysis(resolution.grammar, k, starts)
    except Exception as error:
        return _exception_record(k, "full-analysis", error)
    compressed = analysis._compressed
    if compressed is None:
        return _error_record(
            k,
            "full-analysis",
            "ValueError",
            "compressed analysis is required",
        )
    upper_bounds = compressed.expanded_row_upper_bounds()
    counts = {
        f"concrete_{phase}_upper_bound": upper_bound
        for phase, upper_bound in upper_bounds.items()
    }
    if not materialize_concrete:
        return {
            "status": "compressed-only",
            "timing_ms": (
                time.perf_counter_ns() - started
            ) / 1_000_000,
            "start_productions": list(starts),
            "counts": counts,
        }

    assert max_expanded_rows is not None
    oversized = {
        phase: upper_bound
        for phase, upper_bound in upper_bounds.items()
        if upper_bound > max_expanded_rows
    }
    if oversized:
        return {
            "status": "expansion-skipped",
            "timing_ms": (
                time.perf_counter_ns() - started
            ) / 1_000_000,
            "start_productions": list(starts),
            "expanded_row_limit": max_expanded_rows,
            "oversized_phases": oversized,
            "counts": counts,
        }

    mappings = {
        "first": analysis.first,
        "follow": analysis.follow,
        "select": analysis.select,
    }
    try:
        for phase, mapping in mappings.items():
            counts[f"{phase}_rows"] = sum(
                len(
                    mapping.materialize(
                        key,
                        max_rows=max_expanded_rows,
                    )
                )
                for key in mapping
            )
    except Exception as error:
        return _exception_record(k, "materialization", error)
    return {
        "status": "materialized",
        "timing_ms": (time.perf_counter_ns() - started) / 1_000_000,
        "start_productions": list(starts),
        "counts": counts,
    }


def _run_full_analysis(
    grammar_path: Path,
    k: int,
    timeout_seconds: float,
    materialize_concrete: bool = False,
    max_expanded_rows: int | None = None,
) -> dict[str, object]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONPATH"] = os.pathsep.join(
        part
        for part in (str(SRC), environment.get("PYTHONPATH"))
        if part
    )
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--_full-worker",
        "--grammar",
        str(grammar_path),
        "--worker-k",
        str(k),
    ]
    if materialize_concrete:
        command.append("--materialize-concrete")
        if max_expanded_rows is not None:
            command.extend(
                ("--max-expanded-rows", str(max_expanded_rows))
            )
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "k": k,
            "phase": "full-analysis",
            "type": "TimeoutExpired",
            "message": (
                f"full analysis exceeded {timeout_seconds:g} seconds"
            ),
            "timeout_seconds": timeout_seconds,
        }
    except Exception as error:
        return _exception_record(k, "worker", error)
    if completed.returncode != 0:
        return _error_record(
            k,
            "worker",
            "WorkerExitError",
            f"full analysis worker exited with status {completed.returncode}",
            returncode=completed.returncode,
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return _error_record(
            k,
            "worker-output",
            "JSONDecodeError",
            "full analysis worker emitted invalid JSON",
        )
    if not isinstance(result, dict) or "status" not in result:
        return _error_record(
            k,
            "worker-output",
            "WorkerProtocolError",
            "full analysis worker emitted an invalid result",
        )
    return result


def _summarize_full_runs(
    runs: list[dict[str, object]],
    timeout_seconds: float,
) -> dict[str, object]:
    successful = [run for run in runs if run["status"] == "ok"]
    if len(successful) == len(runs):
        timings = [float(run["timing_ms"]) for run in successful]
        return {
            "status": "ok",
            "timing_ms": statistics.median(timings),
            "min_timing_ms": min(timings),
            "max_timing_ms": max(timings),
            "start_productions": successful[0]["start_productions"],
            "counts": successful[0]["counts"],
        }
    if not successful and all(run["status"] == "timeout" for run in runs):
        return {
            "status": "timeout",
            "timeout_seconds": timeout_seconds,
            "runs": runs,
        }
    return {
        "status": "partial",
        "successful_runs": len(successful),
        "runs": runs,
    }


def benchmark_k(
    grammar_path: Path,
    k: int,
    repeats: int,
    full_timeout: float,
    core_only: bool = False,
    max_expanded_rows: int | None = None,
    materialize_concrete: bool = False,
) -> dict[str, object]:
    if materialize_concrete and (
        max_expanded_rows is None or max_expanded_rows < 1
    ):
        return _error_record(
            k,
            "setup",
            "ValueError",
            "materialization requires a positive max_expanded_rows",
        )
    timing_runs: list[dict[str, float]] = []
    reference_counts: dict[str, int] | None = None
    reference_stats: dict[str, int] | None = None

    for _ in range(repeats):
        parse_started = time.perf_counter_ns()
        try:
            source = grammar_path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return _error_record(
                k,
                "read",
                "FileNotFoundError",
                f"grammar file does not exist: {grammar_path}",
            )
        except Exception as error:
            return _exception_record(k, "read", error)
        try:
            parsed = parse_grammar(source, str(grammar_path))
        except Exception as error:
            return _exception_record(k, "parse", error)
        parse_ended = time.perf_counter_ns()
        if parsed.grammar is None or parsed.diagnostics:
            return _diagnostic_record(k, "parse", parsed.diagnostics)

        try:
            resolution = resolve_grammar(parsed.grammar)
        except Exception as error:
            return _exception_record(k, "resolve", error)
        resolve_ended = time.perf_counter_ns()
        if resolution.grammar is None or resolution.diagnostics:
            return _diagnostic_record(k, "resolve", resolution.diagnostics)
        grammar = resolution.grammar

        prepare_started = time.perf_counter_ns()
        try:
            solver = _ContinuationFirst(grammar, k)
        except Exception as error:
            return _exception_record(k, "prepare", error)
        prepare_ended = time.perf_counter_ns()
        try:
            raw = solver.run_core()
        except Exception as error:
            return _exception_record(k, "core", error)
        core_ended = time.perf_counter_ns()

        try:
            counts = {
                "productions": len(grammar.production_order),
                "variants": solver.stats["variants"],
                "states": solver.stats["states_created"],
                "raw_rows": solver.stats["raw_rows"],
                "facts": solver.stats["facts_published"],
                "work_items": solver.stats["work_items_processed"],
                "expanded_row_upper_bound": (
                    solver.expanded_row_upper_bound(raw)
                ),
            }
        except Exception as error:
            return _exception_record(k, "expansion", error)
        expansion_skipped = (
            materialize_concrete
            and max_expanded_rows is not None
            and counts["expanded_row_upper_bound"] > max_expanded_rows
        )
        if materialize_concrete and not expansion_skipped:
            try:
                expanded = solver.expand(raw)
            except Exception as error:
                return _exception_record(k, "expansion", error)
            expansion_ended = time.perf_counter_ns()

            public_started = time.perf_counter_ns()
            try:
                public = compute_prefix_analysis(grammar, k)
            except Exception as error:
                return _exception_record(k, "public", error)
            public_ended = time.perf_counter_ns()
            if public.first != expanded:
                return _error_record(
                    k,
                    "consistency",
                    "ConsistencyError",
                    "private phase result differs from public FIRST",
                )
            counts["expanded_rows"] = solver.stats["expanded_rows"]
        if reference_counts is not None and counts != reference_counts:
            return _error_record(
                k,
                "determinism",
                "DeterminismError",
                "counts changed between repeats",
            )
        reference_counts = counts
        reference_stats = dict(solver.stats)
        timings = {
            "parse": (parse_ended - parse_started) / 1_000_000,
            "resolve": (resolve_ended - parse_ended) / 1_000_000,
            "continuation_prepare": (
                prepare_ended - prepare_started
            ) / 1_000_000,
            "continuation_core": (
                core_ended - prepare_ended
            ) / 1_000_000,
        }
        if materialize_concrete and not expansion_skipped:
            timings["concrete_expansion"] = (
                expansion_ended - core_ended
            ) / 1_000_000
            timings["public_first_total"] = (
                public_ended - public_started
            ) / 1_000_000
        timing_runs.append(timings)

    phases = tuple(timing_runs[0])
    median_timing_ms = {
        phase: statistics.median(
            run[phase] for run in timing_runs
        )
        for phase in phases
    }
    if core_only:
        return {
            "status": "core-only",
            "k": k,
            "median_timing_ms": median_timing_ms,
            "counts": reference_counts,
            "stats": reference_stats,
        }
    if not materialize_concrete:
        return {
            "status": "compressed-only",
            "k": k,
            "median_timing_ms": median_timing_ms,
            "counts": reference_counts,
            "stats": reference_stats,
        }
    if expansion_skipped:
        return {
            "status": "expansion-skipped",
            "k": k,
            "median_timing_ms": median_timing_ms,
            "expanded_row_limit": max_expanded_rows,
            "counts": reference_counts,
            "stats": reference_stats,
        }

    return {
        "status": "materialized",
        "k": k,
        "median_timing_ms": median_timing_ms,
        "min_public_first_ms": min(
            run["public_first_total"] for run in timing_runs
        ),
        "max_public_first_ms": max(
            run["public_first_total"] for run in timing_runs
        ),
        "counts": reference_counts,
        "stats": reference_stats,
    }


def benchmark_grammar(
    grammar_path: Path,
    k_values: tuple[int, ...],
    repeats: int,
    full_timeout: float,
    core_only: bool = False,
    max_expanded_rows: int | None = None,
    materialize_concrete: bool = False,
) -> dict[str, object]:
    setup_message: str | None = None
    if repeats < 1:
        setup_message = "repeats must be at least 1"
    elif materialize_concrete and (
        max_expanded_rows is None or max_expanded_rows < 1
    ):
        setup_message = (
            "materialization requires a positive max_expanded_rows"
        )

    measurements: list[dict[str, object]] = []
    for k in k_values:
        if setup_message is not None:
            measurements.append(
                _error_record(
                    k,
                    "setup",
                    "ValueError",
                    setup_message,
                )
            )
            continue
        if k < 1:
            measurements.append(
                _error_record(
                    k,
                    "setup",
                    "ValueError",
                    "k must be at least 1",
                )
            )
            continue
        try:
            measurement = benchmark_k(
                grammar_path,
                k,
                repeats,
                full_timeout,
                core_only,
                max_expanded_rows,
                materialize_concrete,
            )
        except Exception as error:
            measurement = _exception_record(k, "benchmark", error)
        measurements.append(measurement)

    return {
        "grammar": str(grammar_path),
        "requested_k": list(k_values),
        "repeats": repeats,
        "measurements": measurements,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grammar", type=Path, default=DEFAULT_GRAMMAR)
    parser.add_argument("--k", type=int, nargs="+", default=(2, 3, 4))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--full-timeout", type=float, default=60.0)
    parser.add_argument("--core-only", action="store_true")
    parser.add_argument("--materialize-concrete", action="store_true")
    parser.add_argument("--max-expanded-rows", type=int)
    parser.add_argument("--_full-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-k", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args._full_worker:
        if args.worker_k is None:
            result = _error_record(
                0,
                "worker-setup",
                "ValueError",
                "--worker-k is required with --_full-worker",
            )
        else:
            result = _full_analysis_worker(
                args.grammar,
                args.worker_k,
                args.materialize_concrete,
                args.max_expanded_rows,
            )
    else:
        result = benchmark_grammar(
            args.grammar,
            tuple(args.k),
            args.repeats,
            args.full_timeout,
            args.core_only,
            args.max_expanded_rows,
            args.materialize_concrete,
        )
    _write_json(result)
    # Benchmark failures and timeouts are measurement data. A syntactically
    # valid CLI invocation deliberately exits zero after emitting its JSON.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
