import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "benchmark_analysis.py"


class AnalysisBenchmarkTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            part
            for part in (
                str(ROOT / "src"),
                environment.get("PYTHONPATH"),
            )
            if part
        )
        return subprocess.run(
            [sys.executable, str(BENCHMARK), *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_reports_each_compressed_phase_and_work_count(self) -> None:
        with TemporaryDirectory() as directory:
            grammar = Path(directory) / "грамматика.txt"
            grammar.write_text(
                "#ID_X ::= ID | ГДЕ\n"
                "<S> ::= <A> #ID_X | done\n"
                "<A> ::= tail | ПУСТО",
                encoding="utf-8",
            )
            completed = self.run_cli(
                "--grammar",
                str(grammar),
                "--k",
                "2",
                "--timeout",
                "10",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        report = json.loads(completed.stdout)
        measurement = report["measurements"][0]
        self.assertEqual(measurement["status"], "ok")
        self.assertEqual(
            set(measurement["timing_ms"]),
            {
                "parse",
                "resolve",
                "packed_suffix_preparation",
                "packed_first",
                "packed_follow_propagation",
                "packed_select_construction",
                "compressed_conflict_scan",
                "validation",
            },
        )
        counts = measurement["counts"]
        for name in (
            "packed_first_rows",
            "packed_follow_rows",
            "packed_select_rows",
            "follow_transforms",
            "follow_delta_facts",
            "follow_work_items",
            "conflict_work_items",
        ):
            self.assertIn(name, counts)
        self.assertEqual(
            set(measurement["concrete_expansion"]),
            {"first", "follow", "select"},
        )
        self.assertEqual(
            {
                item["status"]
                for item in measurement["concrete_expansion"].values()
            },
            {"materialization-disabled"},
        )
        self.assertEqual(counts["select_cartesian_materializations"], 0)
        self.assertEqual(counts["select_packed_product_rows"], 0)

    def test_default_is_compressed_only_even_for_tiny_estimates(self) -> None:
        with TemporaryDirectory() as directory:
            grammar = Path(directory) / "grammar.txt"
            grammar.write_text(
                "#ID_X ::= ID | WORD\n<S> ::= #ID_X #ID_X",
                encoding="utf-8",
            )
            completed = self.run_cli(
                "--grammar",
                str(grammar),
                "--k",
                "2",
                "--timeout",
                "10",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        measurement = json.loads(completed.stdout)["measurements"][0]
        statuses = {
            item["status"]
            for item in measurement["concrete_expansion"].values()
        }
        self.assertEqual(statuses, {"materialization-disabled"})

    def test_explicit_materialization_obeys_each_phase_guard(self) -> None:
        with TemporaryDirectory() as directory:
            grammar = Path(directory) / "grammar.txt"
            grammar.write_text("<S> ::= a | b", encoding="utf-8")
            completed = self.run_cli(
                "--grammar",
                str(grammar),
                "--k",
                "1",
                "--materialize-concrete",
                "--max-expanded-rows",
                "10",
                "--timeout",
                "10",
            )
            guarded = self.run_cli(
                "--grammar",
                str(grammar),
                "--k",
                "1",
                "--materialize-concrete",
                "--max-expanded-rows",
                "1",
                "--timeout",
                "10",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        measurement = json.loads(completed.stdout)["measurements"][0]
        self.assertEqual(
            {
                item["status"]
                for item in measurement["concrete_expansion"].values()
            },
            {"ok"},
        )

        self.assertEqual(guarded.returncode, 0, guarded.stderr)
        guarded_measurement = json.loads(guarded.stdout)["measurements"][0]
        self.assertIn(
            "expansion-skipped",
            {
                item["status"]
                for item in guarded_measurement[
                    "concrete_expansion"
                ].values()
            },
        )

    def test_materialization_requires_an_explicit_positive_guard(self) -> None:
        with TemporaryDirectory() as directory:
            grammar = Path(directory) / "grammar.txt"
            grammar.write_text("<S> ::= a", encoding="utf-8")
            completed = self.run_cli(
                "--grammar",
                str(grammar),
                "--k",
                "1",
                "--materialize-concrete",
                "--timeout",
                "10",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        measurement = json.loads(completed.stdout)["measurements"][0]
        self.assertEqual(measurement["status"], "error")
        self.assertEqual(measurement["phase"], "setup")


if __name__ == "__main__":
    unittest.main()

