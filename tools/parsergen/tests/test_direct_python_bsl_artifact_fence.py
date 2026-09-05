from hashlib import sha256
from pathlib import Path
import subprocess

from parsergen.artifacts import ArtifactSet, render_artifacts
from parsergen.cli import compile_from_config, generate_from_compilation
from parsergen.config import load_config


ROOT = Path(__file__).parents[3]
EXPECTED_GIT_BLOBS = {
    "QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl":
        "f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf",
    "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt":
        "e26a6b3b4fe08455462145de3243338d5da1c8bbb657321a2162b0abe541e208",
    "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt":
        "107fdbdefd57f5b6fe0658037b67806fc95f24a27d3e948eeeeaeb3335ffeff2",
}
EXPECTED_GENERATED = {
    "object_module":
        "358a6123f91cd9068a08c76b3849ffad69f10eb0c7b2ed90b650f87304b960e8",
    "select_template":
        "acb80f86f739d5a4a54fe7d6f2c85cdc57a2d664d779a1f1e51a0aaf54a059c1",
    "identifier_template":
        "13472cb0e1482b5c590a306fe6fc119d026546069e717d8eadd010b6a8661ef6",
}


def fresh_repository_artifacts() -> ArtifactSet:
    config = load_config(ROOT / "parsergen.toml")
    compilation = compile_from_config(config)
    return render_artifacts(generate_from_compilation(config, compilation))


def _artifact_hashes(artifacts: ArtifactSet) -> dict[str, str]:
    return {
        field: sha256(getattr(artifacts, field)).hexdigest()
        for field in (
            "object_module",
            "select_template",
            "identifier_template",
        )
    }


def test_direct_python_work_keeps_raw_bsl_artifacts_byte_identical() -> None:
    first = fresh_repository_artifacts()
    assert _artifact_hashes(first) == EXPECTED_GENERATED
    second = fresh_repository_artifacts()
    assert first == second
    assert {
        relative: sha256(
            subprocess.run(
                ["git", "show", f"HEAD:{relative}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
        ).hexdigest()
        for relative in EXPECTED_GIT_BLOBS
    } == EXPECTED_GIT_BLOBS
