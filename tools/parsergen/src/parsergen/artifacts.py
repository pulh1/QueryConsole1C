from __future__ import annotations

import os
import shutil
import stat
import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .bsl_codegen import GeneratedParser
from .value_table_codec import decode_value_table, encode_value_table


_ROLLBACK_REPLACE = os.replace
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)


@dataclass(frozen=True, slots=True)
class ArtifactSet:
    object_module: bytes
    select_template: bytes
    identifier_template: bytes


@dataclass(frozen=True, slots=True)
class ArtifactComparison:
    changed: tuple[Path, ...]


def artifact_paths(target: Path) -> tuple[Path, Path, Path]:
    root = Path(target)
    return (
        root / "ObjectModule.bsl",
        root / "Templates/ТаблицаПервыхСимволовВариантов/Template.txt",
        root / "Templates/ОпределенияИдентификаторов/Template.txt",
    )


def render_artifacts(generated: GeneratedParser) -> ArtifactSet:
    if not isinstance(generated, GeneratedParser):
        raise TypeError("generated must be a GeneratedParser")
    if not isinstance(generated.module_text, str):
        raise TypeError("generated.module_text must be a string")

    select_text = encode_value_table(generated.select_table)
    if decode_value_table(select_text) != generated.select_table:
        raise ValueError("SELECT ValueTable failed an exact codec round-trip")
    identifier_text = encode_value_table(generated.identifier_table)
    if decode_value_table(identifier_text) != generated.identifier_table:
        raise ValueError("identifier ValueTable failed an exact codec round-trip")

    return ArtifactSet(
        object_module=_normalize_crlf(generated.module_text).encode("utf-8"),
        select_template=select_text.encode("utf-8"),
        identifier_template=identifier_text.encode("utf-8"),
    )


def compare_artifacts(
    target: Path,
    artifacts: ArtifactSet,
) -> ArtifactComparison:
    paths = _validate_layout(Path(target))
    contents = _validate_artifact_bytes(artifacts)
    changed = tuple(
        artifact_path
        for index, (artifact_path, replacement) in enumerate(
            zip(paths, contents)
        )
        if not _artifact_contents_equal(
            index,
            artifact_path.read_bytes(),
            replacement,
        )
    )
    return ArtifactComparison(changed)


def replace_artifacts(
    target: Path,
    artifacts: ArtifactSet,
) -> ArtifactComparison:
    return _replace_artifacts(
        Path(target),
        artifacts,
        forward_replace=os.replace,
    )


def _replace_artifacts(
    target: Path,
    artifacts: ArtifactSet,
    *,
    forward_replace: Callable[[os.PathLike[str], os.PathLike[str]], object],
) -> ArtifactComparison:
    paths = _validate_layout(target)
    contents = _validate_artifact_bytes(artifacts)
    changed_indices = tuple(
        index
        for index, (artifact_path, replacement) in enumerate(zip(paths, contents))
        if not _artifact_contents_equal(
            index,
            artifact_path.read_bytes(),
            replacement,
        )
    )
    changed = tuple(paths[index] for index in changed_indices)
    comparison = ArtifactComparison(changed)
    if not changed:
        return comparison

    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{target.name}.parsergen-",
            dir=target.parent,
        )
    )
    staged: dict[int, Path] = {}
    backups: dict[int, Path] = {}
    operation_failure: BaseException | None = None
    preserve_temporary = False
    try:
        _validate_temporary_sibling(target, temporary)
        for index in changed_indices:
            staged_path = temporary / f"stage-{index}"
            _write_fsynced(staged_path, contents[index])
            staged[index] = staged_path

        for index in changed_indices:
            backup_path = temporary / f"backup-{index}"
            _write_fsynced(backup_path, paths[index].read_bytes())
            backups[index] = backup_path

        try:
            for index in changed_indices:
                forward_replace(staged[index], paths[index])
        except BaseException as primary:
            rollback_failures: list[BaseException] = []
            for index in changed_indices:
                try:
                    _ROLLBACK_REPLACE(backups[index], paths[index])
                except BaseException as rollback:
                    rollback_failures.append(rollback)
            if rollback_failures:
                preserve_temporary = True
                operation_failure = _exception_group(
                    "artifact replacement and rollback both failed; "
                    f"recovery files were preserved at {temporary}",
                    (primary, *rollback_failures),
                )
            else:
                operation_failure = primary
    except BaseException as failure:
        operation_failure = failure

    cleanup_failure: BaseException | None = None
    if not preserve_temporary:
        try:
            _remove_temporary_sibling(target, temporary)
        except BaseException as failure:
            cleanup_failure = failure

    if cleanup_failure is not None:
        if operation_failure is None:
            operation_failure = cleanup_failure
        else:
            operation_failure = _exception_group(
                "artifact transaction failed and its temporary directory "
                "could not be cleaned",
                (operation_failure, cleanup_failure),
            )
    if operation_failure is not None:
        raise operation_failure
    return comparison


def _normalize_crlf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")


def _validate_artifact_bytes(artifacts: ArtifactSet) -> tuple[bytes, bytes, bytes]:
    if not isinstance(artifacts, ArtifactSet):
        raise TypeError("artifacts must be an ArtifactSet")
    fields = (
        ("object_module", artifacts.object_module),
        ("select_template", artifacts.select_template),
        ("identifier_template", artifacts.identifier_template),
    )
    for name, value in fields:
        if not isinstance(value, bytes):
            raise TypeError(f"{name} must be bytes")
    return (
        artifacts.object_module,
        artifacts.select_template,
        artifacts.identifier_template,
    )


def _artifact_contents_equal(
    index: int,
    current: bytes,
    replacement: bytes,
) -> bool:
    if current == replacement:
        return True
    if index == 0:
        try:
            return _normalize_crlf(current.decode("utf-8")) == _normalize_crlf(
                replacement.decode("utf-8")
            )
        except UnicodeDecodeError:
            return False
    try:
        current_table = decode_value_table(current.decode("utf-8"))
        replacement_table = decode_value_table(replacement.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False

    # Legacy compatibility: the reference 1C serializer preserves internal
    # column identifiers and hash-dependent row order. They are not parser
    # semantics, so compare decoded columns and the row multiset instead of
    # forcing canonical Python serialization over a compatible artifact.
    return (
        current_table.columns == replacement_table.columns
        and Counter(current_table.rows) == Counter(replacement_table.rows)
    )


def _validate_layout(target: Path) -> tuple[Path, Path, Path]:
    if not target.exists() or not target.is_dir():
        raise ValueError(f"target is not an existing data processor: {target}")
    _reject_link_or_reparse(target, "target")

    mdo_candidates = tuple(
        child
        for child in target.iterdir()
        if child.suffix.casefold() == ".mdo"
    )
    if len(mdo_candidates) != 1:
        raise ValueError(
            "target must contain exactly one direct-child regular .mdo file"
        )
    mdo_file = mdo_candidates[0]
    _reject_link_or_reparse(mdo_file, "data processor metadata file")
    if not mdo_file.is_file():
        raise ValueError(
            "target .mdo entry must be a direct-child regular file"
        )

    paths = artifact_paths(target)
    resolved_target = target.resolve(strict=True)
    checked_components: set[Path] = set()
    for artifact_path in paths:
        relative = artifact_path.relative_to(target)
        current = target
        for part in relative.parts:
            current /= part
            if current in checked_components:
                continue
            checked_components.add(current)
            if not current.exists():
                raise ValueError(f"required artifact path does not exist: {current}")
            _reject_link_or_reparse(current, "artifact layout component")
        if not artifact_path.is_file():
            raise ValueError(
                f"required artifact is not a regular file: {artifact_path}"
            )
        try:
            artifact_path.resolve(strict=True).relative_to(resolved_target)
        except ValueError as error:
            raise ValueError(
                f"artifact path resolves outside target: {artifact_path}"
            ) from error
    return paths


def _is_link_or_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & _REPARSE_POINT)


def _reject_link_or_reparse(path: Path, description: str) -> None:
    if _is_link_or_reparse(path):
        raise ValueError(f"{description} must not be a link or reparse point: {path}")


def _write_fsynced(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _validate_temporary_sibling(target: Path, temporary: Path) -> None:
    if temporary.parent.resolve(strict=True) != target.parent.resolve(strict=True):
        raise RuntimeError("transaction directory is not a target sibling")
    if not temporary.is_dir() or _is_link_or_reparse(temporary):
        raise RuntimeError("transaction path is not a regular sibling directory")


def _remove_temporary_sibling(target: Path, temporary: Path) -> None:
    expected_parent = target.parent.resolve(strict=True)
    if temporary.parent.resolve(strict=True) != expected_parent:
        raise RuntimeError("refusing to clean an unverified transaction directory")
    prefix = f".{target.name}.parsergen-"
    if not temporary.name.startswith(prefix):
        raise RuntimeError("refusing to clean an unexpected transaction directory")
    if temporary.exists():
        _reject_link_or_reparse(temporary, "transaction directory")
        shutil.rmtree(temporary)


def _exception_group(
    message: str,
    failures: tuple[BaseException, ...],
) -> BaseExceptionGroup:
    if all(isinstance(item, Exception) for item in failures):
        return ExceptionGroup(
            message,
            failures,  # type: ignore[arg-type]
        )
    return BaseExceptionGroup(message, failures)
