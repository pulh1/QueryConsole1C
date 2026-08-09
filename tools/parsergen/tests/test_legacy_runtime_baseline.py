from importlib.util import module_from_spec, spec_from_file_location
import io
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = PACKAGE_ROOT / "benchmarks/legacy_runtime_baseline.py"
MODULE_NAME = "queryconsole_legacy_runtime_baseline_test"
SPEC = spec_from_file_location(MODULE_NAME, BASELINE_PATH)
assert SPEC is not None and SPEC.loader is not None
baseline = module_from_spec(SPEC)
MISSING_MODULE = object()
PREVIOUS_MODULE = sys.modules.get(MODULE_NAME, MISSING_MODULE)
sys.modules[MODULE_NAME] = baseline
try:
    SPEC.loader.exec_module(baseline)
finally:
    if PREVIOUS_MODULE is MISSING_MODULE:
        sys.modules.pop(MODULE_NAME, None)
    else:
        sys.modules[MODULE_NAME] = PREVIOUS_MODULE


def _make_sidecar(component: str) -> dict[str, object]:
    artifacts = [
        {
            "role": "lexer",
            "metadata_object": "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
            "path": "yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/ObjectModule.bsl",
            "sha256": "434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20",
            "hash_scope": "normalized_utf8_lf",
            "source_path": "QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl",
            "source_sha256": "434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20",
        },
    ]
    if component == "parser":
        artifacts = [
            {
                "role": "parser",
                "metadata_object": "DataProcessor.КОНС_СтарыйПарсер",
                "path": "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/ObjectModule.bsl",
                "sha256": "dc401e271105eb34b4b2234c75b13fcdfd0341bb3b6766507d9f8cb1eb62e8b7",
                "hash_scope": "normalized_utf8_lf",
                "source_path": "QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl",
                "source_sha256": "0c365e1e521322554b63e400379be47c0dc5ecaa7f60dd6951dc84bc7cccd084",
            },
            *artifacts,
            {
                "role": "legacy_model_factory",
                "metadata_object": "CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса",
                "path": "yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса/Module.bsl",
                "sha256": "62213fee493659cd38c8678db5cb25a1ec6e79d2075d5128d1a396c6cea9c313",
                "hash_scope": "normalized_utf8_lf",
                "source_path": "QueryConsoleZUP/src/CommonModules/ЭлементыМоделиЗапроса/Module.bsl",
                "source_sha256": "62213fee493659cd38c8678db5cb25a1ec6e79d2075d5128d1a396c6cea9c313",
            },
            {
                "role": "first_symbols_template",
                "metadata_object": "DataProcessor.КОНС_СтарыйПарсер.Template.ТаблицаПервыхСимволовВариантов",
                "path": "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
                "sha256": "4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed",
                "hash_scope": "original_bytes",
                "source_path": "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
                "source_sha256": "4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed",
            },
            {
                "role": "identifiers_template",
                "metadata_object": "DataProcessor.КОНС_СтарыйПарсер.Template.ОпределенияИдентификаторов",
                "path": "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/ОпределенияИдентификаторов/Template.txt",
                "sha256": "7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152",
                "hash_scope": "original_bytes",
                "source_path": "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt",
                "source_sha256": "7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152",
            },
        ]
    corpora = []
    for index, corpus_id in enumerate(baseline.EXPECTED_CORPUS_IDS):
        input_count = 42 if index == 0 else 1
        inputs = [
            {
                "id": f"input_{input_index}",
                "input_length": 1,
                "provenance": "unit test",
            }
            for input_index in range(input_count)
        ]
        corpus = {
            "id": corpus_id,
            "entrypoint": "Разобрать",
            "provenance": "unit test",
            "generator_parameters": {},
            "inputs": inputs,
            "input_count": input_count,
            "input_length": input_count,
            "operation_count_per_iteration": input_count,
            "operations_per_sample": input_count,
            "iterations_per_sample": 1,
            "warmup_count": 3,
            "sample_count": 20,
            "samples_ms": [1.0] * 20,
            "wall_clock_median_ms": 1.0,
            "wall_clock_p95_ms": 1.0,
        }
        if corpus_id == "time_accounting_large":
            manifest = {
                "metadata_object": "CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени",
                "path": "yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/Template.txt",
                "external_source_path": "C:\\work\\1C\\мои разработки\\Теория копмиляторов\\Генерация парсеров АКТУАЛЬНОЕ\\заппросы\\ДанныеУчетаВремени.txt",
                "raw_bytes": 289542,
                "line_count": 5489,
                "character_count": 160135,
                "raw_sha256": "43035fda34f0ccb05817d856374beba9e5539a3a99540fef9ba7d70d3656c93e",
                "normalized_utf8_lf_sha256": "5e4a617dd41f8af97434b797bac46c9f8ba3ca1d167db9d81828b6854f1fc9c5",
            }
            corpus["provenance"] = (
                "Permanent CommonTemplate time-accounting query imported from verified external source"
            )
            corpus["generator_parameters"] = dict(manifest)
            inputs[0]["id"] = "time_accounting_large_1"
            inputs[0]["input_length"] = 160135
            inputs[0]["provenance"] = {
                "type": "common_template_text_document",
                **manifest,
            }
            corpus["input_length"] = 160135
        if component == "lexer":
            corpus["token_count"] = input_count
            corpus["token_reads_per_iteration"] = input_count * 2
            for item in inputs:
                item["token_count"] = 1
        else:
            corpus["parse_calls_per_sample"] = input_count
        corpora.append(corpus)
    document = {
        "schema_version": 2,
        "benchmark_id": f"runtime-old-{component}-baseline",
        "component": component,
        "measurement_scope": (
            "Полная токенизация: установка текста и чтение содержательных и конечного токена"
            if component == "lexer"
            else "Разобрать/РазобратьВыражение вместе с внутренней токенизацией; создание parser object вне sample"
        ),
        "implementation_id": f"old-{component}-59d538f",
        "source_ref": "origin/old_parser",
        "source_commit": baseline.EXPECTED_COMMIT,
        "metadata_object_names": (
            ["DataProcessor.КОНС_СтарыйЛексическийАнализатор"]
            if component == "lexer"
            else [
                "DataProcessor.КОНС_СтарыйПарсер",
                "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
                "CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса",
            ]
        ),
        "artifacts": artifacts,
        "warmup_count": 3,
        "sample_count": 20,
        "batch_calibration_target_ms": 25,
        "clock": "ТекущаяУниверсальнаяДатаВМиллисекундах",
        "clock_resolution_ms": 1,
        "captured_at_platform_ms": 1,
        "runtime": {"execution_context": "YAxUnit server test"},
        "internal_counters": {},
        "corpora": corpora,
    }
    if component == "parser":
        document["parser_artifact"] = artifacts[0]
    return document


class LegacyRuntimeBaselineTests(unittest.TestCase):
    def test_bsl_harness_registers_old_and_current_modes(self) -> None:
        text = baseline.BENCHMARK_MODULE.read_text(encoding="utf-8")
        for test_name in (
            "RuntimeBaselineСтарогоЛексераФормируется",
            "RuntimeBaselineСтарогоПарсераФормируется",
            "RuntimeBaselineЛексераФормируется",
            "RuntimeBaselineПарсераФормируется",
        ):
            self.assertIn(f'ДобавитьСерверныйТест("{test_name}")', text)
        self.assertIn("Функция ВыполнитьБенчмарк(ОписаниеРеализации)", text)
        self.assertIn('Токен.Тип = Неопределено', text)
        self.assertIn(
            'ПолучитьОбщийМакет("КОНС_БенчмаркДанныеУчетаВремени").ПолучитьТекст()',
            text,
        )
        self.assertIn('"time_accounting_large", "Разобрать"', text)
        self.assertIn(
            '"current_model_factory", "CommonModule.ЭлементыМоделиЗапроса"',
            text,
        )
        self.assertEqual(
            text.count(
                'ПолучитьОбщийМакет("КОНС_БенчмаркДанныеУчетаВремени").ПолучитьТекст()'
            ),
            1,
        )
        self.assertNotIn("Метаданные.НайтиПоТипу", text)

    def test_current_parser_benchmark_pins_decision_dag_artifact(self) -> None:
        text = baseline.BENCHMARK_MODULE.read_text(encoding="utf-8")
        self.assertIn(
            '"f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf", "normalized_utf8_lf"',
            text,
        )
        self.assertIn(
            'Возврат НовоеОписаниеРеализации("current-parser-5a054c2", "parser", Парсер,',
            text,
        )
        self.assertIn(
            '"feature/parser-lexer-optimization", "5a054c2d69d46ee261553c3c9ea696f89e65bb23"',
            text,
        )
        self.assertIn(
            '"runtime-parser-decision-dag.json", "runtime-parser-decision-dag"',
            text,
        )

    def test_time_accounting_corpus_manifest_is_strict(self) -> None:
        self.assertEqual(
            baseline.EXPECTED_CORPUS_IDS[-1],
            "time_accounting_large",
        )
        self.assertEqual(len(baseline.EXPECTED_CORPUS_IDS), 9)
        self.assertEqual(
            baseline.EXPECTED_TIME_ACCOUNTING_LARGE["raw_sha256"],
            "43035fda34f0ccb05817d856374beba9e5539a3a99540fef9ba7d70d3656c93e",
        )
        self.assertEqual(
            baseline.EXPECTED_TIME_ACCOUNTING_LARGE["character_count"],
            160135,
        )

    def test_sidecar_rejects_time_accounting_manifest_drift(self) -> None:
        for component in ("lexer", "parser"):
            with self.subTest(component=component):
                sidecar = _make_sidecar(component)
                sidecar["corpora"][-1]["generator_parameters"]["raw_sha256"] = "0" * 64
                with self.assertRaisesRegex(ValueError, "time_accounting_large"):
                    baseline.validate_sidecar(sidecar, component)

    def test_dynamic_loader_imports_dataclass_and_restores_sys_modules(self) -> None:
        if PREVIOUS_MODULE is MISSING_MODULE:
            self.assertNotIn(MODULE_NAME, sys.modules)
        else:
            self.assertIs(sys.modules.get(MODULE_NAME), PREVIOUS_MODULE)
        self.assertEqual(baseline.ArtifactSpec.__module__, MODULE_NAME)
        self.assertEqual(
            baseline.ARTIFACTS["lexer_module"].hash_scope,
            "normalized_utf8_lf",
        )

    def test_manifest_is_pinned_to_approved_commit_and_hashes(self) -> None:
        self.assertEqual(
            baseline.EXPECTED_COMMIT,
            "59d538fd974c723c6b1cf336c61b0fea1aec8453",
        )
        self.assertEqual(
            baseline.ARTIFACTS["lexer_module"].source_sha256,
            "434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20",
        )
        self.assertEqual(
            baseline.ARTIFACTS["parser_module"].materialized_sha256,
            "dc401e271105eb34b4b2234c75b13fcdfd0341bb3b6766507d9f8cb1eb62e8b7",
        )

    def test_parser_adaptation_requires_exact_dependency_renames(self) -> None:
        source = (
            b"A\r\n" + baseline.PRODUCTION_LEXER_FACTORY.encode() + b"\r\n"
            + b"\r\n".join(
                baseline.PRODUCTION_MODEL_FACTORY_PREFIX.encode() + "Экспорт()".encode()
                for _ in range(102)
            )
        )
        adapted = baseline.adapt_parser_source(source)
        self.assertNotIn(baseline.PRODUCTION_LEXER_FACTORY, adapted.decode())
        self.assertEqual(adapted.decode().count(baseline.OLD_LEXER_FACTORY), 1)
        self.assertEqual(adapted.decode().count(baseline.OLD_MODEL_FACTORY_PREFIX), 102)
        with self.assertRaisesRegex(ValueError, "102"):
            baseline.adapt_parser_source(baseline.PRODUCTION_LEXER_FACTORY.encode())

    def test_lexer_materialization_preserves_historical_bytes(self) -> None:
        source = b"A\r\nB\r\n"
        self.assertEqual(
            baseline._materialized_bytes("lexer_module", source),
            source,
        )

    def test_lexer_sidecar_requires_token_counts_and_twenty_samples(self) -> None:
        sidecar = _make_sidecar("lexer")
        baseline.validate_sidecar(sidecar, "lexer")
        del sidecar["corpora"][0]["token_count"]
        with self.assertRaisesRegex(ValueError, "token_count"):
            baseline.validate_sidecar(sidecar, "lexer")

    def test_parser_sidecar_requires_parser_lexer_and_legacy_factory_artifacts(self) -> None:
        sidecar = _make_sidecar("parser")
        sidecar["artifacts"] = [sidecar["artifacts"][0]]
        with self.assertRaisesRegex(ValueError, "artifact row count"):
            baseline.validate_sidecar(sidecar, "parser")

    def test_every_artifact_provenance_field_is_exact_for_every_role(self) -> None:
        cases = (
            ("lexer", 0, "lexer"),
            ("parser", 0, "parser"),
            ("parser", 1, "lexer"),
            ("parser", 2, "legacy_model_factory"),
            ("parser", 3, "first_symbols_template"),
            ("parser", 4, "identifiers_template"),
        )
        replacements = {
            "role": "wrong_role",
            "metadata_object": "DataProcessor.Wrong",
            "path": "wrong/target/path",
            "sha256": "0" * 64,
            "hash_scope": "wrong_scope",
            "source_path": "wrong/source/path",
            "source_sha256": "f" * 64,
        }
        for component, index, role in cases:
            for field, replacement in replacements.items():
                with self.subTest(component=component, role=role, field=field):
                    sidecar = _make_sidecar(component)
                    sidecar["artifacts"][index][field] = replacement
                    with self.assertRaisesRegex(
                        ValueError,
                        rf"{component}\.artifacts\[{index}\]\.{field}",
                    ):
                        baseline.validate_sidecar(sidecar, component)

    def test_artifact_row_rejects_extra_field(self) -> None:
        sidecar = _make_sidecar("parser")
        sidecar["artifacts"][2]["unapproved"] = True
        with self.assertRaisesRegex(ValueError, r"parser\.artifacts\[2\] field set"):
            baseline.validate_sidecar(sidecar, "parser")

    def test_sidecar_identity_fields_are_exact(self) -> None:
        replacements = {
            "schema_version": 1,
            "benchmark_id": "runtime-old-parser-baseline-copy",
            "component": "lexer",
            "measurement_scope": "parser",
            "implementation_id": "old-parser",
            "metadata_object_names": ["DataProcessor.КОНС_СтарыйПарсер"],
            "clock": "another clock",
        }
        for field, value in replacements.items():
            with self.subTest(field=field):
                sidecar = _make_sidecar("parser")
                sidecar[field] = value
                with self.assertRaisesRegex(ValueError, field):
                    baseline.validate_sidecar(sidecar, "parser")

    def test_sidecar_rejects_non_sequence_metadata_object_names(self) -> None:
        sidecar = _make_sidecar("lexer")
        sidecar["metadata_object_names"] = 1
        with self.assertRaisesRegex(ValueError, "metadata_object_names"):
            baseline.validate_sidecar(sidecar, "lexer")

    def test_lexer_sidecar_rejects_an_extra_top_level_field(self) -> None:
        sidecar = _make_sidecar("lexer")
        sidecar["unapproved_top_level"] = True
        with self.assertRaisesRegex(ValueError, "top-level field set"):
            baseline.validate_sidecar(sidecar, "lexer")

    def test_parser_sidecar_rejects_an_extra_top_level_field(self) -> None:
        sidecar = _make_sidecar("parser")
        sidecar["unapproved_top_level"] = True
        with self.assertRaisesRegex(ValueError, "top-level field set"):
            baseline.validate_sidecar(sidecar, "parser")

    def test_validate_durable_cli_returns_three_for_extra_top_level_field(self) -> None:
        lexer = _make_sidecar("lexer")
        lexer["unapproved_top_level"] = True
        parser = _make_sidecar("parser")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lexer_path = root / "lexer.json"
            parser_path = root / "parser.json"
            report_path = root / "report.md"
            lexer_bytes = json.dumps(lexer, ensure_ascii=False).encode("utf-8")
            parser_bytes = json.dumps(parser, ensure_ascii=False).encode("utf-8")
            lexer_path.write_bytes(lexer_bytes)
            parser_path.write_bytes(parser_bytes)
            report_path.write_text(
                baseline.render_markdown(
                    lexer,
                    parser,
                    hashlib.sha256(lexer_bytes).hexdigest(),
                    hashlib.sha256(parser_bytes).hexdigest(),
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BASELINE_PATH),
                    "validate-durable",
                    "--lexer",
                    str(lexer_path),
                    "--parser",
                    str(parser_path),
                    "--report",
                    str(report_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertIn("top-level field set", completed.stderr)

    def test_capture_commands_return_two_for_materialization_error(self) -> None:
        commands = (
            (
                "validate-sidecars",
                [
                    "validate-sidecars",
                    "--repo",
                    ".",
                    "--lexer",
                    "lexer.json",
                    "--parser",
                    "parser.json",
                ],
            ),
            (
                "publish",
                [
                    "publish",
                    "--repo",
                    ".",
                    "--lexer",
                    "lexer.json",
                    "--parser",
                    "parser.json",
                    "--output-dir",
                    "output",
                ],
            ),
        )
        for command, arguments in commands:
            with self.subTest(command=command):
                stderr = io.StringIO()
                with (
                    patch.object(
                        baseline,
                        "verify_materialized_sources",
                        side_effect=ValueError("materialized parser SHA-256 mismatch"),
                    ),
                    patch.object(baseline.sys, "stderr", stderr),
                ):
                    exit_code = baseline.main(arguments)
                self.assertEqual(exit_code, 2)
                self.assertIn("materialized parser SHA-256 mismatch", stderr.getvalue())

    def test_json_output_supports_a_text_only_stdout(self) -> None:
        output = io.StringIO()
        with patch.object(baseline.sys, "stdout", output):
            baseline._write_json({"тест": "значение"})
        self.assertEqual(json.loads(output.getvalue()), {"тест": "значение"})

    def test_sidecar_loader_accepts_utf8_bom_emitted_by_1c(self) -> None:
        sidecar = _make_sidecar("lexer")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lexer.json"
            path.write_bytes(
                b"\xef\xbb\xbf"
                + json.dumps(sidecar, ensure_ascii=False).encode("utf-8")
            )
            loaded = baseline._load_sidecar(path)
        self.assertEqual(loaded, sidecar)

    def test_parser_artifact_alias_equals_parser_role_artifact(self) -> None:
        sidecar = _make_sidecar("parser")
        sidecar["parser_artifact"] = dict(sidecar["parser_artifact"])
        sidecar["parser_artifact"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "parser_artifact"):
            baseline.validate_sidecar(sidecar, "parser")

    def test_validate_durable_does_not_read_deleted_target_sources(self) -> None:
        lexer = _make_sidecar("lexer")
        parser = _make_sidecar("parser")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lexer_path = root / "lexer.json"
            parser_path = root / "parser.json"
            report_path = root / "report.md"
            lexer_bytes = json.dumps(lexer, ensure_ascii=False).encode("utf-8")
            parser_bytes = json.dumps(parser, ensure_ascii=False).encode("utf-8")
            lexer_path.write_bytes(lexer_bytes)
            parser_path.write_bytes(parser_bytes)
            report_path.write_text(
                baseline.render_markdown(
                    lexer,
                    parser,
                    hashlib.sha256(lexer_bytes).hexdigest(),
                    hashlib.sha256(parser_bytes).hexdigest(),
                ),
                encoding="utf-8",
            )
            with patch.object(
                baseline,
                "verify_materialized_sources",
                side_effect=AssertionError("durable validation read target sources"),
            ):
                baseline.validate_durable(lexer_path, parser_path, report_path)

    def test_validate_durable_reuses_strict_artifact_row_validator(self) -> None:
        lexer = _make_sidecar("lexer")
        parser = _make_sidecar("parser")
        parser["artifacts"][4]["source_path"] = "wrong/source/path"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lexer_path = root / "lexer.json"
            parser_path = root / "parser.json"
            report_path = root / "report.md"
            lexer_bytes = json.dumps(lexer, ensure_ascii=False).encode("utf-8")
            parser_bytes = json.dumps(parser, ensure_ascii=False).encode("utf-8")
            lexer_path.write_bytes(lexer_bytes)
            parser_path.write_bytes(parser_bytes)
            report_path.write_text(
                baseline.render_markdown(
                    lexer,
                    parser,
                    hashlib.sha256(lexer_bytes).hexdigest(),
                    hashlib.sha256(parser_bytes).hexdigest(),
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                r"parser\.artifacts\[4\]\.source_path",
            ):
                baseline.validate_durable(lexer_path, parser_path, report_path)
