from __future__ import annotations

from dataclasses import dataclass

from .value_table_codec import ColumnKind, ValueColumn, ValueTable


@dataclass(frozen=True, slots=True)
class GeneratedParser:
    module_text: str
    select_table: ValueTable
    identifier_table: ValueTable
    constructor_names: tuple[str, ...]


def empty_select_table(lookahead: int) -> ValueTable:
    if lookahead < 1:
        raise ValueError("lookahead must be at least 1")
    return ValueTable(
        (
            ValueColumn("КоличествоЭлементов", ColumnKind.NUMBER),
            *(
                ValueColumn(f"Элемент{position}", ColumnKind.STRING)
                for position in range(1, lookahead + 1)
            ),
            ValueColumn("Продукция", ColumnKind.STRING),
            ValueColumn("НомерВарианта", ColumnKind.NUMBER),
        ),
        (),
    )
