import unittest

from parsergen.analysis import compute_analysis
from parsergen.canonical_bsl_codegen import generate_canonical_parser
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import build_parser_ir
from parsergen.resolver import resolve_grammar


def _build(
    source: str,
    k: int = 1,
    entrypoints: dict[str, str] | None = None,
    named_predicates: dict[tuple[str, ...], str] | None = None,
):
    entries = entrypoints or {"Разобрать": "S"}
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.source_grammar is not None
    assert parsed.grammar is not None
    assert parsed.lowering is not None
    resolution = resolve_grammar(parsed.grammar)
    assert resolution.diagnostics == ()
    assert resolution.grammar is not None
    analysis = compute_analysis(
        resolution.grammar,
        k,
        tuple(entries.values()),
    )
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolution.grammar,
        analysis,
    )
    return generate_canonical_parser(
        parsed.source_grammar,
        parser_ir,
        entries,
        named_predicates=named_predicates,
    )


def _function(module: str, name: str) -> str:
    return module.split(f"Функция {name}", 1)[1].split(
        "КонецФункции",
        1,
    )[0]


class CanonicalBslCodegenTests(unittest.TestCase):
    def test_named_token_set_helper_uses_cached_token_only(self) -> None:
        generated = _build(
            "#ID_Large ::= A | B | C | D | E | F | G | H | I\n"
            "<S> ::= #ID_Large | END",
            named_predicates={tuple("ABCDEFGHI"): "ID_Large"},
        )

        helper = _function(
            generated.module_text,
            "ТокенПринадлежитКлассу(ТипТокена, ИмяКласса)",
        )
        self.assertIn(
            "ОпределенияИдентификаторов.НайтиСтроки",
            helper,
        )
        self.assertNotIn("ТипТокенаПросмотра", helper)

    def test_optional_collection_decorator_appends_seed_and_returns_wrapper(
        self,
    ) -> None:
        generated = _build(
            "<S> ::= ('(' <Base> ')') Элементы +=> <Postfix>?\n"
            "<Base> ::= @НовыйБаза BASE\n"
            "<Postfix> ::= @НовыйPostfix POSTFIX"
        )

        function = _function(generated.module_text, "НеТерминалS")
        self.assertIn(".Элементы.Вставить(0, ", function)
        self.assertNotIn(".Элементы = ", function)
        self.assertIn("РезультатПродукции = Значение", function)

    def test_optional_returned_child_decorator_wraps_and_returns_seed(self) -> None:
        generated = _build(
            "<S> ::= <Base> Операнд => <Postfix>?\n"
            "<Base> ::= @НовыйБаза BASE\n"
            "<Postfix> ::= @НовыйPostfix POSTFIX"
        )

        function = _function(generated.module_text, "НеТерминалS")
        self.assertEqual(function.count("НеТерминалBase()"), 1)
        self.assertNotIn("НеТерминалPostfix()", function)
        self.assertEqual(function.count("НовыйPostfix"), 1)
        self.assertEqual(function.count(".Операнд = "), 1)
        self.assertIn('POSTFIX', function)
        self.assertIn("РезультатПродукции = Значение", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_required_returned_child_decorator_wraps_and_returns_child(
        self,
    ) -> None:
        generated = _build(
            "<S> ::= <Seed> Тип => <Child>\n"
            "<Seed> ::= @НовыйТип TYPE\n"
            "<Child> ::= @НовыйУзел CHILD"
        )

        function = _function(generated.module_text, "НеТерминалS")
        self.assertEqual(function.count("НеТерминалSeed()"), 1)
        self.assertEqual(function.count("НеТерминалChild()"), 1)
        self.assertIn(".Тип = ", function)
        self.assertIn("РезультатПродукции = Значение", function)
        self.assertNotIn("НомерВариантаПродукции", function)

    def test_generates_canonical_runtime_without_legacy_matcher(self) -> None:
        generated = _build("<S> ::= ITEM", k=3)

        self.assertIn("Функция Разобрать(Текст) Экспорт", generated.module_text)
        self.assertIn("Функция ТипТокенаПросмотра(Смещение)", generated.module_text)
        self.assertIn("КоличествоПросматриваемыхСимволов = 3;", generated.module_text)
        self.assertNotIn(
            "ТаблицаПервыхСимволовВариантов",
            generated.module_text,
        )
        self.assertNotIn("НомерВариантаПродукции", generated.module_text)

    def test_canonical_syntax_errors_preserve_token_type_and_coordinates(
        self,
    ) -> None:
        module = _build("<S> ::= ITEM").module_text

        self.assertIn(
            '"{(%1, %2)}: Синтаксическая ошибка. '
            'Неожиданный токен ""%3"""',
            module,
        )
        self.assertIn("ТекущийТокен.НомерСтроки", module)
        self.assertIn("ТекущийТокен.НомерСимвола", module)
        self.assertIn("ТекущийТокен.Тип", module)
        self.assertNotIn(
            '"Синтаксическая ошибка. Неожиданный токен " '
            "+ ТекущийТокен.Лексема",
            module,
        )

    def test_preserves_entrypoint_and_identifier_definition_order(self) -> None:
        generated = _build(
            "#ID_Name ::= ID | WORD\n"
            "<S> ::= #ID_Name\n<Expression> ::= &NUMBER",
            entrypoints={
                "Разобрать": "S",
                "РазобратьВыражение": "Expression",
            },
        )

        module = generated.module_text
        self.assertLess(
            module.index("Функция Разобрать(Текст)"),
            module.index("Функция РазобратьВыражение(Текст)"),
        )
        self.assertEqual(
            generated.identifier_table.rows,
            (("ID_Name", "ID"), ("ID_Name", "WORD")),
        )
        self.assertEqual(generated.constructor_names, ())

    def test_renders_symbol_calls_and_only_declared_nonterminal_arguments(
        self,
    ) -> None:
        generated = _build(
            "#ID_Name ::= ID\n"
            "<S>(Context) ::= WORD | 'exact' | &NUMBER | "
            "#ID_Name | <A>(Context)\n"
            "<A>(Context) ::= tail"
        )

        function = _function(generated.module_text, "НеТерминалS")
        self.assertIn("Context = Неопределено", function)
        self.assertIn('Терминал("WORD")', function)
        self.assertIn('Лексема("exact")', function)
        self.assertIn('Константа("NUMBER")', function)
        self.assertIn('Идентификатор("ID_Name")', function)
        self.assertIn("НеТерминалA(Context)", function)
        self.assertNotIn("Родитель", function)
        self.assertNotIn("ЛевыйЭлемент", function)

    def test_multi_alternative_dispatch_has_canonical_error_fallback(self) -> None:
        generated = _build("<S> ::= a | b")

        function = _function(generated.module_text, "НеТерминалS")
        self.assertIn(
            'Если ТокенРешения0 = "a" Тогда',
            function,
        )
        self.assertIn(
            'ИначеЕсли ТокенРешения0 = "b" Тогда',
            function,
        )
        self.assertIn("Иначе", function)
        self.assertIn(
            'ВызватьИсключениеСинтаксическаяОшибкаОжидаемыеТокены('
            '"""a"", ""b""");',
            function,
        )

    def test_unique_first_token_commits_before_invalid_second_token(self) -> None:
        generated = _build("<S> ::= A X | B Y", k=2)

        function = _function(generated.module_text, "НеТерминалS")
        self.assertIn(
            'ТокенРешения0 = "A"',
            function,
        )
        self.assertNotIn(
            'ТипТокенаПросмотра(1) = "X"',
            function,
        )
        self.assertNotIn(
            'ТипТокенаПросмотра(1) = "Y"',
            function,
        )

    def test_shared_prefix_is_rendered_as_one_decision_region(self) -> None:
        function = _function(
            _build("<S> ::= A X | A Y | B Z", k=2).module_text,
            "НеТерминалS",
        )

        self.assertEqual(function.count("ТипТокенаПросмотра(0)"), 1)
        self.assertEqual(function.count("ТипТокенаПросмотра(1)"), 1)
        self.assertIn('ТокенРешения0 = "A"', function)

    def test_returns_explicit_transparent_or_syntax_only_result(self) -> None:
        transparent = _build(
            "#ID_Name ::= ID\n<S> ::= #ID_Name"
        ).module_text
        syntax_only = _build("<S> ::= ITEM").module_text

        transparent_function = _function(transparent, "НеТерминалS")
        self.assertIn(
            'Значение1 = Идентификатор("ID_Name");',
            transparent_function,
        )
        self.assertIn("РезультатПродукции = Значение1;", transparent_function)
        syntax_function = _function(syntax_only, "НеТерминалS")
        self.assertIn("РезультатПродукции = Неопределено;", syntax_function)

    def test_rejects_source_and_parser_ir_mismatch(self) -> None:
        first = parse_grammar("<S> ::= a", "first.grammar")
        second = parse_grammar("<S> ::= b", "second.grammar")
        assert first.source_grammar is not None
        assert second.source_grammar is not None
        assert second.grammar is not None
        assert second.lowering is not None
        resolved = resolve_grammar(second.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))
        parser_ir = build_parser_ir(
            second.source_grammar,
            second.lowering,
            resolved.grammar,
            analysis,
        )

        with self.assertRaisesRegex(ValueError, "does not match Parser IR"):
            generate_canonical_parser(
                first.source_grammar,
                parser_ir,
                {"Разобрать": "S"},
            )


if __name__ == "__main__":
    unittest.main()
