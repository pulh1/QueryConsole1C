from collections.abc import Iterator, Mapping
from dataclasses import replace
import re
import unittest
from unittest import mock

from parsergen.analysis import LookaheadMaterializationError, compute_analysis
from parsergen.bsl_codegen import (
    BslGenerator,
    _substitute_markers,
    generate_parser,
)
from parsergen.grammar_parser import parse_grammar
from parsergen.resolver import resolve_grammar
from parsergen.value_table_codec import ColumnKind
from tests.helpers import compiled


class _ForbiddenSelect(Mapping[tuple[str, int], object]):
    def __getitem__(self, key: tuple[str, int]) -> object:
        raise AssertionError(f"concrete SELECT accessed for {key!r}")

    def __iter__(self) -> Iterator[tuple[str, int]]:
        raise AssertionError("concrete SELECT iterated")

    def __len__(self) -> int:
        raise AssertionError("concrete SELECT sized")


class BslCodegenTests(unittest.TestCase):
    def test_generates_parameters_actions_and_configured_lookahead(self) -> None:
        entrypoints = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "#ID_Name ::= ID | ГДЕ\n"
            "<S>(Owner) ::= {ЭтотУзел = НовыйRoot} "
            "<A>(Owner) {ЭтотУзел.Value = ТекущийЭлемент}\n"
            "<A>(Owner) ::= #ID_Name | ПУСТО",
            k=3,
            entrypoints=entrypoints,
        )

        generated = generate_parser(
            grammar,
            resolved,
            analysis,
            entrypoints,
        )

        self.assertIn("Функция Разобрать(Текст) Экспорт", generated.module_text)
        self.assertIn(
            "Функция НеТерминалS("
            "Родитель = Неопределено, "
            "ЛевыйЭлемент = Неопределено, "
            "Owner = Неопределено)",
            generated.module_text,
        )
        self.assertIn(
            "НеТерминалA(ЭтотУзел, ТекущийЭлемент, Owner)",
            generated.module_text,
        )
        self.assertIn(
            "ЭлементыМоделиЗапроса.НовыйRoot(ТекущийТокен)",
            generated.module_text,
        )
        self.assertIn(
            'Если ТекущийЭлемент <> "ПУСТО" Тогда\r\n'
            "\t\tЭтотУзел.Value = ТекущийЭлемент;",
            generated.module_text,
        )
        self.assertIn(
            "КоличествоПросматриваемыхСимволов = 3;",
            generated.module_text,
        )
        self.assertEqual(generated.constructor_names, ("НовыйRoot",))

    def test_emits_each_symbol_helper_call(self) -> None:
        entrypoints = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "#ID_Name ::= ID | ГДЕ\n"
            "<S> ::= WORD 'точно' &NUMBER #ID_Name <A>(Owner)\n"
            "<A>(Owner) ::= tail",
            k=2,
            entrypoints=entrypoints,
        )

        module = generate_parser(
            grammar,
            resolved,
            analysis,
            entrypoints,
        ).module_text

        self.assertIn('ТекущийЭлемент = Терминал("WORD");', module)
        self.assertIn('ТекущийЭлемент = Лексема("точно");', module)
        self.assertIn('ТекущийЭлемент = Константа("NUMBER");', module)
        self.assertIn('ТекущийЭлемент = Идентификатор("ID_Name");', module)
        self.assertIn(
            "ТекущийЭлемент = НеТерминалA("
            "ЭтотУзел, ТекущийЭлемент, Owner);",
            module,
        )

    def test_dispatches_multiple_alternatives_and_falls_through_epsilon(self) -> None:
        required_entries = {"Разобрать": "Required"}
        grammar, resolved, analysis = compiled(
            "<Required> ::= a | b",
            1,
            required_entries,
        )
        required = generate_parser(
            grammar,
            resolved,
            analysis,
            required_entries,
        ).module_text

        self.assertIn(
            'НомерВариантаПродукции = '
            'НомерВариантаПродукции("Required");',
            required,
        )
        self.assertIn("Если НомерВариантаПродукции = 1 Тогда", required)
        self.assertIn("ИначеЕсли НомерВариантаПродукции = 2 Тогда", required)
        self.assertIn(
            'ВызватьИсключениеНеУдалосьВыпполнитьРазбор("Required");',
            required,
        )
        self.assertIn('ПоследняяПродукция = "Required";', required)

        optional_entries = {"Разобрать": "Optional"}
        grammar, resolved, analysis = compiled(
            "<Optional> ::= a | ПУСТО",
            1,
            optional_entries,
        )
        optional = generate_parser(
            grammar,
            resolved,
            analysis,
            optional_entries,
        ).module_text
        function = optional.split(
            "Функция НеТерминалOptional", 1
        )[1].split("КонецФункции", 1)[0]

        self.assertIn("Если НомерВариантаПродукции = 1 Тогда", function)
        self.assertNotIn("НомерВариантаПродукции = 2 Тогда", function)
        self.assertNotIn("ВызватьИсключениеНеУдалось", function)

    def test_single_nonempty_alternative_has_no_dispatch(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled("<S> ::= a", 1, entries)

        function = generate_parser(
            grammar,
            resolved,
            analysis,
            entries,
        ).module_text.split("Функция НеТерминалS", 1)[1]

        self.assertNotIn("НомерВариантаПродукции(", function)
        self.assertIn('ТекущийЭлемент = Терминал("a");', function)

    def test_generates_two_entrypoints_in_mapping_order(self) -> None:
        entries = {
            "Разобрать": "S",
            "РазобратьВыражение": "Expression",
        }
        grammar, resolved, analysis = compiled(
            "<S> ::= start\n<Expression>(Context) ::= expr",
            1,
            entries,
        )

        module = generate_parser(
            grammar,
            resolved,
            analysis,
            entries,
        ).module_text

        self.assertLess(
            module.index("Функция Разобрать(Текст) Экспорт"),
            module.index("Функция РазобратьВыражение(Текст) Экспорт"),
        )
        self.assertIn("Функция РезультатРазбора()", module)
        self.assertIn("Функция РезультатРазбораВыражения()", module)
        self.assertIn("Результат = НеТерминалS();", module)
        self.assertIn(
            "Результат = НеТерминалExpression("
            "Неопределено, Неопределено);",
            module,
        )
        self.assertIn(
            (
                "Функция Разобрать(Текст) Экспорт\r\n"
                "\tЛексическийАнализатор."
                "УстановитьОбрабатываемыйТекст(Текст);\t\r\n"
                "\tУстановитьБуферТокенов();\r\n"
                "\t\r\n"
                "\tВозврат РезультатРазбора();\r\n"
                "КонецФункции\t\r\n"
                "\r\n"
                "Функция РазобратьВыражение(Текст) Экспорт\r\n"
                "\tЛексическийАнализатор."
                "УстановитьОбрабатываемыйТекст(Текст);\t\r\n"
                "\tУстановитьБуферТокенов();\r\n"
                "\t\r\n"
                "\tВозврат РезультатРазбораВыражения();\r\n"
                "КонецФункции  "
            ),
            module,
        )

    def test_table_schemas_follow_k_and_identifier_row_conventions(self) -> None:
        for k in (1, 2, 4):
            with self.subTest(k=k):
                entries = {"Разобрать": "S"}
                grammar, resolved, analysis = compiled(
                    "#ID_Name ::= ID | ГДЕ\n<S> ::= #ID_Name",
                    k,
                    entries,
                )
                generated = generate_parser(
                    grammar,
                    resolved,
                    analysis,
                    entries,
                )

                self.assertEqual(
                    tuple(column.name for column in generated.select_table.columns),
                    (
                        "КоличествоЭлементов",
                        *(f"Элемент{index}" for index in range(1, k + 1)),
                        "Продукция",
                        "НомерВарианта",
                    ),
                )
                self.assertEqual(
                    tuple(column.kind for column in generated.select_table.columns),
                    (
                        ColumnKind.NUMBER,
                        *((ColumnKind.STRING,) * k),
                        ColumnKind.STRING,
                        ColumnKind.NUMBER,
                    ),
                )
                self.assertTrue(
                    all(
                        len(row) == k + 3
                        for row in generated.select_table.rows
                    )
                )
                self.assertEqual(
                    tuple(column.name for column in generated.identifier_table.columns),
                    ("Тип", "Идентификатор"),
                )
                self.assertIn(
                    ("ID_Name", "ID"),
                    generated.identifier_table.rows,
                )
                self.assertIn(
                    ("ID_Name", "ГДЕ"),
                    generated.identifier_table.rows,
                )

    def test_epsilon_alternative_uses_zero_length_runtime_fallback(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S> ::= <A>\n<A> ::= a | ПУСТО",
            2,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        self.assertIn((0, None, None, "A", 2), generated.select_table.rows)
        self.assertIn((1, "a", None, "A", 1), generated.select_table.rows)
        self.assertNotIn(
            "$",
            {
                value
                for row in generated.select_table.rows
                for value in row
            },
        )

    def test_complete_and_longer_alternatives_keep_distinct_k2_rows(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S> ::= a | a b",
            2,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        self.assertEqual(
            generated.select_table.rows,
            (
                (1, "a", None, "S", 1),
                (2, "a", "b", "S", 2),
            ),
        )

    def test_reference_rows_prune_concrete_prefixes_after_class_expansion(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "#ID_X ::= a | b\n"
            "<A> ::= a | #ID_X c\n"
            "<S> ::= <A>",
            2,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        self.assertEqual(
            {
                row
                for row in generated.select_table.rows
                if row[-2] == "S"
            },
            {
                (1, "a", None, "S", 1),
                (2, "b", "c", "S", 1),
            },
        )

    def test_nullable_runtime_row_does_not_hide_consuming_descendants(self) -> None:
        entries = {"Разобрать": "A"}
        grammar, resolved, analysis = compiled(
            "<A> ::= <B>\n<B> ::= a | ПУСТО",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        self.assertIn((0, None, "A", 1), generated.select_table.rows)
        self.assertIn((1, "a", "A", 1), generated.select_table.rows)

    def test_reference_rows_keep_prefix_when_recursive_expansion_is_cut(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S> ::= a <A>\n<A> ::= <S> | b",
            2,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        self.assertIn((1, "a", None, "S", 1), generated.select_table.rows)
        self.assertNotIn((2, "a", "a", "S", 1), generated.select_table.rows)
        self.assertNotIn((2, "a", "b", "S", 1), generated.select_table.rows)

    def test_reference_runtime_uses_concrete_select_rows(self) -> None:
        entries = {"Разобрать": "S"}
        tokens = tuple(f"T{index}" for index in range(500))
        grammar, resolved, analysis = compiled(
            f"#ID_Large ::= {' | '.join(tokens)}\n<S> ::= #ID_Large",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        self.assertEqual(
            set(generated.select_table.rows),
            {(1, token, "S", 1) for token in tokens},
        )
        self.assertEqual(
            sum(
                row[0] == "ID_Large"
                for row in generated.identifier_table.rows
            ),
            500,
        )
        self.assertNotIn(
            "СовпадаетСтрокаПервыхСимволов",
            generated.module_text,
        )
        self.assertNotIn(
            'Индексы.Добавить("Продукция, КоличествоЭлементов")',
            generated.module_text,
        )
        self.assertIn(
            'СтруктураПоиска.Вставить("Элемент1", ТекущийТокен.Тип)',
            generated.module_text,
        )
        self.assertEqual(
            analysis._compressed.stats["select_cartesian_materializations"],
            0,
        )

    def test_identifier_table_keeps_equivalent_declared_aliases(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "#ID_A ::= ID | WORD\n"
            "#ID_B ::= ID | WORD\n"
            "<S> ::= #ID_B",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        for pair in (
            ("ID_A", "ID"),
            ("ID_A", "WORD"),
            ("ID_B", "ID"),
            ("ID_B", "WORD"),
        ):
            self.assertIn(pair, generated.identifier_table.rows)
        self.assertIn('Идентификатор("ID_B")', generated.module_text)

    def test_declared_alias_cannot_widen_an_unrelated_terminal_matcher(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "#WORD ::= ID\n<S> ::= WORD | #WORD",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)
        concrete_tokens = {
            row[-1]: row[1]
            for row in generated.select_table.rows
            if row[-2] == "S"
        }

        self.assertEqual(concrete_tokens, {1: "WORD", 2: "ID"})

    def test_generation_is_deterministic_and_emits_one_function_per_production(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S> ::= <A> | b\n<A> ::= a",
            2,
            entries,
        )

        first = generate_parser(grammar, resolved, analysis, entries)
        second = generate_parser(grammar, resolved, analysis, entries)

        self.assertEqual(first, second)
        for name in ("S", "A"):
            self.assertEqual(
                len(
                    re.findall(
                        rf"^Функция НеТерминал{name}\(",
                        first.module_text,
                        re.MULTILINE,
                    )
                ),
                1,
            )

    def test_reference_renderer_keeps_only_first_action_at_each_boundary(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S> ::= {A = 1} {B = 2} a",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        self.assertIn("\tA = 1;\r\n", generated.module_text)
        self.assertNotIn("\tB = 2;\r\n", generated.module_text)

    def test_reference_snapshot_uses_legacy_variant_numbers(self) -> None:
        entries = {"Разобрать": "ПервыеРазличныеОпционально"}
        grammar, resolved, analysis = compiled(
            "<ПервыеРазличныеОпционально> ::= ПЕРВЫЕ\n"
            "<ПервыеРазличныеОпционально> ::= РАЗЛИЧНЫЕ\n"
            "<ПервыеРазличныеОпционально> ::= ПУСТО",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)
        module = generated.module_text

        distinct = module.index('Терминал("РАЗЛИЧНЫЕ")')
        first = module.index('Терминал("ПЕРВЫЕ")')
        self.assertLess(distinct, first)
        self.assertIn(
            "\tЕсли НомерВариантаПродукции = 1 Тогда\r\n",
            module,
        )
        self.assertIn(
            "\tИначеЕсли НомерВариантаПродукции = 3 Тогда\r\n",
            module,
        )
        self.assertIn(
            (1, "РАЗЛИЧНЫЕ", "ПервыеРазличныеОпционально", 1),
            generated.select_table.rows,
        )
        self.assertIn(
            (0, None, "ПервыеРазличныеОпционально", 2),
            generated.select_table.rows,
        )
        self.assertIn(
            (1, "ПЕРВЫЕ", "ПервыеРазличныеОпционально", 3),
            generated.select_table.rows,
        )

    def test_generation_expands_compressed_analysis_without_public_select(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "#ID_X ::= ID | WORD | ГДЕ\n<S> ::= #ID_X #ID_X",
            2,
            entries,
        )
        guarded = replace(analysis, select=_ForbiddenSelect())

        generated = generate_parser(grammar, resolved, guarded, entries)

        self.assertEqual(len(generated.select_table.rows), 9)
        self.assertEqual(
            analysis._compressed.stats["select_cartesian_materializations"],
            0,
        )
        self.assertEqual(
            analysis._compressed.stats["select_packed_product_rows"],
            0,
        )

    def test_identifier_table_preserves_declared_duplicate_rows(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "#ID_X ::= ID | ID\n<S> ::= #ID_X",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)

        self.assertEqual(
            generated.identifier_table.rows,
            (("ID_X", "ID"), ("ID_X", "ID")),
        )

    def test_generation_enforces_an_explicit_matcher_row_limit(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled("<S> ::= a | b", 1, entries)

        with mock.patch("parsergen.bsl_codegen.MAX_MATCHER_ROWS", 1):
            with self.assertRaises(LookaheadMaterializationError):
                generate_parser(grammar, resolved, analysis, entries)

    def test_rejects_reserved_end_token_defensively(self) -> None:
        entries = {"Разобрать": "S"}
        _, resolved, analysis = compiled("<S> ::= a", 1, entries)
        parsed = parse_grammar("<S> ::= '$'")
        assert parsed.grammar is not None

        with self.assertRaisesRegex(ValueError, r"reserved.*\$"):
            generate_parser(
                parsed.grammar,
                resolved,
                analysis,
                entries,
            )

    def test_rejects_empty_invalid_and_colliding_generated_bsl_names(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled("<S> ::= a", 1, entries)
        cases = (
            ({}, "entrypoint"),
            ({"Bad Name": "S"}, "identifier"),
            ({"foo": "S", "FOO": "S"}, "collision"),
            ({"Foo": "S", "РезультатFoo": "S"}, "collision"),
            ({"НомерВариантаПродукции": "S"}, "collision"),
            ({"НеТерминалS": "S"}, "collision"),
        )

        for invalid_entries, message in cases:
            with self.subTest(entries=invalid_entries):
                with self.assertRaisesRegex(ValueError, message):
                    generate_parser(
                        grammar,
                        resolved,
                        analysis,
                        invalid_entries,
                    )

    def test_rejects_bsl_keywords_as_entrypoint_names_case_insensitively(
        self,
    ) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled("<S> ::= a", 1, entries)

        for keyword in ("еСлИ", "FuNcTiOn", "оБлАсТь", "rEgIoN"):
            with self.subTest(keyword=keyword):
                with self.assertRaisesRegex(ValueError, "reserved BSL keyword"):
                    generate_parser(
                        grammar,
                        resolved,
                        analysis,
                        {keyword: "S"},
                    )

    def test_rejects_invalid_or_colliding_production_parameters(self) -> None:
        entries = {"Разобрать": "S"}
        cases = (
            ("<S>(Bad Name) ::= a", "valid BSL identifier"),
            ("<S>(иНаЧе) ::= a", "reserved BSL keyword"),
            ("<S>(eNdIf) ::= a", "reserved BSL keyword"),
            ("<S>(нОвЫй) ::= a", "reserved BSL keyword"),
            ("<S>(ОбЛаСтЬ) ::= a", "reserved BSL keyword"),
            ("<S>(X, x) ::= a", "duplicate"),
            ("<S>(рОдИтЕлЬ) ::= a", "implicit parameter"),
            ("<S>(лЕвЫйЭлЕмЕнТ) ::= a", "implicit parameter"),
            ("<S>(эТоТуЗеЛ) ::= a", "generated local"),
            ("<S>(тЕкУщИйЭлЕмЕнТ) ::= a", "generated local"),
            (
                "<S>(нОмЕрВаРиАнТаПрОдУкЦиИ) ::= a",
                "generated local",
            ),
        )

        for grammar_text, message in cases:
            with self.subTest(grammar=grammar_text):
                grammar, resolved, analysis = compiled(
                    grammar_text,
                    1,
                    entries,
                )
                with self.assertRaisesRegex(ValueError, message):
                    generate_parser(
                        grammar,
                        resolved,
                        analysis,
                        entries,
                    )

    def test_preserves_valid_cyrillic_production_parameters(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S>(Контекст, УзелВладелец) ::= a",
            1,
            entries,
        )

        module = generate_parser(
            grammar,
            resolved,
            analysis,
            entries,
        ).module_text

        self.assertIn(
            "Функция НеТерминалS("
            "Родитель = Неопределено, "
            "ЛевыйЭлемент = Неопределено, "
            "Контекст = Неопределено, "
            "УзелВладелец = Неопределено)",
            module,
        )

    def test_rejects_formals_that_shadow_generated_runtime_state(self) -> None:
        entries = {"Разобрать": "S"}
        cases = (
            (
                "<S>(тЕкУщИйТоКеН) ::= "
                "{ЭтотУзел = НовыйRoot} a",
                "ТекущийТокен",
            ),
            (
                "<S>(эЛеМеНтЫмОдЕлИзАпРоСа) ::= "
                "{ЭтотУзел = НовыйRoot} a",
                "ЭлементыМоделиЗапроса",
            ),
            (
                "<S>(пОсЛеДнЯяПрОдУкЦиЯ) ::= a | b",
                "ПоследняяПродукция",
            ),
        )

        for grammar_text, runtime_name in cases:
            with self.subTest(runtime_name=runtime_name):
                grammar, resolved, analysis = compiled(
                    grammar_text,
                    1,
                    entries,
                )
                with self.assertRaisesRegex(
                    ValueError,
                    rf"generated runtime.*{runtime_name}",
                ):
                    generate_parser(
                        grammar,
                        resolved,
                        analysis,
                        entries,
                    )

    def test_rejects_incoherent_grammar_resolved_and_analysis_inputs(self) -> None:
        entries = {"Разобрать": "S"}
        grammar_a, resolved_a, analysis_a = compiled(
            "<S> ::= a | b",
            1,
            entries,
        )
        grammar_b, resolved_b, analysis_b = compiled(
            "<S> ::= c | d",
            1,
            entries,
        )
        _, equivalent_resolved, _ = compiled(
            "<S> ::= a | b",
            1,
            entries,
        )

        with self.assertRaisesRegex(ValueError, "parsed.*resolved"):
            generate_parser(
                grammar_a,
                resolved_b,
                analysis_b,
                entries,
            )
        with self.assertRaisesRegex(ValueError, "analysis.*resolved"):
            generate_parser(
                grammar_a,
                equivalent_resolved,
                analysis_a,
                entries,
            )

        unseeded = compute_analysis(resolved_a, 1, ())
        with self.assertRaisesRegex(ValueError, "END-seeded"):
            generate_parser(
                grammar_a,
                resolved_a,
                unseeded,
                entries,
            )
        tampered_k = replace(analysis_a, k=2)
        with self.assertRaisesRegex(ValueError, "lookahead"):
            generate_parser(
                grammar_a,
                resolved_a,
                tampered_k,
                entries,
            )

        self.assertIsNot(grammar_a, grammar_b)

    def test_replacing_public_analysis_mapping_preserves_input_binding(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled("<S> ::= a", 1, entries)
        guarded = replace(analysis, select=_ForbiddenSelect())

        generated = generate_parser(
            grammar,
            resolved,
            guarded,
            entries,
        )

        self.assertEqual(generated.select_table.rows, ((1, "a", "S", 1),))

    def test_substitution_requires_every_marker_exactly_once(self) -> None:
        valid = (
            "a\r\n// <parsergen:entrypoints>\r\n"
            "b\r\n// <parsergen:entry-results>\r\n"
            "c\r\n// <parsergen:productions>\r\n"
        )
        rendered = _substitute_markers(valid, "E", "R", "P")
        self.assertEqual(rendered, "a\r\nE\r\nb\r\nR\r\nc\r\nP\r\n")

        for broken in (
            valid.replace("// <parsergen:entrypoints>\r\n", ""),
            valid.replace(
                "// <parsergen:productions>",
                "// <parsergen:productions>\r\n"
                "// <parsergen:productions>",
            ),
        ):
            with self.subTest(broken=broken):
                with self.assertRaisesRegex(ValueError, "exactly once"):
                    _substitute_markers(broken, "E", "R", "P")

    def test_constructor_names_follow_first_use_across_productions(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S> ::= {A = НовыйSecond} <A> {B = НовыйFirst}\n"
            "<A> ::= {C = НовыйFirst} a {D = НовыйThird}",
            1,
            entries,
        )

        generated = BslGenerator(
            grammar,
            resolved,
            analysis,
            entries,
        ).generate()

        self.assertEqual(
            generated.constructor_names,
            ("НовыйSecond", "НовыйFirst", "НовыйThird"),
        )

    def test_actionful_epsilon_alternative_executes_its_exact_branch(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S> ::= a | {ЭтотУзел = НовыйEmpty} ПУСТО",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)
        function = generated.module_text.split(
            "Функция НеТерминалS", 1
        )[1].split("КонецФункции", 1)[0]

        self.assertIn("ИначеЕсли НомерВариантаПродукции = 2 Тогда", function)
        self.assertIn(
            "ЭлементыМоделиЗапроса.НовыйEmpty(ТекущийТокен)",
            function,
        )
        self.assertEqual(generated.constructor_names, ("НовыйEmpty",))

    def test_actionful_epsilon_rejects_tokens_outside_select(self) -> None:
        entries = {"Разобрать": "S"}
        grammar, resolved, analysis = compiled(
            "<S> ::= a | {ЭтотУзел = НовыйEmpty} ПУСТО",
            1,
            entries,
        )

        generated = generate_parser(grammar, resolved, analysis, entries)
        function = generated.module_text.split(
            "Функция НеТерминалS", 1
        )[1].split("КонецФункции", 1)[0]

        self.assertIn(
            "ИначеЕсли НомерВариантаПродукции = 2 Тогда",
            function,
        )
        self.assertIn(
            "ВызватьИсключениеНеУдалосьВыпполнитьРазбор",
            function,
        )


if __name__ == "__main__":
    unittest.main()
