from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from parsergen.artifacts import (
    ArtifactSet,
    artifact_paths,
    compare_artifacts,
    render_artifacts,
    replace_artifacts,
)
from parsergen.bsl_codegen import GeneratedParser
from parsergen.value_table_codec import (
    ColumnKind,
    ValueColumn,
    ValueTable,
    decode_value_table,
    encode_value_table,
)


def sample_table(prefix: str) -> ValueTable:
    return ValueTable(
        (
            ValueColumn("Имя", ColumnKind.STRING),
            ValueColumn("Номер", ColumnKind.NUMBER),
        ),
        (
            (f"{prefix} строка", 1),
            (None, -2),
        ),
    )


class ArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def make_target(self, name: str = "Парсер") -> Path:
        target = self.root / name
        (target / "Templates/ТаблицаПервыхСимволовВариантов").mkdir(
            parents=True
        )
        (target / "Templates/ОпределенияИдентификаторов").mkdir(parents=True)
        (target / "Парсер.mdo").write_bytes(b"<dataProcessor/>")
        (target / "ManagerModule.bsl").write_bytes(b"untouched\x00manager")
        originals = (b"old module", b"old select", b"old identifiers")
        for artifact_path, content in zip(artifact_paths(target), originals):
            artifact_path.write_bytes(content)
        return target

    def assert_no_transaction_directories(self, target: Path) -> None:
        prefix = f".{target.name}.parsergen-"
        leftovers = [
            child for child in target.parent.iterdir()
            if child.name.startswith(prefix)
        ]
        self.assertEqual(leftovers, [])

    def test_artifact_paths_have_fixed_order(self) -> None:
        target = self.root / "Парсер"

        self.assertEqual(
            artifact_paths(target),
            (
                target / "ObjectModule.bsl",
                target
                / "Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
                target
                / "Templates/ОпределенияИдентификаторов/Template.txt",
            ),
        )

    def test_render_normalizes_module_and_round_trips_both_tables(self) -> None:
        select = sample_table("select")
        identifiers = sample_table("identifier")
        generated = GeneratedParser(
            "первая\nвторая\rтретья\r\nчетвертая",
            select,
            identifiers,
            ("Узел",),
        )

        artifacts = render_artifacts(generated)

        self.assertEqual(
            artifacts.object_module,
            "первая\r\nвторая\r\nтретья\r\nчетвертая".encode("utf-8"),
        )
        self.assertFalse(artifacts.object_module.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(
            decode_value_table(artifacts.select_template.decode("utf-8")),
            select,
        )
        self.assertEqual(
            decode_value_table(artifacts.identifier_template.decode("utf-8")),
            identifiers,
        )
        self.assertEqual(render_artifacts(generated), artifacts)

    def test_reference_templates_are_utf8_value_tables_without_bom(self) -> None:
        fixture = Path(__file__).parent / "fixtures/reference_parser/Templates"
        for relative in (
            "ТаблицаПервыхСимволовВариантов/Template.txt",
            "ОпределенияИдентификаторов/Template.txt",
        ):
            with self.subTest(relative=relative):
                content = (fixture / relative).read_bytes()
                self.assertFalse(content.startswith(b"\xef\xbb\xbf"))
                decoded = decode_value_table(content.decode("utf-8"))
                self.assertGreater(len(decoded.rows), 0)

    def test_rejects_missing_target_wrong_mdo_count_and_missing_artifacts(
        self,
    ) -> None:
        artifacts = ArtifactSet(b"a", b"b", b"c")
        cases: list[tuple[str, Path]] = [
            ("missing-target", self.root / "missing"),
            ("plain-directory", self.root / "plain"),
        ]
        cases[1][1].mkdir()
        extra_mdo = self.make_target("extra-mdo")
        (extra_mdo / "Second.mdo").write_bytes(b"x")
        cases.append(("extra-mdo", extra_mdo))
        disguised_extra_mdo = self.make_target("directory-mdo")
        (disguised_extra_mdo / "Second.mdo").mkdir()
        cases.append(("directory-mdo", disguised_extra_mdo))
        missing_artifact = self.make_target("missing-artifact")
        artifact_paths(missing_artifact)[1].unlink()
        cases.append(("missing-artifact", missing_artifact))
        for label, target in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    compare_artifacts(target, artifacts)

    def test_rejects_symlinked_artifact_and_layout_directory(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks are unavailable")
        artifacts = ArtifactSet(b"a", b"b", b"c")

        linked_file_target = self.make_target("linked-file")
        external_file = self.root / "external-template.txt"
        external_file.write_bytes(b"external")
        linked_file = artifact_paths(linked_file_target)[1]
        linked_file.unlink()
        try:
            linked_file.symlink_to(external_file)
        except OSError as error:
            self.skipTest(f"symlink creation unavailable: {error}")
        with self.assertRaisesRegex(ValueError, "link|reparse"):
            compare_artifacts(linked_file_target, artifacts)

        linked_dir_target = self.make_target("linked-directory")
        identifier_dir = (
            linked_dir_target / "Templates/ОпределенияИдентификаторов"
        )
        identifier_file = identifier_dir / "Template.txt"
        identifier_file.unlink()
        identifier_dir.rmdir()
        external_dir = self.root / "external-directory"
        external_dir.mkdir()
        (external_dir / "Template.txt").write_bytes(b"external")
        identifier_dir.symlink_to(external_dir, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "link|reparse"):
            compare_artifacts(linked_dir_target, artifacts)

    def test_rejects_mocked_reparse_artifact_without_symlink_privilege(
        self,
    ) -> None:
        target = self.make_target()
        blocked = artifact_paths(target)[2]
        real_lstat = Path.lstat

        def lstat_with_reparse(path_value: Path) -> os.stat_result | object:
            if path_value == blocked:
                return SimpleNamespace(
                    st_mode=stat.S_IFREG,
                    st_file_attributes=1,
                )
            return real_lstat(path_value)

        with (
            mock.patch.object(Path, "lstat", new=lstat_with_reparse),
            mock.patch("parsergen.artifacts._REPARSE_POINT", 1),
        ):
            with self.assertRaisesRegex(ValueError, "link|reparse"):
                compare_artifacts(target, ArtifactSet(b"a", b"b", b"c"))

    def test_compare_reports_none_one_and_three_changes_without_writes(self) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        original = tuple(item.read_bytes() for item in paths)
        manager = (target / "ManagerModule.bsl").read_bytes()
        cases = (
            ("none", ArtifactSet(*original), ()),
            (
                "one",
                ArtifactSet(original[0], b"new select", original[2]),
                (paths[1],),
            ),
            (
                "three",
                ArtifactSet(b"a", b"b", b"c"),
                paths,
            ),
        )
        for label, artifacts, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(compare_artifacts(target, artifacts).changed, expected)
                self.assertEqual(
                    tuple(item.read_bytes() for item in paths),
                    original,
                )
                self.assertEqual(
                    (target / "ManagerModule.bsl").read_bytes(),
                    manager,
                )
                self.assert_no_transaction_directories(target)

    def test_compare_ignores_object_module_line_ending_style(self) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        paths[0].write_bytes("первая\nвторая\n".encode("utf-8"))
        artifacts = ArtifactSet(
            "первая\r\nвторая\r\n".encode("utf-8"),
            paths[1].read_bytes(),
            paths[2].read_bytes(),
        )

        self.assertEqual(compare_artifacts(target, artifacts).changed, ())
        self.assertEqual(replace_artifacts(target, artifacts).changed, ())
        self.assertEqual(
            paths[0].read_bytes(),
            "первая\nвторая\n".encode("utf-8"),
        )

    def test_compare_ignores_value_table_row_order(self) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        original_table = sample_table("select")
        reordered_table = ValueTable(
            original_table.columns,
            tuple(reversed(original_table.rows)),
        )
        original_select = encode_value_table(original_table).encode("utf-8")
        reordered_select = encode_value_table(reordered_table).encode("utf-8")
        paths[0].write_bytes(b"module")
        paths[1].write_bytes(original_select)
        paths[2].write_bytes(b"identifiers")

        artifacts = ArtifactSet(
            b"module",
            reordered_select,
            b"identifiers",
        )

        self.assertEqual(compare_artifacts(target, artifacts).changed, ())
        self.assertEqual(replace_artifacts(target, artifacts).changed, ())
        self.assertEqual(paths[1].read_bytes(), original_select)

    def test_replaces_only_three_artifacts_and_idempotent_second_is_noop(
        self,
    ) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        artifacts = ArtifactSet(b"module", b"select", b"identifiers")
        manager = target / "ManagerModule.bsl"
        manager_before = manager.read_bytes()

        first = replace_artifacts(target, artifacts)
        with mock.patch("parsergen.artifacts.os.replace") as replaced:
            second = replace_artifacts(target, artifacts)

        self.assertEqual(first.changed, paths)
        self.assertEqual(second.changed, ())
        replaced.assert_not_called()
        self.assertEqual(
            tuple(item.read_bytes() for item in paths),
            (b"module", b"select", b"identifiers"),
        )
        self.assertEqual(manager.read_bytes(), manager_before)
        self.assert_no_transaction_directories(target)

    def test_failure_on_each_forward_replace_restores_every_original(self) -> None:
        for failure_number in (1, 2, 3):
            with self.subTest(failure_number=failure_number):
                target = self.make_target(f"failure-{failure_number}")
                paths = artifact_paths(target)
                originals = tuple(item.read_bytes() for item in paths)
                real_replace = os.replace
                calls = 0

                def failing_replace(source: object, destination: object) -> None:
                    nonlocal calls
                    calls += 1
                    if calls == failure_number:
                        raise OSError(f"forced failure {failure_number}")
                    real_replace(source, destination)

                with mock.patch(
                    "parsergen.artifacts.os.replace",
                    side_effect=failing_replace,
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        f"forced failure {failure_number}",
                    ):
                        replace_artifacts(
                            target,
                            ArtifactSet(b"a", b"b", b"c"),
                        )

                self.assertEqual(
                    tuple(item.read_bytes() for item in paths),
                    originals,
                )
                self.assert_no_transaction_directories(target)

    def test_rollback_uses_captured_primitive_when_os_replace_is_patched(
        self,
    ) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        originals = tuple(item.read_bytes() for item in paths)

        with mock.patch(
            "parsergen.artifacts.os.replace",
            side_effect=OSError("patched forward replace"),
        ):
            with self.assertRaisesRegex(OSError, "patched forward replace"):
                replace_artifacts(target, ArtifactSet(b"a", b"b", b"c"))

        self.assertEqual(tuple(item.read_bytes() for item in paths), originals)
        self.assert_no_transaction_directories(target)

    def test_rollback_failure_preserves_backups_and_both_failures(self) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        originals = tuple(item.read_bytes() for item in paths)

        with (
            mock.patch(
                "parsergen.artifacts.os.replace",
                side_effect=OSError("forced forward failure"),
            ),
            mock.patch(
                "parsergen.artifacts._ROLLBACK_REPLACE",
                side_effect=OSError("forced rollback failure"),
            ),
        ):
            with self.assertRaises(BaseExceptionGroup) as raised:
                replace_artifacts(target, ArtifactSet(b"a", b"b", b"c"))

        messages = tuple(str(error) for error in raised.exception.exceptions)
        self.assertTrue(any("forced forward failure" in item for item in messages))
        self.assertTrue(any("forced rollback failure" in item for item in messages))
        prefix = f".{target.name}.parsergen-"
        transaction_directories = tuple(
            child
            for child in target.parent.iterdir()
            if child.name.startswith(prefix)
        )
        self.assertEqual(len(transaction_directories), 1)
        transaction = transaction_directories[0]
        self.assertIn(str(transaction), str(raised.exception))
        self.assertEqual(
            tuple((transaction / f"backup-{index}").read_bytes() for index in range(3)),
            originals,
        )

    def test_cleanup_failure_does_not_replace_forward_failure(self) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        originals = tuple(item.read_bytes() for item in paths)

        with (
            mock.patch(
                "parsergen.artifacts.os.replace",
                side_effect=OSError("forced forward failure"),
            ),
            mock.patch(
                "parsergen.artifacts.shutil.rmtree",
                side_effect=OSError("forced cleanup failure"),
            ),
        ):
            with self.assertRaises(BaseExceptionGroup) as raised:
                replace_artifacts(target, ArtifactSet(b"a", b"b", b"c"))

        messages = tuple(str(error) for error in raised.exception.exceptions)
        self.assertTrue(any("forced forward failure" in item for item in messages))
        self.assertTrue(any("forced cleanup failure" in item for item in messages))
        self.assertEqual(tuple(item.read_bytes() for item in paths), originals)

    def test_staged_fsync_failure_leaves_targets_untouched(self) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        originals = tuple(item.read_bytes() for item in paths)

        with mock.patch(
            "parsergen.artifacts.os.fsync",
            side_effect=OSError("forced fsync failure"),
        ):
            with self.assertRaisesRegex(OSError, "forced fsync failure"):
                replace_artifacts(target, ArtifactSet(b"a", b"b", b"c"))

        self.assertEqual(tuple(item.read_bytes() for item in paths), originals)
        self.assert_no_transaction_directories(target)

    def test_transaction_validation_failure_cleans_temporary_sibling(self) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        originals = tuple(item.read_bytes() for item in paths)

        with mock.patch(
            "parsergen.artifacts._validate_temporary_sibling",
            side_effect=RuntimeError("forced transaction validation failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "forced transaction validation failure",
            ):
                replace_artifacts(target, ArtifactSet(b"a", b"b", b"c"))

        self.assertEqual(tuple(item.read_bytes() for item in paths), originals)
        self.assert_no_transaction_directories(target)

    def test_invalid_artifact_field_types_are_rejected_before_writes(self) -> None:
        target = self.make_target()
        paths = artifact_paths(target)
        originals = tuple(item.read_bytes() for item in paths)
        invalid = ArtifactSet(b"module", "select", b"identifiers")  # type: ignore[arg-type]

        with mock.patch("parsergen.artifacts.os.replace") as replaced:
            with self.assertRaisesRegex(TypeError, "select_template"):
                replace_artifacts(target, invalid)

        replaced.assert_not_called()
        self.assertEqual(tuple(item.read_bytes() for item in paths), originals)
        self.assert_no_transaction_directories(target)


if __name__ == "__main__":
    unittest.main()
