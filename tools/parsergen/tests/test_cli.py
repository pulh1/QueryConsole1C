from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        source_path = str(Path(__file__).parents[1] / "src")
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            os.pathsep.join((source_path, existing)) if existing else source_path
        )
        return subprocess.run(
            (sys.executable, "-m", "parsergen", *arguments),
            capture_output=True,
            check=False,
            encoding="utf-8",
            env=environment,
        )

    def run_full_canonical_cli_without_legacy_backend(
        self,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        source_path = str(Path(__file__).parents[1] / "src")
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            os.pathsep.join((source_path, existing)) if existing else source_path
        )
        script = """
import importlib.abc
import sys

class BlockLegacyBackend(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "parsergen.bsl_codegen":
            raise RuntimeError("legacy backend imported by canonical route")
        return None

sys.meta_path.insert(0, BlockLegacyBackend())
from parsergen.cli import main
raise SystemExit(main(sys.argv[1:]))
"""
        return subprocess.run(
            (sys.executable, "-c", script, *arguments),
            capture_output=True,
            check=False,
            encoding="utf-8",
            env=environment,
        )

    def make_configured_project(self) -> tuple[Path, Path]:
        target = self.root / "Парсер"
        (target / "Templates/ТаблицаПервыхСимволовВариантов").mkdir(
            parents=True
        )
        (target / "Templates/ОпределенияИдентификаторов").mkdir(parents=True)
        (target / "Парсер.mdo").write_text("<dataProcessor/>", encoding="utf-8")
        (target / "ManagerModule.bsl").write_text("untouched", encoding="utf-8")
        (target / "ObjectModule.bsl").write_bytes(b"old module")
        (
            target
            / "Templates/ТаблицаПервыхСимволовВариантов/Template.txt"
        ).write_bytes(b"old select")
        (
            target
            / "Templates/ОпределенияИдентификаторов/Template.txt"
        ).write_bytes(b"old identifiers")
        (self.root / "grammar.txt").write_text("<S> ::= a", encoding="utf-8")
        config = self.root / "parsergen.toml"
        config.write_text(
            'grammar = "grammar.txt"\n'
            'target = "Парсер"\n'
            "lookahead = 1\n"
            "[entrypoints]\n"
            '"Разобрать" = "S"\n',
            encoding="utf-8",
        )
        return config, target

    def test_validate_reports_resolution_error_and_returns_one(self) -> None:
        grammar = self.root / "grammar.txt"
        grammar.write_text("<S> ::= <Missing>", encoding="utf-8")

        completed = self.run_cli(
            "validate",
            "--grammar",
            str(grammar),
            "--entry",
            "Разобрать=S",
            "--lookahead",
            "1",
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertIn("RES001", completed.stderr)
        self.assertIn(str(grammar), completed.stderr)

    def test_zero_lookahead_without_config_is_rejected(self) -> None:
        grammar = self.root / "grammar.txt"
        grammar.write_text("<S> ::= a", encoding="utf-8")

        completed = self.run_cli(
            "validate",
            "--grammar",
            str(grammar),
            "--entry",
            "Разобрать=S",
            "--lookahead",
            "0",
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertIn(
            "--lookahead must be an integer at least 1",
            completed.stderr,
        )

    def test_validate_reports_warnings_without_failing(self) -> None:
        grammar = self.root / "grammar.txt"
        grammar.write_text("<S> ::= a\n<Unused> ::= b", encoding="utf-8")

        completed = self.run_cli(
            "validate",
            "--grammar",
            str(grammar),
            "--entry",
            "Разобрать=S",
            "--lookahead",
            "1",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertIn("warning VAL102", completed.stderr)
        self.assertIn("grammar.txt:2:1", completed.stderr)

    def test_missing_grammar_file_is_an_io_failure_with_exit_two(self) -> None:
        missing = self.root / "missing-grammar.txt"

        completed = self.run_cli(
            "validate",
            "--grammar",
            str(missing),
            "--entry",
            "Разобрать=S",
        )

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("missing-grammar.txt", completed.stderr)

    def test_analyze_json_sorts_nullable_first_and_follow(self) -> None:
        grammar = self.root / "grammar.txt"
        grammar.write_text("<S> ::= a | ПУСТО", encoding="utf-8")

        completed = self.run_cli(
            "analyze",
            "--grammar",
            str(grammar),
            "--entry",
            "Разобрать=S",
            "--lookahead",
            "1",
            "--format",
            "json",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["nullable"], ["S"])
        self.assertEqual(payload["first"]["S"], [[], ["a"]])
        self.assertEqual(payload["follow"]["S"], [["$"]])

    def test_analyze_reports_materialization_limit_without_traceback(
        self,
    ) -> None:
        grammar = self.root / "grammar.txt"
        tokens = " | ".join(f"T{index:03d}" for index in range(101))
        grammar.write_text(
            f"#ID_X ::= {tokens}\n<S> ::= #ID_X #ID_X",
            encoding="utf-8",
        )

        completed = self.run_cli(
            "analyze",
            "--grammar",
            str(grammar),
            "--entry",
            "Разобрать=S",
            "--lookahead",
            "2",
            "--format",
            "json",
        )

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn(
            "may expand to 10201 rows; limit is 10000",
            completed.stderr,
        )
        self.assertNotIn("Traceback", completed.stderr)

    def test_analyze_text_materialization_limit_leaves_stdout_empty(
        self,
    ) -> None:
        grammar = self.root / "grammar.txt"
        tokens = " | ".join(f"T{index:03d}" for index in range(101))
        grammar.write_text(
            f"#ID_X ::= {tokens}\n<S> ::= #ID_X #ID_X",
            encoding="utf-8",
        )

        completed = self.run_cli(
            "analyze",
            "--grammar",
            str(grammar),
            "--entry",
            "Разобрать=S",
            "--lookahead",
            "2",
            "--format",
            "text",
        )

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn(
            "may expand to 10201 rows; limit is 10000",
            completed.stderr,
        )
        self.assertNotIn("Traceback", completed.stderr)

    def test_analyze_text_has_stable_human_readable_sections(self) -> None:
        grammar = self.root / "grammar.txt"
        grammar.write_text("<S> ::= a | ПУСТО", encoding="utf-8")

        completed = self.run_cli(
            "analyze",
            "--grammar",
            str(grammar),
            "--entry",
            "Разобрать=S",
            "--lookahead",
            "1",
            "--format",
            "text",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            (
                "lookahead: 1\n"
                "nullable: S\n"
                "FIRST S: ε | a\n"
                "FOLLOW S: $\n"
                "SELECT S:1: a\n"
                "SELECT S:2: $\n"
            ),
        )

    def test_generate_then_check_clean_then_detect_drift_without_writes(
        self,
    ) -> None:
        config, target = self.make_configured_project()
        manager = target / "ManagerModule.bsl"
        manager_before = manager.read_bytes()

        generated = self.run_cli("generate", "--config", str(config))
        self.assertEqual(generated.returncode, 0, generated.stderr)
        self.assertIn("ObjectModule.bsl", generated.stdout)
        self.assertEqual(manager.read_bytes(), manager_before)

        clean = self.run_cli("generate", "--config", str(config), "--check")
        self.assertEqual(clean.returncode, 0, clean.stderr)
        self.assertIn("artifacts are current", clean.stdout)

        target_module = target / "ObjectModule.bsl"
        target_module.write_text("stale", encoding="utf-8")
        drift = self.run_cli("generate", "--config", str(config), "--check")

        self.assertEqual(drift.returncode, 3, drift.stderr)
        self.assertIn("ObjectModule.bsl", drift.stdout)
        self.assertEqual(target_module.read_text(encoding="utf-8"), "stale")
        self.assertEqual(manager.read_bytes(), manager_before)

    def test_generate_uses_hybrid_backend_only_with_explicit_migration(self) -> None:
        config, target = self.make_configured_project()
        (self.root / "grammar.txt").write_text(
            "<S> ::= <Expr> {ЭтотУзел = ТекущийЭлемент}\n"
            "<Expr> ::= @НовыйБинарный Левая = <Expr> "
            "Оператор = '+' Правая = <Term> | <Term>\n"
            "<Term> ::= {ЭтотУзел = НовыйТерм} ITEM | "
            "{ЭтотУзел = НовыйТерм} NUMBER",
            encoding="utf-8",
        )
        config.write_text(
            'grammar = "grammar.txt"\n'
            'target = "Парсер"\n'
            "lookahead = 1\n"
            "[migration]\n"
            'canonical_productions = ["Expr"]\n'
            "[entrypoints]\n"
            '"Разобрать" = "S"\n',
            encoding="utf-8",
        )

        completed = self.run_cli("generate", "--config", str(config))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        module = (target / "ObjectModule.bsl").read_text(encoding="utf-8")
        expression = module.split("Функция НеТерминалExpr", 1)[1].split(
            "КонецФункции",
            1,
        )[0]
        self.assertEqual(expression.count("Пока "), 1)
        self.assertNotIn("НомерВариантаПродукции", expression)
        self.assertNotIn("Функция НеТерминал__parsergen_ebnf__", module)

    def test_full_canonical_generate_does_not_import_legacy_backend(self) -> None:
        config, _target = self.make_configured_project()
        (self.root / "grammar.txt").write_text(
            "<S> ::= @НовыйS ITEM",
            encoding="utf-8",
        )
        config.write_text(
            'grammar = "grammar.txt"\n'
            'target = "Парсер"\n'
            "lookahead = 1\n"
            "[migration]\n"
            'canonical_productions = ["S"]\n'
            "[entrypoints]\n"
            '"Разобрать" = "S"\n',
            encoding="utf-8",
        )

        completed = self.run_full_canonical_cli_without_legacy_backend(
            "generate",
            "--config",
            str(config),
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("legacy backend imported", completed.stderr)

    def test_generate_rejects_canonical_action_before_writing_artifacts(
        self,
    ) -> None:
        config, target = self.make_configured_project()
        (self.root / "grammar.txt").write_text(
            "<S> ::= {ЭтотУзел = НовыйS} ITEM",
            encoding="utf-8",
        )
        config.write_text(
            'grammar = "grammar.txt"\n'
            'target = "Парсер"\n'
            "lookahead = 1\n"
            "[migration]\n"
            'canonical_productions = ["S"]\n'
            "[entrypoints]\n"
            '"Разобрать" = "S"\n',
            encoding="utf-8",
        )
        artifact_paths = (
            target / "ObjectModule.bsl",
            target / "Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
            target / "Templates/ОпределенияИдентификаторов/Template.txt",
        )
        before = tuple(path.read_bytes() for path in artifact_paths)

        completed = self.run_cli("generate", "--config", str(config))

        self.assertEqual(completed.returncode, 2)
        self.assertIn("arbitrary source actions", completed.stderr)
        self.assertEqual(
            tuple(path.read_bytes() for path in artifact_paths),
            before,
        )

    def test_generate_layout_failure_returns_two_without_partial_writes(
        self,
    ) -> None:
        config, target = self.make_configured_project()
        paths = (
            target / "ObjectModule.bsl",
            target / "Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
            target / "Templates/ОпределенияИдентификаторов/Template.txt",
        )
        paths[0].unlink()
        before = (paths[1].read_bytes(), paths[2].read_bytes())

        completed = self.run_cli("generate", "--config", str(config))

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("ObjectModule.bsl", completed.stderr)
        self.assertFalse(paths[0].exists())
        self.assertEqual((paths[1].read_bytes(), paths[2].read_bytes()), before)

    def test_generate_target_argument_overrides_config_target(self) -> None:
        config, configured_target = self.make_configured_project()
        override_target = self.root / "ДругойПарсер"
        shutil.copytree(configured_target, override_target)

        completed = self.run_cli(
            "generate",
            "--config",
            str(config),
            "--target",
            str(override_target),
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            (configured_target / "ObjectModule.bsl").read_bytes(),
            b"old module",
        )
        self.assertNotEqual(
            (override_target / "ObjectModule.bsl").read_bytes(),
            b"old module",
        )


if __name__ == "__main__":
    unittest.main()
