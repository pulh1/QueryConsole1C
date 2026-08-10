from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

import parsergen.parser_ir as parser_ir_module
from parsergen.analysis import compute_analysis
from parsergen.canonical_bsl_codegen import generate_canonical_parser
from parsergen.canonical_select import (
    AlternativeOutcome,
    ExitOutcome,
    specialize_outcome,
)
from parsergen.decision_dag import (
    CommitAlternative,
    ExitDecision,
    build_decision_dag,
    evaluate_decision,
)
from parsergen.grammar_parser import parse_grammar
from parsergen.model import Constant, IdentifierRef, Lexeme, NonterminalCall, Terminal
from parsergen.parser_ir import (
    AssignConstant,
    BindScalar,
    ConstructNode,
    LeftFold,
    OptionalBranch,
    ParseSymbol,
    ReturnConstant,
    WrapOptional,
    build_parser_ir,
)
from parsergen.parser_ir_optimization import (
    classify_semantic_transparency,
    optimize_parser_ir,
)
from parsergen.resolver import resolve_grammar


def _build_raw(
    source: str,
    k: int = 1,
    *,
    entrypoints: tuple[str, ...] = ("S",),
):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.diagnostics == ()
    assert parsed.grammar is not None
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.diagnostics == ()
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, k, entrypoints)
    with patch(
        "parsergen.parser_ir_optimization.optimize_parser_ir",
        side_effect=lambda parser_ir: parser_ir,
    ):
        return build_parser_ir(
            parsed.source_grammar,
            parsed.lowering,
            resolved.grammar,
            analysis,
            entrypoint_productions=entrypoints,
        )


def _build(
    source: str,
    k: int = 1,
    *,
    entrypoints: tuple[str, ...] = ("S",),
):
    return optimize_parser_ir(
        _build_raw(source, k, entrypoints=entrypoints)
    )


def _function(module_text: str, name: str) -> str:
    marker = f"Функция НеТерминал{name}("
    start = module_text.index(marker)
    end = module_text.index("КонецФункции", start)
    return module_text[start:end]


def _accepts(language, word: tuple[str, ...]) -> bool:
    states = {language.root}
    for token in word:
        states = {
            edge.target
            for state in states
            for edge in language.nodes[state].edges
            if token in edge.predicate.token_types
        }
    return any(language.nodes[state].accepting for state in states)


class _TraceFailure(Exception):
    pass


class _ActionTraceEvaluator:
    def __init__(self, parser_ir, tokens: tuple[str, ...]) -> None:
        self.productions = {item.name: item for item in parser_ir.productions}
        self.tokens = tokens
        self.position = 0
        self.trace: list[tuple[str, str]] = []

    def execute(self, production: str):
        try:
            return self._production(production)
        except _TraceFailure:
            return None

    def _lookahead(self) -> tuple[str, ...]:
        values = self.tokens[self.position :]
        return tuple((*values, "$"))

    def _production(self, name: str):
        production = self.productions[name]
        alternative = production.alternatives[0]
        if production.decision is not None:
            leaf = evaluate_decision(production.decision.dag, self._lookahead())
            if not isinstance(leaf, CommitAlternative):
                raise _TraceFailure
            alternative = next(
                item
                for item in production.alternatives
                if item.index + 1 == leaf.outcome.alternative
            )
        values, current = self._operations(alternative.operations)
        if current is not None:
            return current
        if alternative.result_index is None:
            return None
        return values[alternative.result_index]

    def _branch(self, branches, leaf):
        matching = tuple(
            branch
            for branch in branches
            if branch.outcome == leaf.outcome
            and (
                branch.path_facts is None
                or all(
                    fact.offset < len(self._lookahead())
                    and self._lookahead()[fact.offset]
                    in fact.predicate.token_types
                    for fact in branch.path_facts
                )
            )
        )
        if len(matching) != 1:
            raise AssertionError(matching)
        return matching[0]

    def _operations(self, operations, current=None):
        values = []
        for operation in operations:
            if isinstance(operation, ConstructNode):
                self.trace.append(("construct", operation.constructor))
                current = {"type": operation.constructor}
                values.append(None)
            elif isinstance(operation, ParseSymbol):
                values.append(self._parse(operation.symbol))
            elif isinstance(operation, parser_ir_module.ConsumeKnownSymbol):
                values.append(self._consume_known(operation))
            elif isinstance(operation, BindScalar):
                value = self._bound(operation.value)
                self.trace.append(("bind", operation.property))
                assert current is not None
                current[operation.property] = value
                values.append(None)
            elif isinstance(operation, AssignConstant):
                self.trace.append(("bind", operation.property))
                assert current is not None
                current[operation.property] = operation.value
                values.append(None)
            elif isinstance(operation, WrapOptional):
                seed = self._operation_value(operation.seed)
                leaf = evaluate_decision(
                    operation.decision.dag,
                    self._lookahead(),
                )
                if isinstance(leaf, ExitDecision):
                    values.append(seed)
                    continue
                if not isinstance(leaf, CommitAlternative):
                    raise _TraceFailure
                branch = self._branch(operation.branches, leaf)
                branch_values, branch_current = self._operations(
                    branch.operations
                )
                child = (
                    branch_current
                    if branch_current is not None
                    else branch_values[branch.result_index]
                )
                self.trace.append(("bind", operation.property))
                child[operation.property] = seed
                values.append(child)
            elif isinstance(operation, OptionalBranch):
                leaf = evaluate_decision(
                    operation.decision.dag,
                    self._lookahead(),
                )
                if isinstance(leaf, ExitDecision):
                    branch_values, branch_current = self._operations(
                        operation.exit_operations,
                        current,
                    )
                elif isinstance(leaf, CommitAlternative):
                    branch = self._branch(operation.branches, leaf)
                    branch_values, branch_current = self._operations(
                        branch.operations,
                        current,
                    )
                else:
                    raise _TraceFailure
                values.append(
                    branch_current
                    if branch_current is not None
                    else (
                        branch_values[-1] if branch_values else None
                    )
                )
            elif isinstance(operation, parser_ir_module.ResolvedRegion):
                region_values, region_current = self._operations(
                    operation.operations,
                    current,
                )
                values.append(
                    region_current
                    if region_current is not None
                    else (
                        region_values[operation.result_index]
                        if operation.result_index is not None
                        else None
                    )
                )
            elif isinstance(operation, parser_ir_module.UndefinedValue):
                values.append(None)
            else:
                raise AssertionError(type(operation))
        return values, current

    def _operation_value(self, operation):
        values, current = self._operations((operation,))
        return current if current is not None else values[0]

    def _bound(self, value):
        if isinstance(value, ParseSymbol):
            return self._parse(value.symbol)
        if isinstance(value, parser_ir_module.ConsumeKnownSymbol):
            return self._consume_known(value)
        raise AssertionError(type(value))

    def _consume_known(self, operation):
        symbol = operation.symbol
        if isinstance(symbol, (Terminal, Lexeme)):
            expected = (
                symbol.token_type
                if isinstance(symbol, Terminal)
                else symbol.text
            )
        elif isinstance(symbol, IdentifierRef):
            expected = symbol.name
        elif isinstance(symbol, Constant):
            expected = symbol.token_type
        else:
            raise AssertionError(type(symbol))
        self.trace.append(("parse", expected))
        if self.position >= len(self.tokens):
            raise _TraceFailure
        value = self.tokens[self.position]
        self.position += 1
        return value if operation.capture_value else None

    def _parse(self, symbol):
        if isinstance(symbol, NonterminalCall):
            return self._production(symbol.name)
        if isinstance(symbol, (Terminal, Lexeme)):
            expected = symbol.token_type if isinstance(symbol, Terminal) else symbol.text
            self.trace.append(("parse", expected))
            if self.position >= len(self.tokens) or self.tokens[self.position] != expected:
                raise _TraceFailure
            self.position += 1
            return expected
        if isinstance(symbol, IdentifierRef):
            self.trace.append(("parse", symbol.name))
            if self.position >= len(self.tokens):
                raise _TraceFailure
            value = self.tokens[self.position]
            self.position += 1
            return value
        if isinstance(symbol, Constant):
            self.trace.append(("parse", symbol.token_type))
            if self.position >= len(self.tokens):
                raise _TraceFailure
            value = self.tokens[self.position]
            self.position += 1
            return value
        raise AssertionError(type(symbol))


class ParserIrTransparencyTests(unittest.TestCase):
    def test_transparency_is_structural_not_name_based(self) -> None:
        cases = (
            ("forward", "<S> ::= <Wrapper>\n<Wrapper> ::= <A>\n<A> ::= ITEM", True),
            (
                "constructor",
                "<S> ::= <Wrapper>\n<Wrapper> ::= @НовыйУзел <A>\n<A> ::= ITEM",
                False,
            ),
            (
                "binding",
                "<S> ::= <Wrapper>\n<Wrapper> ::= @НовыйУзел Значение = <A>\n<A> ::= ITEM",
                False,
            ),
            (
                "return-constant",
                "<S> ::= <Wrapper>\n<Wrapper> ::= := Неопределено",
                False,
            ),
            (
                "syntax-only",
                "<S> ::= <Wrapper>\n<Wrapper> ::= '(' ITEM ')'",
                True,
            ),
        )
        for name, grammar, expected in cases:
            with self.subTest(name=name):
                parser_ir = _build_raw(grammar)
                wrapper = next(
                    item for item in parser_ir.productions if item.name == "Wrapper"
                )
                result = classify_semantic_transparency(
                    wrapper,
                    entrypoints=frozenset({"S"}),
                    recursive_productions=frozenset(),
                )
                self.assertEqual(result.transparent, expected)
                self.assertTrue(result.reason)

    def test_entrypoints_recursive_scc_left_fold_and_source_boundaries_are_protected(self) -> None:
        forward = _build_raw(
            "<S> ::= <Wrapper>\n<Wrapper> ::= <A>\n<A> ::= ITEM"
        )
        wrapper = next(item for item in forward.productions if item.name == "Wrapper")
        self.assertFalse(
            classify_semantic_transparency(
                wrapper,
                entrypoints=frozenset({"Wrapper"}),
                recursive_productions=frozenset(),
            ).transparent
        )
        self.assertFalse(
            classify_semantic_transparency(
                wrapper,
                entrypoints=frozenset(),
                recursive_productions=frozenset({"Wrapper"}),
            ).transparent
        )

        left_recursive = _build_raw(
            "<S> ::= <Expr>\n<Expr> ::= <Expr> PLUS ITEM | ITEM"
        )
        expression = next(
            item for item in left_recursive.productions if item.name == "Expr"
        )
        self.assertIsInstance(expression.alternatives[0].operations[0], LeftFold)
        self.assertFalse(
            classify_semantic_transparency(
                expression,
                entrypoints=frozenset({"S"}),
                recursive_productions=frozenset(),
            ).transparent
        )

        alternative = wrapper.alternatives[0]
        call = alternative.operations[0]
        assert isinstance(call, ParseSymbol)
        boundary_call = replace(
            call,
            source_span=replace(call.source_span, path="included.grammar"),
        )
        boundary_wrapper = replace(
            wrapper,
            alternatives=(
                replace(alternative, operations=(boundary_call,)),
            ),
        )
        self.assertFalse(
            classify_semantic_transparency(
                boundary_wrapper,
                entrypoints=frozenset({"S"}),
                recursive_productions=frozenset(),
            ).transparent
        )

    def test_transparent_chain_is_inlined_but_semantic_wrapper_is_retained(self) -> None:
        transparent = _build(
            "<S> ::= <Wrapper>\n<Wrapper> ::= <A>\n<A> ::= ITEM"
        )
        self.assertEqual(
            tuple(item.name for item in transparent.productions),
            ("S",),
        )
        operation = transparent.productions[0].alternatives[0].operations[0]
        self.assertIsInstance(operation, ParseSymbol)
        self.assertIsInstance(operation.symbol, Terminal)

        semantic = _build(
            "<S> ::= <Wrapper>\n"
            "<Wrapper> ::= @НовыйУзел <A>\n"
            "<A> ::= ITEM"
        )
        self.assertIn("Wrapper", {item.name for item in semantic.productions})


class ParserIrSpecializationTests(unittest.TestCase):
    GRAMMAR = (
        "<S> ::= <Base> Child => <Choice>?\n"
        "<Base> ::= @НовыйBase BASE\n"
        "<Choice> ::= @НовыйA A X | @НовыйB B Y"
    )

    PATH_FACTS_GRAMMAR = (
        "<S> ::= <Base> Child => <Choice>?\n"
        "<Base> ::= @НовыйBase BASE\n"
        "<Choice> ::= @НовыйBetween (NOT Inverted := Истина)? BETWEEN <Tail>\n"
        "<Choice> ::= @НовыйIn (NOT Inverted := Истина)? IN <Tail>\n"
        "<Tail> ::= VALUE"
    )

    VALUE_PRODUCING_OPTIONAL_EXIT_GRAMMAR = (
        "#ID_Name ::= ID | WORD\n"
        "<S> ::= <Base> Child => <Choice>?\n"
        "<Base> ::= @НовыйBase BASE\n"
        "<Choice> ::= #ID_Name? X\n"
        "<Choice> ::= @НовыйOther #ID_Name Y"
    )

    def test_known_symbol_and_resolved_region_validate_their_contracts(self) -> None:
        raw = _build_raw("<S> ::= A")
        operation = raw.productions[0].alternatives[0].operations[0]
        assert isinstance(operation, ParseSymbol)
        span = operation.source_span
        known_symbol = parser_ir_module.ConsumeKnownSymbol
        resolved_region = parser_ir_module.ResolvedRegion

        for symbol in (
            Terminal("A", span),
            Lexeme("A", span),
            Constant("A", span),
            IdentifierRef("ID_A", span),
        ):
            with self.subTest(symbol=type(symbol).__name__):
                self.assertEqual(
                    known_symbol(symbol, True, ("A",), span).proven_token_types,
                    ("A",),
                )
        for proven in ((), ("B", "A"), ("A", "A")):
            with self.subTest(proven=proven):
                with self.assertRaises(ValueError):
                    known_symbol(Terminal("A", span), False, proven, span)
        with self.assertRaises(ValueError):
            known_symbol(NonterminalCall("S", (), span), True, ("A",), span)
        with self.assertRaises(ValueError):
            resolved_region((), 0, span)

    def test_path_facts_partially_evaluate_known_prefix_and_preserve_traces(
        self,
    ) -> None:
        before = _build_raw(self.PATH_FACTS_GRAMMAR, 2)
        after = optimize_parser_ir(before)
        wrapper = after.productions[0].alternatives[0].operations[0]
        assert isinstance(wrapper, WrapOptional)
        choice_1 = tuple(
            branch
            for branch in wrapper.branches
            if branch.outcome == AlternativeOutcome("Choice", 1)
        )
        choice_2 = tuple(
            branch
            for branch in wrapper.branches
            if branch.outcome == AlternativeOutcome("Choice", 2)
        )

        self.assertEqual(len(choice_1), 2)
        self.assertEqual(len(choice_2), 2)
        self.assertTrue(
            all(
                branch.path_facts is not None
                for branch in (*choice_1, *choice_2)
            )
        )
        self.assertEqual(
            {
                tuple(fact.predicate.token_types for fact in branch.path_facts or ())
                for branch in choice_1
            },
            {
                (("BETWEEN",),),
                (("NOT",), ("BETWEEN",)),
            },
        )
        self.assertEqual(
            {
                tuple(fact.predicate.token_types for fact in branch.path_facts or ())
                for branch in choice_2
            },
            {
                (("IN",),),
                (("NOT",), ("IN",)),
            },
        )

        def known_tokens(branch):
            result = []

            def visit(operations):
                for item in operations:
                    if isinstance(item, parser_ir_module.ConsumeKnownSymbol):
                        result.append(item.symbol.token_type)
                    elif isinstance(item, parser_ir_module.ResolvedRegion):
                        visit(item.operations)

            visit(branch.operations)
            return tuple(result)

        by_facts = {
            tuple(
                fact.predicate.token_types
                for fact in branch.path_facts or ()
            ): branch
            for branch in (*choice_1, *choice_2)
        }
        self.assertEqual(known_tokens(by_facts[(("BETWEEN",),)]), ("BETWEEN",))
        self.assertEqual(
            known_tokens(by_facts[(("NOT",), ("BETWEEN",))]),
            ("NOT", "BETWEEN"),
        )
        self.assertEqual(known_tokens(by_facts[(("IN",),)]), ("IN",))
        self.assertEqual(
            known_tokens(by_facts[(("NOT",), ("IN",))]),
            ("NOT", "IN"),
        )
        for branch in (*choice_1, *choice_2):
            self.assertEqual(
                sum(isinstance(item, ConstructNode) for item in branch.operations),
                1,
            )

        for name, tokens, returned in (
            ("between", ("BASE", "BETWEEN", "VALUE"), True),
            ("not-between", ("BASE", "NOT", "BETWEEN", "VALUE"), True),
            ("in", ("BASE", "IN", "VALUE"), True),
            ("not-in", ("BASE", "NOT", "IN", "VALUE"), True),
            ("exit", ("BASE",), True),
            ("invalid-suffix", ("BASE", "NOT", "BETWEEN", "WRONG"), False),
        ):
            with self.subTest(name=name):
                before_evaluator = _ActionTraceEvaluator(before, tokens)
                after_evaluator = _ActionTraceEvaluator(after, tokens)
                before_result = before_evaluator.execute("S")
                after_result = after_evaluator.execute("S")
                self.assertEqual(after_evaluator.trace, before_evaluator.trace)
                self.assertEqual(
                    after_evaluator.position,
                    before_evaluator.position,
                )
                self.assertEqual(before_result is not None, returned)
                self.assertEqual(after_result is not None, returned)
                if name == "invalid-suffix":
                    self.assertEqual(
                        after_evaluator.trace.count(("construct", "НовыйIn")),
                        0,
                    )

    def test_value_producing_optional_exit_keeps_undefined_in_specialized_path(
        self,
    ) -> None:
        before = _build_raw(self.VALUE_PRODUCING_OPTIONAL_EXIT_GRAMMAR, 2)
        after = optimize_parser_ir(before)
        wrapper = after.productions[0].alternatives[0].operations[0]
        assert isinstance(wrapper, WrapOptional)
        choice_1 = tuple(
            branch
            for branch in wrapper.branches
            if branch.outcome == AlternativeOutcome("Choice", 1)
        )
        self.assertEqual(len(choice_1), 2)
        self.assertTrue(all(branch.path_facts is not None for branch in choice_1))
        exit_branch = next(
            branch
            for branch in choice_1
            if tuple(
                fact.predicate.token_types
                for fact in branch.path_facts or ()
            )
            == (("X",),)
        )

        generated = generate_canonical_parser(
            after.source_grammar,
            after,
            {"Parse": "S"},
        )
        function = _function(generated.module_text, "S")
        self.assertNotIn("НеТерминалChoice()", function)
        self.assertNotIn("Функция НеТерминалChoice(", generated.module_text)
        self.assertEqual(generated.module_text.count("НовыйBase"), 1)
        self.assertEqual(function.count(".Child = "), 1)

        region = exit_branch.operations[0]
        self.assertIsInstance(region, parser_ir_module.ResolvedRegion)
        assert isinstance(region, parser_ir_module.ResolvedRegion)
        self.assertIsNotNone(region.result_index)
        assert region.result_index is not None
        self.assertIsInstance(
            region.operations[region.result_index],
            parser_ir_module.UndefinedValue,
        )
        self.assertEqual(
            sum(
                isinstance(operation, parser_ir_module.ConsumeKnownSymbol)
                for operation in exit_branch.operations
            ),
            1,
        )

        before_evaluator = _ActionTraceEvaluator(before, ("X",))
        before_result = before_evaluator.execute("Choice")
        after_evaluator = _ActionTraceEvaluator(after, ("X",))
        values, current = after_evaluator._operations(exit_branch.operations)
        self.assertIsNone(current)
        assert exit_branch.result_index is not None
        after_result = values[exit_branch.result_index]
        self.assertEqual(after_result, before_result)
        self.assertEqual(after_evaluator.trace, before_evaluator.trace)
        self.assertEqual(after_evaluator.position, before_evaluator.position)

    def test_path_expansion_cost_33_rejects_composition_without_emitted_duplication(
        self,
    ) -> None:
        # The two source branches cost 37 operations recursively.  Their
        # direct paths each remove two optional-branch operations, so cloning
        # direct and inverted fragments adds exactly 37 - 4 = 33 operations.
        between_actions = " ".join(
            f"BetweenFlag{index} := Истина" for index in range(13)
        )
        in_actions = " ".join(
            f"InFlag{index} := Истина" for index in range(12)
        )
        parser_ir = _build(
            "<S> ::= <Base> Child => <Choice>?\n"
            "<Base> ::= @НовыйBase BASE\n"
            f"<Choice> ::= @НовыйBetween {between_actions} "
            "(NOT Inverted := Истина)? BETWEEN <Tail>\n"
            f"<Choice> ::= @НовыйIn {in_actions} "
            "(NOT Inverted := Истина)? IN <Tail>\n"
            "<Tail> ::= VALUE",
            2,
        )
        generated = generate_canonical_parser(
            parser_ir.source_grammar,
            parser_ir,
            {"Parse": "S"},
        )
        function = _function(generated.module_text, "S")

        self.assertNotIn("НовыйBetween", function)
        self.assertNotIn("НовыйIn", function)
        self.assertNotIn(".BetweenFlag0 = Истина;", function)
        self.assertNotIn(".InFlag0 = Истина;", function)
        self.assertNotIn('Терминал("VALUE")', function)
        self.assertEqual(function.count("НеТерминалChoice()"), 1)
        self.assertIn("Функция НеТерминалChoice(", generated.module_text)

        wrapper = parser_ir.productions[0].alternatives[0].operations[0]
        assert isinstance(wrapper, WrapOptional)
        self.assertEqual(len(wrapper.branches), 1)
        caller_branch = wrapper.branches[0]
        self.assertIsNone(caller_branch.path_facts)
        self.assertEqual(len(caller_branch.operations), 1)
        call = caller_branch.operations[0]
        self.assertIsInstance(call, ParseSymbol)
        assert isinstance(call, ParseSymbol)
        self.assertIsInstance(call.symbol, NonterminalCall)
        assert isinstance(call.symbol, NonterminalCall)
        self.assertEqual(call.symbol.name, "Choice")
        self.assertIn("Choice", {item.name for item in parser_ir.productions})

    def test_symbolic_specialization_intersects_languages_and_retains_exit(self) -> None:
        parser_ir = _build_raw(self.GRAMMAR, 2)
        wrapper = parser_ir.productions[0].alternatives[0].operations[0]
        assert isinstance(wrapper, WrapOptional)
        callee = next(
            item for item in parser_ir.productions if item.name == "Choice"
        )
        assert callee.decision is not None

        source = specialize_outcome(
            wrapper.decision.source,
            wrapper.branches[0].outcome,
            callee.decision.source,
        )
        dag = build_decision_dag(source)
        outcomes = {item.outcome for item in source.languages}
        self.assertEqual(
            outcomes,
            {
                AlternativeOutcome("Choice", 1),
                AlternativeOutcome("Choice", 2),
                ExitOutcome(wrapper.decision.source.production, 2),
            },
        )
        languages = {item.outcome: item.language for item in source.languages}
        self.assertTrue(_accepts(languages[AlternativeOutcome("Choice", 1)], ("A", "X")))
        self.assertFalse(_accepts(languages[AlternativeOutcome("Choice", 1)], ("A", "Y")))
        self.assertEqual(
            evaluate_decision(dag, ("A", "X")),
            CommitAlternative(AlternativeOutcome("Choice", 1)),
        )
        self.assertIsInstance(evaluate_decision(dag, ("$",)), ExitDecision)

    def test_optional_semantic_callee_is_selected_once_and_actions_are_preserved(self) -> None:
        parser_ir = _build(self.GRAMMAR, 2)
        self.assertNotIn("Choice", {item.name for item in parser_ir.productions})
        wrapper = parser_ir.productions[0].alternatives[0].operations[0]
        assert isinstance(wrapper, WrapOptional)
        self.assertEqual(len(wrapper.branches), 2)
        self.assertEqual(
            sum(
                isinstance(operation, ConstructNode)
                for branch in wrapper.branches
                for operation in branch.operations
            ),
            2,
        )

    def test_repeated_semantic_action_without_common_prefix_proof_is_unchanged(self) -> None:
        parser_ir = _build(
            "<S> ::= <Base> Child => <Choice>?\n"
            "<Base> ::= @НовыйBase BASE\n"
            "<Choice> ::= @НовыйChild A X | @НовыйChild B Y",
            2,
        )
        generated = generate_canonical_parser(
            parser_ir.source_grammar,
            parser_ir,
            {"Parse": "S"},
        )
        function = _function(generated.module_text, "S")

        self.assertIn("НеТерминалChoice()", function)
        self.assertIn("Функция НеТерминалChoice(", generated.module_text)
        self.assertEqual(generated.module_text.count("НовыйChild"), 2)

    def test_success_exit_and_committed_failure_preserve_action_traces(self) -> None:
        before = _build_raw(self.GRAMMAR, 2)
        after = optimize_parser_ir(before)
        for name, tokens, returned in (
            ("success", ("BASE", "A", "X"), True),
            ("exit", ("BASE",), True),
            ("committed-failure", ("BASE", "A", "Q"), False),
        ):
            with self.subTest(name=name):
                before_evaluator = _ActionTraceEvaluator(before, tokens)
                after_evaluator = _ActionTraceEvaluator(after, tokens)
                before_result = before_evaluator.execute("S")
                after_result = after_evaluator.execute("S")
                self.assertEqual(before_evaluator.trace, after_evaluator.trace)
                self.assertEqual(before_result is not None, returned)
                self.assertEqual(after_result is not None, returned)
                self.assertLessEqual(
                    after_evaluator.trace.count(("construct", "НовыйA")),
                    1,
                )
                self.assertLessEqual(
                    after_evaluator.trace.count(("bind", "Child")),
                    1,
                )

    def test_unsupported_calls_remain_and_entrypoint_callee_is_not_removed(self) -> None:
        with_arguments = _build(
            "<S> ::= <Wrapper>(Value)\n<Wrapper>(Value) ::= ITEM"
        )
        s_operation = with_arguments.productions[0].alternatives[0].operations[0]
        self.assertIsInstance(s_operation, ParseSymbol)
        self.assertEqual(s_operation.symbol.arguments, ("Value",))
        self.assertIn("Wrapper", {item.name for item in with_arguments.productions})

        with_prefix = _build(
            "<S> ::= (PREFIX <Choice>)?\n<Choice> ::= A | B",
            1,
        )
        optional = with_prefix.productions[0].alternatives[0].operations[0]
        assert isinstance(optional, OptionalBranch)
        self.assertEqual(len(optional.branches[0].operations), 2)
        self.assertIn("Choice", {item.name for item in with_prefix.productions})

        protected = _build(
            self.GRAMMAR,
            2,
            entrypoints=("S", "Choice"),
        )
        self.assertIn("Choice", {item.name for item in protected.productions})

    def test_reachability_is_computed_from_actual_entrypoints(self) -> None:
        optimized = _build(
            "<S> ::= <Live>\n<Live> ::= LIVE\n<Dead> ::= DEAD"
        )
        self.assertEqual(
            tuple(item.name for item in optimized.productions),
            ("S",),
        )


if __name__ == "__main__":
    unittest.main()
