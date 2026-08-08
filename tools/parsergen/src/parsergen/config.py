from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ParsergenConfig:
    grammar: Path
    target: Path
    lookahead: int
    entrypoints: Mapping[str, str]
    canonical_productions: tuple[str, ...] = ()


def load_config(path: Path) -> ParsergenConfig:
    config_path = Path(path)
    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    expected = {
        "grammar",
        "target",
        "lookahead",
        "entrypoints",
        "migration",
    }
    unexpected = tuple(key for key in parsed if key not in expected)
    if unexpected:
        names = ", ".join(repr(key) for key in unexpected)
        raise ValueError(f"unexpected top-level configuration keys: {names}")

    grammar = _required_path(parsed, "grammar", config_path.parent)
    target = _required_path(parsed, "target", config_path.parent)

    lookahead = parsed.get("lookahead")
    if (
        isinstance(lookahead, bool)
        or not isinstance(lookahead, int)
        or lookahead < 1
    ):
        raise ValueError("lookahead must be an integer greater than or equal to 1")

    raw_entrypoints = parsed.get("entrypoints")
    if not isinstance(raw_entrypoints, dict) or not raw_entrypoints:
        raise ValueError("entrypoints must be a non-empty TOML table")
    entrypoints: dict[str, str] = {}
    for name, production in raw_entrypoints.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("entrypoints keys must be non-empty strings")
        if not isinstance(production, str) or not production.strip():
            raise ValueError("entrypoints values must be non-empty strings")
        entrypoints[name] = production

    canonical_productions = _canonical_productions(parsed.get("migration"))

    return ParsergenConfig(
        grammar=grammar,
        target=target,
        lookahead=lookahead,
        entrypoints=MappingProxyType(entrypoints),
        canonical_productions=canonical_productions,
    )


def _canonical_productions(raw_migration: object) -> tuple[str, ...]:
    if raw_migration is None:
        return ()
    if not isinstance(raw_migration, dict):
        raise ValueError("migration must be a TOML table")
    unexpected = tuple(
        key for key in raw_migration if key != "canonical_productions"
    )
    if unexpected:
        names = ", ".join(repr(key) for key in unexpected)
        raise ValueError(f"unexpected migration keys: {names}")
    raw_names = raw_migration.get("canonical_productions")
    if not isinstance(raw_names, list) or not raw_names:
        raise ValueError(
            "migration.canonical_productions must be a non-empty string array"
        )
    if any(not isinstance(name, str) or not name.strip() for name in raw_names):
        raise ValueError(
            "migration.canonical_productions must contain non-empty strings"
        )
    names = tuple(raw_names)
    if len(frozenset(names)) != len(names):
        raise ValueError(
            "migration.canonical_productions must not contain duplicates"
        )
    return names


def _required_path(
    parsed: dict[str, object],
    key: str,
    base_directory: Path,
) -> Path:
    raw = parsed.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{key} must be a non-empty string")
    value = Path(raw)
    if not value.is_absolute():
        value = base_directory / value
    return value.resolve(strict=False)
