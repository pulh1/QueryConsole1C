from pathlib import Path
import unittest

from parsergen.analysis import (
    compute_analysis,
    find_runtime_dispatch_conflicts,
    find_select_conflicts,
)
from parsergen.grammar_parser import parse_grammar
from parsergen.hybrid_bsl_codegen import generate_hybrid_parser
from parsergen.parser_ir import LeftFold, build_parser_ir
from parsergen.resolver import resolve_grammar


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_GRAMMAR = PACKAGE_ROOT / "grammar/query-language.grammar"
MIGRATED_PRODUCTIONS = (
    "Выражение",
    "ЛогическоеСлагаемое",
    "АрифметическоеВыражение",
    "Слагаемое",
    "УнарнаяОперация",
    "СписокВыражений",
    "СписокВыраженийМодели",
    "Выбор",
)


def _generated_function(module: str, production: str) -> str:
    marker = f"Функция НеТерминал{production}("
    return module.split(marker, 1)[1].split("КонецФункции", 1)[0]


class RepositoryGrammarCompatibilityTests(unittest.TestCase):
    def test_repository_grammar_parses_and_resolves_without_diagnostics(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        self.assertEqual(parsed.diagnostics, ())
        assert parsed.source_grammar is not None
        assert parsed.grammar is not None
        self.assertEqual(len(parsed.source_grammar.productions), 112)
        self.assertEqual(len(parsed.grammar.productions), 124)

        resolution = resolve_grammar(parsed.grammar)
        self.assertEqual(resolution.diagnostics, ())
        self.assertIsNotNone(resolution.grammar)
        assert resolution.grammar is not None
        self.assertEqual(
            {
                name: len(token_types)
                for name, token_types in resolution.grammar.identifier_tokens.items()
            },
            {
                "ID_Полный": 78,
                "ID_ИмяТаблицы": 18,
                "ID_Псевдоним": 40,
                "ID_ПсевдонимРасширенный": 45,
                "ID_ПсевдонимКонтрольнойТочкиИтогов": 45,
                "ID_ПолеБезРазыменования": 31,
                "ID_ГруппаТипаСсылки": 1,
                "ID_ИмяТипа": 17,
            },
        )

    def test_repository_k2_analysis_stays_compressed_through_conflict_scan(
        self,
    ) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        grammar = resolution.grammar

        analysis = compute_analysis(
            grammar,
            2,
            ("ПакетЗапросов", "Выражение"),
        )
        stats = analysis._compressed.stats
        self.assertGreater(stats["follow_delta_facts"], 0)
        self.assertEqual(stats["select_cartesian_materializations"], 0)
        self.assertEqual(stats["select_packed_product_rows"], 0)
        self.assertEqual(
            stats["select_descriptors"],
            sum(
                len(grammar.productions[name])
                for name in grammar.production_order
            ),
        )
        self.assertGreater(stats["select_short_complete_prefixes"], 0)
        self.assertEqual(stats["public_first_expansions"], 0)
        self.assertEqual(stats["public_follow_expansions"], 0)
        self.assertEqual(stats["public_select_expansions"], 0)

        self.assertEqual(
            find_select_conflicts(grammar, analysis),
            (),
        )
        self.assertEqual(find_runtime_dispatch_conflicts(grammar, analysis), ())
        self.assertEqual(stats["public_select_expansions"], 0)
        self.assertEqual(stats["select_cartesian_materializations"], 0)
        self.assertEqual(stats["select_packed_product_rows"], 0)

    def test_arithmetic_families_lower_to_canonical_left_folds(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(
            resolution.grammar,
            2,
            ("ПакетЗапросов", "Выражение"),
        )

        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=("АрифметическоеВыражение", "Слагаемое"),
        )

        self.assertEqual(
            tuple(production.name for production in parser_ir.productions),
            ("АрифметическоеВыражение", "Слагаемое"),
        )
        for production in parser_ir.productions:
            with self.subTest(production=production.name):
                self.assertEqual(len(production.alternatives), 1)
                self.assertIsInstance(
                    production.alternatives[0].operations[0],
                    LeftFold,
                )

    def test_arithmetic_families_generate_iterative_left_folds(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(
            resolution.grammar,
            2,
            ("ПакетЗапросов", "Выражение"),
        )
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=MIGRATED_PRODUCTIONS,
        )

        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=MIGRATED_PRODUCTIONS,
            entrypoints={
                "РазобратьПакетЗапросов": "ПакетЗапросов",
                "РазобратьВыражение": "Выражение",
            },
        )

        module = generated.module_text
        self.assertNotIn("Функция НеТерминалАрифметическаяОперация(", module)
        self.assertNotIn("Функция НеТерминалОперацияУмножения(", module)
        expected = {
            "АрифметическоеВыражение": (2, "НеТерминалСлагаемое()"),
            "Слагаемое": (3, "НеТерминалМножитель()"),
        }
        for production, (branches, base_call) in expected.items():
            with self.subTest(production=production):
                function = _generated_function(module, production)
                self.assertEqual(function.count("Пока "), 1)
                self.assertNotIn(f"НеТерминал{production}(", function)
                self.assertNotIn("НомерВариантаПродукции", function)
                self.assertIn(base_call, function)
                self.assertEqual(
                    function.count("ЭлементыМоделиЗапроса.НовыйБинарнаяОперация("),
                    branches,
                )
                self.assertEqual(function.count("ЭтотУзел.ЛеваяЧасть ="), branches)
                self.assertEqual(function.count("ЭтотУзел.Операция ="), branches)
                self.assertEqual(function.count("ЭтотУзел.ПраваяЧасть ="), branches)

    def test_logical_families_generate_iterative_left_folds(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(
            resolution.grammar,
            2,
            ("ПакетЗапросов", "Выражение"),
        )
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=MIGRATED_PRODUCTIONS,
        )

        for production in parser_ir.productions[:2]:
            with self.subTest(ir=production.name):
                self.assertEqual(len(production.alternatives), 1)
                self.assertIsInstance(
                    production.alternatives[0].operations[0],
                    LeftFold,
                )

        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=MIGRATED_PRODUCTIONS,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )
        module = generated.module_text
        self.assertNotIn("Функция НеТерминалЛогическоеИли(", module)
        self.assertNotIn("Функция НеТерминалЛогическоеИ(", module)
        expected = {
            "Выражение": "НеТерминалЛогическоеСлагаемое()",
            "ЛогическоеСлагаемое": "НеТерминалЛогическийМножитель()",
        }
        for production, base_call in expected.items():
            with self.subTest(codegen=production):
                function = _generated_function(module, production)
                self.assertEqual(function.count("Пока "), 1)
                self.assertNotIn(f"НеТерминал{production}(", function)
                self.assertNotIn("НомерВариантаПродукции", function)
                self.assertIn(base_call, function)
                self.assertEqual(
                    function.count("ЭлементыМоделиЗапроса.НовыйБинарнаяОперация("),
                    1,
                )
                self.assertEqual(function.count("ЭтотУзел.ЛеваяЧасть ="), 1)
                self.assertEqual(function.count("ЭтотУзел.ПраваяЧасть ="), 1)

    def test_expression_list_generates_collection_loop(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(
            resolution.grammar,
            2,
            ("ПакетЗапросов", "Выражение"),
        )
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=MIGRATED_PRODUCTIONS,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=MIGRATED_PRODUCTIONS,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        self.assertNotIn(
            "Функция НеТерминалОпциональноеПродолжениеСпискаВыражений(",
            module,
        )
        function = _generated_function(module, "СписокВыражений")
        self.assertEqual(function.count("Пока "), 1)
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйСписокВыражений("),
            1,
        )
        self.assertEqual(function.count("ЭтотУзел.Элементы.Добавить("), 2)
        self.assertEqual(function.count('Лексема(",")'), 1)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_unary_signs_generate_canonical_one_or_more_loop(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(
            resolution.grammar,
            2,
            ("ПакетЗапросов", "Выражение"),
        )
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=MIGRATED_PRODUCTIONS,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=MIGRATED_PRODUCTIONS,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        self.assertNotIn(
            "Функция НеТерминалУнарнаяОперацияПродолжение(",
            module,
        )
        function = _generated_function(module, "УнарнаяОперация")
        self.assertEqual(function.count("Пока "), 1)
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйУнарнаяОперация("),
            1,
        )
        self.assertEqual(function.count("ЭтотУзел.Знаки.Добавить("), 4)
        self.assertEqual(function.count("ЭтотУзел.Выражение ="), 1)
        self.assertNotIn("НомерВариантаПродукции", function)
        self.assertEqual(function.count('Лексема("-")'), 2)
        self.assertEqual(function.count('Лексема("+")'), 2)
        self.assertNotIn("Добавить(Неопределено)", function)
        self.assertNotIn(
            "Функция НеТерминалЗнакУнарнойОперации(",
            module,
        )

    def test_model_expression_list_generates_collection_loop(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(
            resolution.grammar,
            2,
            ("ПакетЗапросов", "Выражение"),
        )
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=MIGRATED_PRODUCTIONS,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=MIGRATED_PRODUCTIONS,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        self.assertNotIn(
            "Функция НеТерминалОпциональноеПродолжениеСпискаВыраженийМодели(",
            module,
        )
        function = _generated_function(module, "СписокВыраженийМодели")
        self.assertEqual(function.count("Пока "), 1)
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйСписокВыражений("),
            1,
        )
        self.assertEqual(function.count("ЭтотУзел.Элементы.Добавить("), 2)
        self.assertEqual(function.count('Лексема(",")'), 1)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_choice_generates_optional_bindings_and_alternative_loop(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        assert parsed.grammar is not None
        resolution = resolve_grammar(parsed.grammar)
        assert resolution.grammar is not None
        analysis = compute_analysis(
            resolution.grammar,
            2,
            ("ПакетЗапросов", "Выражение"),
        )
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=MIGRATED_PRODUCTIONS,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=MIGRATED_PRODUCTIONS,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        for helper in (
            "ВыражениеВыбора",
            "АльтернативыВыбора",
            "ПродолжениеАльтернативВыбора",
            "Иначе",
        ):
            self.assertNotIn(f"Функция НеТерминал{helper}(", module)
        function = _generated_function(module, "Выбор")
        self.assertEqual(function.count("Пока "), 1)
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйВыбор("),
            1,
        )
        self.assertEqual(
            function.count("ЭтотУзел.АльтернативыВыбора.Добавить("),
            2,
        )
        self.assertIn("ЭтотУзел.ВыражениеВыбора = Неопределено;", function)
        self.assertIn("ЭтотУзел.Иначе = Неопределено;", function)
        self.assertNotRegex(
            function,
            r'Значение\d+ = Терминал\("(?:ВЫБОР|ИНАЧЕ|КОНЕЦ)"\);',
        )
        self.assertNotIn("НомерВариантаПродукции", function)


if __name__ == "__main__":
    unittest.main()
