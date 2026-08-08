from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from parsergen.artifacts import artifact_paths
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
        self.assertEqual(
            report["config"]["canonical_productions"],
            [
                "ПакетЗапросов",
                "ЗапросПакета",
                "ЗапросУничтожения",
                "Псевдоним",
                "ТипСоединения",
                "ИсточникДанных",
                "ПрисоединяемаяТаблица",
                "ИсточникДанныхВременнаяТаблица",
                "ИсточникДанныхВложенныйЗапрос",
                "ЭлементУпорядочивания",
                "НаправлениеУпорядочивания",
                "ТипКонтрольнойТочки",
                "Выражение",
                "ЛогическоеСлагаемое",
                "ТипСсылочногоПоля",
                "ОперандВ",
                "ОператорСравнения",
                "ШаблонПодобия",
                "АрифметическоеВыражение",
                "Слагаемое",
                "УнарнаяОперация",
                "Множитель",
                "Операнд",
                "Поле",
                "ВыражениеВсеПоляИсточника",
                "ПоляВложеннойТаблицы",
                "СписокВыражений",
                "ВыражениеМоделиЗапроса",
                "СписокВыраженийМодели",
                "ПриведениеТипа",
                "ОписаниеТипа",
                "Выбор",
                "КогдаТогда",
                "Константа",
                "Параметр",
                "АгрегатнаяФункция",
                "Функция",
                "ТипПериода",
            ],
        )
        self.assertEqual(report["canonical"]["conflicts"], [])
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
                "source_productions": 104,
                "source_alternatives": 238,
                "productions": 134,
                "alternatives": 294,
                "epsilon_alternatives": 67,
                "formal_parameters": 7,
                "actual_arguments": 22,
                "action_blocks": 160,
                "statements": 176,
                "constructor_statements": 29,
                "collection_statements": 16,
                "constant_statements": 14,
                "structural_statements": 114,
                "other_assignment_statements": 0,
                "other_statements": 3,
            },
        )

    def test_canonical_and_legacy_contracts_are_separate(self) -> None:
        self.assertEqual(
            self.report["canonical"],
            {
                "conflicts": [],
                "diagnostics": [
                    {
                        "code": "VAL102",
                        "severity": "warning",
                        "message": (
                            "production is unreachable from every entry point"
                        ),
                    },
                    {
                        "code": "VAL102",
                        "severity": "warning",
                        "message": (
                            "production is unreachable from every entry point"
                        ),
                    },
                ],
                "stats": {
                    "packed_first_rows": 10_940,
                    "packed_follow_rows": 50_148,
                    "select_descriptors": 294,
                    "select_direct_facts": 10_610,
                    "select_short_complete_prefixes": 330,
                    "packed_select_upper_bound": 34_222,
                    "conflict_work_items": 508,
                    "public_select_expansions": 0,
                    "select_cartesian_materializations": 0,
                },
            },
        )
        self.assertEqual(
            self.report["legacy"],
            {
                "matcher_rows": 9_293,
                "matcher_definitions": 0,
                "runtime_conflicts": [],
            },
        )
        self.assertEqual(self.report["artifacts"]["changed"], [])

    def test_generated_shape_baseline_is_explicit(self) -> None:
        self.assertEqual(
            self.report["generated"],
            {
                "bsl_functions": 116,
                "bsl_loc": 2726,
                "constructor_names": 78,
                "select_rows": 4_527,
                "identifier_rows": 276,
            },
        )


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

    def test_audit_does_not_write_changed_target_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            grammar = temporary_root / "query-language.grammar"
            target = temporary_root / "Parser"
            config = temporary_root / "parsergen.toml"
            shutil.copy2(
                PACKAGE_ROOT / "grammar/query-language.grammar",
                grammar,
            )
            shutil.copytree(
                REPOSITORY_ROOT / "QueryConsoleZUP/src/DataProcessors/Парсер",
                target,
            )
            config.write_text(
                'grammar = "query-language.grammar"\n'
                'target = "Parser"\n'
                "lookahead = 2\n\n"
                "[migration]\n"
                'canonical_productions = ["ПакетЗапросов", '
                '"ЗапросПакета", "ЗапросУничтожения", "Псевдоним", '
                '"ТипСоединения", "ИсточникДанных", '
                '"ПрисоединяемаяТаблица", '
                '"ИсточникДанныхВременнаяТаблица", '
                '"ИсточникДанныхВложенныйЗапрос", '
                '"ЭлементУпорядочивания", '
                '"НаправлениеУпорядочивания", "ТипКонтрольнойТочки", '
                '"Выражение", '
                '"ЛогическоеСлагаемое", '
                '"ТипСсылочногоПоля", '
                '"ОперандВ", "ОператорСравнения", '
                '"ШаблонПодобия", '
                '"АрифметическоеВыражение", "Слагаемое", '
                '"УнарнаяОперация", "Множитель", "Операнд", '
                '"Поле", "ВыражениеВсеПоляИсточника", '
                '"ПоляВложеннойТаблицы", "СписокВыражений", '
                '"ВыражениеМоделиЗапроса", '
                '"СписокВыраженийМодели", "ПриведениеТипа", '
                '"ОписаниеТипа", '
                '"Выбор", "КогдаТогда", "Константа", "Параметр", '
                '"АгрегатнаяФункция", "Функция", "ТипПериода"]\n\n'
                "[entrypoints]\n"
                '"Разобрать" = "ПакетЗапросов"\n'
                '"РазобратьВыражение" = "Выражение"\n',
                encoding="utf-8",
            )
            object_module, _, _ = artifact_paths(target)
            object_module.write_bytes(
                object_module.read_bytes() + b"\n// deliberately changed\n"
            )
            before = {
                path: (path.read_bytes(), path.stat().st_mtime_ns)
                for path in artifact_paths(target)
            }

            report = audit_migration.build_migration_audit(config)

            self.assertEqual(
                report["artifacts"]["changed"],
                [str(Path("Parser") / "ObjectModule.bsl")],
            )
            self.assertEqual(
                {
                    path: (path.read_bytes(), path.stat().st_mtime_ns)
                    for path in artifact_paths(target)
                },
                before,
            )
