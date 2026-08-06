import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from benchmarks import benchmark_first

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "benchmark_first.py"


class FirstBenchmarkTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        environment = os.environ.copy()
        environment.pop("PYTHONIOENCODING", None)
        environment["PYTHONUTF8"] = "0"
        return subprocess.run(
            [sys.executable, str(BENCHMARK), *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
        )

    def test_documented_windows_cli_writes_utf8_without_encoding_environment(self) -> None:
        with TemporaryDirectory() as directory:
            grammar_path = Path(directory) / "грамматика.txt"
            grammar_path.write_bytes(
                (ROOT / "grammar/query-language.grammar").read_bytes()
            )
            completed = self.run_cli(
                "--grammar",
                str(grammar_path),
                "--k",
                "2",
                "--repeats",
                "1",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, b"")
        text = completed.stdout.decode("utf-8")
        self.assertIn("грамматика.txt", text)
        report = json.loads(text)
        self.assertEqual(report["requested_k"], [2])
        self.assertEqual(
            report["measurements"][0]["status"],
            "compressed-only",
        )

    def test_cli_materializes_first_only_with_explicit_opt_in(self) -> None:
        with TemporaryDirectory() as directory:
            grammar_path = Path(directory) / "грамматика.txt"
            grammar_path.write_text(
                "#ID_X ::= ID\n"
                "#ID_X ::= WORD\n"
                "<S> ::= #ID_X <A> | done\n"
                "<A> ::= tail | ПУСТО",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = os.pathsep.join(
                part
                for part in (
                    str(ROOT / "src"),
                    environment.get("PYTHONPATH"),
                )
                if part
            )
            environment["PYTHONIOENCODING"] = "utf-8"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK),
                    "--grammar",
                    str(grammar_path),
                    "--k",
                    "1",
                    "--repeats",
                    "1",
                    "--materialize-concrete",
                    "--max-expanded-rows",
                    "100",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("грамматика.txt", completed.stdout)
        report = json.loads(completed.stdout)
        self.assertEqual(report["grammar"], str(grammar_path))
        self.assertEqual(report["requested_k"], [1])
        self.assertEqual(report["repeats"], 1)
        measurement = report["measurements"][0]
        self.assertEqual(measurement["status"], "materialized")
        self.assertEqual(measurement["k"], 1)
        self.assertEqual(
            set(measurement["median_timing_ms"]),
            {
                "parse",
                "resolve",
                "continuation_prepare",
                "continuation_core",
                "concrete_expansion",
                "public_first_total",
            },
        )
        self.assertEqual(measurement["counts"]["productions"], 2)
        for name in ("variants", "states", "raw_rows", "expanded_rows", "facts", "work_items"):
            self.assertGreater(measurement["counts"][name], 0)
        self.assertNotIn("full_analysis", measurement)

    def test_cli_can_measure_compressed_core_without_materializing_words(self) -> None:
        with TemporaryDirectory() as directory:
            grammar_path = Path(directory) / "grammar.txt"
            grammar_path.write_text(
                "#ID_X ::= ID | WORD\n<S> ::= #ID_X #ID_X",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK),
                    "--grammar",
                    str(grammar_path),
                    "--k",
                    "2",
                    "--repeats",
                    "1",
                    "--core-only",
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    "PYTHONPATH": str(ROOT / "src"),
                    "PYTHONIOENCODING": "utf-8",
                },
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        measurement = json.loads(completed.stdout)["measurements"][0]
        self.assertEqual(measurement["status"], "core-only")
        self.assertEqual(
            set(measurement["median_timing_ms"]),
            {
                "parse",
                "resolve",
                "continuation_prepare",
                "continuation_core",
            },
        )
        self.assertNotIn("full_analysis", measurement)
        self.assertGreaterEqual(
            measurement["counts"]["expanded_row_upper_bound"],
            measurement["counts"]["raw_rows"],
        )

    def test_cli_reports_large_expansion_as_bounded_data(self) -> None:
        with TemporaryDirectory() as directory:
            grammar_path = Path(directory) / "grammar.txt"
            grammar_path.write_text(
                "#ID_X ::= ID | WORD\n<S> ::= #ID_X #ID_X",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK),
                    "--grammar",
                    str(grammar_path),
                    "--k",
                    "2",
                    "--repeats",
                    "1",
                    "--materialize-concrete",
                    "--max-expanded-rows",
                    "1",
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    "PYTHONPATH": str(ROOT / "src"),
                    "PYTHONIOENCODING": "utf-8",
                },
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        measurement = json.loads(completed.stdout)["measurements"][0]
        self.assertEqual(measurement["status"], "expansion-skipped")
        self.assertEqual(measurement["expanded_row_limit"], 1)
        self.assertEqual(measurement["counts"]["expanded_row_upper_bound"], 4)
        self.assertNotIn("full_analysis", measurement)

    def test_missing_grammar_is_utf8_json_data_with_success_exit_status(self) -> None:
        grammar_path = ROOT / "definitely-missing-04b.txt"
        completed = self.run_cli(
            "--grammar",
            str(grammar_path),
            "--k",
            "2",
            "--repeats",
            "1",
            "--core-only",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, b"")
        report = json.loads(completed.stdout.decode("utf-8"))
        self.assertEqual(
            report["measurements"],
            [
                {
                    "status": "error",
                    "k": 2,
                    "phase": "read",
                    "type": "FileNotFoundError",
                    "message": f"grammar file does not exist: {grammar_path}",
                }
            ],
        )

    def test_parse_resolve_and_setup_failures_are_json_data(self) -> None:
        with TemporaryDirectory() as directory:
            parse_path = Path(directory) / "parse.txt"
            parse_path.write_text("<S> ::= ", encoding="utf-8")
            resolve_path = Path(directory) / "resolve.txt"
            resolve_path.write_text("<S> ::= <Missing>", encoding="utf-8")
            cases = (
                (
                    ("--grammar", str(parse_path), "--k", "2", "--repeats", "1", "--core-only"),
                    "parse",
                    "GrammarDiagnostics",
                ),
                (
                    ("--grammar", str(resolve_path), "--k", "2", "--repeats", "1", "--core-only"),
                    "resolve",
                    "GrammarDiagnostics",
                ),
                (
                    ("--grammar", str(resolve_path), "--k", "0", "--repeats", "1", "--core-only"),
                    "setup",
                    "ValueError",
                ),
            )
            for arguments, phase, error_type in cases:
                with self.subTest(phase=phase):
                    completed = self.run_cli(*arguments)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(completed.stderr, b"")
                    measurement = json.loads(
                        completed.stdout.decode("utf-8")
                    )["measurements"][0]
                    self.assertEqual(measurement["status"], "error")
                    self.assertEqual(measurement["phase"], phase)
                    self.assertEqual(measurement.get("type"), error_type)
                    self.assertIsInstance(measurement.get("message"), str)

    def test_benchmark_k_converts_phase_exceptions_to_error_records(self) -> None:
        with TemporaryDirectory() as directory:
            grammar_path = Path(directory) / "grammar.txt"
            grammar_path.write_text("<S> ::= token", encoding="utf-8")
            cases = (
                (
                    mock.patch.object(
                        benchmark_first,
                        "_ContinuationFirst",
                        side_effect=RuntimeError("prepare failed"),
                    ),
                    "prepare",
                    "prepare failed",
                    False,
                ),
                (
                    mock.patch.object(
                        benchmark_first._ContinuationFirst,
                        "run_core",
                        side_effect=RuntimeError("core failed"),
                    ),
                    "core",
                    "core failed",
                    False,
                ),
                (
                    mock.patch.object(
                        benchmark_first._ContinuationFirst,
                        "expand",
                        side_effect=RuntimeError("expansion failed"),
                    ),
                    "expansion",
                    "expansion failed",
                    True,
                ),
                (
                    mock.patch.object(
                        benchmark_first,
                        "compute_prefix_analysis",
                        side_effect=RuntimeError("public failed"),
                    ),
                    "public",
                    "public failed",
                    True,
                ),
            )
            for patcher, phase, message, materialize in cases:
                with self.subTest(phase=phase), patcher:
                    try:
                        result = benchmark_first.benchmark_k(
                            grammar_path,
                            1,
                            1,
                            1,
                            materialize_concrete=materialize,
                            max_expanded_rows=10 if materialize else None,
                        )
                    except Exception as error:
                        self.fail(
                            f"{phase} exception escaped as "
                            f"{type(error).__name__}: {error}"
                        )
                    self.assertEqual(
                        result,
                        {
                            "status": "error",
                            "k": 1,
                            "phase": phase,
                            "type": "RuntimeError",
                            "message": message,
                        },
                    )

    def test_default_benchmark_never_expands_small_first_language(self) -> None:
        with TemporaryDirectory() as directory:
            grammar_path = Path(directory) / "grammar.txt"
            grammar_path.write_text("<S> ::= a", encoding="utf-8")
            with mock.patch.object(
                benchmark_first._ContinuationFirst,
                "expand",
                side_effect=AssertionError("must stay compressed"),
            ):
                result = benchmark_first.benchmark_k(
                    grammar_path,
                    1,
                    1,
                    1,
                )

        self.assertEqual(result["status"], "compressed-only")
        self.assertNotIn("expanded_rows", result["counts"])

    def test_hidden_full_worker_requires_guarded_materialization_opt_in(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            grammar_path = Path(directory) / "grammar.txt"
            grammar_path.write_text("<S> ::= a | b", encoding="utf-8")

            with (
                mock.patch(
                    "parsergen.analysis._LazyPackedMapping.materialize",
                    side_effect=AssertionError("must stay compressed"),
                ),
                mock.patch(
                    "parsergen.analysis._LazySelectMapping.materialize",
                    side_effect=AssertionError("must stay compressed"),
                ),
            ):
                compressed = benchmark_first._full_analysis_worker(
                    grammar_path,
                    1,
                )

            missing_guard = benchmark_first._full_analysis_worker(
                grammar_path,
                1,
                materialize_concrete=True,
            )
            materialized = benchmark_first._full_analysis_worker(
                grammar_path,
                1,
                materialize_concrete=True,
                max_expanded_rows=10,
            )
            cli_materialized = self.run_cli(
                "--grammar",
                str(grammar_path),
                "--_full-worker",
                "--worker-k",
                "1",
                "--materialize-concrete",
                "--max-expanded-rows",
                "10",
            )

        self.assertEqual(compressed["status"], "compressed-only")
        self.assertEqual(
            set(compressed["counts"]),
            {
                "concrete_first_upper_bound",
                "concrete_follow_upper_bound",
                "concrete_select_upper_bound",
            },
        )
        self.assertEqual(missing_guard["status"], "error")
        self.assertEqual(missing_guard["phase"], "setup")
        self.assertEqual(materialized["status"], "materialized")
        self.assertEqual(cli_materialized.returncode, 0)
        self.assertEqual(
            json.loads(cli_materialized.stdout.decode("utf-8"))["status"],
            "materialized",
        )
        self.assertEqual(
            {
                "first_rows",
                "follow_rows",
                "select_rows",
            },
            set(materialized["counts"])
            - {
                "concrete_first_upper_bound",
                "concrete_follow_upper_bound",
                "concrete_select_upper_bound",
            },
        )

    def test_worker_timeout_and_unexpected_errors_are_structured(self) -> None:
        grammar_path = ROOT / "grammar.txt"
        with mock.patch.object(
            benchmark_first.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(("python",), 0.25),
        ):
            timeout = benchmark_first._run_full_analysis(
                grammar_path,
                2,
                0.25,
            )
        self.assertEqual(
            timeout,
            {
                "status": "timeout",
                "k": 2,
                "phase": "full-analysis",
                "type": "TimeoutExpired",
                "message": "full analysis exceeded 0.25 seconds",
                "timeout_seconds": 0.25,
            },
        )

        with mock.patch.object(
            benchmark_first,
            "compute_analysis",
            side_effect=RuntimeError("worker failed"),
        ):
            with TemporaryDirectory() as directory:
                valid_path = Path(directory) / "grammar.txt"
                valid_path.write_text("<S> ::= token", encoding="utf-8")
                worker = benchmark_first._full_analysis_worker(valid_path, 2)
        self.assertEqual(
            worker,
            {
                "status": "error",
                "k": 2,
                "phase": "full-analysis",
                "type": "RuntimeError",
                "message": "worker failed",
            },
        )

    def test_unexpected_benchmark_exception_is_a_measurement_record(self) -> None:
        grammar_path = ROOT / "grammar.txt"
        with mock.patch.object(
            benchmark_first,
            "benchmark_k",
            side_effect=RuntimeError("unexpected failure"),
        ):
            try:
                result = benchmark_first.benchmark_grammar(
                    grammar_path,
                    (2,),
                    1,
                    1,
                )
            except Exception as error:
                self.fail(
                    "unexpected benchmark exception escaped as "
                    f"{type(error).__name__}: {error}"
                )
        self.assertEqual(
            result["measurements"],
            [
                {
                    "status": "error",
                    "k": 2,
                    "phase": "benchmark",
                    "type": "RuntimeError",
                    "message": "unexpected failure",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
