import unittest

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.parser_ir import (
    Dispatch,
    ExtendCollection,
    OptionalBranch,
    ParseSymbol,
    RepeatLoop,
    WrapOptional,
    WrapValue,
    build_parser_ir,
)
from parsergen.resolver import resolve_grammar


def _build(source: str, k: int = 1):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, k, ("S",))
    return build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
    )


class ParserIrTests(unittest.TestCase):
    def test_collection_decorator_marks_optional_wrap_as_append(self) -> None:
        parser_ir = _build(
            "<S> ::= <Base> Элементы +=> <Postfix>?\n"
            "<Base> ::= @НовыйБаза BASE\n"
            "<Postfix> ::= @НовыйPostfix POSTFIX"
        )

        operation = parser_ir.productions[0].alternatives[0].operations[0]
        self.assertIsInstance(operation, WrapOptional)
        self.assertTrue(operation.prepend)

    def test_optional_returned_child_decorator_is_one_semantic_operation(
        self,
    ) -> None:
        parser_ir = _build(
            "<S> ::= <Base> Операнд => <Postfix>?\n"
            "<Base> ::= @НовыйБаза BASE\n"
            "<Postfix> ::= @НовыйPostfix POSTFIX"
        )

        alternative = parser_ir.productions[0].alternatives[0]
        self.assertEqual(len(alternative.operations), 1)
        self.assertIsInstance(alternative.operations[0], WrapOptional)
        self.assertEqual(alternative.result_index, 0)

    def test_required_returned_child_decorator_is_one_semantic_operation(
        self,
    ) -> None:
        parser_ir = _build(
            "<S> ::= <Seed> Тип => <Child>\n"
            "<Seed> ::= @НовыйТип TYPE\n"
            "<Child> ::= @НовыйУзел CHILD"
        )

        alternative = parser_ir.productions[0].alternatives[0]
        self.assertEqual(len(alternative.operations), 1)
        self.assertIsInstance(alternative.operations[0], WrapValue)
        self.assertEqual(alternative.result_index, 0)

    def test_collection_extend_is_one_structural_operation(self) -> None:
        parser_ir = _build(
            "<S> ::= @НовыйУзел Элементы *= <Items>\n"
            "<Items> ::= @НовыйСписок += ITEM"
        )

        alternative = parser_ir.productions[0].alternatives[0]
        self.assertEqual(len(alternative.operations), 2)
        self.assertIsInstance(alternative.operations[1], ExtendCollection)
        self.assertIsNone(alternative.result_index)

    def test_projection_builds_only_selected_production_and_skips_legacy_actions(
        self,
    ) -> None:
        parsed = parse_grammar(
            "<S> ::= <Expr> {Legacy = ТекущийЭлемент}\n"
            "<Expr> ::= <Term>\n"
            "<Term> ::= ITEM"
        )
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolved.grammar,
            analysis,
            production_names=("Expr",),
        )

        self.assertEqual(
            tuple(item.name for item in parser_ir.productions),
            ("Expr",),
        )

    def test_projection_ignores_conflict_owned_by_legacy_island(self) -> None:
        parsed = parse_grammar(
            "<S> ::= <Expr> <Legacy>\n"
            "<Expr> ::= ITEM\n"
            "<Legacy> ::= 'a'* 'a'"
        )
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        parser_ir = build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolved.grammar,
            analysis,
            production_names=("Expr",),
        )

        self.assertEqual(parser_ir.productions[0].name, "Expr")

    def test_projection_rejects_unknown_production(self) -> None:
        parsed = parse_grammar("<S> ::= ITEM")
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        with self.assertRaisesRegex(ValueError, "unknown Parser IR production"):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved.grammar,
                analysis,
                production_names=("Missing",),
            )

    def test_projection_rejects_duplicate_production(self) -> None:
        parsed = parse_grammar("<S> ::= ITEM")
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        with self.assertRaisesRegex(ValueError, "duplicate Parser IR production"):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved.grammar,
                analysis,
                production_names=("S", "S"),
            )

    def test_transparent_nonterminal_identifier_and_constant_have_result(
        self,
    ) -> None:
        parser_ir = _build(
            "#ID_Name ::= ID\n"
            "<S> ::= <Node>\n"
            "<Node> ::= #ID_Name\n"
            "<ConstantNode> ::= &NUMBER"
        )

        productions = {
            item.name: item
            for item in parser_ir.productions
        }
        self.assertEqual(
            productions["S"].alternatives[0].result_index,
            0,
        )
        self.assertEqual(
            productions["Node"].alternatives[0].result_index,
            0,
        )
        self.assertEqual(
            productions["ConstantNode"].alternatives[0].result_index,
            0,
        )

    def test_terminal_only_alternative_is_syntax_only(self) -> None:
        parser_ir = _build("<S> ::= ITEM")

        alternative = parser_ir.productions[0].alternatives[0]
        self.assertIsNone(alternative.result_index)

    def test_group_branches_record_exact_transparent_result(self) -> None:
        parser_ir = _build(
            "<S> ::= (',' <A> | ';' <B>)\n"
            "<A> ::= A\n<B> ::= B"
        )

        dispatch = parser_ir.productions[0].alternatives[0].operations[0]
        assert isinstance(dispatch, Dispatch)
        self.assertEqual(
            [branch.result_index for branch in dispatch.branches],
            [1, 1],
        )
        self.assertEqual(
            parser_ir.productions[0].alternatives[0].result_index,
            0,
        )

    def test_rejects_two_transparent_semantic_values_before_codegen(self) -> None:
        parsed = parse_grammar(
            "<S> ::= <A> <B>\n<A> ::= A\n<B> ::= B"
        )
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        with self.assertRaisesRegex(
            ValueError,
            "multiple transparent semantic values",
        ):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved.grammar,
                analysis,
            )

    def test_rejects_unbound_repeated_semantic_value_before_codegen(self) -> None:
        for operator in ("*", "+"):
            with self.subTest(operator=operator):
                parsed = parse_grammar(
                    f"<S> ::= <A>{operator}\n<A> ::= ITEM"
                )
                assert parsed.grammar is not None
                assert parsed.source_grammar is not None
                assert parsed.lowering is not None
                resolved = resolve_grammar(parsed.grammar)
                assert resolved.grammar is not None
                analysis = compute_analysis(resolved.grammar, 1, ("S",))

                with self.assertRaisesRegex(
                    ValueError,
                    "repeated semantic value requires collection binding",
                ):
                    build_parser_ir(
                        parsed.source_grammar,
                        parsed.lowering,
                        resolved.grammar,
                        analysis,
                    )

    def test_separator_star_becomes_repeat_loop_without_synthetic_function(
        self,
    ) -> None:
        parser_ir = _build("<S> ::= 'a' (',' 'a')*")

        self.assertEqual(
            [production.name for production in parser_ir.productions],
            ["S"],
        )
        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [ParseSymbol, RepeatLoop])
        loop = operations[1]
        assert isinstance(loop, RepeatLoop)
        self.assertEqual(len(loop.branches), 1)
        self.assertEqual(
            [item.symbol.text for item in loop.branches[0].operations],
            [",", "a"],
        )
        self.assertTrue(loop.decision.production.startswith("__parsergen_ebnf__"))
        self.assertEqual(
            {row.alternative for row in loop.decision.rows},
            {1, 2},
        )
        self.assertFalse(
            any(
                production.name.startswith("__parsergen_ebnf__")
                for production in parser_ir.productions
            )
        )

    def test_plus_becomes_mandatory_parse_followed_by_repeat_loop(self) -> None:
        parser_ir = _build("<S> ::= 'a'+")

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [ParseSymbol, RepeatLoop])
        self.assertEqual(operations[0].symbol.text, "a")
        self.assertEqual(len(operations[1].branches), 1)

    def test_optional_becomes_optional_branch(self) -> None:
        parser_ir = _build("<S> ::= (a | b)?")

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [OptionalBranch])
        optional = operations[0]
        self.assertEqual(len(optional.branches), 2)
        self.assertEqual(optional.exit_operations, ())
        self.assertEqual(
            [branch.operations[0].symbol.token_type for branch in optional.branches],
            ["a", "b"],
        )

    def test_standalone_group_becomes_canonical_dispatch(self) -> None:
        parser_ir = _build("<S> ::= (a | b) c")

        operations = parser_ir.productions[0].alternatives[0].operations
        self.assertEqual([type(item) for item in operations], [Dispatch, ParseSymbol])
        self.assertEqual(len(operations[0].branches), 2)

    def test_canonical_decision_keeps_identifier_matcher_factorized(self) -> None:
        parser_ir = _build("#ID_A ::= ID | WORD\n<S> ::= #ID_A?")

        optional = parser_ir.productions[0].alternatives[0].operations[0]
        assert isinstance(optional, OptionalBranch)
        consuming = [
            row
            for row in optional.decision.rows
            if row.alternative == 1
        ]
        self.assertEqual(len(consuming), 1)
        matcher = next(
            definition
            for definition in optional.decision.matcher_definitions
            if definition.label == consuming[0].matchers[0]
        )
        self.assertEqual(matcher.token_types, ("ID", "WORD"))

    def test_conflicting_select_prevents_parser_ir_build(self) -> None:
        parsed = parse_grammar("<S> ::= 'a'* 'a'")
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        with self.assertRaisesRegex(ValueError, "overlapping canonical SELECT"):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved.grammar,
                analysis,
            )

    def test_source_action_requires_declarative_binding_before_ir_build(self) -> None:
        parsed = parse_grammar("<S> ::= {Value = 1} a")
        assert parsed.grammar is not None
        assert parsed.source_grammar is not None
        assert parsed.lowering is not None
        resolved = resolve_grammar(parsed.grammar)
        assert resolved.grammar is not None
        analysis = compute_analysis(resolved.grammar, 1, ("S",))

        with self.assertRaisesRegex(ValueError, "arbitrary source actions"):
            build_parser_ir(
                parsed.source_grammar,
                parsed.lowering,
                resolved.grammar,
                analysis,
            )


if __name__ == "__main__":
    unittest.main()
