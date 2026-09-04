from hashlib import sha256
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[3]
EXPECTED = {
    "QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl":
        "f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf",
    "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt":
        "e26a6b3b4fe08455462145de3243338d5da1c8bbb657321a2162b0abe541e208",
    "QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt":
        "107fdbdefd57f5b6fe0658037b67806fc95f24a27d3e948eeeeaeb3335ffeff2",
}


def test_direct_python_work_keeps_raw_bsl_artifacts_byte_identical() -> None:
    assert {
        relative: sha256(
            subprocess.run(
                ["git", "show", f"HEAD:{relative}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
        ).hexdigest()
        for relative in EXPECTED
    } == EXPECTED
