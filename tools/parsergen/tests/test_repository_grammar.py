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
    "ПакетЗапросов",
    "ЗапросПакета",
    "ЗапросУничтожения",
    "ПолеВыборки",
    "ВыражениеВсеПоляВыборки",
    "ВыражениеВсеПоля",
    "Псевдоним",
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
    "КонтрольныеТочкиИтогов",
    "КонтрольнаяТочкаИтогов",
    "ТипКонтрольнойТочки",
    "ТипПериодаИтогов",
    "Выражение",
    "ЛогическоеСлагаемое",
    "ТипСсылочногоПоля",
    "ОперандВ",
    "ОператорСравнения",
    "Отрицание",
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
)


def _generated_function(module: str, production: str) -> str:
    marker = f"Функция НеТерминал{production}("
    return module.split(marker, 1)[1].split("КонецФункции", 1)[0]


class RepositoryGrammarCompatibilityTests(unittest.TestCase):
    def test_order_element_preserves_factory_defaults_on_absent_options(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(
            generated.module_text,
            "ЭлементУпорядочивания",
        )
        self.assertEqual(
            function.count(
                "ЭлементыМоделиЗапроса.НовыйЭлементПорядка("
            ),
            1,
        )
        self.assertEqual(function.count('Терминал("ИЕРАРХИЯ");'), 1)
        self.assertEqual(function.count("ЭтотУзел.Иерархия = Истина;"), 1)
        self.assertEqual(
            function.count("НеТерминалНаправлениеУпорядочивания()"),
            1,
        )
        self.assertEqual(function.count("ЭтотУзел.Направление ="), 1)
        self.assertNotIn("НеТерминалИерархияОпционально", function)
        self.assertNotIn("ЭтотУзел.Направление = Неопределено;", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_order_direction_generates_constructor_alternatives(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(
            generated.module_text,
            "НаправлениеУпорядочивания",
        )
        expected = {
            "ВОЗР": "НовыйНаправлениеВозрастание",
            "УБЫВ": "НовыйНаправлениеУбывание",
        }
        for token, constructor in expected.items():
            with self.subTest(token=token):
                self.assertEqual(function.count(f'Терминал("{token}");'), 1)
                self.assertEqual(
                    function.count(
                        f"ЭлементыМоделиЗапроса.{constructor}("
                    ),
                    1,
                )
        self.assertIn("ВызватьИсключениеCanonicalСинтаксическаяОшибка", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_totals_checkpoint_type_generates_constructor_or_empty_result(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(
            generated.module_text,
            "ТипКонтрольнойТочки",
        )
        self.assertEqual(function.count('Терминал("ТОЛЬКО");'), 1)
        self.assertEqual(function.count('Терминал("ИЕРАРХИЯ");'), 2)
        self.assertEqual(
            function.count(
                "ЭлементыМоделиЗапроса."
                "НовыйТипКонтрольнойТочкиТолькоИерархия("
            ),
            1,
        )
        self.assertEqual(
            function.count(
                "ЭлементыМоделиЗапроса."
                "НовыйТипКонтрольнойТочкиИерархия("
            ),
            1,
        )
        self.assertIn("РезультатПродукции = Неопределено;", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_join_type_generates_constructor_only_alternatives(self) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(generated.module_text, "ТипСоединения")
        expected = {
            "ЛЕВОЕ": "НовыйТипСоединенияЛевое",
            "ПРАВОЕ": "НовыйТипСоединенияПравое",
            "ВНУТРЕННЕЕ": "НовыйТипСоединенияВнутреннее",
            "ПОЛНОЕ": "НовыйТипСоединенияПолное",
        }
        for token, constructor in expected.items():
            with self.subTest(token=token):
                self.assertIn(f'Терминал("{token}");', function)
                self.assertEqual(
                    function.count(
                        f"ЭлементыМоделиЗапроса.{constructor}("
                    ),
                    1,
                )
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_alias_alternatives_return_their_identifier_value(self) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(generated.module_text, "Псевдоним")
        self.assertIn('Терминал("КАК");', function)
        self.assertIn(
            'Значение1 = Идентификатор("ID_ПсевдонимРасширенный");',
            function,
        )
        self.assertIn(
            'Значение2 = Идентификатор("ID_Псевдоним");',
            function,
        )
        self.assertIn("РезультатПродукции = Значение1;", function)
        self.assertIn("РезультатПродукции = Значение2;", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_period_type_returns_its_identifier_value(self) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(generated.module_text, "ТипПериода")
        self.assertIn(
            'Значение1 = Идентификатор("ID_Полный");',
            function,
        )
        self.assertIn("РезультатПродукции = Значение1;", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_package_query_alternatives_return_their_single_child(self) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(generated.module_text, "ЗапросПакета")
        self.assertIn("Значение1 = НеТерминалЗапросВыбора();", function)
        self.assertIn("Значение2 = НеТерминалЗапросУничтожения();", function)
        self.assertIn("РезультатПродукции = Значение1;", function)
        self.assertIn("РезультатПродукции = Значение2;", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_operand_alternatives_return_their_single_child(self) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(generated.module_text, "Операнд")
        for index, child in enumerate(
            (
                "Выбор",
                "Поле",
                "Константа",
                "Параметр",
                "АгрегатнаяФункция",
                "Функция",
            ),
            start=1,
        ):
            with self.subTest(child=child):
                self.assertIn(
                    f"Значение{index} = НеТерминал{child}();",
                    function,
                )
                self.assertIn(
                    f"РезультатПродукции = Значение{index};",
                    function,
                )
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_factor_alternatives_return_their_single_child(self) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(generated.module_text, "Множитель")
        self.assertIn("Значение1 = НеТерминалОперанд();", function)
        self.assertIn("РезультатПродукции = Значение1;", function)
        self.assertIn("Значение2 = НеТерминалУнарнаяОперация();", function)
        self.assertIn("РезультатПродукции = Значение2;", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_type_cast_family_generates_declarative_bindings_and_optionals(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        for helper in ("ОписаниеЧисла", "ТочностьЧисла", "ОписаниеСтроки"):
            with self.subTest(helper=helper):
                self.assertNotIn(f"Функция НеТерминал{helper}(", module)

        type_cast = _generated_function(module, "ПриведениеТипа")
        self.assertIn("ЭлементыМоделиЗапроса.НовыйПриведениеТипа(", type_cast)
        self.assertIn("НеТерминалВыражение()", type_cast)
        self.assertIn("ЭтотУзел.Выражение =", type_cast)
        self.assertIn("НеТерминалОписаниеТипа()", type_cast)
        self.assertIn("ЭтотУзел.ОписаниеТипа =", type_cast)

        description = _generated_function(module, "ОписаниеТипа")
        self.assertIn("НеТерминалТипСсылочногоПоля()", description)
        self.assertEqual(
            description.count("ЭлементыМоделиЗапроса.НовыйОписаниеТипа"),
            4,
        )
        self.assertEqual(description.count("ЭтотУзел.Длина ="), 2)
        self.assertEqual(description.count("ЭтотУзел.Точность ="), 1)
        for function in (type_cast, description):
            self.assertNotIn("ТекущийЭлемент", function)
            self.assertNotIn("НомерВариантаПродукции", function)

    def test_query_package_generates_collection_loop_and_optional_terminator(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        self.assertNotIn(
            "Функция НеТерминалПродолжениеПакетаЗапросов(",
            module,
        )
        function = _generated_function(module, "ПакетЗапросов")
        self.assertEqual(function.count("Пока "), 1)
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйПакетЗапросов("),
            1,
        )
        self.assertEqual(function.count("НеТерминалЗапросПакета()"), 2)
        self.assertEqual(function.count("ЭтотУзел.Элементы.Добавить("), 2)
        self.assertEqual(function.count('Лексема(";")'), 2)
        self.assertNotIn("НомерВариантаПродукции", function)
        self.assertNotIn("ТекущийЭлемент", function)

    def test_destroy_query_generates_canonical_table_name_binding(self) -> None:
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

        function = _generated_function(generated.module_text, "ЗапросУничтожения")
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйЗапросУничтожения("),
            1,
        )
        self.assertIn('Терминал("УНИЧТОЖИТЬ");', function)
        self.assertIn('Значение1 = Идентификатор("ID_ИмяТаблицы");', function)
        self.assertIn("ЭтотУзел.ИмяТаблицы = Значение1;", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_repository_grammar_parses_and_resolves_without_diagnostics(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        self.assertEqual(parsed.diagnostics, ())
        assert parsed.source_grammar is not None
        assert parsed.grammar is not None
        self.assertEqual(len(parsed.source_grammar.productions), 90)
        self.assertEqual(len(parsed.grammar.productions), 136)
        self.assertNotIn(
            "КакОпционально",
            {item.name for item in parsed.source_grammar.productions},
        )
        self.assertNotIn(
            "ВыражениеСКДПараметр",
            {item.name for item in parsed.source_grammar.productions},
        )

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

        productions = {
            production.name: production
            for production in parser_ir.productions
        }
        for name in ("Выражение", "ЛогическоеСлагаемое"):
            with self.subTest(ir=name):
                production = productions[name]
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

    def test_choice_alternative_generates_canonical_scalar_bindings(self) -> None:
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

        function = _generated_function(generated.module_text, "КогдаТогда")
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйАльтернативаВыбора("),
            1,
        )
        self.assertEqual(function.count("ЭтотУзел.Условие ="), 1)
        self.assertEqual(function.count("ЭтотУзел.Действие ="), 1)
        self.assertIn('Терминал("КОГДА");', function)
        self.assertIn('Терминал("ТОГДА");', function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotRegex(
            function,
            r'Значение\d+ = Терминал\("(?:КОГДА|ТОГДА)"\);',
        )
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_aggregate_functions_generate_name_and_argument_bindings(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        function = _generated_function(
            generated.module_text,
            "АгрегатнаяФункция",
        )
        for token in ("СУММА", "МАКСИМУМ", "МИНИМУМ", "СРЕДНЕЕ"):
            with self.subTest(token=token):
                self.assertEqual(function.count(f'Терминал("{token}")'), 1)
        self.assertEqual(
            function.count(
                "ЭлементыМоделиЗапроса.НовыйАгрегатнаяФункция("
            ),
            4,
        )
        self.assertEqual(function.count("ЭтотУзел.ИмяФункции ="), 4)
        self.assertEqual(function.count("ЭтотУзел.Аргумент ="), 5)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_count_aggregate_preserves_default_and_argument_choice(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        self.assertNotIn("Функция НеТерминалАргументКоличество(", module)
        function = _generated_function(module, "АгрегатнаяФункция")
        self.assertEqual(
            function.count(
                "ЭлементыМоделиЗапроса.НовыйАгрегатнаяФункцияКоличество("
            ),
            1,
        )
        self.assertEqual(function.count('Терминал("РАЗЛИЧНЫЕ");'), 1)
        self.assertEqual(function.count("ЭтотУзел.Различные = Истина;"), 1)
        self.assertNotIn("ЭтотУзел.Различные = Неопределено;", function)
        self.assertEqual(function.count('Лексема("*")'), 1)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_functions_generate_declarative_scalar_and_collection_bindings(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        for helper in (
            "СписокАргументовДатаВремя",
            "ПродолжениеАргументовДатаВремя",
            "ОпциональноеПродолжениеАргументаЗначение",
        ):
            with self.subTest(helper=helper):
                self.assertNotIn(f"Функция НеТерминал{helper}(", module)
        function = _generated_function(module, "Функция")
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйФункция"),
            22,
        )
        self.assertEqual(function.count("ЭтотУзел.Аргументы.Добавить("), 2)
        self.assertEqual(function.count("ЭтотУзел.ЧастиПути.Добавить("), 3)
        self.assertEqual(function.count("ЭтотУзел.ТипПериода ="), 4)
        self.assertEqual(function.count("Пока "), 1)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_query_parameter_generates_canonical_identifier_binding(self) -> None:
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

        function = _generated_function(generated.module_text, "Параметр")
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйПараметрЗапроса("),
            1,
        )
        self.assertIn('Лексема("&");', function)
        self.assertIn('Значение1 = Идентификатор("ID_Полный");', function)
        self.assertEqual(function.count("ЭтотУзел.Имя = Значение1;"), 1)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_constants_generate_canonical_value_bindings(self) -> None:
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

        function = _generated_function(generated.module_text, "Константа")
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйКонстанта("),
            6,
        )
        self.assertEqual(function.count("ЭтотУзел.Значение ="), 6)
        self.assertRegex(
            function,
            r'ЭтотУзел\.Значение = Значение\d+;',
        )
        for keyword, value in (
            ("ИСТИНА", "Истина"),
            ("ЛОЖЬ", "Ложь"),
            ("NULL", "Null"),
            ("НЕОПРЕДЕЛЕНО", "Неопределено"),
        ):
            with self.subTest(keyword=keyword):
                self.assertIn(f'Терминал("{keyword}");', function)
                self.assertIn(f"ЭтотУзел.Значение = {value};", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_reference_type_generates_two_identifier_bindings(self) -> None:
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

        function = _generated_function(generated.module_text, "ТипСсылочногоПоля")
        self.assertEqual(
            function.count("ЭлементыМоделиЗапроса.НовыйТипСсылочногоПоля("),
            1,
        )
        self.assertIn(
            'Значение1 = Идентификатор("ID_ГруппаТипаСсылки");',
            function,
        )
        self.assertIn("ЭтотУзел.Группа = Значение1;", function)
        self.assertIn('Лексема(".");', function)
        self.assertIn('Значение2 = Идентификатор("ID_ИмяТипа");', function)
        self.assertIn("ЭтотУзел.Таблица = Значение2;", function)
        self.assertNotIn("ТекущийЭлемент", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_field_dereference_package_generates_loops_and_bindings(
        self,
    ) -> None:
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
            "Функция НеТерминалОперацияРазыменования(",
            module,
        )

        field = _generated_function(module, "Поле")
        self.assertEqual(
            field.count("ЭлементыМоделиЗапроса.НовыйРазыменование("),
            1,
        )
        self.assertEqual(field.count("Пока "), 1)
        self.assertIn("ЭтотУзел.Элементы.Добавить(", field)
        self.assertNotIn("ТекущийЭлемент", field)
        self.assertNotIn("НомерВариантаПродукции", field)

        all_fields = _generated_function(
            module,
            "ВыражениеВсеПоляИсточника",
        )
        self.assertEqual(
            all_fields.count(
                "ЭлементыМоделиЗапроса.НовыйВыражениеВсеПоляИсточника("
            ),
            1,
        )
        self.assertIn('Лексема("*");', all_fields)
        self.assertNotIn("ТекущийЭлемент", all_fields)

        nested_fields = _generated_function(module, "ПоляВложеннойТаблицы")
        self.assertEqual(
            nested_fields.count(
                "ЭлементыМоделиЗапроса.НовыйПоляВложеннойТаблицы("
            ),
            1,
        )
        self.assertIn("ЭтотУзел.Элементы =", nested_fields)
        self.assertNotIn("ТекущийЭлемент", nested_fields)

        model_expression = _generated_function(
            module,
            "ВыражениеМоделиЗапроса",
        )
        self.assertEqual(
            model_expression.count(
                "ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса("
            ),
            1,
        )
        self.assertIn("ЭтотУзел.Значение =", model_expression)
        self.assertNotIn("ТекущийЭлемент", model_expression)

    def test_source_data_package_generates_dispatch_and_bindings(
        self,
    ) -> None:
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
        self.assertNotIn("Функция НеТерминалКакОпционально(", module)
        self.assertNotIn(
            "Функция НеТерминалВыражениеСКДПараметр(",
            module,
        )
        for removed in (
            "ПсевдонимОпционально",
            "РазыменованиеТаблицы",
            "ПродолжениеРазыменованияТаблицы",
            "ПараметрыТаблицыОпционально",
            "ПродолжениеСпискаПараметров",
        ):
            with self.subTest(removed=removed):
                self.assertNotIn(f"Функция НеТерминал{removed}(", module)
        source_data = _generated_function(module, "ИсточникДанных")
        for child in (
            "ИсточникДанныхТаблицаЗначений",
            "ИсточникДанныхТаблица",
            "ИсточникДанныхВложенныйЗапрос",
            "ИсточникДанныхВременнаяТаблица",
        ):
            with self.subTest(production="ИсточникДанных", child=child):
                self.assertIn(f"НеТерминал{child}()", source_data)
        self.assertNotIn("ТекущийЭлемент", source_data)
        self.assertNotIn("НомерВариантаПродукции", source_data)

        joinable = _generated_function(module, "ПрисоединяемаяТаблица")
        for child in (
            "ИсточникДанныхТаблица",
            "ИсточникДанныхВложенныйЗапрос",
            "ИсточникДанныхВременнаяТаблица",
        ):
            with self.subTest(
                production="ПрисоединяемаяТаблица",
                child=child,
            ):
                self.assertIn(f"НеТерминал{child}()", joinable)
        self.assertNotIn("ТекущийЭлемент", joinable)
        self.assertNotIn("НомерВариантаПродукции", joinable)

        temporary = _generated_function(
            module,
            "ИсточникДанныхВременнаяТаблица",
        )
        self.assertEqual(
            temporary.count(
                "ЭлементыМоделиЗапроса.НовыйИсточникДанныхВременнаяТаблица("
            ),
            1,
        )
        self.assertIn("ЭтотУзел.ИмяТаблицы =", temporary)
        self.assertIn("ЭтотУзел.Псевдоним =", temporary)
        self.assertNotIn("НеТерминалПсевдонимОпционально", temporary)
        self.assertNotIn("ТекущийЭлемент", temporary)

        nested = _generated_function(
            module,
            "ИсточникДанныхВложенныйЗапрос",
        )
        self.assertEqual(
            nested.count(
                "ЭлементыМоделиЗапроса.НовыйИсточникДанныхВложенныйЗапрос("
            ),
            1,
        )
        self.assertIn("ЭтотУзел.ЗапросВыбора =", nested)
        self.assertIn("ЭтотУзел.Псевдоним =", nested)
        self.assertNotIn("ТекущийЭлемент", nested)

        value_table = _generated_function(
            module,
            "ИсточникДанныхТаблицаЗначений",
        )
        self.assertEqual(
            value_table.count(
                "ЭлементыМоделиЗапроса."
                "НовыйИсточникДанныхТаблицаЗначений("
            ),
            1,
        )
        self.assertIn('Идентификатор("ID_Полный")', value_table)
        self.assertIn("ЭтотУзел.ИмяТаблицы =", value_table)
        self.assertIn("ЭтотУзел.Псевдоним =", value_table)
        self.assertNotIn("НеТерминалПараметр", value_table)
        self.assertNotIn("ТекущийЭлемент", value_table)
        self.assertNotIn("НомерВариантаПродукции", value_table)

        table = _generated_function(
            module,
            "ИсточникДанныхТаблица",
        )
        self.assertEqual(
            table.count(
                "ЭлементыМоделиЗапроса."
                "НовыйИсточникДанныхТаблица("
            ),
            1,
        )
        self.assertEqual(table.count("Пока "), 1)
        self.assertEqual(
            table.count(
                "ЭтотУзел.ИмяТаблицы = "
                "ЭтотУзел.ИмяТаблицы +"
            ),
            5,
        )
        self.assertIn("НеТерминалСписокПараметров()", table)
        self.assertIn("ЭтотУзел.Параметры =", table)
        self.assertIn("НеТерминалПсевдоним()", table)
        self.assertIn("ЭтотУзел.Псевдоним =", table)
        self.assertNotIn("ТекущийЭлемент", table)
        self.assertNotIn("НомерВариантаПродукции", table)

        parameters = _generated_function(module, "СписокПараметров")
        self.assertEqual(
            parameters.count(
                "ЭлементыМоделиЗапроса.НовыйСписокПараметров("
            ),
            1,
        )
        self.assertEqual(parameters.count("ЭтотУзел.Добавить("), 2)
        self.assertEqual(parameters.count("Пока "), 1)
        self.assertNotIn("ТекущийЭлемент", parameters)
        self.assertNotIn("НомерВариантаПродукции", parameters)

        parameter = _generated_function(module, "ПараметрТаблицы")
        self.assertIn("РезультатПродукции = Неопределено;", parameter)
        self.assertNotIn("ТекущийЭлемент", parameter)
        self.assertNotIn("НомерВариантаПродукции", parameter)

    def test_logical_leaf_package_generates_values_without_actions(
        self,
    ) -> None:
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
        in_operand = _generated_function(module, "ОперандВ")
        self.assertIn("НеТерминалСписокВыражений()", in_operand)
        self.assertIn("НеТерминалЗапросВыбора()", in_operand)
        self.assertNotIn("ТекущийЭлемент", in_operand)
        self.assertNotIn("НомерВариантаПродукции", in_operand)

        comparison = _generated_function(module, "ОператорСравнения")
        for operator in ("=", "<>", ">", "<", ">=", "<="):
            with self.subTest(operator=operator):
                self.assertIn(f'Лексема("{operator}")', comparison)
        self.assertNotIn("ТекущийЭлемент", comparison)
        self.assertNotIn("НомерВариантаПродукции", comparison)

        pattern = _generated_function(module, "ШаблонПодобия")
        self.assertEqual(
            pattern.count("ЭлементыМоделиЗапроса.НовыйКонстанта("),
            1,
        )
        self.assertIn("ЭтотУзел.Значение =", pattern)
        self.assertIn("НеТерминалПараметр()", pattern)
        self.assertNotIn("ТекущийЭлемент", pattern)
        self.assertNotIn("НомерВариантаПродукции", pattern)

        negation = _generated_function(module, "Отрицание")
        self.assertEqual(
            negation.count(
                "ЭлементыМоделиЗапроса.НовыйЛогическоеОтрицание("
            ),
            1,
        )
        self.assertEqual(negation.count("Пока "), 1)
        self.assertIn(
            "ЭтотУзел.Количество = ЭтотУзел.Количество + 1;",
            negation,
        )
        self.assertNotIn("ТекущийЭлемент", negation)
        self.assertNotIn("НомерВариантаПродукции", negation)
        self.assertNotIn(
            "Функция НеТерминалОтрицаниеПродолжение(",
            module,
        )

    def test_root_collection_lists_generate_loops_without_continuations(
        self,
    ) -> None:
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
        selected = {
            *MIGRATED_PRODUCTIONS,
            "СписокЭлементовУпорядочивания",
            "КонтрольныеТочкиИтогов",
        }
        canonical = tuple(
            production.name
            for production in parsed.source_grammar.productions
            if production.name in selected
        )
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        for helper in (
            "ПродолжениеСпискаЭлементовУпорядочивания",
            "СписокКонтрольныхТочекОпциональное",
        ):
            with self.subTest(helper=helper):
                self.assertNotIn(f"Функция НеТерминал{helper}(", module)

        cases = (
            (
                "СписокЭлементовУпорядочивания",
                "НовыйЭлементыПорядка",
            ),
            (
                "КонтрольныеТочкиИтогов",
                "НовыйКонтрольныеТочкиИтогов",
            ),
        )
        for production, constructor in cases:
            with self.subTest(production=production):
                function = _generated_function(module, production)
                self.assertEqual(
                    function.count(
                        f"ЭлементыМоделиЗапроса.{constructor}("
                    ),
                    1,
                )
                self.assertEqual(function.count("Пока "), 1)
                self.assertEqual(function.count("ЭтотУзел.Добавить("), 2)
                self.assertNotIn("ТекущийЭлемент", function)
                self.assertNotIn("НомерВариантаПродукции", function)

    def test_select_field_package_generates_semantic_wrappers_and_bindings(
        self,
    ) -> None:
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
        canonical = MIGRATED_PRODUCTIONS
        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolution.grammar,
            analysis,
            production_names=canonical,
        )
        generated = generate_hybrid_parser(
            parsed.source_grammar,
            parsed.lowering,
            parsed.grammar,
            resolution.grammar,
            analysis,
            parser_ir,
            canonical_productions=canonical,
            entrypoints={"Разобрать": "ПакетЗапросов"},
        )

        module = generated.module_text
        select_field = _generated_function(module, "ПолеВыборки")
        self.assertEqual(
            select_field.count(
                "ЭлементыМоделиЗапроса.НовыйПолеЗапроса("
            ),
            2,
        )
        self.assertIn("ЭтотУзел.Выражение =", select_field)
        self.assertIn("ЭтотУзел.Псевдоним =", select_field)
        self.assertNotIn("НеТерминалПсевдонимОпционально", select_field)
        self.assertNotIn("ТекущийЭлемент", select_field)
        self.assertNotIn("НомерВариантаПродукции", select_field)

        all_fields_model = _generated_function(
            module,
            "ВыражениеВсеПоляВыборки",
        )
        self.assertEqual(
            all_fields_model.count(
                "ЭлементыМоделиЗапроса.НовыйВыражениеМоделиЗапроса("
            ),
            1,
        )
        self.assertIn("ЭтотУзел.Значение =", all_fields_model)
        self.assertNotIn("ТекущийЭлемент", all_fields_model)

        all_fields = _generated_function(module, "ВыражениеВсеПоля")
        self.assertEqual(
            all_fields.count(
                "ЭлементыМоделиЗапроса.НовыйВыражениеВсеПоля("
            ),
            1,
        )
        self.assertIn('Лексема("*");', all_fields)
        self.assertNotIn("ТекущийЭлемент", all_fields)

    def test_totals_control_point_package_generates_nested_optionals_and_bindings(
        self,
    ) -> None:
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
            "ПродолжениеКонтрольнойТочкиИтогов",
            "ДополнениеПериодамиИтогов",
            "ПсевдонимКонтрольнойТочкиИтогов",
            "ПериодДополненияИтогов",
            "ОкончаниеПериодаИтогов",
            "ПериодИтогов",
        ):
            with self.subTest(helper=helper):
                self.assertNotIn(f"Функция НеТерминал{helper}(", module)

        control_point = _generated_function(module, "КонтрольнаяТочкаИтогов")
        self.assertEqual(
            control_point.count(
                "ЭлементыМоделиЗапроса.НовыйКонтрольнаяТочкаИтогов("
            ),
            1,
        )
        self.assertEqual(
            control_point.count("ЭлементыМоделиЗапроса.НовыйОбщиеИтоги("),
            3,
        )
        for property_name in (
            "Выражение",
            "ТипКонтрольнойТочки",
            "ТипДополненияПериодами",
            "НачалоПериодаДополнения",
            "КонецПериодаДополнения",
            "ИмяКолонки",
        ):
            with self.subTest(property_name=property_name):
                self.assertIn(f"ЭтотУзел.{property_name} =", control_point)
        self.assertNotIn("ТекущийЭлемент", control_point)
        self.assertNotIn("НомерВариантаПродукции", control_point)
        self.assertNotIn("НеТерминалПсевдоним()", control_point)

        period_type = _generated_function(module, "ТипПериодаИтогов")
        for period in (
            "СЕКУНДА",
            "МИНУТА",
            "ЧАС",
            "ДЕНЬ",
            "НЕДЕЛЯ",
            "МЕСЯЦ",
            "ГОД",
            "ДЕКАДА",
            "ПОЛУГОДИЕ",
        ):
            with self.subTest(period=period):
                self.assertIn(f'Терминал("{period}")', period_type)
        self.assertNotIn("ТекущийЭлемент", period_type)
        self.assertNotIn("НомерВариантаПродукции", period_type)


if __name__ == "__main__":
    unittest.main()
