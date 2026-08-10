from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


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
    "external_source_path": "C:\\work\\1C\\мои разработки\\Теория копмиляторов\\Генерация парсеров АКТУАЛЬНОЕ\\заппросы\\ДанныеУчетаВремени.txt",
    "raw_bytes": 289542,
    "line_count": 5489,
    "character_count": 160135,
    "raw_sha256": "43035fda34f0ccb05817d856374beba9e5539a3a99540fef9ba7d70d3656c93e",
    "normalized_utf8_lf_sha256": "5e4a617dd41f8af97434b797bac46c9f8ba3ca1d167db9d81828b6854f1fc9c5",
}
EXPECTED_TIME_ACCOUNTING_PROVENANCE = (
    "Permanent CommonTemplate time-accounting query imported from verified external source"
)
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
    ),
}
EXPECTED_SIDECARS = {
    "lexer": {
        "schema_version": 2,
        "benchmark_id": "runtime-old-lexer-baseline",
        "component": "lexer",
        "measurement_scope": "Полная токенизация: установка текста и чтение содержательных и конечного токена",
        "implementation_id": "old-lexer-59d538f",
        "metadata_object_names": (
            "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
        ),
    },
    "parser": {
        "schema_version": 2,
        "benchmark_id": "runtime-old-parser-baseline",
        "component": "parser",
        "measurement_scope": "Разобрать/РазобратьВыражение вместе с внутренней токенизацией; создание parser object вне sample",
        "implementation_id": "old-parser-59d538f",
        "metadata_object_names": (
            "DataProcessor.КОНС_СтарыйПарсер",
            "DataProcessor.КОНС_СтарыйЛексическийАнализатор",
            "CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса",
        ),
    },
}


class ProvenanceMaterializationError(Exception):
    """Distinguishes source/ref mismatches from sidecar evidence failures."""


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


def qualified_factory_prefix_count(text: str, prefix: str) -> int:
    pattern = rf"(?<![0-9A-Za-zА-Яа-я_]){re.escape(prefix)}"
    return len(re.findall(pattern, text))


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


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _historical_bytes(repo: Path, spec: ArtifactSpec) -> bytes:
    return git_bytes(repo, "show", f"{EXPECTED_COMMIT}:{spec.source_path}")


def verify_ref(repo: Path) -> dict[str, str]:
    local_commit = git_bytes(repo, "rev-parse", EXPECTED_REF).decode().strip()
    remote_rows = git_bytes(repo, "ls-remote", "--exit-code", "origin", EXPECTED_REMOTE_REF)
    remote_commit = remote_rows.decode().split()[0]
    if local_commit != EXPECTED_COMMIT or remote_commit != EXPECTED_COMMIT:
        raise ValueError(
            f"old_parser ref mismatch: local={local_commit} remote={remote_commit} expected={EXPECTED_COMMIT}"
        )
    return {"local_commit": local_commit, "remote_commit": remote_commit}


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _materialized_bytes(spec_name: str, historical: bytes) -> bytes:
    if spec_name == "lexer_module":
        return historical
    if spec_name == "parser_module":
        return adapt_parser_source(historical)
    return historical


def materialize_sources(repo: Path, target_dir: Path) -> dict[str, str]:
    verify_ref(repo)
    hashes: dict[str, str] = {}
    for spec_name, spec in ARTIFACTS.items():
        historical = _historical_bytes(repo, spec)
        if _sha256(normalize_bsl(historical) if spec.hash_scope == "normalized_utf8_lf" else historical) != spec.source_sha256:
            raise ValueError(f"historical {spec_name} SHA-256 mismatch")
        materialized = _materialized_bytes(spec_name, historical)
        hashed_materialized = (
            normalize_bsl(materialized)
            if spec.hash_scope == "normalized_utf8_lf"
            else materialized
        )
        if _sha256(hashed_materialized) != spec.materialized_sha256:
            raise ValueError(f"materialized {spec_name} SHA-256 mismatch")
        _atomic_write(target_dir / spec.target_path, materialized)
        hashes[spec_name] = _sha256(hashed_materialized)
    return hashes


def verify_materialized_sources(repo: Path) -> dict[str, str]:
    verify_ref(repo)
    hashes: dict[str, str] = {}
    for spec_name, spec in ARTIFACTS.items():
        historical = _historical_bytes(repo, spec)
        target = repo / spec.target_path
        target_bytes = target.read_bytes()
        source_bytes = normalize_bsl(historical) if spec.hash_scope == "normalized_utf8_lf" else historical
        if _sha256(source_bytes) != spec.source_sha256:
            raise ValueError(f"historical {spec_name} SHA-256 mismatch")
        if spec_name == "parser_module":
            materialized = normalize_bsl(target_bytes)
            if reverse_parser_adaptation(materialized) != source_bytes:
                raise ValueError("materialized parser does not reverse to historical source")
        elif spec.hash_scope == "normalized_utf8_lf":
            materialized = normalize_bsl(target_bytes)
        else:
            materialized = target_bytes
        actual = _sha256(materialized)
        if actual != spec.materialized_sha256:
            raise ValueError(
                f"materialized {spec_name} SHA-256 mismatch: {actual} != {spec.materialized_sha256}"
            )
        hashes[spec_name] = actual
    return hashes


def current_hashes(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in ("lexer_module", "parser_module", "legacy_model_factory_module"):
        spec = ARTIFACTS[name]
        result[name] = _sha256(normalize_bsl((repo / spec.source_path).read_bytes()))
    return result


def validate_artifact_rows(artifacts: object, component: str) -> None:
    if component not in EXPECTED_ARTIFACTS:
        raise ValueError(f"unsupported component: {component}")
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
                    f"{component}.artifacts[{index}].{field}: {artifact[field]!r} != {expected_row[field]!r}"
                )


def _positive_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _validate_corpus(corpus: object, component: str, index: int) -> None:
    prefix = f"{component}.corpora[{index}]"
    if not isinstance(corpus, dict):
        raise ValueError(f"{prefix} must be an object")
    missing = REQUIRED_CORPUS_FIELDS - set(corpus)
    if missing:
        raise ValueError(f"{prefix} missing fields: {', '.join(sorted(missing))}")
    if corpus["id"] != EXPECTED_CORPUS_IDS[index]:
        raise ValueError(f"{prefix}.id mismatch")
    if not _positive_integer(corpus["input_count"]):
        raise ValueError(f"{prefix}.input_count must be positive")
    inputs = corpus["inputs"]
    if not isinstance(inputs, list) or len(inputs) != corpus["input_count"]:
        raise ValueError(f"{prefix}.inputs count mismatch")
    if index == 0 and corpus["input_count"] != 42:
        raise ValueError(f"{prefix}.input_count must be 42")
    for input_index, item in enumerate(inputs):
        input_prefix = f"{prefix}.inputs[{input_index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{input_prefix} must be an object")
        if not {"id", "input_length", "provenance"}.issubset(item):
            raise ValueError(f"{input_prefix} missing required fields")
        if component == "lexer" and not _positive_integer(item.get("token_count")):
            raise ValueError(f"{input_prefix}.token_count must be positive")
    if corpus["operation_count_per_iteration"] != corpus["input_count"]:
        raise ValueError(f"{prefix}.operation_count_per_iteration mismatch")
    if corpus["operations_per_sample"] != (
        corpus["iterations_per_sample"] * corpus["input_count"]
    ):
        raise ValueError(f"{prefix}.operations_per_sample mismatch")
    for field in (
        "input_length",
        "operation_count_per_iteration",
        "operations_per_sample",
        "iterations_per_sample",
    ):
        if not _positive_integer(corpus[field]):
            raise ValueError(f"{prefix}.{field} must be positive")
    if corpus["warmup_count"] != 3:
        raise ValueError(f"{prefix}.warmup_count mismatch")
    if corpus["sample_count"] != 20:
        raise ValueError(f"{prefix}.sample_count mismatch")
    samples = corpus["samples_ms"]
    if not isinstance(samples, list) or len(samples) != 20 or not all(_positive_number(sample) for sample in samples):
        raise ValueError(f"{prefix}.samples_ms must contain 20 positive samples")
    for field in ("wall_clock_median_ms", "wall_clock_p95_ms"):
        if not _positive_number(corpus[field]):
            raise ValueError(f"{prefix}.{field} must be positive")
    if component == "lexer":
        if not _positive_integer(corpus.get("token_count")):
            raise ValueError(f"{prefix}.token_count must be positive")
        input_token_count = sum(item["token_count"] for item in inputs)
        if corpus["token_count"] != input_token_count:
            raise ValueError(f"{prefix}.token_count mismatch")
        if corpus.get("token_reads_per_iteration") != input_token_count + corpus["input_count"]:
            raise ValueError(f"{prefix}.token_reads_per_iteration mismatch")
    elif corpus.get("parse_calls_per_sample") != corpus["operations_per_sample"]:
        raise ValueError(f"{prefix}.parse_calls_per_sample mismatch")
    if corpus["id"] == "time_accounting_large":
        _validate_time_accounting_corpus(corpus, prefix)


def _validate_time_accounting_corpus(corpus: dict[str, Any], prefix: str) -> None:
    if corpus["entrypoint"] != "Разобрать":
        raise ValueError(f"{prefix} time_accounting_large entrypoint mismatch")
    if corpus["provenance"] != EXPECTED_TIME_ACCOUNTING_PROVENANCE:
        raise ValueError(f"{prefix} time_accounting_large provenance mismatch")
    if corpus["generator_parameters"] != EXPECTED_TIME_ACCOUNTING_LARGE:
        raise ValueError(f"{prefix} time_accounting_large generator manifest mismatch")
    if corpus["input_count"] != 1 or corpus["input_length"] != 160135:
        raise ValueError(f"{prefix} time_accounting_large input dimensions mismatch")
    item = corpus["inputs"][0]
    expected_provenance = {
        "type": "common_template_text_document",
        **EXPECTED_TIME_ACCOUNTING_LARGE,
    }
    if item.get("id") != "time_accounting_large_1":
        raise ValueError(f"{prefix} time_accounting_large input id mismatch")
    if item.get("input_length") != 160135:
        raise ValueError(f"{prefix} time_accounting_large input length mismatch")
    if item.get("provenance") != expected_provenance:
        raise ValueError(f"{prefix} time_accounting_large input provenance mismatch")


def validate_sidecar(document: object, component: str) -> None:
    if component not in EXPECTED_SIDECARS:
        raise ValueError(f"unsupported component: {component}")
    if not isinstance(document, dict):
        raise ValueError(f"{component} sidecar must be an object")
    expected_top_level = REQUIRED_TOP_LEVEL | (
        {"parser_artifact"} if component == "parser" else set()
    )
    if set(document) != expected_top_level:
        raise ValueError(f"{component} sidecar top-level field set mismatch")
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
    if document["source_ref"] != "origin/old_parser":
        raise ValueError(f"{component}.source_ref mismatch")
    if document["source_commit"] != EXPECTED_COMMIT:
        raise ValueError(f"{component}.source_commit mismatch")
    metadata_object_names = document["metadata_object_names"]
    if not isinstance(metadata_object_names, list) or tuple(metadata_object_names) != expected["metadata_object_names"]:
        raise ValueError(f"{component}.metadata_object_names mismatch")
    if document["warmup_count"] != 3:
        raise ValueError(f"{component}.warmup_count mismatch")
    if document["sample_count"] != 20:
        raise ValueError(f"{component}.sample_count mismatch")
    if document["batch_calibration_target_ms"] != 25:
        raise ValueError(f"{component}.batch_calibration_target_ms mismatch")
    if document["clock"] != EXPECTED_CLOCK:
        raise ValueError(f"{component}.clock mismatch")
    validate_artifact_rows(document["artifacts"], component)
    if component == "parser":
        parser_artifact = document["artifacts"][0]
        if document.get("parser_artifact") != parser_artifact:
            raise ValueError("parser.parser_artifact must equal parser-role artifact")
    corpora = document["corpora"]
    if not isinstance(corpora, list) or len(corpora) != len(EXPECTED_CORPUS_IDS):
        raise ValueError(f"{component}.corpora count mismatch")
    if tuple(corpus.get("id") if isinstance(corpus, dict) else None for corpus in corpora) != EXPECTED_CORPUS_IDS:
        raise ValueError(f"{component}.corpora order mismatch")
    for index, corpus in enumerate(corpora):
        _validate_corpus(corpus, component, index)


def _load_json_bytes(payload: bytes) -> Any:
    return json.loads(payload.decode("utf-8-sig"))


def _load_sidecar(path: Path) -> dict[str, Any]:
    value = _load_json_bytes(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"sidecar must be a JSON object: {path}")
    return value


def validate_capture_sidecars(repo: Path, lexer_path: Path, parser_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        verify_materialized_sources(repo)
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError) as error:
        raise ProvenanceMaterializationError(str(error)) from error
    lexer = _load_sidecar(lexer_path)
    parser = _load_sidecar(parser_path)
    validate_sidecar(lexer, "lexer")
    validate_sidecar(parser, "parser")
    return lexer, parser


def _markdown_table(document: dict[str, Any]) -> list[str]:
    rows = [
        "| corpus | input_count | input_length | operation_count_per_iteration | median_ms | p95_ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for corpus in document["corpora"]:
        rows.append(
            "| {id} | {input_count} | {input_length} | {operation_count_per_iteration} | {wall_clock_median_ms} | {wall_clock_p95_ms} |".format(
                **corpus
            )
        )
    return rows


def render_markdown(
    lexer_document: dict[str, Any],
    parser_document: dict[str, Any],
    lexer_json_sha256: str,
    parser_json_sha256: str,
) -> str:
    return "\n".join(
        [
            "# Runtime baseline старых lexer и parser",
            "",
            "## Provenance",
            "",
            f"- lexer_json_sha256: `{lexer_json_sha256}`",
            f"- parser_json_sha256: `{parser_json_sha256}`",
            f"- source_ref: `{lexer_document['source_ref']}`",
            f"- source_commit: `{lexer_document['source_commit']}`",
            "",
            "## Lexer",
            "",
            *_markdown_table(lexer_document),
            "",
            "## Parser",
            "",
            *_markdown_table(parser_document),
            "",
        ]
    )


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary_path)
        os.replace(temporary_path, target)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def publish(repo: Path, lexer_path: Path, parser_path: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    validate_capture_sidecars(repo, lexer_path, parser_path)
    durable_lexer = output_dir / "2026-08-08-runtime-old-lexer-baseline.json"
    durable_parser = output_dir / "2026-08-08-runtime-old-parser-baseline.json"
    durable_report = output_dir / "2026-08-08-runtime-old-lexer-parser-baseline.md"
    _atomic_copy(lexer_path, durable_lexer)
    _atomic_copy(parser_path, durable_parser)
    lexer_bytes = durable_lexer.read_bytes()
    parser_bytes = durable_parser.read_bytes()
    markdown = render_markdown(
        _load_json_bytes(lexer_bytes),
        _load_json_bytes(parser_bytes),
        _sha256(lexer_bytes),
        _sha256(parser_bytes),
    )
    _atomic_write(durable_report, markdown.encode("utf-8"))
    return durable_lexer, durable_parser, durable_report


def validate_durable(lexer_path: Path, parser_path: Path, report_path: Path) -> None:
    lexer_bytes = lexer_path.read_bytes()
    parser_bytes = parser_path.read_bytes()
    lexer_document = _load_json_bytes(lexer_bytes)
    parser_document = _load_json_bytes(parser_bytes)
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


def _write_json(value: object) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(payload.decode("utf-8"))
    else:
        buffer.write(payload)


def _arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Old parser/lexer baseline provenance utility")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("verify-ref", "verify-source", "current-hashes"):
        command = commands.add_parser(name)
        command.add_argument("--repo", type=Path, default=Path("."))
    materialize = commands.add_parser("materialize")
    materialize.add_argument("--repo", type=Path, default=Path("."))
    materialize.add_argument("--target-dir", type=Path, default=Path("build/legacy-runtime-baseline-source"))
    for name in ("validate-sidecars", "publish"):
        command = commands.add_parser(name)
        command.add_argument("--repo", type=Path, default=Path("."))
        command.add_argument("--lexer", type=Path, required=True)
        command.add_argument("--parser", type=Path, required=True)
        if name == "publish":
            command.add_argument("--output-dir", type=Path, required=True)
    durable = commands.add_parser("validate-durable")
    durable.add_argument("--lexer", type=Path, required=True)
    durable.add_argument("--parser", type=Path, required=True)
    durable.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _arguments().parse_args(argv)
    try:
        if arguments.command == "verify-ref":
            _write_json(verify_ref(arguments.repo))
        elif arguments.command == "materialize":
            _write_json(materialize_sources(arguments.repo, arguments.target_dir))
        elif arguments.command == "verify-source":
            _write_json(verify_materialized_sources(arguments.repo))
        elif arguments.command == "current-hashes":
            _write_json(current_hashes(arguments.repo))
        elif arguments.command == "validate-sidecars":
            lexer, parser = validate_capture_sidecars(arguments.repo, arguments.lexer, arguments.parser)
            _write_json({"lexer": lexer["benchmark_id"], "parser": parser["benchmark_id"]})
        elif arguments.command == "publish":
            paths = publish(arguments.repo, arguments.lexer, arguments.parser, arguments.output_dir)
            _write_json({"lexer": str(paths[0]), "parser": str(paths[1]), "report": str(paths[2])})
        else:
            validate_durable(arguments.lexer, arguments.parser, arguments.report)
            _write_json({"status": "valid"})
    except ProvenanceMaterializationError as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 3 if arguments.command in {"validate-sidecars", "publish", "validate-durable"} else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
