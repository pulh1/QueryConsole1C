from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from parsergen.config import load_config


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def write_config(self, text: str) -> Path:
        config_path = self.root / "parsergen.toml"
        config_path.write_text(text, encoding="utf-8")
        return config_path

    def test_loads_repository_config_with_cyrillic_entrypoints(self) -> None:
        repository_root = Path(__file__).resolve().parents[3]

        config = load_config(repository_root / "parsergen.toml")

        self.assertEqual(
            config.grammar,
            (repository_root / "tools/parsergen/grammar/query-language.grammar").resolve(),
        )
        self.assertEqual(
            config.target,
            (repository_root / "QueryConsoleZUP/src/DataProcessors/Парсер").resolve(),
        )
        self.assertEqual(config.lookahead, 2)
        self.assertEqual(
            config.canonical_productions,
            (
                "Выражение",
                "ЛогическоеСлагаемое",
                "АрифметическоеВыражение",
                "Слагаемое",
                "УнарнаяОперация",
                "СписокВыражений",
                "СписокВыраженийМодели",
                "Выбор",
                "КогдаТогда",
                "Параметр",
            ),
        )
        self.assertEqual(
            list(config.entrypoints.items()),
            [
                ("Разобрать", "ПакетЗапросов"),
                ("РазобратьВыражение", "Выражение"),
            ],
        )

    def test_resolves_relative_paths_and_freezes_ordered_entrypoints(self) -> None:
        config = load_config(
            self.write_config(
                'grammar = "grammar/extended.txt"\n'
                'target = "src/DataProcessors/Парсер"\n'
                "lookahead = 3\n"
                "[entrypoints]\n"
                '"РазобратьЗапрос" = "Запрос"\n'
                '"РазобратьВыражение" = "Выражение"\n'
            )
        )

        self.assertEqual(
            config.grammar,
            (self.root / "grammar/extended.txt").resolve(),
        )
        self.assertEqual(
            config.target,
            (self.root / "src/DataProcessors/Парсер").resolve(),
        )
        self.assertEqual(config.lookahead, 3)
        self.assertIsInstance(config.entrypoints, MappingProxyType)
        self.assertEqual(
            list(config.entrypoints.items()),
            [
                ("РазобратьЗапрос", "Запрос"),
                ("РазобратьВыражение", "Выражение"),
            ],
        )
        with self.assertRaises(TypeError):
            config.entrypoints["Новая"] = "S"  # type: ignore[index]

    def test_loads_explicit_canonical_migration_productions(self) -> None:
        config = load_config(
            self.write_config(
                'grammar = "grammar.txt"\n'
                'target = "Парсер"\n'
                "lookahead = 2\n"
                "[migration]\n"
                'canonical_productions = ["Expr", "Term"]\n'
                "[entrypoints]\n"
                '"Разобрать" = "S"\n'
            )
        )

        self.assertEqual(config.canonical_productions, ("Expr", "Term"))

    def test_rejects_invalid_canonical_migration_productions(self) -> None:
        cases = {
            "wrong-type": 'canonical_productions = "Expr"\n',
            "empty": "canonical_productions = []\n",
            "empty-name": 'canonical_productions = [""]\n',
            "non-string": 'canonical_productions = ["Expr", 1]\n',
            "duplicate": 'canonical_productions = ["Expr", "Expr"]\n',
        }
        for label, migration in cases.items():
            with self.subTest(label=label):
                path = self.write_config(
                    'grammar = "grammar.txt"\n'
                    'target = "Парсер"\n'
                    "lookahead = 2\n"
                    "[migration]\n"
                    f"{migration}"
                    "[entrypoints]\n"
                    '"Разобрать" = "S"\n'
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "canonical_productions",
                ):
                    load_config(path)

    def test_normalizes_absolute_paths_without_requiring_existence(self) -> None:
        grammar = (self.root / "abs/../grammar.txt").absolute()
        target = (self.root / "abs/../Парсер").absolute()
        config = load_config(
            self.write_config(
                f'grammar = "{grammar.as_posix()}"\n'
                f'target = "{target.as_posix()}"\n'
                "lookahead = 1\n"
                "[entrypoints]\n"
                '"Разобрать" = "S"\n'
            )
        )

        self.assertEqual(config.grammar, grammar.resolve())
        self.assertEqual(config.target, target.resolve())
        self.assertFalse(config.grammar.exists())
        self.assertFalse(config.target.exists())

    def test_rejects_missing_wrong_boolean_and_small_lookahead(self) -> None:
        cases = {
            "missing": "",
            "string": 'lookahead = "2"\n',
            "boolean": "lookahead = true\n",
            "zero": "lookahead = 0\n",
            "negative": "lookahead = -2\n",
        }
        for label, lookahead in cases.items():
            with self.subTest(label=label):
                path = self.write_config(
                    'grammar = "grammar.txt"\n'
                    'target = "Парсер"\n'
                    f"{lookahead}"
                    "[entrypoints]\n"
                    '"Разобрать" = "S"\n'
                )
                with self.assertRaisesRegex(ValueError, "lookahead"):
                    load_config(path)

    def test_rejects_missing_wrong_and_empty_entrypoints(self) -> None:
        cases = {
            "missing": "",
            "array": "entrypoints = []\n",
            "empty": "[entrypoints]\n",
            "empty-key": '[entrypoints]\n"" = "S"\n',
            "empty-value": '[entrypoints]\n"Разобрать" = ""\n',
            "non-string": '[entrypoints]\n"Разобрать" = 1\n',
        }
        for label, entrypoints in cases.items():
            with self.subTest(label=label):
                path = self.write_config(
                    'grammar = "grammar.txt"\n'
                    'target = "Парсер"\n'
                    "lookahead = 2\n"
                    f"{entrypoints}"
                )
                with self.assertRaisesRegex(ValueError, "entrypoints"):
                    load_config(path)

    def test_rejects_missing_wrong_and_empty_paths(self) -> None:
        cases = {
            "missing-grammar": (
                "",
                'target = "Парсер"\n',
                "grammar",
            ),
            "wrong-grammar": (
                "grammar = []\n",
                'target = "Парсер"\n',
                "grammar",
            ),
            "empty-grammar": (
                'grammar = "   "\n',
                'target = "Парсер"\n',
                "grammar",
            ),
            "missing-target": (
                'grammar = "grammar.txt"\n',
                "",
                "target",
            ),
            "wrong-target": (
                'grammar = "grammar.txt"\n',
                "target = 7\n",
                "target",
            ),
            "empty-target": (
                'grammar = "grammar.txt"\n',
                'target = ""\n',
                "target",
            ),
        }
        for label, (grammar, target, expected) in cases.items():
            with self.subTest(label=label):
                path = self.write_config(
                    f"{grammar}{target}"
                    "lookahead = 2\n"
                    "[entrypoints]\n"
                    '"Разобрать" = "S"\n'
                )
                with self.assertRaisesRegex(ValueError, expected):
                    load_config(path)

    def test_rejects_unexpected_top_level_keys(self) -> None:
        path = self.write_config(
            'grammar = "grammar.txt"\n'
            'target = "Парсер"\n'
            "lookahead = 2\n"
            'output = "elsewhere"\n'
            "[entrypoints]\n"
            '"Разобрать" = "S"\n'
        )

        with self.assertRaisesRegex(ValueError, "unexpected.*output"):
            load_config(path)


if __name__ == "__main__":
    unittest.main()
