from pathlib import Path
import sys
import unittest

from parsergen.value_table_codec import (
    ColumnKind,
    ValueColumn,
    ValueTable,
    decode_value_table,
    encode_value_table,
)


VALID_ONE_ROW_TEXT = (
    '{"#",acf6192e-81ca-46ef-93a6-5a6968b78663,\r\n'
    "{9,\r\n"
    "{1,\r\n"
    '{0,"Name",\r\n'
    '{"Pattern",\r\n'
    '{"S"}\r\n'
    '},"",0}\r\n'
    "},\r\n"
    "{2,1,0,0,\r\n"
    "{1,1,\r\n"
    "{2,0,1,\r\n"
    '{"S","x"},0}\r\n'
    "},0,0},\r\n"
    "{0,0}\r\n"
    "}\r\n"
    "}"
)


class ValueTableCodecTests(unittest.TestCase):
    def assert_malformed(self, text: str) -> None:
        with self.assertRaisesRegex(ValueError, r"offset \d+"):
            decode_value_table(text)

    def test_value_table_round_trip_quotes_unicode_and_undefined(self) -> None:
        table = ValueTable(
            columns=(
                ValueColumn("Name", ColumnKind.STRING),
                ValueColumn("Count", ColumnKind.NUMBER),
            ),
            rows=(('A"Б', 2), (None, 0)),
        )

        self.assertEqual(decode_value_table(encode_value_table(table)), table)

    def test_encoder_emits_canonical_crlf_layout_and_counters(self) -> None:
        table = ValueTable(
            columns=(ValueColumn("Name", ColumnKind.STRING),),
            rows=(("x",),),
        )
        self.assertEqual(encode_value_table(table), VALID_ONE_ROW_TEXT)

    def test_decodes_reference_tables(self) -> None:
        root = Path(__file__).resolve().parent / "fixtures/reference_parser/Templates"
        identifiers = decode_value_table(
            (root / "ОпределенияИдентификаторов/Template.txt").read_text(
                encoding="utf-8"
            )
        )
        select = decode_value_table(
            (
                root
                / "ТаблицаПервыхСимволовВариантов/Template.txt"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(
            [column.name for column in identifiers.columns],
            ["Тип", "Идентификатор"],
        )
        self.assertEqual(
            [column.kind for column in identifiers.columns],
            [ColumnKind.STRING, ColumnKind.STRING],
        )
        self.assertEqual(len(identifiers.rows), 276)
        self.assertEqual(identifiers.rows[0], ("ID_Полный", "ID"))
        self.assertEqual(
            identifiers.rows[-1],
            ("ID_ПолеБезРазыменования", "ССЫЛКА"),
        )
        self.assertEqual(
            [column.name for column in select.columns],
            [
                "КоличествоЭлементов",
                "Элемент1",
                "Элемент2",
                "Продукция",
                "НомерВарианта",
            ],
        )
        self.assertEqual(
            [column.kind for column in select.columns],
            [
                ColumnKind.NUMBER,
                ColumnKind.STRING,
                ColumnKind.STRING,
                ColumnKind.STRING,
                ColumnKind.NUMBER,
            ],
        )
        self.assertEqual(len(select.rows), 6479)
        self.assertEqual(
            select.rows[0],
            (2, "ВЫБРАТЬ", "&", "ЗапросВыбора", 1),
        )
        self.assertEqual(
            select.rows[-1],
            (
                0,
                None,
                None,
                "ОпциональноеПродолжениеАргументаЗначение",
                2,
            ),
        )
        self.assertEqual(decode_value_table(encode_value_table(select)), select)

    def test_rejects_wrong_value_table_guid_with_offset(self) -> None:
        self.assert_malformed(
            VALID_ONE_ROW_TEXT.replace(
                "acf6192e-81ca-46ef-93a6-5a6968b78663",
                "00000000-0000-0000-0000-000000000000",
            )
        )

    def test_rejects_unsupported_column_kind_with_offset(self) -> None:
        self.assert_malformed(
            VALID_ONE_ROW_TEXT.replace('{"S"}\r\n},"",0', '{"B"}\r\n},"",0')
        )

    def test_rejects_truncated_list_with_offset(self) -> None:
        self.assert_malformed(VALID_ONE_ROW_TEXT[:-1])

    def test_rejects_excessive_nesting_before_python_recursion_limit(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"nesting limit exceeded at offset 256$",
        ):
            decode_value_table("{" * 1200)

    def test_rejects_malformed_quoted_string_with_offset(self) -> None:
        self.assert_malformed(VALID_ONE_ROW_TEXT.replace('"x"', '"x'))

    def test_rejects_row_width_mismatch_with_offset(self) -> None:
        self.assert_malformed(
            VALID_ONE_ROW_TEXT.replace("{2,0,1,\r\n", "{2,0,2,\r\n")
        )

    def test_rejects_incorrect_row_count_with_offset(self) -> None:
        self.assert_malformed(
            VALID_ONE_ROW_TEXT.replace("{1,1,\r\n", "{1,2,\r\n")
        )

    def test_rejects_trailing_data_with_offset(self) -> None:
        self.assert_malformed(VALID_ONE_ROW_TEXT + "trailing")

    def test_rejects_structural_counter_and_order_mutations(self) -> None:
        mutations = (
            VALID_ONE_ROW_TEXT.replace("{9,\r\n", "{8,\r\n", 1),
            VALID_ONE_ROW_TEXT.replace("{2,1,0,0,\r\n", "{2,1,0,1,\r\n"),
            VALID_ONE_ROW_TEXT.replace("{2,0,1,\r\n", "{2,1,1,\r\n"),
            VALID_ONE_ROW_TEXT.replace("},0,0},\r\n", "},1,0},\r\n"),
            VALID_ONE_ROW_TEXT.replace("},0,0},\r\n", "},0,1},\r\n"),
            VALID_ONE_ROW_TEXT.replace("{0,0}\r\n}", "{1,0}\r\n}"),
        )

        for text in mutations:
            with self.subTest(text=text):
                self.assert_malformed(text)

    def test_rejects_unsupported_and_malformed_cells_with_offsets(self) -> None:
        mutations = (
            VALID_ONE_ROW_TEXT.replace('{"S","x"}', '{"B",1}'),
            VALID_ONE_ROW_TEXT.replace('{"S","x"}', '{"S"}'),
            VALID_ONE_ROW_TEXT.replace('{"S","x"}', '{"N","1"}'),
            VALID_ONE_ROW_TEXT.replace('{"S","x"}', '{"U",0}'),
        )

        for text in mutations:
            with self.subTest(text=text):
                self.assert_malformed(text)

    def test_rejects_empty_column_collection_with_offset(self) -> None:
        self.assert_malformed(
            '{"#",acf6192e-81ca-46ef-93a6-5a6968b78663,'
            "{9,{},{2,0,{1,0},-1,-1},{0,0}}}"
        )

    def test_reports_first_empty_list_pattern_offset(self) -> None:
        text = (
            '{"#",acf6192e-81ca-46ef-93a6-5a6968b78663,'
            "{9,"
            "{2,"
            '{0,"A",{},"",0},'
            '{1,"B",{},"",0}'
            "},"
            "{2,2,0,0,1,1,{1,0},1,-1},"
            "{0,0}"
            "}}"
        )
        first_pattern_offset = text.index("{}")
        second_pattern_offset = text.index(
            "{}", first_pattern_offset + 1
        )
        self.assertNotEqual(first_pattern_offset, second_pattern_offset)

        with self.assertRaisesRegex(
            ValueError,
            rf"unsupported column pattern at offset "
            rf"{first_pattern_offset}$",
        ):
            decode_value_table(text)

    def test_decodes_integer_beyond_decimal_conversion_limit(self) -> None:
        digit_count = 5000
        literal = "-" + "9" * digit_count
        expected = -(10**digit_count - 1)
        text = VALID_ONE_ROW_TEXT.replace(
            '{"S"}\r\n},"",0',
            '{"N"}\r\n},"",0',
        ).replace('{"S","x"}', f'{{"N",{literal}}}')
        policy_before = sys.get_int_max_str_digits()

        try:
            table = decode_value_table(text)
        finally:
            self.assertEqual(
                sys.get_int_max_str_digits(), policy_before
            )

        self.assertEqual(table.rows, ((expected,),))

    def test_round_trips_signed_integers_across_decimal_boundary(self) -> None:
        policy_before = sys.get_int_max_str_digits()
        for digit_count in (4300, 4301, 5000):
            with self.subTest(digit_count=digit_count):
                literal = "-" + "9" * digit_count
                value = -(10**digit_count - 1)
                table = ValueTable(
                    (ValueColumn("Count", ColumnKind.NUMBER),),
                    ((value,),),
                )

                try:
                    encoded = encode_value_table(table)
                    decoded = decode_value_table(encoded)
                finally:
                    self.assertEqual(
                        sys.get_int_max_str_digits(), policy_before
                    )

                self.assertIn(f'{{"N",{literal}}}', encoded)
                self.assertEqual(decoded, table)

    def test_rejects_unquoted_string_tokens_with_offsets(self) -> None:
        mutations = (
            VALID_ONE_ROW_TEXT.replace('{"#",', "{#,", 1),
            VALID_ONE_ROW_TEXT.replace('"Name"', "Name", 1),
            VALID_ONE_ROW_TEXT.replace(
                '{"S"}\r\n},"",0', '{S}\r\n},"",0'
            ),
            VALID_ONE_ROW_TEXT.replace('{"S","x"}', '{S,"x"}'),
            VALID_ONE_ROW_TEXT.replace('{"S","x"}', '{"S",x}'),
        )

        for text in mutations:
            with self.subTest(text=text):
                self.assert_malformed(text)

    def test_encoder_rejects_width_kind_and_cell_type_violations(self) -> None:
        invalid_tables = (
            ValueTable(
                (ValueColumn("Name", ColumnKind.STRING),),
                (("a", "b"),),
            ),
            ValueTable(
                (ValueColumn("Count", ColumnKind.NUMBER),),
                (("one",),),
            ),
            ValueTable(
                (ValueColumn("Name", ColumnKind.STRING),),
                ((1,),),
            ),
            ValueTable(
                (ValueColumn("Count", ColumnKind.NUMBER),),
                ((True,),),
            ),
            ValueTable(
                (ValueColumn("Count", ColumnKind.NUMBER),),
                ((1.5,),),  # type: ignore[arg-type]
            ),
            ValueTable(
                (ValueColumn("Flag", "boolean"),),  # type: ignore[arg-type]
                ((1,),),
            ),
            ValueTable(
                (ValueColumn(42, ColumnKind.NUMBER),),  # type: ignore[arg-type]
                ((1,),),
            ),
            ValueTable(  # type: ignore[arg-type]
                [ValueColumn("Name", ColumnKind.STRING)],
                (),
            ),
            ValueTable((), []),  # type: ignore[arg-type]
        )

        for table in invalid_tables:
            with self.subTest(table=table):
                with self.assertRaises(ValueError):
                    encode_value_table(table)


if __name__ == "__main__":
    unittest.main()
