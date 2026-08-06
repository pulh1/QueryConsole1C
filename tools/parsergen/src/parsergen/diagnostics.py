from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True, order=True)
class SourcePosition:
    line: int
    column: int
    offset: int


@dataclass(frozen=True, slots=True)
class SourceSpan:
    path: str
    start: SourcePosition
    end: SourcePosition


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class RelatedLocation:
    message: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    span: SourceSpan
    related: tuple[RelatedLocation, ...] = ()
    details: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.span.path,
            self.span.start.offset,
            self.code,
            tuple(item.span.start.offset for item in self.related),
        )


class DiagnosticBag:
    def __init__(self, diagnostics: Iterable[Diagnostic] = ()) -> None:
        self._items = list(diagnostics)

    def add(self, diagnostic: Diagnostic) -> None:
        self._items.append(diagnostic)

    def extend(self, diagnostics: Iterable[Diagnostic]) -> None:
        self._items.extend(diagnostics)

    @property
    def has_errors(self) -> bool:
        return any(item.severity is Severity.ERROR for item in self._items)

    def sorted(self) -> tuple[Diagnostic, ...]:
        return tuple(sorted(self._items, key=Diagnostic.sort_key))
