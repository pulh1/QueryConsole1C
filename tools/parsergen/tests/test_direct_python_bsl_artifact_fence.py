from hashlib import sha256
from pathlib import Path
import subprocess

from parsergen.artifacts import ArtifactSet, render_artifacts
from parsergen.cli import compile_from_config, generate_from_compilation
from parsergen.config import load_config


ROOT = Path(__file__).parents[3]
EXPECTED_GIT_BLOBS = {
    "QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl":
        "e1ef168aa409e4651569e34cdb2288624fa97cee566e5b976e4cd9becc83a0da",
    "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt":
        "e26a6b3b4fe08455462145de3243338d5da1c8bbb657321a2162b0abe541e208",
    "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt":
        "4cd2f1d11a0d92f57e029c0b06b6e936b8bb16090a111ee9f43dde5a86e69340",
}
EXPECTED_GENERATED = {
    "object_module":
        "4064d39fb8bfd6a0e9fde489692fb5b35c54634e14afea33e25931cd07fdb7ef",
    "select_template":
        "acb80f86f739d5a4a54fe7d6f2c85cdc57a2d664d779a1f1e51a0aaf54a059c1",
    "identifier_template":
        "c49de3e16af30dfbfb9e035163c99c39b40e6f797b38b5f942c3d969c50415ed",
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
