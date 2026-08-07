from pathlib import Path
import unittest

from parsergen.analysis import (
    compute_analysis,
    find_runtime_dispatch_conflicts,
    find_select_conflicts,
)
from parsergen.grammar_parser import parse_grammar
from parsergen.resolver import resolve_grammar


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_GRAMMAR = PACKAGE_ROOT / "grammar/query-language.grammar"


class RepositoryGrammarCompatibilityTests(unittest.TestCase):
    def test_repository_grammar_parses_and_resolves_without_diagnostics(self) -> None:
        parsed = parse_grammar(
            REPOSITORY_GRAMMAR.read_text(encoding="utf-8-sig"),
            str(REPOSITORY_GRAMMAR),
        )
        self.assertEqual(parsed.diagnostics, ())
        assert parsed.grammar is not None
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


if __name__ == "__main__":
    unittest.main()
