from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from parsergen.grammar_parser import parse_grammar


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
AUDIT_PATH = PACKAGE_ROOT / "benchmarks/audit_migration.py"
SPEC = spec_from_file_location("audit_migration", AUDIT_PATH)
assert SPEC is not None and SPEC.loader is not None
audit_migration = module_from_spec(SPEC)
SPEC.loader.exec_module(audit_migration)


class MigrationAuditUnitTests(unittest.TestCase):
    def test_classifies_constructor_structural_collection_and_constant_actions(
        self,
    ) -> None:
        parsed = parse_grammar(
            "<S> ::= "
            "{ЭтотУзел = НовыйСписок; "
            "ЭтотУзел.Элементы.Добавить(ТекущийЭлемент); "
            "ЭтотУзел.Флаг = Истина; "
            "ЭтотУзел.Значение = ТекущийЭлемент} item",
        )
        assert parsed.grammar is not None

        self.assertEqual(
            audit_migration.classify_semantic_actions(parsed.grammar),
            {
                "action_blocks": 1,
                "statements": 4,
                "constructor_statements": 1,
                "collection_statements": 1,
                "constant_statements": 1,
                "structural_statements": 1,
                "other_assignment_statements": 0,
                "other_statements": 0,
            },
        )

    def test_build_report_has_separate_canonical_and_legacy_sections(
        self,
    ) -> None:
        report = audit_migration.build_migration_audit(
            REPOSITORY_ROOT / "parsergen.toml"
        )

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(
            set(report),
            {
                "schema_version",
                "config",
                "structural",
                "canonical",
                "legacy",
                "generated",
                "artifacts",
            },
        )
        self.assertEqual(report["config"]["entrypoints"], {
            "Разобрать": "ПакетЗапросов",
            "РазобратьВыражение": "Выражение",
        })
        self.assertEqual(len(report["canonical"]["conflicts"]), 2)
        self.assertEqual(report["legacy"]["runtime_conflicts"], [])
        self.assertEqual(report["artifacts"]["changed"], [])


class MigrationAuditProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit_migration.build_migration_audit(
            REPOSITORY_ROOT / "parsergen.toml"
        )

    def test_structural_baseline_is_explicit(self) -> None:
        self.assertEqual(
            self.report["structural"],
            {
                "productions": 124,
                "alternatives": 281,
                "epsilon_alternatives": 63,
                "formal_parameters": 8,
                "actual_arguments": 26,
                "action_blocks": 398,
                "statements": 431,
                "constructor_statements": 102,
                "collection_statements": 37,
                "constant_statements": 33,
                "structural_statements": 254,
                "other_assignment_statements": 0,
                "other_statements": 5,
            },
        )

    def test_canonical_and_legacy_contracts_are_separate(self) -> None:
        self.assertEqual(
            self.report["canonical"]["conflicts"],
            [
                {
                    "production": "ЛогическийОператор",
                    "left_alternative": 2,
                    "right_alternative": 5,
                    "witness": ["ССЫЛКА", "АВТОУПОРЯДОЧИВАНИЕ"],
                },
                {
                    "production": "ОперандВ",
                    "left_alternative": 1,
                    "right_alternative": 2,
                    "witness": ["ВЫБРАТЬ", "*"],
                },
            ],
        )
        self.assertEqual(self.report["legacy"]["matcher_rows"], 11_273)
        self.assertEqual(self.report["legacy"]["runtime_conflicts"], [])
        self.assertEqual(self.report["artifacts"]["changed"], [])

    def test_generated_shape_baseline_is_explicit(self) -> None:
        self.assertEqual(self.report["generated"]["bsl_functions"], 135)
        self.assertEqual(self.report["generated"]["bsl_loc"], 3394)
        self.assertEqual(self.report["generated"]["constructor_names"], 79)


class MigrationAuditCompatibilityTests(unittest.TestCase):
    def test_cli_returns_structured_json_for_missing_config(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_PATH),
                "--config",
                "missing-parsergen.toml",
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["type"], "FileNotFoundError")
        self.assertNotIn("Traceback", result.stderr.decode("utf-8"))

    def test_report_derives_runtime_conflicts_from_its_legacy_rows(self) -> None:
        with patch.object(
            audit_migration,
            "find_runtime_dispatch_conflicts",
            side_effect=AssertionError("must not build a second artifact"),
            create=True,
        ):
            report = audit_migration.build_migration_audit(
                REPOSITORY_ROOT / "parsergen.toml",
                max_matcher_rows=100_001,
            )

        self.assertEqual(report["legacy"]["runtime_conflicts"], [])
