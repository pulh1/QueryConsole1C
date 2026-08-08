# Legacy Parser/Lexer Benchmark Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Подключить в `yaxunit` проверенные исторические lexer/parser и factory `ЭлементыМоделиЗапроса` из `origin/old_parser`, постоянный TextDocument с большим запросом учёта времени, снять раздельные воспроизводимые wall-clock baseline и опубликовать два JSON и один Markdown-отчёт с доказуемым provenance.

**Architecture:** Исторические BSL, self-contained factory и два parser template материализуются из фиксированного Git commit в EDT-созданные test-only metadata objects. Независимый постоянный TextDocument импортирует большой запрос учёта времени с фиксированным byte/text manifest; harness читает его до preflight и измерений. Parser получает только две статические адаптации имён зависимостей: один lexer factory call и 102 вызова legacy model factory; wrapper и dynamic dispatch в измеряемый путь не добавляются. Существующий `КОНС_Обр_БенчмаркПарсера_МО` становится общим descriptor-driven harness для режимов `lexer` и `parser`, а Python CLI доказывает ref/source bytes, обе прямые и обратные адаптации, corpus manifest, sidecar и durable evidence.

**Tech Stack:** Python 3.11+, стандартная библиотека, pytest 8+, Git object database, EDT 2026.1/EDT-MCP, 1С:Предприятие 8.3.24, русский BSL UTF-8, YAxUnit 25.12, JSON и Markdown.

## Global Constraints

- Source ref: `origin/old_parser`; expected full commit: `59d538fd974c723c6b1cf336c61b0fea1aec8453`.
- `КОНС_СтарыйЛексическийАнализатор/ObjectModule.bsl` должен быть функционально и после UTF-8/LF-нормализации побайтно эквивалентен историческому lexer source.
- В old parser разрешены только две механические адаптации: ровно одна замена `Обработки.ЛексическийАнализатор.Создать()` на `Обработки.КОНС_СтарыйЛексическийАнализатор.Создать()` и ровно 102 статических замены `ЭлементыМоделиЗапроса.` на `КОНС_СтарыеЭлементыМоделиЗапроса.`; других compatibility-правок нет.
- `КОНС_СтарыеЭлементыМоделиЗапроса/Module.bsl` после UTF-8/LF-нормализации побайтно эквивалентен historical factory source; его historical runtime flags — `clientManagedApplication`, `server`, `externalConnection`, `clientOrdinaryApplication` = `true`, `global` = `false`.
- Оба parser template переносятся как исходные bytes из commit `59d538f`; их metadata template type — `TextDocument`.
- Production `QueryConsoleZUP/src/**`, grammar, Parser IR, query model и downstream consumers не изменяются.
- Corpus содержит ровно девять классов: восемь существующих, включая все 42 embedded `QueryExamples`, и девятый `time_accounting_large` из постоянного `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени` (один input, `Разобрать`).
- Внешний import source — `C:\work\1C\мои разработки\Теория копмиляторов\Генерация парсеров АКТУАЛЬНОЕ\заппросы\ДанныеУчетаВремени.txt`; до копирования доказать: raw `289542` bytes, `5489` lines, `160135` chars, raw SHA-256 `43035fda34f0ccb05817d856374beba9e5539a3a99540fef9ba7d70d3656c93e`, normalized UTF-8/LF SHA-256 `5e4a617dd41f8af97434b797bac46c9f8ba3ca1d167db9d81828b6854f1fc9c5`.
- Постоянный template загружается ровно через `ПолучитьОбщийМакет("КОНС_БенчмаркДанныеУчетаВремени").ПолучитьТекст()` при построении corpus; получение текста не входит в preflight, calibration, warm-ups или samples.
- Для каждого component/corpus: preflight до измерения, batch calibration до 25 ms, 3 прогрева, 20 samples, median и nearest-rank p95.
- Один заранее созданный runtime object повторно используется для preflight, calibration, warm-ups и samples внутри запуска реализации; создание объекта не входит в sample.
- Lexer sample включает `УстановитьОбрабатываемыйТекст` и чтение всех содержательных токенов вместе с конечным токеном `Токен.Тип = Неопределено`.
- Parser sample вызывает исходную corpus entrypoint `Разобрать` или `РазобратьВыражение` и тем самым включает токенизацию.
- Ошибка preflight обязана включать component, implementation id, corpus id и input id; входы не пропускаются, corpus не сокращается, fallback не выполняется.
- Performance threshold и verdict не вводятся.
- Durable JSON и Markdown создаются только после двух успешных фактических YAxUnit runs; JSON копируются без изменения bytes.
- Каждый YAxUnit launch использует `updateBeforeLaunch=true` и `updateScope="extension:yaxunit"`; нулевой test count, skipped corpus, failure или отсутствие sidecar блокируют публикацию.
- Ручной runtime gate закрыт: непосредственно перед каждым timing-run исполнитель сообщает готовность, перечисляет подготовленные проверки и ждёт свежего явного подтверждения, что тяжёлые процессы остановлены. До такого подтверждения разрешены только metadata/provenance/functional preflight проверки, но не benchmark registrations с timing sidecar.
- Перед EDT write `list_projects` обязан показать, что project `yaxunit` указывает на каталог `yaxunit` текущего execution checkout. Если EDT всё ещё указывает на основной checkout, EDT write запрещён до явного переключения workspace; непроверенная команда переключения в этот план не вводится.
- Ветка Decision DAG после `17c105d` на момент планирования не меняет `yaxunit/**` или production lexer/parser. Перед исполнением повторить `git diff --name-status 17c105d..feature/parser-lexer-optimization`; при новом пересечении с benchmark-модулем сначала объединить descriptor/runtime contracts, не перезаписывая изменения другой ветки.

---

## File Structure

- Create: `tools/parsergen/benchmarks/legacy_runtime_baseline.py` — единственный CLI для ref verification, извлечения historical blobs, source verification, capture-time sidecar validation, post-cleanup durable validation и evidence publication.
- Create: `tools/parsergen/tests/test_legacy_runtime_baseline.py` — unit/contract tests CLI, hashes, schema, Markdown и статического BSL harness contract.
- Create through EDT-MCP: `yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса/КОНС_СтарыеЭлементыМоделиЗапроса.mdo` — test-only non-global common module с новым EDT UUID и историческими runtime flags.
- Create from verified Git blob: `yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса/Module.bsl` — полный historical factory source без правок.
- Create through EDT-MCP: `yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/КОНС_СтарыйЛексическийАнализатор.mdo` — test-only metadata с новым EDT UUID.
- Create from verified Git blob: `yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/ObjectModule.bsl` — historical lexer source без правок.
- Create through EDT-MCP: `yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/КОНС_СтарыйПарсер.mdo` — test-only parser metadata с двумя TextDocument templates и новым EDT UUID.
- Create from verified Git blob: `yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/ObjectModule.bsl` — historical parser source с одной lexer-factory и 102 model-factory статическими заменами.
- Create from verified Git blobs: `yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt` and `yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/ОпределенияИдентификаторов/Template.txt` — exact historical bytes.
- Create through EDT-MCP: `yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/КОНС_БенчмаркДанныеУчетаВремени.mdo` — permanent `TextDocument` corpus template with a fresh EDT UUID.
- Create by byte-preserving copy after EDT creation: `yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/Template.txt` — the verified external time-accounting query bytes.
- Modify through EDT-MCP: `yaxunit/src/Configuration/Configuration.mdo` — EDT-managed registration трёх временных metadata objects and one permanent common template.
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl` — implementation descriptors, two modes, preflight, shared measurement/statistics, four explicit registrations и sidecar names.
- Modify: `yaxunit/UPSTREAM.md` — перечисление permanent benchmark module и permanent corpus template, затем трёх временных project-local metadata objects; cleanup удалит только временные строки.
- Create only from successful runtime sidecars: `docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json`.
- Create only from successful runtime sidecars: `docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json`.
- Create only from those two JSON: `docs/superpowers/matrices/2026-08-08-runtime-old-lexer-parser-baseline.md`.

## Execution Waves

- **Wave A — Provenance RED/GREEN:** Task 1; review one complete CLI/test unit.
- **Wave B — Historical objects RED/GREEN:** Task 2; review EDT metadata, extracted sources and provenance together.
- **Wave C — Harness RED/GREEN:** Task 3 plus Task 4 gate; review descriptor, preflight, measurement and current-regression evidence together.
- **Wave D — Runtime evidence RED/GREEN:** Task 5; review only after both actual sidecars and durable artifacts exist.
- **Later cleanup wave:** Task 6 runs after optimizations and before MR; it is intentionally not part of baseline capture.

### Task 1: Build the provenance/materialization/evidence CLI

**Execution status:** исходная lexer/parser-версия CLI уже закоммичена в Wave A (`e8ffa1e` в baseline worktree, cherry-pick `17dca9f` в основной ветке). Эта задача повторно открыта как TDD-расширение для legacy factory; существующие строгие schema checks сохраняются.

**Files:**
- Modify: `tools/parsergen/benchmarks/legacy_runtime_baseline.py`
- Modify: `tools/parsergen/tests/test_legacy_runtime_baseline.py`

**Interfaces:**
- Consumes: repository root, local `refs/remotes/origin/old_parser`, remote `refs/heads/old_parser`, exact Git blobs and completed YAxUnit sidecars.
- Produces commands `verify-ref`, `materialize`, `verify-source`, `current-hashes`, `validate-sidecars`, `publish`, and `validate-durable`.
- Produces pure/effect-separated functions `verify_materialized_sources(repo)`, `validate_artifact_rows(artifacts, component)`, `validate_sidecar(document, component)`, `render_markdown(lexer_document, parser_document, lexer_json_sha256, parser_json_sha256)`, and `validate_durable(lexer_path, parser_path, report_path)`.
- Produces normalized source SHA-256 values and raw template SHA-256 values shown below.
- Exit codes: `0` success, `2` provenance/materialization mismatch, `3` sidecar/evidence validation failure.

Approved manifest:

| Artifact | Historical SHA-256 | Materialized SHA-256 | Hash scope |
|---|---|---|---|
| lexer module | `434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20` | same | UTF-8 text with CRLF/CR normalized to LF, no BOM added |
| legacy model factory module | `62213fee493659cd38c8678db5cb25a1ec6e79d2075d5128d1a396c6cea9c313` | same | UTF-8 text with CRLF/CR normalized to LF, no BOM added |
| parser module | `0c365e1e521322554b63e400379be47c0dc5ecaa7f60dd6951dc84bc7cccd084` | `dc401e271105eb34b4b2234c75b13fcdfd0341bb3b6766507d9f8cb1eb62e8b7` | same normalization; materialized hash includes one lexer-factory and exactly 102 model-factory prefix replacements |
| `ТаблицаПервыхСимволовВариантов` | `4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed` | same | original bytes, 1,263,239 bytes |
| `ОпределенияИдентификаторов` | `7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152` | same | original bytes, 18,172 bytes |

- [ ] **Step 1: Write failing manifest, normalization, replacement and sidecar tests**

Use the repository's existing `spec_from_file_location` convention, but register the dynamic module before `exec_module`; `@dataclass(frozen=True, slots=True)` resolves its module through `sys.modules` during import. Restore any previous entry after `exec_module` completes and also on import failure; use a sentinel so a pre-existing `None` entry is restored rather than mistaken for absence:

```python
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import hashlib
import json
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
                baseline.PRODUCTION_MODEL_FACTORY_PREFIX.encode() + b"Экспорт()"
                for _ in range(102)
            )
        )
        adapted = baseline.adapt_parser_source(source)
        self.assertNotIn(baseline.PRODUCTION_LEXER_FACTORY, adapted.decode())
        self.assertEqual(adapted.decode().count(baseline.OLD_LEXER_FACTORY), 1)
        self.assertEqual(adapted.decode().count(baseline.OLD_MODEL_FACTORY_PREFIX), 102)
        with self.assertRaisesRegex(ValueError, "102"):
            baseline.adapt_parser_source(b"no factory here")

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
        parser["artifacts"][3]["source_path"] = "wrong/source/path"
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
```

This importability test is part of the RED/GREEN contract: after the CLI file first exists, the test module must still import and instantiate the slotted dataclass through this dynamic loader; a loader that calls `exec_module` before `sys.modules[MODULE_NAME] = baseline` fails during test collection and is not GREEN.

- [ ] **Step 2: Run the focused tests and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_legacy_runtime_baseline.py -v
```

Expected: FAIL because existing CLI does not yet define the legacy-factory artifact, the 102-prefix adaptation contract or the expanded parser sidecar schema.

- [ ] **Step 3: Implement exact Git, normalization and adaptation primitives**

Use argument arrays, binary stdout and atomic target replacement; never invoke a shell for Git:

```python
import re

EXPECTED_REF = "refs/remotes/origin/old_parser"
EXPECTED_REMOTE_REF = "refs/heads/old_parser"
EXPECTED_COMMIT = "59d538fd974c723c6b1cf336c61b0fea1aec8453"
PRODUCTION_LEXER_FACTORY = "Обработки.ЛексическийАнализатор.Создать()"
OLD_LEXER_FACTORY = "Обработки.КОНС_СтарыйЛексическийАнализатор.Создать()"
PRODUCTION_MODEL_FACTORY_PREFIX = "ЭлементыМоделиЗапроса."
OLD_MODEL_FACTORY_PREFIX = "КОНС_СтарыеЭлементыМоделиЗапроса."
MODEL_FACTORY_REPLACEMENT_COUNT = 102
BENCHMARK_MODULE = (
    Path(__file__).resolve().parents[3]
    / "yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl"
)


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    source_path: str
    target_path: str
    source_sha256: str
    materialized_sha256: str
    hash_scope: str


ARTIFACTS = {
    "lexer_module": ArtifactSpec(
        "QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl",
        "yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/ObjectModule.bsl",
        "434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20",
        "434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20",
        "normalized_utf8_lf",
    ),
    "legacy_model_factory_module": ArtifactSpec(
        "QueryConsoleZUP/src/CommonModules/ЭлементыМоделиЗапроса/Module.bsl",
        "yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса/Module.bsl",
        "62213fee493659cd38c8678db5cb25a1ec6e79d2075d5128d1a396c6cea9c313",
        "62213fee493659cd38c8678db5cb25a1ec6e79d2075d5128d1a396c6cea9c313",
        "normalized_utf8_lf",
    ),
    "parser_module": ArtifactSpec(
        "QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl",
        "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/ObjectModule.bsl",
        "0c365e1e521322554b63e400379be47c0dc5ecaa7f60dd6951dc84bc7cccd084",
        "dc401e271105eb34b4b2234c75b13fcdfd0341bb3b6766507d9f8cb1eb62e8b7",
        "normalized_utf8_lf",
    ),
    "first_symbols_template": ArtifactSpec(
        "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
        "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
        "4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed",
        "4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed",
        "original_bytes",
    ),
    "identifiers_template": ArtifactSpec(
        "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt",
        "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/ОпределенияИдентификаторов/Template.txt",
        "7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152",
        "7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152",
        "original_bytes",
    ),
}


def git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def normalize_bsl(source: bytes) -> bytes:
    text = source.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def adapt_parser_source(source: bytes) -> bytes:
    text = normalize_bsl(source).decode("utf-8")
    if text.count(PRODUCTION_LEXER_FACTORY) != 1:
        raise ValueError("historical parser must contain exactly one production lexer factory")
    if qualified_factory_prefix_count(text, PRODUCTION_MODEL_FACTORY_PREFIX) != MODEL_FACTORY_REPLACEMENT_COUNT:
        raise ValueError("historical parser must contain exactly 102 production model-factory prefixes")
    return (
        text.replace(PRODUCTION_LEXER_FACTORY, OLD_LEXER_FACTORY)
        .replace(PRODUCTION_MODEL_FACTORY_PREFIX, OLD_MODEL_FACTORY_PREFIX)
        .encode("utf-8")
    )


def qualified_factory_prefix_count(text: str, prefix: str) -> int:
    pattern = rf"(?<![0-9A-Za-zА-Яа-я_]){re.escape(prefix)}"
    return len(re.findall(pattern, text))


def reverse_parser_adaptation(source: bytes) -> bytes:
    text = normalize_bsl(source).decode("utf-8")
    if text.count(OLD_LEXER_FACTORY) != 1:
        raise ValueError("materialized parser must contain exactly one old lexer factory")
    if qualified_factory_prefix_count(text, PRODUCTION_MODEL_FACTORY_PREFIX) != 0:
        raise ValueError("materialized parser still contains a production model-factory prefix")
    if qualified_factory_prefix_count(text, OLD_MODEL_FACTORY_PREFIX) != MODEL_FACTORY_REPLACEMENT_COUNT:
        raise ValueError("materialized parser must contain exactly 102 legacy model-factory prefixes")
    restored = (
        text.replace(OLD_LEXER_FACTORY, PRODUCTION_LEXER_FACTORY)
        .replace(OLD_MODEL_FACTORY_PREFIX, PRODUCTION_MODEL_FACTORY_PREFIX)
    )
    if qualified_factory_prefix_count(restored, PRODUCTION_MODEL_FACTORY_PREFIX) != MODEL_FACTORY_REPLACEMENT_COUNT:
        raise ValueError("reverse parser adaptation lost production model-factory prefixes")
    return restored.encode("utf-8")
```

`verify-ref` must compare both commands without fetching or updating refs:

```python
local_commit = git_bytes(repo, "rev-parse", EXPECTED_REF).decode().strip()
remote_rows = git_bytes(repo, "ls-remote", "--exit-code", "origin", EXPECTED_REMOTE_REF)
remote_commit = remote_rows.decode().split()[0]
if local_commit != EXPECTED_COMMIT or remote_commit != EXPECTED_COMMIT:
    raise ValueError(
        f"old_parser ref mismatch: local={local_commit} remote={remote_commit} expected={EXPECTED_COMMIT}"
    )
```

`materialize --target-dir build/legacy-runtime-baseline-source` writes lexer and legacy factory bytes unchanged, parser bytes through `adapt_parser_source`, and both template blobs unchanged into ignored staging storage. It refuses to write until `verify-ref` succeeds and reports all five resulting hashes. `current-hashes` reads the production lexer, parser and `ЭлементыМоделиЗапроса` BSL files from the working tree, applies `normalize_bsl`, and reports all three hashes without changing files.

- [ ] **Step 4: Implement strict sidecar validation and byte-preserving publication**

`validate_sidecar(document, component)` must require:

```python
REQUIRED_TOP_LEVEL = {
    "schema_version",
    "benchmark_id",
    "component",
    "measurement_scope",
    "implementation_id",
    "source_ref",
    "source_commit",
    "metadata_object_names",
    "artifacts",
    "warmup_count",
    "sample_count",
    "batch_calibration_target_ms",
    "clock",
    "clock_resolution_ms",
    "captured_at_platform_ms",
    "runtime",
    "internal_counters",
    "corpora",
}
REQUIRED_CORPUS_FIELDS = {
    "id",
    "entrypoint",
    "provenance",
    "generator_parameters",
    "inputs",
    "input_count",
    "input_length",
    "operation_count_per_iteration",
    "operations_per_sample",
    "iterations_per_sample",
    "warmup_count",
    "sample_count",
    "samples_ms",
    "wall_clock_median_ms",
    "wall_clock_p95_ms",
}
EXPECTED_CORPUS_IDS = (
    "query_examples_all_42",
    "large_package",
    "long_field_list",
    "join_chain",
    "union_package_chain",
    "arithmetic_chain",
    "logical_chain",
    "dereference_chain",
    "time_accounting_large",
)
EXPECTED_TIME_ACCOUNTING_LARGE = {
    "metadata_object": "CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени",
    "path": "yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/Template.txt",
    "external_source_path": (
        r"C:\work\1C\мои разработки\Теория копмиляторов\"
        r"Генерация парсеров АКТУАЛЬНОЕ\заппросы\ДанныеУчетаВремени.txt"
    ),
    "raw_bytes": 289542,
    "line_count": 5489,
    "character_count": 160135,
    "raw_sha256": "43035fda34f0ccb05817d856374beba9e5539a3a99540fef9ba7d70d3656c93e",
    "normalized_utf8_lf_sha256": "5e4a617dd41f8af97434b797bac46c9f8ba3ca1d167db9d81828b6854f1fc9c5",
}
EXPECTED_CLOCK = "ТекущаяУниверсальнаяДатаВМиллисекундах"
EXPECTED_ARTIFACT_FIELDS = (
    "role",
    "metadata_object",
    "path",
    "sha256",
    "hash_scope",
    "source_path",
    "source_sha256",
)
OLD_LEXER_ARTIFACT = {
    "role": "lexer",
    "metadata_object": "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
    "path": "yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/ObjectModule.bsl",
    "sha256": "434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20",
    "hash_scope": "normalized_utf8_lf",
    "source_path": "QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl",
    "source_sha256": "434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20",
}
EXPECTED_ARTIFACTS = {
    "lexer": (OLD_LEXER_ARTIFACT,),
    "parser": (
        {
            "role": "parser",
            "metadata_object": "DataProcessor.КОНС_СтарыйПарсер",
            "path": "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/ObjectModule.bsl",
            "sha256": "dc401e271105eb34b4b2234c75b13fcdfd0341bb3b6766507d9f8cb1eb62e8b7",
            "hash_scope": "normalized_utf8_lf",
            "source_path": "QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl",
            "source_sha256": "0c365e1e521322554b63e400379be47c0dc5ecaa7f60dd6951dc84bc7cccd084",
        },
        OLD_LEXER_ARTIFACT,
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
            "metadata_object": (
                "DataProcessor.КОНС_СтарыйПарсер.Template."
                "ТаблицаПервыхСимволовВариантов"
            ),
            "path": (
                "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/"
                "ТаблицаПервыхСимволовВариантов/Template.txt"
            ),
            "sha256": "4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed",
            "hash_scope": "original_bytes",
            "source_path": (
                "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/"
                "ТаблицаПервыхСимволовВариантов/Template.txt"
            ),
            "source_sha256": "4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed",
        },
        {
            "role": "identifiers_template",
            "metadata_object": (
                "DataProcessor.КОНС_СтарыйПарсер.Template."
                "ОпределенияИдентификаторов"
            ),
            "path": (
                "yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/"
                "ОпределенияИдентификаторов/Template.txt"
            ),
            "sha256": "7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152",
            "hash_scope": "original_bytes",
            "source_path": (
                "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/"
                "ОпределенияИдентификаторов/Template.txt"
            ),
            "source_sha256": "7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152",
        },
    ),
}
EXPECTED_SIDECARS = {
    "lexer": {
        "schema_version": 2,
        "benchmark_id": "runtime-old-lexer-baseline",
        "component": "lexer",
        "measurement_scope": (
            "Полная токенизация: установка текста и чтение содержательных и конечного токена"
        ),
        "implementation_id": "old-lexer-59d538f",
        "metadata_object_names": (
            "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
        ),
    },
    "parser": {
        "schema_version": 2,
        "benchmark_id": "runtime-old-parser-baseline",
        "component": "parser",
        "measurement_scope": (
            "Разобрать/РазобратьВыражение вместе с внутренней токенизацией; "
            "создание parser object вне sample"
        ),
        "implementation_id": "old-parser-59d538f",
        "metadata_object_names": (
            "DataProcessor.КОНС_СтарыйПарсер",
            "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
            "CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса",
        ),
    },
}
```

Implement one pure strict artifact-row validator. It rejects wrong row count/order, missing or extra fields, and any value substitution; both sidecar commands reach this same function through `validate_sidecar`:

```python
def validate_artifact_rows(artifacts: object, component: str) -> None:
    if not isinstance(artifacts, list):
        raise ValueError(f"{component}.artifacts must be a list")
    expected_rows = EXPECTED_ARTIFACTS[component]
    if len(artifacts) != len(expected_rows):
        raise ValueError(f"{component}.artifact row count mismatch")
    for index, (artifact, expected_row) in enumerate(zip(artifacts, expected_rows)):
        if not isinstance(artifact, dict):
            raise ValueError(f"{component}.artifacts[{index}] must be an object")
        if set(artifact) != set(EXPECTED_ARTIFACT_FIELDS):
            raise ValueError(f"{component}.artifacts[{index}] field set mismatch")
        for field in EXPECTED_ARTIFACT_FIELDS:
            if artifact[field] != expected_row[field]:
                raise ValueError(
                    f"{component}.artifacts[{index}].{field}: "
                    f"{artifact[field]!r} != {expected_row[field]!r}"
                )
```

For the remaining `validate_sidecar` fields, compare by equality rather than mere presence, then delegate every artifact row to the pure validator:

```python
expected = EXPECTED_SIDECARS[component]
for field in (
    "schema_version",
    "benchmark_id",
    "component",
    "measurement_scope",
    "implementation_id",
):
    if document[field] != expected[field]:
        raise ValueError(f"{component}.{field}: {document[field]!r} != {expected[field]!r}")
if tuple(document["metadata_object_names"]) != expected["metadata_object_names"]:
    raise ValueError(f"{component}.metadata_object_names mismatch")
if document["clock"] != EXPECTED_CLOCK:
    raise ValueError(f"{component}.clock mismatch")
validate_artifact_rows(document["artifacts"], component)
if component == "parser":
    parser_artifact = document["artifacts"][0]
    if document.get("parser_artifact") != parser_artifact:
        raise ValueError("parser.parser_artifact must equal parser-role artifact")
```

Also require `source_ref == "origin/old_parser"`, the full expected commit, `warmup_count == 3`, `sample_count == 20`, calibration `25`, exact corpus order, 42 inputs in the first corpus, 20 positive samples and positive median/p95 in every corpus. For corpus index `8`, require exactly one `Разобрать` input and exact `CommonTemplate` provenance: its metadata FQN, repository `Template.txt` path, external source path, raw bytes, line count, character count, raw SHA-256 and normalized UTF-8/LF SHA-256 equal `EXPECTED_TIME_ACCOUNTING_LARGE`; require corpus and input length `160135`. Lexer requires positive per-input and aggregate `token_count`. No extra or duplicate artifact row, metadata object name or corpus is accepted. Keep both `validate_artifact_rows(artifacts, component)` and `validate_sidecar(document, component)` pure. The capture-time `validate-sidecars` handler first runs `verify-source`, then loads each JSON and calls `validate_sidecar`; `publish` delegates to that same capture validation before copying bytes. The post-cleanup `validate-durable` handler loads retained JSON and calls the same `validate_sidecar`/`validate_artifact_rows` chain, but never runs `verify-source` or reads a temporary target path.

`publish` performs capture-time validation first, copies sidecar bytes with `shutil.copyfile`, reads the copied JSON, and renders Markdown tables with columns `corpus`, `input_count`, `input_length`, `operation_count_per_iteration`, `median_ms`, and `p95_ms`. Its provenance section includes `lexer_json_sha256`, `parser_json_sha256` and the exact raw/normalized hash manifest of `time_accounting_large`, computed from the exact copied bytes. The report contains no percentage or verdict.

Implement the post-cleanup validator without Git or target-source access:

```python
def validate_durable(lexer_path: Path, parser_path: Path, report_path: Path) -> None:
    lexer_bytes = lexer_path.read_bytes()
    parser_bytes = parser_path.read_bytes()
    lexer_document = json.loads(lexer_bytes.decode("utf-8"))
    parser_document = json.loads(parser_bytes.decode("utf-8"))
    validate_sidecar(lexer_document, "lexer")
    validate_sidecar(parser_document, "parser")
    expected_report = render_markdown(
        lexer_document,
        parser_document,
        hashlib.sha256(lexer_bytes).hexdigest(),
        hashlib.sha256(parser_bytes).hexdigest(),
    )
    if report_path.read_text(encoding="utf-8") != expected_report:
        raise ValueError("durable Markdown does not match durable JSON bytes")
```

The `validate-durable` CLI calls only this function. It validates durable JSON bytes through the hashes embedded in regenerated Markdown, strict schema/provenance through `validate_sidecar`, and exact Markdown regeneration; it must not call `verify-ref`, `verify_materialized_sources`, `git_bytes`, or inspect either temporary DataProcessor directory.

- [ ] **Step 5: Run unit tests and a read-only verification against Git objects**

```powershell
python -m pytest tools/parsergen/tests/test_legacy_runtime_baseline.py -v
python tools/parsergen/benchmarks/legacy_runtime_baseline.py verify-ref --repo .
```

Expected: PASS and both local/remote refs equal `59d538fd974c723c6b1cf336c61b0fea1aec8453`.

- [ ] **Step 6: Commit the reopened Wave A extension**

```powershell
git add tools/parsergen/benchmarks/legacy_runtime_baseline.py tools/parsergen/tests/test_legacy_runtime_baseline.py
git commit -m "Расширить provenance baseline старой фабрикой"
```

### Task 2: Create and prove the three historical runtime objects and permanent corpus template

**Files:**
- Create through EDT-MCP: `yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса/**`
- Create through EDT-MCP: `yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/**`
- Create through EDT-MCP: `yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/**`
- Create through EDT-MCP: `yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/**`
- Modify through EDT-MCP: `yaxunit/src/Configuration/Configuration.mdo`
- Modify: `yaxunit/UPSTREAM.md`

**Interfaces:**
- Consumes: Task 1 verified Git blobs and exact materialization command.
- Produces: `DataProcessor.КОНС_СтарыйЛексическийАнализатор` with exported historical `Инициализировать()`, `УстановитьОбрабатываемыйТекст(Текст)`, `СледующийТокен()`.
- Produces: `DataProcessor.КОНС_СтарыйПарсер` with exported historical `Разобрать(Текст)` and `РазобратьВыражение(Текст)` and two TextDocument templates.
- Produces: non-global `CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса` with the complete historical 91-function factory API; parser uses 79 exports in exactly 102 direct call sites.
- Produces: permanent `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени` of type `TextDocument`; its repository `Template.txt` has the approved raw and normalized time-accounting manifest and is the only source of the ninth corpus at runtime.

- [ ] **Step 1: Establish RED with absent target artifacts**

```powershell
python tools/parsergen/benchmarks/legacy_runtime_baseline.py verify-source --repo .
```

Expected: exit `2`, naming absent targets for the common module and two DataProcessor directories; production sources remain unchanged.

- [ ] **Step 2: Enforce the EDT execution-checkout path gate**

Call EDT-MCP `list_projects`. Resolve the execution root with `Resolve-Path .` and require these exact path equalities before a write:

```text
QueryConsoleZUP project path = Join-Path EXECUTION_ROOT 'QueryConsoleZUP'
yaxunit project path         = Join-Path EXECUTION_ROOT 'yaxunit'
```

The values on the right come from the live `Resolve-Path` result, not a copied literal. If either differs, stop the EDT phase and switch/reopen the projects through the actual EDT workspace UI or a separately verified EDT tool; do not write metadata into the main checkout.

- [ ] **Step 3: Snapshot background diagnostics, then create exact EDT metadata**

Record `get_problem_summary(projectName="yaxunit")` and `get_project_errors(projectName="yaxunit", limit=1000, responseFormat="concise")` before creation.

Use the confirmed `create_metadata` contract:

```text
create_metadata(projectName="yaxunit",
  fqn="CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса",
  expectedNotExists=true,
  properties=[{name:"synonym", value:"КОНС старые элементы модели запроса", language:"ru"},
              {name:"comment", value:"Temporary old_parser model-factory runtime baseline object"},
              {name:"global", value:false},
              {name:"clientManagedApplication", value:true},
              {name:"server", value:true},
              {name:"externalConnection", value:true},
              {name:"clientOrdinaryApplication", value:true}])

create_metadata(projectName="yaxunit",
  fqn="DataProcessor.КОНС_СтарыйЛексическийАнализатор",
  expectedNotExists=true,
  properties=[{name:"synonym", value:"КОНС старый лексический анализатор", language:"ru"},
              {name:"comment", value:"Temporary old_parser runtime baseline object"}])

create_metadata(projectName="yaxunit",
  fqn="DataProcessor.КОНС_СтарыйПарсер",
  expectedNotExists=true,
  properties=[{name:"synonym", value:"КОНС старый парсер", language:"ru"},
              {name:"comment", value:"Temporary old_parser runtime baseline object"}])

create_metadata(projectName="yaxunit",
  fqn="DataProcessor.КОНС_СтарыйПарсер.Template.ТаблицаПервыхСимволовВариантов",
  expectedNotExists=true,
  properties=[{name:"synonym", value:"Таблица первых символов вариантов", language:"ru"}])

create_metadata(projectName="yaxunit",
  fqn="DataProcessor.КОНС_СтарыйПарсер.Template.ОпределенияИдентификаторов",
  expectedNotExists=true,
  properties=[{name:"synonym", value:"Определения идентификаторов", language:"ru"}])

create_metadata(projectName="yaxunit",
  fqn="CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени",
  expectedNotExists=true,
  properties=[{name:"synonym", value:"КОНС бенчмарк данные учета времени", language:"ru"},
              {name:"comment", value:"Permanent time-accounting benchmark corpus"}])
```

For each template call `get_metadata_details(projectName="yaxunit", objectFqns=[FQN], assignable=true)`, require `templateType` allows `TextDocument`, then call:

```text
modify_metadata(projectName="yaxunit",
  fqn="DataProcessor.КОНС_СтарыйПарсер.Template.ТаблицаПервыхСимволовВариантов",
  properties=[{name:"templateType", value:"TextDocument"}])

modify_metadata(projectName="yaxunit",
  fqn="DataProcessor.КОНС_СтарыйПарсер.Template.ОпределенияИдентификаторов",
  properties=[{name:"templateType", value:"TextDocument"}])

get_metadata_details(projectName="yaxunit",
  objectFqns=["CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени"], assignable=true)
modify_metadata(projectName="yaxunit",
  fqn="CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени",
  properties=[{name:"templateType", value:"TextDocument"}])
```

Before the `CommonTemplate` copy, prove the exact source manifest without rewriting its bytes:

```powershell
$timeAccountingSource = 'C:\work\1C\мои разработки\Теория копмиляторов\Генерация парсеров АКТУАЛЬНОЕ\заппросы\ДанныеУчетаВремени.txt'
@'
from hashlib import sha256
from pathlib import Path

source = Path(r"C:\work\1C\мои разработки\Теория копмиляторов\Генерация парсеров АКТУАЛЬНОЕ\заппросы\ДанныеУчетаВремени.txt")
raw = source.read_bytes()
text = raw.decode("utf-8")
normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
assert len(raw) == 289542
assert len(text.splitlines()) == 5489
assert len(text) == 160135
assert sha256(raw).hexdigest() == "43035fda34f0ccb05817d856374beba9e5539a3a99540fef9ba7d70d3656c93e"
assert sha256(normalized).hexdigest() == "5e4a617dd41f8af97434b797bac46c9f8ba3ca1d167db9d81828b6854f1fc9c5"
'@ | python -
Copy-Item -LiteralPath $timeAccountingSource -Destination 'yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/Template.txt' -Force
```

Immediately hash the repository target with the same two SHA-256 scopes and assert the same byte, line and character counts. Expected: EDT creates fresh UUIDs, registers the three temporary top objects and the permanent common template in `Configuration.mdo`, and persists the three `Template.txt` paths. Do not copy any historical `.mdo`, lexer form or parser manager module; the only external byte copy is the approved source above.

- [ ] **Step 4: Materialize historical sources and make provenance GREEN**

```powershell
python tools/parsergen/benchmarks/legacy_runtime_baseline.py materialize --repo . --target-dir build/legacy-runtime-baseline-source
```

Read all three newly created empty modules through EDT-MCP. Write staged factory content to `objectName="CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса"`, `moduleType="Module"`; write staged lexer/parser content to their exact DataProcessor FQNs with `moduleType="ObjectModule"`. Every `write_module_source` uses `projectName="yaxunit"`, `mode="replace"`, the `expectedHash` and `expectedSource` from its immediately preceding read, and the corresponding staged UTF-8 text. Copy only the two staged EDT-created `Template.txt` blobs to their EDT-created target paths with `Copy-Item -LiteralPath`; this preserves original bytes because EDT exposes no TextDocument-content writer.

Then run:

```powershell
python tools/parsergen/benchmarks/legacy_runtime_baseline.py verify-source --repo .
```

Expected: all five hashes equal the approved manifest; reverse replacement of both `КОНС_СтарыйЛексическийАнализатор` and `КОНС_СтарыеЭлементыМоделиЗапроса` yields the historical parser hash. Verify that there is no lexer production factory and no lexical-token reference to the production model factory:

```powershell
rg -n "Обработки\.ЛексическийАнализатор" yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/ObjectModule.bsl
rg -n -P "(?<![0-9A-Za-zА-Яа-я_])ЭлементыМоделиЗапроса\." yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/ObjectModule.bsl
```

- [ ] **Step 5: Revalidate exact EDT FQNs and compare new errors to the snapshot**

```text
revalidate_objects(projectName="yaxunit", objects=[
  "CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса",
  "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
  "DataProcessor.КОНС_СтарыйПарсер",
  "CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени"
])
```

Read `get_project_errors` filtered to those four FQNs. Expected: no new `ERRORS`; existing unrelated markers remain documented as background. Read `get_metadata_details` for `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени`, require `templateType == TextDocument`, then repeat the raw/normalized hash, byte, line and character manifest against its repository `Template.txt`.

Immediately after revalidation, prove EDT refresh/export did not rewrite historical BSL normalization or template bytes:

```powershell
python tools/parsergen/benchmarks/legacy_runtime_baseline.py verify-source --repo .
```

Expected: all five approved materialized hashes still match, including the factory source and both original-byte template hashes.

- [ ] **Step 6: Register project-local additions and commit Wave B**

In `yaxunit/UPSTREAM.md`, add `КОНС_Обр_БенчмаркПарсера_МО` and `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени` to the permanent retained objects, recording its repository path and both exact SHA-256 values; add all three temporary metadata objects under a clearly labeled baseline subsection. Cleanup removes only the latter subsection rows.

```powershell
git diff -- QueryConsoleZUP/src
git diff --check
git add yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор yaxunit/src/DataProcessors/КОНС_СтарыйПарсер yaxunit/src/Configuration/Configuration.mdo yaxunit/UPSTREAM.md
git commit -m "Добавить старый runtime baseline в YAxUnit"
```

Expected: first diff command is empty; commit contains only `yaxunit/**`.

### Task 3: Parameterize the shared harness, add the permanent corpus and lexer/parser preflight

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`
- Modify: `tools/parsergen/tests/test_legacy_runtime_baseline.py`

**Interfaces:**
- Consumes: exact runtime objects and permanent `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени` from Task 2; retains the ordered eight existing corpus and appends one time-accounting corpus.
- Produces descriptor fields `implementation_id`, `component`, `runtime_object`, `source_ref`, `source_commit`, `metadata_object_names`, `artifacts`, `sidecar_name`, `benchmark_id`, `measurement_scope`.
- Produces `ВыполнитьБенчмарк(ОписаниеРеализации)`, `ВыполнитьPreflight`, `ИзмеритьКорпус(ОписаниеРеализации, Корпус, КоличествоПрогревов, КоличествоЗамеров)`, and descriptor-driven batch functions.
- Preserves the current parser test name `RuntimeBaselineПарсераФормируется` for Decision DAG follow-up work.

- [ ] **Step 1: Add RED static-contract tests before BSL changes**

```python
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
    self.assertNotIn("Метаданные.НайтиПоТипу", text)

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
```

Run:

```powershell
python -m pytest tools/parsergen/tests/test_legacy_runtime_baseline.py -v
```

Expected: FAIL because the current module registers only the parser benchmark and `ВыполнитьБенчмарк()` has no descriptor parameter.

- [ ] **Step 2: Add the four explicit descriptors and artifact schema**

Read the current module with EDT-MCP `read_module_source(projectName="yaxunit", modulePath="CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl")`; retain its `contentHash` for guarded writes.

Immediately before every Task 3 `write_module_source` call, repeat EDT-MCP `list_projects`, recompute `EXECUTION_ROOT = (Resolve-Path .).Path`, and assert exact normalized path equality for both rows:

```text
QueryConsoleZUP.path == Join-Path EXECUTION_ROOT 'QueryConsoleZUP'
yaxunit.path         == Join-Path EXECUTION_ROOT 'yaxunit'
```

Abort that write if either assertion fails, even if Task 2 previously passed the same gate. After each successful write, obtain a fresh `contentHash`; never reuse the revision guard from an earlier write.

Add these exact factories:

```bsl
Функция ОписаниеСтарогоЛексера()
	Лексер = Обработки.КОНС_СтарыйЛексическийАнализатор.Создать();
	Лексер.Инициализировать();
	Артефакты = Новый Массив;
	Артефакты.Добавить(НовыйАртефакт("lexer", "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
		"yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/ObjectModule.bsl",
		"434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20", "normalized_utf8_lf",
		"QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl",
		"434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20"));
	ИменаОбъектовМетаданных = Новый Массив;
	ИменаОбъектовМетаданных.Добавить("DataProcessor.КОНС_СтарыйЛексическийАнализатор");
	Возврат НовоеОписаниеРеализации("old-lexer-59d538f", "lexer", Лексер,
		"origin/old_parser", "59d538fd974c723c6b1cf336c61b0fea1aec8453",
		ИменаОбъектовМетаданных, Артефакты,
		"runtime-old-lexer-baseline.json", "runtime-old-lexer-baseline",
		"Полная токенизация: установка текста и чтение содержательных и конечного токена");
КонецФункции
```

Add the parser factory in full:

```bsl
Функция ОписаниеСтарогоПарсера()
	Парсер = Обработки.КОНС_СтарыйПарсер.Создать();
	Артефакты = Новый Массив;
	Артефакты.Добавить(НовыйАртефакт("parser", "DataProcessor.КОНС_СтарыйПарсер",
		"yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/ObjectModule.bsl",
		"dc401e271105eb34b4b2234c75b13fcdfd0341bb3b6766507d9f8cb1eb62e8b7", "normalized_utf8_lf",
		"QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl",
		"0c365e1e521322554b63e400379be47c0dc5ecaa7f60dd6951dc84bc7cccd084"));
	Артефакты.Добавить(НовыйАртефакт("lexer", "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
		"yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/ObjectModule.bsl",
		"434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20", "normalized_utf8_lf",
		"QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl",
		"434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20"));
	Артефакты.Добавить(НовыйАртефакт("legacy_model_factory",
		"CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса",
		"yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса/Module.bsl",
		"62213fee493659cd38c8678db5cb25a1ec6e79d2075d5128d1a396c6cea9c313", "normalized_utf8_lf",
		"QueryConsoleZUP/src/CommonModules/ЭлементыМоделиЗапроса/Module.bsl",
		"62213fee493659cd38c8678db5cb25a1ec6e79d2075d5128d1a396c6cea9c313"));
	Артефакты.Добавить(НовыйАртефакт("first_symbols_template",
		"DataProcessor.КОНС_СтарыйПарсер.Template.ТаблицаПервыхСимволовВариантов",
		"yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
		"4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed", "original_bytes",
		"QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
		"4e3f87f15291de1a0d216773f2dc3d69144759d56796504473fdd8bfb74dc3ed"));
	Артефакты.Добавить(НовыйАртефакт("identifiers_template",
		"DataProcessor.КОНС_СтарыйПарсер.Template.ОпределенияИдентификаторов",
		"yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/Templates/ОпределенияИдентификаторов/Template.txt",
		"7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152", "original_bytes",
		"QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt",
		"7c08a5a520ab66c1b931a9e401f06c3acbd9f1652c3acefe101fc38181e58152"));
	ИменаОбъектовМетаданных = Новый Массив;
	ИменаОбъектовМетаданных.Добавить("DataProcessor.КОНС_СтарыйПарсер");
	ИменаОбъектовМетаданных.Добавить("DataProcessor.КОНС_СтарыйЛексическийАнализатор");
	ИменаОбъектовМетаданных.Добавить("CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса");
	Возврат НовоеОписаниеРеализации("old-parser-59d538f", "parser", Парсер,
		"origin/old_parser", "59d538fd974c723c6b1cf336c61b0fea1aec8453",
		ИменаОбъектовМетаданных, Артефакты, "runtime-old-parser-baseline.json",
		"runtime-old-parser-baseline",
		"Разобрать/РазобратьВыражение вместе с внутренней токенизацией; создание parser object вне sample");
КонецФункции
```

Keep current parser compatibility by making `ОписаниеТекущегоПарсера()` use `Обработки.Парсер.Создать()`, normalized parser source hash `07d7f88f2926cb9fab32ab7eda6506a7cdbfb897eb4e87e9abdc70a21dd695f0`, current model-factory hash `d66ba83eb808e487f3b7a5a17b16572ac7fc000b959eb55edc32b9bdb287ed02`, template hashes `acb80f86f739d5a4a54fe7d6f2c85cdc57a2d664d779a1f1e51a0aaf54a059c1` and `13472cb0e1482b5c590a306fe6fc119d026546069e717d8eadd010b6a8661ef6`, sidecar `runtime-parser-benchmark-after.json`, and existing test `RuntimeBaselineПарсераФормируется`. Add `ОписаниеТекущегоЛексера()` with explicit `Обработки.ЛексическийАнализатор.Создать()` plus one `Инициализировать()`, normalized source hash `434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20`, sidecar `runtime-lexer-benchmark-after.json`, and new test `RuntimeBaselineЛексераФормируется`. Current descriptor `source_ref` is `17c105d` and `source_commit` is `17c105dcc864ea475353c350088e3cdbe97a3761`; immediately before the BSL write, run `current-hashes --repo .` and require exact equality with all three current source hashes. Build current artifact rows with `НовыйАртефакт` exactly as for old artifacts but with production metadata FQNs and paths; current parser includes parser, lexer, production `CommonModule.ЭлементыМоделиЗапроса` and both templates, while current lexer includes only lexer. Including both generations of the model factory is required because parser timings include semantic-node construction.

Append the ninth corpus after `Dereference` and before `Возврат Корпусы`; use the existing `НовыйКорпус` and `ДобавитьВход` interfaces exactly once, so common-template retrieval occurs while `КорпусыБенчмарка()` builds its data and before `ВыполнитьPreflight`, calibration, warm-ups or samples:

```bsl
TimeAccountingLarge = НовыйКорпус("time_accounting_large", "Разобрать",
	"Permanent CommonTemplate time-accounting query imported from verified external source",
	Новый Структура("metadata_object,path,external_source_path,raw_bytes,line_count,character_count,raw_sha256,normalized_utf8_lf_sha256",
		"CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени",
		"yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/Template.txt",
		"C:\\work\\1C\\мои разработки\\Теория копмиляторов\\Генерация парсеров АКТУАЛЬНОЕ\\заппросы\\ДанныеУчетаВремени.txt",
		289542, 5489, 160135,
		"43035fda34f0ccb05817d856374beba9e5539a3a99540fef9ba7d70d3656c93e",
		"5e4a617dd41f8af97434b797bac46c9f8ba3ca1d167db9d81828b6854f1fc9c5"));
ТекстДанныхУчетаВремени = ПолучитьОбщийМакет("КОНС_БенчмаркДанныеУчетаВремени").ПолучитьТекст();
Если СтрДлина(ТекстДанныхУчетаВремени) <> 160135 Тогда
	ВызватьИсключение "time_accounting_large: CommonTemplate character count mismatch";
КонецЕсли;
ДобавитьВход(TimeAccountingLarge.inputs, "time_accounting_large_1", ТекстДанныхУчетаВремени,
	Новый Структура("type,metadata_object,path,external_source_path,raw_bytes,line_count,character_count,raw_sha256,normalized_utf8_lf_sha256",
		"common_template_text_document",
		TimeAccountingLarge.generator_parameters.metadata_object,
		TimeAccountingLarge.generator_parameters.path,
		TimeAccountingLarge.generator_parameters.external_source_path,
		TimeAccountingLarge.generator_parameters.raw_bytes,
		TimeAccountingLarge.generator_parameters.line_count,
		TimeAccountingLarge.generator_parameters.character_count,
		TimeAccountingLarge.generator_parameters.raw_sha256,
		TimeAccountingLarge.generator_parameters.normalized_utf8_lf_sha256));
Корпусы.Добавить(TimeAccountingLarge);
```

Use helpers with these exact signatures:

```bsl
Функция НовыйАртефакт(Роль, ОбъектМетаданных, Путь, Хеш, ОбластьХеша, ИсходныйПуть, ИсходныйХеш)
	Возврат Новый Структура(
		"role,metadata_object,path,sha256,hash_scope,source_path,source_sha256",
		Роль, ОбъектМетаданных, Путь, Хеш, ОбластьХеша, ИсходныйПуть, ИсходныйХеш);
КонецФункции

Функция НовоеОписаниеРеализации(Идентификатор, Компонент, ОбъектRuntime,
	ИсходныйRef, ИсходныйCommit, ИменаОбъектовМетаданных, Артефакты,
	ИмяSidecar, ИдентификаторБенчмарка, ОбластьИзмерения)

	Возврат Новый Структура(
		"implementation_id,component,runtime_object,source_ref,source_commit,metadata_object_names,artifacts,sidecar_name,benchmark_id,measurement_scope",
		Идентификатор, Компонент, ОбъектRuntime, ИсходныйRef, ИсходныйCommit,
		ИменаОбъектовМетаданных, Артефакты, ИмяSidecar, ИдентификаторБенчмарка, ОбластьИзмерения);
КонецФункции
```

- [ ] **Step 3: Implement preflight with contextual hard failures**

Build corpus once per benchmark invocation, then preflight each input before calibration. Lexer preflight records token counts on the input and corpus:

```bsl
Функция ВыполнитьLexerInput(ОписаниеРеализации, Корпус, Вход, СчитатьТокены)
	Лексер = ОписаниеРеализации.runtime_object;
	Лексер.УстановитьОбрабатываемыйТекст(Вход.text);
	КоличествоТокенов = 0;
	КоличествоЧтений = 0;
	Пока Истина Цикл
		Токен = Лексер.СледующийТокен();
		КоличествоЧтений = КоличествоЧтений + 1;
		Если Токен.Тип = Неопределено Тогда
			Прервать;
		КонецЕсли;
		КоличествоТокенов = КоличествоТокенов + 1;
	КонецЦикла;
	Если СчитатьТокены И КоличествоТокенов <= 0 Тогда
		ВызватьИсключение "lexer preflight получил ноль содержательных токенов";
	КонецЕсли;
	Возврат Новый Структура("token_count,token_reads", КоличествоТокенов, КоличествоЧтений);
КонецФункции
```

Parser preflight calls only the corpus entrypoint and rejects `Неопределено`. It does not compare old/current ASTs: the legacy factory and production factory intentionally produce different model generations. `КонтекстОшибки` uses:

```bsl
Функция ВыполнитьParserInput(ОписаниеРеализации, Корпус, Вход)
	Парсер = ОписаниеРеализации.runtime_object;
	Если Корпус.entrypoint = "Разобрать" Тогда
		РезультатРазбора = Парсер.Разобрать(Вход.text);
	ИначеЕсли Корпус.entrypoint = "РазобратьВыражение" Тогда
		РезультатРазбора = Парсер.РазобратьВыражение(Вход.text);
	Иначе
		ВызватьИсключение КонтекстОшибки(ОписаниеРеализации, Корпус, Вход,
			"неизвестный parser entrypoint: " + Корпус.entrypoint);
	КонецЕсли;
	Если РезультатРазбора = Неопределено Тогда
		ВызватьИсключение КонтекстОшибки(ОписаниеРеализации, Корпус, Вход,
			"parser вернул Неопределено");
	КонецЕсли;
	Возврат РезультатРазбора;
КонецФункции

Процедура ВыполнитьPreflight(ОписаниеРеализации, Корпусы)
	Для Каждого Корпус Из Корпусы Цикл
		КоличествоТокеновКорпуса = 0;
		Для Каждого Вход Из Корпус.inputs Цикл
			Попытка
				Если ОписаниеРеализации.component = "lexer" Тогда
					Счетчики = ВыполнитьLexerInput(ОписаниеРеализации, Корпус, Вход, Истина);
					Вход.Вставить("token_count", Счетчики.token_count);
					КоличествоТокеновКорпуса = КоличествоТокеновКорпуса + Счетчики.token_count;
				ИначеЕсли ОписаниеРеализации.component = "parser" Тогда
					ВыполнитьParserInput(ОписаниеРеализации, Корпус, Вход);
				Иначе
					ВызватьИсключение "неизвестный component";
				КонецЕсли;
			Исключение
				ВызватьИсключение КонтекстОшибки(ОписаниеРеализации, Корпус, Вход, ОписаниеОшибки());
			КонецПопытки;
		КонецЦикла;
		Если ОписаниеРеализации.component = "lexer" Тогда
			Корпус.Вставить("token_count", КоличествоТокеновКорпуса);
		КонецЕсли;
	КонецЦикла;
КонецПроцедуры

Функция КонтекстОшибки(ОписаниеРеализации, Корпус, Вход, Причина)
	Возврат СтрШаблон("component=%1 implementation=%2 corpus=%3 input=%4: %5",
		ОписаниеРеализации.component, ОписаниеРеализации.implementation_id,
		Корпус.id, Вход.id, Причина);
КонецФункции
```

Do not catch these exceptions to select another implementation.

- [ ] **Step 4: Parameterize calibration, warm-ups and samples without changing statistics**

Change the call chain to pass `ОписаниеРеализации` instead of a parser variable:

```bsl
Функция ИзмеритьКорпус(ОписаниеРеализации, Корпус, КоличествоПрогревов, КоличествоЗамеров)
Функция КалиброватьРазмерПакета(ОписаниеРеализации, Корпус, ЦелеваяДлительностьМс)
Функция ИзмеритьПакет(ОписаниеРеализации, Корпус, КоличествоИтераций)
Процедура ВыполнитьПакет(ОписаниеРеализации, Корпус, КоличествоИтераций)
```

The inner dispatch is explicit:

```bsl
Если ОписаниеРеализации.component = "lexer" Тогда
	ВыполнитьLexerInput(ОписаниеРеализации, Корпус, Вход, Ложь);
ИначеЕсли ОписаниеРеализации.component = "parser" Тогда
	ВыполнитьParserInput(ОписаниеРеализации, Корпус, Вход);
Иначе
	ВызватьИсключение КонтекстОшибки(ОписаниеРеализации, Корпус, Вход,
		"неизвестный component");
КонецЕсли;
```

Keep the existing `Медиана` and `Процентиль95` bodies unchanged. Preserve existing corpus construction bytes and order. Add `operations_per_sample`; keep `parse_calls_per_sample` for parser compatibility and add `token_reads_per_iteration` plus aggregate `token_count` for lexer.

Build input descriptions without assuming a token field on parser inputs:

```bsl
Функция ОписаниеВходов(Входы)
	Результат = Новый Массив;
	Для Каждого Вход Из Входы Цикл
		Описание = Новый Структура("id,input_length,provenance",
			Вход.id, СтрДлина(Вход.text), Вход.provenance);
		Если Вход.Свойство("token_count") Тогда
			Описание.Вставить("token_count", Вход.token_count);
		КонецЕсли;
		Результат.Добавить(Описание);
	КонецЦикла;
	Возврат Результат;
КонецФункции
```

For every component set `operation_count_per_iteration = Корпус.inputs.Количество()` and `operations_per_sample = ИтерацийВПакете * Корпус.inputs.Количество()`. For lexer additionally set `token_count = Корпус.token_count` and `token_reads_per_iteration = Корпус.token_count + Корпус.inputs.Количество()`; the second term counts one terminal token read per input.

- [ ] **Step 5: Version the JSON and make each registration assert its own contract**

`ВыполнитьБенчмарк(ОписаниеРеализации)` writes schema version `2`, keeps `captured_at_platform_ms`, `runtime`, `clock_resolution_ms`, `internal_counters` and every existing corpus/sample field, copies all descriptor provenance fields, and calls `ПутьКРезультатуJSON(ОписаниеРеализации.sidecar_name)`. Change the output helper signature exactly to `Функция ПутьКРезультатуJSON(ИмяSidecar)` and return `ЮТФайлы.ОбъединитьПути(КаталогОтчета, ИмяSidecar)`. Parser output keeps `parser_artifact` as a compatibility alias of its parser-role artifact while `artifacts` is the authoritative multi-artifact list. A shared `ПроверитьРезультатБенчмарка` asserts nine corpus in exact order, first corpus 42 inputs, final `time_accounting_large` one `Разобрать` input with the full CommonTemplate manifest, 20 samples, and positive median/p95. Lexer registrations additionally assert positive corpus/input token counts.

Register exactly these server tests in one test set:

```bsl
ЮТТесты.ДобавитьСерверныйТест("RuntimeBaselineСтарогоЛексераФормируется");
ЮТТесты.ДобавитьСерверныйТест("RuntimeBaselineСтарогоПарсераФормируется");
ЮТТесты.ДобавитьСерверныйТест("RuntimeBaselineЛексераФормируется");
ЮТТесты.ДобавитьСерверныйТест("RuntimeBaselineПарсераФормируется");
```

Each exported procedure calls only its matching explicit descriptor; no metadata availability query appears.

- [ ] **Step 6: Run headless GREEN checks and guarded EDT revalidation**

```powershell
python -m pytest tools/parsergen/tests/test_legacy_runtime_baseline.py -v
git diff --check
```

Then use:

```text
revalidate_objects(projectName="yaxunit", objects=[
  "CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса",
  "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
  "DataProcessor.КОНС_СтарыйПарсер",
  "CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени",
  "CommonModule.КОНС_Обр_БенчмаркПарсера_МО"
])
```

Expected: no new `ERRORS` for those FQNs. Re-read the changed module through EDT-MCP and confirm the guarded source matches disk.

- [ ] **Step 7: Commit Wave C implementation**

```powershell
git add tools/parsergen/tests/test_legacy_runtime_baseline.py yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl
git commit -m "Параметризовать runtime benchmark lexer и parser"
```

### Task 4: Pass the EDT integration and current-regression gate

**Files:**
- Read only: EDT project/model/diagnostics state.
- Read only: YAxUnit reports for current lexer/parser modules.

**Interfaces:**
- Consumes: Wave C committed metadata and BSL.
- Produces: recorded diagnostics delta and successful current-regression evidence before old timing is accepted.

- [ ] **Step 1: Rediscover the runnable application instead of reusing a stale id**

Call `get_applications(projectName="yaxunit")`. Bind its live `defaultApplicationId` result to `YAXUNIT_APP_ID`. The planning-time workspace had one inherited application and no client launch configuration, so the supported project/application form of `run_yaxunit_tests` is used.

- [ ] **Step 2: Revalidate and compare diagnostics**

Repeat the exact five-FQN `revalidate_objects` call from Task 3 (legacy factory, both temporary DataProcessor, permanent corpus `CommonTemplate` and benchmark common module), then `get_problem_summary` and filtered `get_project_errors`. Expected: no new errors relative to the Task 2 snapshot; warnings already present in the snapshot are not reported as newly introduced.

- [ ] **Step 3: Run existing current lexer/parser unit modules**

Call `run_yaxunit_tests` with the live `YAXUNIT_APP_ID` and exact arguments:

```text
projectName="yaxunit"
applicationId=YAXUNIT_APP_ID
extensions=["YAXUNIT"]
modules=[
  "КОНС_Обр_ЛексическийАнализатор_МО",
  "КОНС_Обр_Парсер_МО",
  "КОНС_Обр_ПарсерЗапросов_МО"
]
updateBeforeLaunch=true
updateScope="extension:yaxunit"
timeout=60
```

If the call returns Pending, call again with identical arguments until the run completes. Expected: matched test count is positive and there are no new failures. Record exact passed/failed/skipped totals and `report.md` path.

- [ ] **Step 4: Run the permanent current lexer/parser benchmark registrations**

Run two exact tests separately so their sidecars and timing failures are attributable:

```text
КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineЛексераФормируется
КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineПарсераФормируется
```

Use the same project/application/update arguments only after the fresh Task 5-style manual runtime confirmation. Expected: one test matched per call, nine corpus, 20 samples each, both sidecars created. These current sidecars are integration evidence only and are not copied to the three durable old-baseline paths.

- [ ] **Step 5: Record the gate without creating a synthetic commit**

This task is read-only. If any source adjustment was required, return to Task 3 RED/GREEN, recommit the cohesive Wave C change, and rerun the entire gate.

### Task 5: Capture and publish factual old lexer/parser runtime evidence

**Files:**
- Create from actual run: `docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json`
- Create from actual run: `docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json`
- Create from the copied JSON: `docs/superpowers/matrices/2026-08-08-runtime-old-lexer-parser-baseline.md`

**Interfaces:**
- Consumes: successful EDT gate, live `YAXUNIT_APP_ID`, actual report directories and sidecars.
- Produces: two byte-identical durable JSON files and a deterministic Markdown report without verdict.

- [ ] **Step 1: Establish runtime RED before the first old run**

Run `validate-sidecars` against the most recent YAxUnit report directories. Expected: exit `3` because `runtime-old-lexer-baseline.json` and `runtime-old-parser-baseline.json` do not yet both exist. Do not create empty JSON fixtures under `docs/superpowers/matrices`.

- [ ] **Step 2: Open a fresh manual runtime gate immediately before timing**

After all provenance, schema, EDT and functional-preflight checks are ready, report that state to the user and request explicit confirmation that heavy processes are stopped. Do not run any old or current benchmark registration that writes a timing sidecar before that fresh confirmation. A confirmation from an earlier task or earlier turn is not reusable. Record the exact user message and timestamp in the execution report.

- [ ] **Step 3: Run the old lexer benchmark alone**

Call `run_yaxunit_tests` with:

```text
projectName="yaxunit"
applicationId=YAXUNIT_APP_ID
extensions=["YAXUNIT"]
tests=["КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineСтарогоЛексераФормируется"]
updateBeforeLaunch=true
updateScope="extension:yaxunit"
timeout=60
```

Poll Pending with identical arguments. Require exactly one matched test, zero failures, nine corpus and the sidecar `runtime-old-lexer-baseline.json` next to the returned `report.md`. Bind its resolved path to `OLD_LEXER_SIDECAR`.

- [ ] **Step 4: Run the old parser benchmark alone**

Repeat with:

```text
tests=["КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineСтарогоПарсераФормируется"]
```

Require exactly one matched test, zero failures, nine corpus and `runtime-old-parser-baseline.json`; bind its resolved path to `OLD_PARSER_SIDECAR`.

If historical parser fails any corpus, stop Wave D. Preserve the failing JUnit report path and contextual error, make no parser compatibility edit, and report the baseline as blocked by the approved design rule.

- [ ] **Step 5: Validate both actual sidecars before publication**

```powershell
python tools/parsergen/benchmarks/legacy_runtime_baseline.py validate-sidecars --repo . --lexer $OLD_LEXER_SIDECAR --parser $OLD_PARSER_SIDECAR
```

Expected: source provenance passes, exact corpus order matches, all 18 corpus rows have 20 positive samples and positive median/p95, lexer counts are positive, both ninth corpus rows carry the exact CommonTemplate raw/normalized manifest, and all six artifact rows (one lexer row plus parser, lexer, legacy factory and two template rows for parser) equal their full approved `role`/metadata/path/hash-scope/source-path/hash manifests.

- [ ] **Step 6: Publish byte-identical JSON and render Markdown from them**

```powershell
python tools/parsergen/benchmarks/legacy_runtime_baseline.py publish --repo . --lexer $OLD_LEXER_SIDECAR --parser $OLD_PARSER_SIDECAR --output-dir docs/superpowers/matrices
```

Expected output paths are exactly the three names from File Structure. Prove JSON byte identity:

```powershell
$lexerDurable = 'docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json'
$parserDurable = 'docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json'
(Get-FileHash -Algorithm SHA256 -LiteralPath $OLD_LEXER_SIDECAR).Hash -eq (Get-FileHash -Algorithm SHA256 -LiteralPath $lexerDurable).Hash
(Get-FileHash -Algorithm SHA256 -LiteralPath $OLD_PARSER_SIDECAR).Hash -eq (Get-FileHash -Algorithm SHA256 -LiteralPath $parserDurable).Hash
```

Both expressions must return `True`.

- [ ] **Step 7: Run the factual runtime evidence gate**

```powershell
python tools/parsergen/benchmarks/legacy_runtime_baseline.py validate-sidecars --repo . --lexer docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json --parser docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json
python tools/parsergen/benchmarks/legacy_runtime_baseline.py validate-durable --lexer docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json --parser docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json --report docs/superpowers/matrices/2026-08-08-runtime-old-lexer-parser-baseline.md
python -m pytest tools/parsergen/tests/test_legacy_runtime_baseline.py -v
git diff --check
git status --short
```

This is the **capture gate before cleanup**: `validate-sidecars` must still see and hash the legacy factory, both temporary DataProcessor sources/templates, while `validate-durable` proves the independently retained artifacts are self-consistent. Inspect both JSON and Markdown diffs. Baseline is not captured if either run matched zero tests, skipped a corpus, failed, omitted a JSON or differs from the approved source manifest.

- [ ] **Step 8: Commit Wave D evidence**

```powershell
git add docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json docs/superpowers/matrices/2026-08-08-runtime-old-lexer-parser-baseline.md
git commit -m "Зафиксировать baseline старых lexer и parser"
```

### Task 6: Remove the three temporary legacy runtime objects after optimization and before MR

**Execution timing:** This is a separate later task. Do not execute it during Tasks 1–5; the temporary objects must remain available while optimization comparisons are being collected.

**Files:**
- Delete through EDT-MCP: `yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/**`
- Delete through EDT-MCP: `yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/**`
- Delete through EDT-MCP: `yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса/**`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`
- Modify: `yaxunit/src/Configuration/Configuration.mdo`
- Modify: `yaxunit/UPSTREAM.md`
- Preserve: `yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/**`, both durable baseline JSON, baseline Markdown, Python verifier/publisher, shared measurement functions and current lexer/parser registrations.

**Interfaces:**
- Removes only `ОписаниеСтарогоЛексера`, `ОписаниеСтарогоПарсера`, their two exported tests and references to all three temporary metadata objects.
- Keeps `RuntimeBaselineЛексераФормируется`, `RuntimeBaselineПарсераФормируется`, descriptor/schema helpers, all nine corpus including the permanent CommonTemplate load, preflight/statistics and current sidecars.

- [ ] **Step 1: Add RED cleanup assertions**

Immediately before editing `tools/parsergen/tests/test_legacy_runtime_baseline.py`, repeat `list_projects`, recompute `EXECUTION_ROOT`, and require the two exact Task 3 path equalities. Update the static BSL contract test only after that fresh gate to require no `КОНС_Старый` reference while still requiring both current test registrations. Run it before cleanup and expect failure on the old references.

- [ ] **Step 2: Remove old factories/tests and temporary UPSTREAM rows**

Immediately before the guarded benchmark-module write, repeat `list_projects`, recompute `EXECUTION_ROOT`, and require the two exact Task 3 path equalities. Remove the two old exported test registrations and old descriptor factories with `write_module_source` only after that fresh gate and a fresh module `contentHash`.

Immediately before editing `yaxunit/UPSTREAM.md`, repeat the same `list_projects` and path assertions again; then remove only the three temporary-object rows and keep `КОНС_Обр_БенчмаркПарсера_МО` plus `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени` and its two hashes listed. Revalidate both permanent FQNs before deleting metadata so no executable BSL reference points at any temporary object. A successful earlier cleanup write never substitutes for either fresh path assertion.

- [ ] **Step 3: Preview then execute exact EDT deletions**

For every `delete_metadata` invocation below—including each preview and each confirmed deletion—repeat `list_projects`, recompute `EXECUTION_ROOT`, and require both exact Task 3 path equalities immediately before the call. Do not reuse the result from the previous preview or deletion.

Call `delete_metadata` first with `confirm=false`, require only expected registrations/references, then repeat the path gate and call with `confirm=true` and `force=false` for:

```text
DataProcessor.КОНС_СтарыйПарсер
DataProcessor.КОНС_СтарыйЛексическийАнализатор
CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса
```

Delete parser first because it references the old lexer and legacy factory; delete lexer second; delete the legacy factory last. Never use `force=true`; a blocking reference means the BSL cleanup order must be corrected.

- [ ] **Step 4: Revalidate permanent objects and run current gates**

Revalidate `CommonModule.КОНС_Обр_БенчмаркПарсера_МО` and `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени`, then run current lexer/parser benchmark registrations only after another fresh manual runtime confirmation and the three current unit modules using the exact Task 4 arguments. Expected: positive test counts, no new failures and no new EDT errors.

- [ ] **Step 5: Prove cleanup completeness and preserve evidence**

```powershell
rg -n "КОНС_СтарыйЛексическийАнализатор|КОНС_СтарыйПарсер|КОНС_СтарыеЭлементыМоделиЗапроса" yaxunit/src yaxunit/UPSTREAM.md
Test-Path 'yaxunit/src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/Template.txt'
Test-Path 'docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json'
Test-Path 'docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json'
python tools/parsergen/benchmarks/legacy_runtime_baseline.py validate-durable --lexer docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json --parser docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json --report docs/superpowers/matrices/2026-08-08-runtime-old-lexer-parser-baseline.md
git diff --check
```

Expected: no temporary runtime/metadata references remain; all three `Test-Path` calls return `True`; recheck the retained CommonTemplate raw/normalized SHA-256 manifest; `validate-durable` passes without reading deleted temporary targets. Do not run `verify-source`, `validate-sidecars` or `publish` after deletion because those are intentionally capture-time commands.

- [ ] **Step 6: Commit the later cleanup wave**

```powershell
git add -A yaxunit/src/CommonModules/КОНС_СтарыеЭлементыМоделиЗапроса yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор yaxunit/src/DataProcessors/КОНС_СтарыйПарсер yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl yaxunit/src/Configuration/Configuration.mdo yaxunit/UPSTREAM.md tools/parsergen/tests/test_legacy_runtime_baseline.py
git commit -m "Удалить временный baseline старых lexer, parser и factory"
```

## Final Verification

- [ ] Run `python -m pytest tools/parsergen/tests/test_legacy_runtime_baseline.py -v`.
- [ ] Before cleanup, run the capture gate: `verify-ref`, `verify-source`, `validate-sidecars`, byte-identity checks and `validate-durable` against the durable JSON/Markdown.
- [ ] Revalidate `CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса`, both temporary DataProcessor, permanent `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени` and the benchmark common module before cleanup; after cleanup revalidate both permanent FQNs.
- [ ] Compare filtered EDT diagnostics to the recorded pre-change background and report newly introduced errors separately.
- [ ] Record exact YAxUnit passed/failed/skipped counts and report paths for old lexer, old parser, current lexer/parser benchmarks and current lexer/parser unit modules.
- [ ] Confirm exactly nine ordered corpus and 20 samples per corpus in both durable JSON; ninth `time_accounting_large` has one `Разобрать` input with the approved raw/normalized CommonTemplate manifest.
- [ ] Confirm positive token counts in lexer JSON and exact full provenance rows for parser, lexer, legacy factory and both templates in the parser durable JSON.
- [ ] Confirm before cleanup that durable JSON hashes equal their actual sidecar hashes and Markdown contains no performance verdict.
- [ ] After cleanup, run only `validate-durable` for retained evidence; require strict schema/provenance, embedded JSON-byte hashes and exact Markdown regeneration without temporary source files.
- [ ] Run `git diff --check`, inspect `git diff --stat` and `git status --short`, and confirm production `QueryConsoleZUP/src/**` has no diff.
- [ ] Before MR, execute Task 6 and prove no temporary metadata or runtime references remain for legacy factory, lexer or parser while the permanent CommonTemplate and all durable evidence stay tracked.
