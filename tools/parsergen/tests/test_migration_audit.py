from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from parsergen.analysis import compute_analysis
from parsergen.artifacts import artifact_paths
from parsergen.decision_dag import CommitAlternative, decision_paths
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import (
    ConsumeKnownSymbol,
    Dispatch,
    ParseSymbol,
    WrapOptional,
    build_parser_ir,
)
from parsergen.resolver import resolve_grammar


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
AUDIT_PATH = PACKAGE_ROOT / "benchmarks/audit_migration.py"
SPEC = spec_from_file_location("audit_migration", AUDIT_PATH)
assert SPEC is not None and SPEC.loader is not None
audit_migration = module_from_spec(SPEC)
SPEC.loader.exec_module(audit_migration)


class MigrationAuditUnitTests(unittest.TestCase):
    def test_redundant_validations_include_unspecialized_fallback_commit_paths(
        self,
    ) -> None:
        parsed = parse_grammar("<S> ::= (A | B)", "grammar.txt")
        assert parsed.diagnostics == ()
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.diagnostics == ()
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))
        with patch(
            "parsergen.parser_ir_optimization.optimize_parser_ir",
            side_effect=lambda parser_ir: parser_ir,
        ):
            parser_ir = build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved.grammar,
                analysis,
                entrypoint_productions=("S",),
            )

        production = parser_ir.productions[0]
        alternative = production.alternatives[0]
        dispatch = alternative.operations[0]
        assert isinstance(dispatch, Dispatch)
        first_branch, fallback_branch = dispatch.branches
        first_parse = first_branch.operations[0]
        assert isinstance(first_parse, ParseSymbol)
        first_path = next(
            path
            for path in decision_paths(dispatch.decision.dag)
            if isinstance(path.leaf, CommitAlternative)
            and path.leaf.outcome == first_branch.outcome
        )
        known = ConsumeKnownSymbol(
            first_parse.symbol,
            False,
            first_path.facts[0].predicate.token_types,
            first_parse.source_span,
        )
        specialized_branch = replace(
            first_branch,
            operations=(known,),
            path_facts=first_path.facts,
        )
        dispatch = replace(
            dispatch,
            branches=(specialized_branch, fallback_branch),
        )
        alternative = replace(alternative, operations=(dispatch,))
        production = replace(production, alternatives=(alternative,))
        parser_ir = replace(parser_ir, productions=(production,))

        self.assertEqual(
            audit_migration.decision_path_metrics(parser_ir),
            {
                "specialized_paths": 1,
                "known_symbol_consumes": 1,
                "redundant_validations": 1,
            },
        )

    def test_redundant_validations_include_single_collapsed_composed_fallback(
        self,
    ) -> None:
        parsed = parse_grammar(
            "#ID_Name ::= A\n"
            "<S> ::= <Base> Child => <Choice>?\n"
            "<Base> ::= @НовыйBase BASE\n"
            "<Choice> ::= @НовыйChoice #ID_Name",
            "grammar.txt",
        )
        assert parsed.diagnostics == ()
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.diagnostics == ()
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolved.grammar,
            analysis,
            entrypoint_productions=("S",),
        )

        production = parser_ir.productions[0]
        alternative = production.alternatives[0]
        wrapper = alternative.operations[0]
        assert isinstance(wrapper, WrapOptional)
        self.assertEqual(len(wrapper.branches), 1)
        fallback = wrapper.branches[0]
        self.assertIsNone(fallback.path_facts)
        self.assertEqual(fallback.outcome.production, "Choice")
        self.assertNotEqual(
            wrapper.decision.source.production,
            fallback.outcome.production,
        )
        self.assertNotIn("Choice", {item.name for item in parser_ir.productions})
        known_index, known = next(
            (index, operation)
            for index, operation in enumerate(fallback.operations)
            if isinstance(operation, ConsumeKnownSymbol)
        )
        operations = list(fallback.operations)
        operations[known_index] = ParseSymbol(known.symbol, known.source_span)
        fallback = replace(fallback, operations=tuple(operations))
        wrapper = replace(wrapper, branches=(fallback,))
        alternative = replace(alternative, operations=(wrapper,))
        production = replace(production, alternatives=(alternative,))
        parser_ir = replace(parser_ir, productions=(production,))

        self.assertEqual(
            audit_migration.decision_path_metrics(parser_ir),
            {
                "specialized_paths": 0,
                "known_symbol_consumes": 0,
                "redundant_validations": 1,
            },
        )

    def test_predicate_strategy_benchmark_selects_measured_exact_policy(
        self,
    ) -> None:
        comparison = audit_migration.benchmark_predicate_strategies(
            REPOSITORY_ROOT / "parsergen.toml"
        )

        self.assertEqual(
            set(comparison),
            {"inline", "named", "eligible_named_sets", "selected"},
        )
        for policy in ("inline", "named"):
            self.assertEqual(
                set(comparison[policy]),
                {
                    "bsl_loc",
                    "max_condition_chars",
                    "helper_calls",
                    "generation_seconds",
                },
            )
            self.assertGreater(comparison[policy]["generation_seconds"], 0)
        self.assertEqual(comparison["inline"]["helper_calls"], 0)
        self.assertGreater(comparison["named"]["helper_calls"], 0)
        self.assertGreater(comparison["eligible_named_sets"], 0)
        self.assertEqual(comparison["selected"], "inline")

    def test_generated_bsl_metrics_count_decisions_and_lookahead_atoms(
        self,
    ) -> None:
        module = (
            'Функция НеТерминалS()\n'
            'Если ТипТокенаПросмотра(0) = "A" Или '
            'ТипТокенаПросмотра(1) = "B" Тогда\n'
            'КонецЕсли;\n'
            'КонецФункции\n'
        )
        self.assertEqual(
            audit_migration.generated_bsl_metrics(module),
            {
                "lookahead_calls": 2,
                "decision_lines": 1,
                "predicate_atoms": 2,
                "nonterminal_functions": 1,
                "nonterminal_call_sites": 0,
                "max_condition_chars": 70,
                "max_condition_predicate_atoms": 2,
                "max_condition_lookahead_calls": 2,
                "max_condition_nesting": 1,
            },
        )

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
                "decision_dag",
                "decision_path",
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
                "ЗапросВыбора",
                "ОбъединяемыйЗапрос",
                "ОператорОбъединения",
                "ТипОбъединенияЗапроса",
                "ПоляВыборки",
                "ПолеВыборки",
                "ВыражениеВсеПоляВыборки",
                "ВыражениеВсеПоля",
                "Псевдоним",
                "БлокИз",
                "ИсточникДанныхЗапроса",
                "СписокСоединений",
                "ПраваяЧастьСоединения",
                "ИсточникДанныхСоединения",
                "ТипСоединения",
                "ИсточникДанных",
                "ПрисоединяемаяТаблица",
                "ИсточникДанныхТаблицаЗначений",
                "ИсточникДанныхВременнаяТаблица",
                "ИсточникДанныхТаблица",
                "ИсточникДанныхВложенныйЗапрос",
                "СписокПараметров",
                "ПараметрТаблицы",
                "СписокЭлементовУпорядочивания",
                "ЭлементУпорядочивания",
                "НаправлениеУпорядочивания",
                "ПоляИтогов",
                "КонтрольныеТочкиИтогов",
                "КонтрольнаяТочкаИтогов",
                "ТипКонтрольнойТочки",
                "РасширениеСКД",
                "Выражение",
                "ЛогическоеСлагаемое",
                "ЛогическийМножитель",
                "ЛогическийОператор",
                "ТипСсылочногоПоля",
                "ОперандВ",
                "ЛогическаяОперация",
                "ЛогическаяОперацияБезОтрицания",
                "ОперандСравнения",
                "ОператорПодобно",
                "ШаблонПодобия",
                "АрифметическоеВыражение",
                "Слагаемое",
                "УнарнаяОперация",
                "Множитель",
                "Операнд",
                "Поле",
                "РазыменованиеПослеСкобок",
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
        self.assertEqual(
            set(report["decision_dag"]),
            {
                "source_states",
                "dag_states",
                "shared_states",
                "max_depth",
                "decision_regions",
                "emitted_predicates",
            },
        )
        self.assertGreater(report["decision_dag"]["source_states"], 0)
        self.assertGreater(report["decision_dag"]["dag_states"], 0)
        self.assertGreater(report["decision_dag"]["decision_regions"], 0)
        self.assertGreater(report["decision_dag"]["emitted_predicates"], 0)
        self.assertEqual(
            report["decision_path"],
            {
                "specialized_paths": 6,
                "known_symbol_consumes": 11,
                "redundant_validations": 0,
            },
        )
        self.assertEqual(
            report["canonical"]["stats"]["public_select_expansions"],
            0,
        )
        self.assertEqual(
            report["canonical"]["stats"]["select_cartesian_materializations"],
            0,
        )
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
                "source_productions": 66,
                "source_alternatives": 144,
                "productions": 156,
                "alternatives": 334,
                "epsilon_alternatives": 80,
                "formal_parameters": 0,
                "actual_arguments": 0,
                "action_blocks": 0,
                "statements": 0,
                "constructor_statements": 0,
                "collection_statements": 0,
                "constant_statements": 0,
                "structural_statements": 0,
                "other_assignment_statements": 0,
                "other_statements": 0,
            },
        )

    def test_canonical_and_legacy_contracts_are_separate(self) -> None:
        self.assertEqual(
            self.report["canonical"],
            {
                "conflicts": [],
                "diagnostics": [],
                "stats": {
                    "packed_first_rows": 12_182,
                    "packed_follow_rows": 61_150,
                    "select_descriptors": 334,
                    "select_direct_facts": 11_810,
                    "select_short_complete_prefixes": 372,
                    "packed_select_upper_bound": 41_209,
                    "conflict_work_items": 531,
                    "public_select_expansions": 0,
                    "select_cartesian_materializations": 0,
                },
            },
        )
        self.assertEqual(
            self.report["legacy"],
            {
                "matcher_rows": 10_615,
                "matcher_definitions": 0,
                "runtime_conflicts": [],
            },
        )
        self.assertEqual(
            self.report["decision_dag"],
            {
                "source_states": 33_659,
                "dag_states": 406,
                "shared_states": 89,
                "max_depth": 2,
                "decision_regions": 109,
                "emitted_predicates": 310,
            },
        )
        self.assertEqual(self.report["artifacts"]["changed"], [])

    def test_decision_path_baseline_is_explicit(self) -> None:
        self.assertEqual(
            self.report["decision_path"],
            {
                "specialized_paths": 6,
                "known_symbol_consumes": 11,
                "redundant_validations": 0,
            },
        )

    def test_generated_shape_baseline_is_explicit(self) -> None:
        self.assertEqual(
            self.report["generated"],
            {
                "bsl_functions": 74,
                "bsl_loc": 2463,
                "constructor_names": 79,
                "select_rows": 0,
                "identifier_rows": 276,
                "lookahead_calls": 130,
                "decision_lines": 366,
                "predicate_atoms": 3_779,
                "nonterminal_functions": 63,
                "nonterminal_call_sites": 180,
                "max_condition_chars": 2_551,
                "max_condition_predicate_atoms": 88,
                "max_condition_lookahead_calls": 1,
                "max_condition_nesting": 2,
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
                '"ЗапросПакета", "ЗапросУничтожения", "ЗапросВыбора", "ОбъединяемыйЗапрос", "ОператорОбъединения", "ТипОбъединенияЗапроса", '
                '"ПоляВыборки", "ПолеВыборки", '
                '"ВыражениеВсеПоляВыборки", "ВыражениеВсеПоля", '
                '"Псевдоним", "БлокИз", '
                '"ИсточникДанныхЗапроса", "СписокСоединений", '
                '"ПраваяЧастьСоединения", "ИсточникДанныхСоединения", '
                '"ТипСоединения", "ИсточникДанных", '
                '"ПрисоединяемаяТаблица", '
                    '"ИсточникДанныхТаблицаЗначений", '
                    '"ИсточникДанныхВременнаяТаблица", '
                    '"ИсточникДанныхТаблица", '
                '"ИсточникДанныхВложенныйЗапрос", '
                '"СписокПараметров", "ПараметрТаблицы", '
                '"СписокЭлементовУпорядочивания", '
                '"ЭлементУпорядочивания", '
                '"НаправлениеУпорядочивания", '
                '"ПоляИтогов", '
                '"КонтрольныеТочкиИтогов", '
                '"КонтрольнаяТочкаИтогов", "ТипКонтрольнойТочки", '
                '"РасширениеСКД", '
                '"Выражение", '
                '"ЛогическоеСлагаемое", '
                '"ЛогическийМножитель", "ЛогическийОператор", '
                '"ТипСсылочногоПоля", '
                '"ОперандВ", '
                '"ЛогическаяОперация", '
                '"ЛогическаяОперацияБезОтрицания", '
                '"ОперандСравнения", "ОператорПодобно", '
                '"ШаблонПодобия", '
                '"АрифметическоеВыражение", "Слагаемое", '
                '"УнарнаяОперация", "Множитель", "Операнд", '
                '"Поле", "РазыменованиеПослеСкобок", '
                '"ВыражениеВсеПоляИсточника", '
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
