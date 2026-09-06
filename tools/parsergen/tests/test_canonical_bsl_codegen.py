import re
import unittest
from dataclasses import replace

from parsergen.analysis import compute_analysis
from parsergen.canonical_bsl_codegen import generate_canonical_parser
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import Dispatch, ResolvedRegion, build_parser_ir
from parsergen.recursion_plan import analyze_recursion_plan
from parsergen.resolver import resolve_grammar


def _build_ir(
    source: str,
    k: int = 1,
    entrypoints: dict[str, str] | None = None,
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
    return parsed.source_grammar, parser_ir, entries


def _build(
    source: str,
    k: int = 1,
    entrypoints: dict[str, str] | None = None,
    named_predicates: dict[tuple[str, ...], str] | None = None,
):
    source_grammar, parser_ir, entries = _build_ir(source, k, entrypoints)
    return generate_canonical_parser(
        source_grammar,
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
    PATH_FACTS_GRAMMAR = (
        "<S> ::= <Base> Child => <Choice>?\n"
        "<Base> ::= @НовыйBase BASE\n"
        "<Choice> ::= @НовыйBetween (NOT Inverted := Истина)? "
        "BETWEEN <Tail>\n"
        "<Choice> ::= @НовыйIn (NOT Inverted := Истина)? IN <Tail>\n"
        "<Tail> ::= VALUE"
    )

    # Mutation caught: emit a tail/continuation transfer that loses argument
    # evaluation, including its side effects, exceptions and next state.
    def test_recursive_arguments_remain_evaluated_by_normal_bsl_calls(self) -> None:
        for grammar in (
            "<S>(Context) ::= ITEM <S>(Context.Next()) | STOP",
            "<S>(Context) ::= @Link Value = ITEM Rest = <S>(Context.Next()) | @End STOP",
        ):
            with self.subTest(grammar=grammar):
                function = _function(_build(grammar).module_text, "НеТерминалS")

                self.assertEqual(function.count("НеТерминалS(Context.Next())"), 1)
                self.assertNotIn("Пока Истина Цикл", function)

    # Mutation caught: ignore the shared tail_loop plan and retain the
    # recursive nonterminal call in canonical BSL output.
    def test_tail_loop_plan_removes_canonical_bsl_self_call(self) -> None:
        function = _function(
            _build("<S> ::= ITEM <S> | STOP").module_text,
            "НеТерминалS",
        )

        self.assertIn("Пока Истина Цикл", function)
        self.assertIn("КонецЦикла;", function)
        self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: render a local_continuation as a self-call rather than
    # restoring the pending child binding before its constant suffix.
    def test_local_continuation_plan_unwinds_constant_suffix_lifo(self) -> None:
        function = _function(
            _build(
                "<S> ::= @Link Value = ITEM Rest = <S> Kind := Истина | @End STOP"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn("СтекПродолжений = Новый Массив;", function)
        self.assertIn(
            "СтекПродолжений.Получить(СтекПродолжений.Количество() - 1)",
            function,
        )
        self.assertIn("СтекПродолжений.Удалить(СтекПродолжений.Количество() - 1);", function)
        self.assertNotIn("НеТерминалS();", function)
        self.assertLess(
            function.index("СтекПродолжений.Получить"),
            function.rindex("ЭтотУзел.Kind = Истина;"),
        )
        self.assertEqual(function.count("ЭтотУзел.Kind = Истина;"), 1)

    # Mutation caught: reuse a single mutable pending-node variable instead
    # of storing each continuation layout in an independent stack frame.
    def test_local_continuation_plan_stores_an_isolated_layout_frame(self) -> None:
        function = _function(
            _build("<S> ::= @Link Value = ITEM Rest = <S> | @End STOP").module_text,
            "НеТерминалS",
        )

        self.assertIn("Продолжение = Новый Структура;", function)
        self.assertIn('Продолжение.Вставить("Узел", ЭтотУзел);', function)
        self.assertIn('Продолжение.Вставить("Слот1", ЭтотУзел.Value);', function)
        self.assertIn("СтекПродолжений.Добавить(Продолжение);", function)
        self.assertIn("ЭтотУзел = Продолжение.Узел;", function)
        self.assertIn("ЭтотУзел.Value = Продолжение.Слот1;", function)

    # Mutation caught: ignore the wrap_seed slot and reconstruct the wrapper
    # from the recursive result without the already parsed seed.
    def test_local_continuation_restores_wrap_seed_slot(self) -> None:
        function = _function(
            _build(
                "<S> ::= <Leaf> Next => <S> | @End STOP\n"
                "<Leaf> ::= @Leaf ITEM"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn('Продолжение.Вставить("Слот0", Значение1);', function)
        self.assertIn("РезультатПродукции.Next = Продолжение.Слот0;", function)
        self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: ask BSL to save a seed after its wrapper has already
    # completed, or return the discarded recursive child instead of the wrapper.
    def test_completed_prefix_wrap_restores_its_result_after_recursion(self) -> None:
        function = _function(
            _build(
                "<S> ::= <Leaf> Next => <Wrapped> -= <S> | @End STOP\n"
                "<Leaf> ::= @Leaf ITEM\n<Wrapped> ::= @Wrapped WRAP"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn("Значение2.Next = Значение1;", function)
        self.assertIn('Продолжение.Вставить("Слот0", Значение2);', function)
        self.assertIn("РезультатПродукции = Продолжение.Слот0;", function)
        self.assertNotIn('Продолжение.Вставить("Слот1"', function)
        self.assertNotIn("НеТерминалS();", function)
        self.assertLess(function.index("Значение2.Next = Значение1;"),
                        function.index("СтекПродолжений.Добавить"))

    # Mutation caught: fail to snapshot and restore the collection_accumulator
    # slot, allowing nested frames to share a collection receiver.
    def test_local_continuation_restores_collection_accumulator_slot(self) -> None:
        function = _function(
            _build("<S> ::= @List Items += ITEM <S> | @End STOP").module_text,
            "НеТерминалS",
        )

        self.assertIn('Продолжение.Вставить("Слот1", ЭтотУзел.Items);', function)
        self.assertIn("ЭтотУзел.Items = Продолжение.Слот1;", function)
        self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: only lower a top-level local_continuation and leave an
    # exact nested OptionalBranch IrSite as a recursive BSL self-call.
    def test_nested_optional_local_continuation_uses_its_exact_plan_site(self) -> None:
        function = _function(
            _build(
                "<S> ::= @ModuleElements (METHOD Item = ITEM Rest = <S>)?"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn("Пока Истина Цикл", function)
        self.assertIn("СтекПродолжений.Добавить(Продолжение);", function)
        self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: consume only the first nested plan site and leave a
    # second OptionalBranch continuation as a BSL self-call.
    def test_multiple_nested_local_continuations_share_the_structural_dispatch(self) -> None:
        function = _function(
            _build(
                "<S> ::= @Node ("
                "A Item = ITEM Rest = <S> | "
                "B First = ITEM (SEP Rest = <S>)?"
                ")? | @End STOP"
            ).module_text,
            "НеТерминалS",
        )

        self.assertIn("Пока Истина Цикл", function)
        self.assertGreaterEqual(
            function.count("СтекПродолжений.Добавить(Продолжение);"),
            2,
        )
        self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: restore the recursive result instead of the live
    # operation_result slot selected by the shared continuation layout.
    def test_local_continuation_restores_operation_result_slot(self) -> None:
        source, parser_ir, entries = _build_ir(
            "<S> ::= <A> -= <S> | STOP\n<A> ::= ITEM"
        )
        production = parser_ir.productions[0]
        parser_ir = replace(
            parser_ir,
            productions=(
                replace(
                    production,
                    alternatives=(
                        replace(production.alternatives[0], result_index=0),
                        *production.alternatives[1:],
                    ),
                ),
                *parser_ir.productions[1:],
            ),
        )
        function = _function(
            generate_canonical_parser(source, parser_ir, entries).module_text,
            "НеТерминалS",
        )

        self.assertIn('Продолжение.Вставить("Слот0", Значение1);', function)
        self.assertIn("РезультатПродукции = Продолжение.Слот0;", function)
        self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: restrict tail_loop lowering to a top-level ParseSymbol
    # and leave an exact nested/DiscardSymbol planner site recursive.
    def test_tail_loop_plan_consumes_nested_and_discarded_sites(self) -> None:
        for grammar in (
            "<S> ::= (ITEM <S>) | STOP",
            "<S> ::= ITEM -= <S> | STOP",
            "<S> ::= (ITEM <S> | MARK <S>) | STOP",
            "<S> ::= ITEM -= (<S>) | STOP",
            "<S> ::= (ITEM <S>)?",
        ):
            with self.subTest(grammar=grammar):
                source, parser_ir, _ = _build_ir(grammar)
                self.assertTrue(analyze_recursion_plan(source, parser_ir).sites)
                function = _function(_build(grammar).module_text, "НеТерминалS")

                self.assertIn("Пока Истина Цикл", function)
                self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: stop carrying IrSite through an optimized resolved
    # region and leave its planner-issued tail call recursive.
    def test_tail_loop_plan_consumes_resolved_region_site(self) -> None:
        source, parser_ir, entries = _build_ir("<S> ::= (ITEM <S>) | STOP")
        production = parser_ir.productions[0]
        alternative = production.alternatives[0]
        dispatch = alternative.operations[0]
        self.assertIsInstance(dispatch, Dispatch)
        branch = dispatch.branches[0]
        parser_ir = replace(
            parser_ir,
            productions=(replace(
                production,
                alternatives=(replace(
                    alternative,
                    operations=(ResolvedRegion(
                        branch.operations, branch.result_index, dispatch.source_span
                    ),),
                ), *production.alternatives[1:]),
            ),),
        )
        plan = analyze_recursion_plan(source, parser_ir)
        self.assertEqual(len(plan.sites), 1)
        self.assertEqual(plan.sites[0].site.trail,
                         (("operation", 0), ("region", 0), ("operation", 1)))
        function = _function(
            generate_canonical_parser(source, parser_ir, entries).module_text,
            "НеТерминалS",
        )
        self.assertIn("Пока Истина Цикл", function)
        self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: select the local_continuation renderer first and let a
    # simultaneous tail_loop site remain a recursive BSL self-call.
    def test_mixed_tail_and_local_plan_sites_share_one_structural_loop(self) -> None:
        for recursive_value in ("<S>", "Rest = <S>"):
            with self.subTest(recursive_value=recursive_value):
                source, parser_ir, entries = _build_ir(
                    "<S> ::= ITEM <S> | "
                    f"@Node Value = MARK {recursive_value} | @End STOP"
                )
                self.assertEqual(
                    [(call.site.alternative, call.kind) for call in
                     analyze_recursion_plan(source, parser_ir).sites],
                    [(0, "tail_loop"), (1, "local_continuation")],
                )
                function = _function(
                    generate_canonical_parser(source, parser_ir, entries).module_text,
                    "НеТерминалS",
                )
                self.assertIn("Пока Истина Цикл", function)
                self.assertIn("СтекПродолжений = Новый Массив;", function)
                self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: reject multiple direct constructor continuations rather
    # than emitting frames for every planner-issued local site.
    def test_multiple_direct_continuations_are_all_lowered(self) -> None:
        for recursive_value in ("<S>", "Rest = <S>"):
            with self.subTest(recursive_value=recursive_value):
                function = _function(
                    _build(
                        f"<S> ::= @A Value = A {recursive_value} | "
                        f"@B Value = B {recursive_value} | @End STOP"
                    ).module_text,
                    "НеТерминалS",
                )
                self.assertEqual(
                    function.count("СтекПродолжений.Добавить(Продолжение);"),
                    2,
                )
                self.assertNotIn("НеТерминалS();", function)

    # Mutation caught: number continuation frame kinds per alternative, so
    # two different alternatives both push `Вид = 0` and unwind as the first.
    def test_cross_alternative_continuation_frames_use_global_plan_tags(self) -> None:
        function = _function(
            _build(
                "<S> ::= @A A (Value = ITEM Rest = <S>)? | "
                "@B B (Other = ITEM Tail = <S>)? | @End STOP"
            ).module_text,
            "НеТерминалS",
        )

        pushes = re.findall(
            r'Продолжение = Новый Структура;(.*?)СтекПродолжений.Добавить',
            function, re.S,
        )
        self.assertEqual(len(pushes), 2)
        for frame, tag, field in zip(pushes, (0, 1), ("Value", "Other")):
            self.assertIn(f'Продолжение.Вставить("Вид", {tag});', frame)
            self.assertIn(f'Продолжение.Вставить("Слот1", ЭтотУзел.{field});', frame)
        first, second = function.split("ИначеЕсли Продолжение.Вид = 1 Тогда")
        first = first.split("Если Продолжение.Вид = 0 Тогда")[1]
        self.assertIn("ЭтотУзел.Value = Продолжение.Слот1;", first)
        self.assertIn("ЭтотУзел.Rest = РезультатПродукции;", first)
        self.assertNotIn("ЭтотУзел.Other =", first)
        self.assertIn("ЭтотУзел.Other = Продолжение.Слот1;", second)
        self.assertIn("ЭтотУзел.Tail = РезультатПродукции;", second)
        self.assertNotIn("ЭтотУзел.Value =", second)

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

    def test_specialized_paths_render_proven_prefixes_and_one_continuation(
        self,
    ) -> None:
        function = _function(
            _build(self.PATH_FACTS_GRAMMAR, k=2).module_text,
            "НеТерминалS",
        )

        self.assertEqual(function.count("ТипТокенаПросмотра(1)"), 1)
        self.assertRegex(
            function,
            r'Если ТокенРешения0 = "NOT" Тогда\s+'
            r'ТокенРешения1 = ТипТокенаПросмотра\(1\);',
        )
        for token in ("NOT", "BETWEEN", "IN"):
            with self.subTest(checked_helper=token):
                self.assertNotIn(f'Терминал("{token}")', function)
        self.assertEqual(function.count("УстановитьТекущийТокен();"), 6)
        self.assertEqual(function.count("НеТерминалTail()"), 4)
        self.assertNotRegex(
            function,
            r"Если Значение\d+ = [1-9]\d* Тогда",
        )
        self.assertNotIn("НомерВариантаПродукции", function)
        self.assertEqual(function.count(".Child = "), 1)
        self.assertGreater(
            function.rfind(".Child = "),
            function.rfind("НеТерминалTail()"),
        )
        self.assertNotIn("Попытка", function)

    def test_known_symbol_consumes_capture_original_semantic_values(
        self,
    ) -> None:
        function = _function(
            _build(
                "#ID_Name ::= ID\n"
                "<S> ::= <Base> Child => <Choice>?\n"
                "<Base> ::= @НовыйBase BASE\n"
                "<Choice> ::= @НовыйTerminal Тип = WORD\n"
                "<Choice> ::= @НовыйLexeme Тип = 'exact'\n"
                "<Choice> ::= @НовыйConstant Значение = &NUMBER\n"
                "<Choice> ::= @НовыйIdentifier Значение = #ID_Name\n"
                "<Choice> ::= @НовыйDiscard DISCARD",
                k=2,
            ).module_text,
            "НеТерминалS",
        )

        self.assertEqual(
            len(
                re.findall(
                    r"Значение\d+ = ТекущийТокен\.Тип;\s+"
                    r"УстановитьТекущийТокен\(\);",
                    function,
                )
            ),
            2,
        )
        self.assertRegex(
            function,
            r"Значение\d+ = ТекущийТокен\.Значение;\s+"
            r"УстановитьТекущийТокен\(\);",
        )
        self.assertRegex(
            function,
            r"Значение\d+ = ТекущийТокен\.Лексема;\s+"
            r"УстановитьТекущийТокен\(\);",
        )
        self.assertRegex(
            function,
            r"НовыйDiscard\(ТекущийТокен\);\s+"
            r"УстановитьТекущийТокен\(\);",
        )
        for helper in (
            'Терминал("WORD")',
            'Лексема("exact")',
            'Константа("NUMBER")',
            'Идентификатор("ID_Name")',
            'Терминал("DISCARD")',
        ):
            with self.subTest(checked_helper=helper):
                self.assertNotIn(helper, function)

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
