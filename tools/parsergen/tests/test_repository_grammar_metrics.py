from __future__ import annotations

from pathlib import Path
import re
import unittest

from parsergen.canonical_bsl_codegen import generate_canonical_parser
from parsergen.cli import compile_from_config
from parsergen.config import load_config
from parsergen.decision_dag import aggregate_decision_dag_metrics
from parsergen.parser_ir import build_parser_ir
from tests.parser_ir_metrics import (
    decision_path_metrics,
    parser_ir_decisions,
)


ROOT = Path(__file__).parents[3]
DECISION_LINE = re.compile(r"^\s*(?:Если|ИначеЕсли|Пока)\b", re.IGNORECASE)
NONTERMINAL_FUNCTION = re.compile(
    r"^\s*Функция\s+НеТерминал",
    re.IGNORECASE,
)
NONTERMINAL_REFERENCE = re.compile(
    r"\bНеТерминал[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*\s*\(",
    re.IGNORECASE,
)
PREDICATE_ATOM = re.compile(
    r"(?:ТипТокенаПросмотра\(\d+\)|ТокенРешения\d+)\s*(?:=|<>)",
    re.IGNORECASE,
)


def _canonical_production_output():
    config = load_config(ROOT / "parsergen.toml")
    compilation = compile_from_config(config)
    assert compilation.report.diagnostics == ()
    assert compilation.source_grammar is not None
    assert compilation.lowering is not None
    assert compilation.resolved is not None
    assert compilation.analysis is not None
    parser_ir = build_parser_ir(
        compilation.source_grammar,
        compilation.lowering,
        compilation.resolved,
        compilation.analysis,
        entrypoint_productions=config.entrypoints.values(),
    )
    generated = generate_canonical_parser(
        compilation.source_grammar,
        parser_ir,
        config.entrypoints,
    )
    return compilation, parser_ir, generated


def _generated_bsl_shape(module_text: str) -> dict[str, int]:
    lines = module_text.splitlines()
    decisions = [line.strip() for line in lines if DECISION_LINE.match(line)]
    nonterminal_functions = sum(
        NONTERMINAL_FUNCTION.match(line) is not None for line in lines
    )
    return {
        "bsl_functions": sum(
            line.strip().casefold().startswith("функция ") for line in lines
        ),
        "bsl_loc": len(lines),
        "lookahead_calls": module_text.count("ТипТокенаПросмотра("),
        "decision_lines": len(decisions),
        "predicate_atoms": sum(
            len(PREDICATE_ATOM.findall(line)) for line in decisions
        ),
        "nonterminal_functions": nonterminal_functions,
        "nonterminal_call_sites": max(
            0,
            len(NONTERMINAL_REFERENCE.findall(module_text))
            - nonterminal_functions,
        ),
        "max_condition_chars": max(map(len, decisions), default=0),
        "max_condition_predicate_atoms": max(
            (len(PREDICATE_ATOM.findall(line)) for line in decisions),
            default=0,
        ),
        "max_condition_lookahead_calls": max(
            (line.count("ТипТокенаПросмотра(") for line in decisions),
            default=0,
        ),
    }


class RepositoryGrammarMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compilation, cls.parser_ir, cls.generated = (
            _canonical_production_output()
        )

    def test_structural_and_decision_dag_baselines_remain_bounded(self) -> None:
        source = self.compilation.source_grammar
        grammar = self.compilation.grammar
        assert source is not None
        assert grammar is not None

        self.assertEqual(
            {
                "source_productions": len(source.productions),
                "source_alternatives": sum(
                    len(production.alternatives)
                    for production in source.productions
                ),
                "lowered_productions": len(grammar.productions),
                "lowered_alternatives": sum(
                    len(production.alternatives)
                    for production in grammar.productions
                ),
                "epsilon_alternatives": sum(
                    not alternative.syntax_symbols
                    for production in grammar.productions
                    for alternative in production.alternatives
                ),
            },
            {
                "source_productions": 66,
                "source_alternatives": 144,
                "lowered_productions": 156,
                "lowered_alternatives": 334,
                "epsilon_alternatives": 80,
            },
        )
        self.assertEqual(
            aggregate_decision_dag_metrics(
                decision.dag
                for decision in parser_ir_decisions(self.parser_ir, unique=True)
            ),
            {
                "source_states": 33_659,
                "dag_states": 406,
                "shared_states": 89,
                "max_depth": 2,
                "decision_regions": 109,
                "emitted_predicates": 310,
            },
        )

    def test_canonical_bsl_shape_and_ir_path_metrics_remain_exact(self) -> None:
        self.assertEqual(
            decision_path_metrics(self.parser_ir),
            {
                "specialized_paths": 6,
                "known_symbol_consumes": 11,
                "redundant_validations": 0,
            },
        )
        self.assertEqual(
            {
                "constructor_names": len(self.generated.constructor_names),
                "select_rows": len(self.generated.select_table.rows),
                "identifier_rows": len(self.generated.identifier_table.rows),
                **_generated_bsl_shape(self.generated.module_text),
            },
            {
                "constructor_names": 79,
                "select_rows": 0,
                "identifier_rows": 276,
                "bsl_functions": 74,
                "bsl_loc": 2463,
                "lookahead_calls": 130,
                "decision_lines": 366,
                "predicate_atoms": 3_779,
                "nonterminal_functions": 63,
                "nonterminal_call_sites": 180,
                "max_condition_chars": 2_551,
                "max_condition_predicate_atoms": 88,
                "max_condition_lookahead_calls": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
