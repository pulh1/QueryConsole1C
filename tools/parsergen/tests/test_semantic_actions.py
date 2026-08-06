import unittest

from parsergen.diagnostics import SourcePosition, SourceSpan
from parsergen.model import Action
from parsergen.semantic_actions import ActionCompiler, compile_action


SPAN = SourceSpan(
    "<test>",
    SourcePosition(1, 1, 0),
    SourcePosition(1, 2, 1),
)


class SemanticActionCompilerTests(unittest.TestCase):
    def test_compiles_pseudo_constructor_and_one_guard(self) -> None:
        text = compile_action(
            Action(
                "ЭтотУзел = НовыйЗапрос; "
                "ЭтотУзел.Value = ТекущийЭлемент",
                1,
                SPAN,
            ),
            indent="\t",
            guard=True,
        )

        self.assertEqual(
            text,
            '\tЕсли ТекущийЭлемент <> "ПУСТО" Тогда\r\n'
            "\t\tЭтотУзел = "
            "ЭлементыМоделиЗапроса.НовыйЗапрос(ТекущийТокен);\r\n"
            "\t\tЭтотУзел.Value = ТекущийЭлемент;\r\n"
            "\tКонецЕсли;\r\n",
        )
        self.assertEqual(text.count("Если ТекущийЭлемент"), 1)

    def test_does_not_split_semicolon_or_equals_inside_strings(self) -> None:
        text = compile_action(
            Action(
                'Text = "a;b=c"; Result = Call("x=y")',
                0,
                SPAN,
            ),
            indent="",
            guard=False,
        )

        self.assertEqual(
            text,
            'Text = "a;b=c";\r\nResult = Call("x=y");\r\n',
        )

    def test_normalizes_assignment_spacing_for_reference_compatibility(self) -> None:
        text = compile_action(
            Action(
                "ЭтотУзел.Value  =  ТекущийЭлемент",
                0,
                SPAN,
            ),
            indent="",
            guard=False,
        )

        self.assertEqual(
            text,
            "ЭтотУзел.Value = ТекущийЭлемент;\r\n",
        )

    def test_preserves_empty_tail_statement_for_reference_compatibility(self) -> None:
        text = compile_action(
            Action(
                "ЭтотУзел = Разыменование;",
                0,
                SPAN,
            ),
            indent="\t",
            guard=False,
        )

        self.assertEqual(
            text,
            "\tЭтотУзел = Разыменование;\r\n\t;\r\n",
        )

    def test_tracks_doubled_quotes_nested_calls_and_line_comments(self) -> None:
        compiler = ActionCompiler(indent="", guard=False)

        text = compiler.compile(
            Action(
                'Text = "a"";=b"; '
                "Call(One(1; 2), [3; 4]); "
                "// НовыйIgnored; X = НовыйIgnored\n"
                "Result = НовыйReal",
                0,
                SPAN,
            )
        )

        self.assertEqual(text.count("\r\n"), 4)
        self.assertIn('Text = "a"";=b";\r\n', text)
        self.assertIn("Call(One(1; 2), [3; 4]);\r\n", text)
        self.assertIn("// НовыйIgnored; X = НовыйIgnored\r\n", text)
        self.assertIn(
            "Result = ЭлементыМоделиЗапроса.НовыйReal(ТекущийТокен);",
            text,
        )
        self.assertEqual(compiler.constructor_names, ("НовыйReal",))

    def test_rewrites_only_a_complete_constructor_rhs(self) -> None:
        text = compile_action(
            Action(
                "A = НовыйOne(); B = НовыйTwo + Suffix; C = НовыйТри",
                0,
                SPAN,
            ),
            indent="",
            guard=False,
        )

        self.assertEqual(
            text,
            "A = НовыйOne();\r\n"
            "B = НовыйTwo + Suffix;\r\n"
            "C = ЭлементыМоделиЗапроса.НовыйТри(ТекущийТокен);\r\n",
        )

    def test_does_not_rewrite_comparisons_or_nonassignable_left_sides(self) -> None:
        compiler = ActionCompiler(indent="", guard=False)

        text = compiler.compile(
            Action(
                "Возврат A >= НовыйGreater; "
                "Возврат B <= НовыйLess; "
                "Возврат C = НовыйComparison; "
                "Если D = НовыйCondition Тогда",
                0,
                SPAN,
            )
        )

        self.assertEqual(
            text,
            "Возврат A >= НовыйGreater;\r\n"
            "Возврат B <= НовыйLess;\r\n"
            "Возврат C = НовыйComparison;\r\n"
            "Если D = НовыйCondition Тогда;\r\n",
        )
        self.assertEqual(compiler.constructor_names, ())

    def test_rewrites_dotted_and_indexed_assignment_targets(self) -> None:
        compiler = ActionCompiler(indent="", guard=False)

        text = compiler.compile(
            Action(
                "ЭтотУзел.Value = НовыйDot; "
                "Items[Index + Call(1)] = НовыйIndex; "
                "Map[\"a=b;c\"].Value = НовыйNested",
                0,
                SPAN,
            )
        )

        self.assertIn(
            "ЭтотУзел.Value = "
            "ЭлементыМоделиЗапроса.НовыйDot(ТекущийТокен);",
            text,
        )
        self.assertIn(
            "Items[Index + Call(1)] = "
            "ЭлементыМоделиЗапроса.НовыйIndex(ТекущийТокен);",
            text,
        )
        self.assertIn(
            'Map["a=b;c"].Value = '
            "ЭлементыМоделиЗапроса.НовыйNested(ТекущийТокен);",
            text,
        )
        self.assertEqual(
            compiler.constructor_names,
            ("НовыйDot", "НовыйIndex", "НовыйNested"),
        )


if __name__ == "__main__":
    unittest.main()

