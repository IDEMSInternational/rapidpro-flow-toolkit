from unittest import TestCase

from rpft.parsers.sheets import DatasetSheetReader
from rpft.parsers.universal import (
    convert_cell,
    create_workbook,
    parse_legacy_sheets,
    parse_table,
    parse_tables,
    tabulate,
)
from tablib import Dataset


class TestConvertUniversalToTable(TestCase):
    def test_headers_must_be_first_row(self):
        data = [
            {"type": "create_flow", "sheet_name": "flow1"},
        ]

        table = tabulate(data)

        self.assertEqual(
            table[0],
            ["type", "sheet_name"],
            "First row must be column headers",
        )
        self.assertEqual(
            table[1],
            ["create_flow", "flow1"],
            "Subsequent rows must contain values",
        )

    def test_values_must_be_strings(self):
        data = [
            {
                "boolean": True,
                "float": 1.23,
                "integer": "123",
                "string": "hello",
            },
        ]

        table = tabulate(data)

        self.assertEqual(table[1], ["true", "1.23", "123", "hello"])

    def test_arrays_use_single_cell_layout_by_default(self):
        data = [
            {
                "choices": ["yes", "no", 1, False],
            },
        ]

        table = tabulate(data)

        self.assertEqual(table[1], ["yes | no | 1 | false"])

    def test_arrays_use_wide_layout_if_indicated_by_metadata(self):
        meta = {"choices": {"layout": "wide"}}
        data = [
            {
                "choices": ["yes", "no", 1, False],
            },
        ]

        table = tabulate(data, meta)

        self.assertEqual(table[0], ["choices", "choices", "choices", "choices"])
        self.assertEqual(table[1], ["yes", "no", "1", "false"])

    def test_objects_use_single_cell_layout_by_default(self):
        data = [
            {
                "obj": {
                    "prop1": "val1",
                    "prop2": "val2",
                },
            },
        ]

        table = tabulate(data)

        self.assertEqual(table[1], ["prop1: val1 | prop2: val2"])

    def test_objects_use_wide_layout_if_indicated_by_metadata(self):
        meta = {"obj": {"layout": "wide"}}
        data = [
            {
                "obj": {
                    "prop1": "val1",
                    "prop2": "val2",
                },
            },
        ]

        table = tabulate(data, meta)

        self.assertEqual(table[0], ["obj.prop1", "obj.prop2"])
        self.assertEqual(table[1], ["val1", "val2"])

    # TODO: test pointers/references
    # TODO: add explicit type information
    # TODO: integrate zero-knowledge type inference


class TestUniversalToWorkbook(TestCase):
    def test_assembly(self):
        data = {
            "group1": [{"a": "a1", "b": "b1"}],
            "group2": [{"A": "A1", "B": "B1"}],
        }

        workbook = create_workbook(data)

        self.assertEqual(len(workbook), 2)
        self.assertEqual(workbook[0][0], "group1")
        self.assertEqual(workbook[0][1], [["a", "b"], ["a1", "b1"]])
        self.assertEqual(workbook[1][0], "group2")
        self.assertEqual(workbook[1][1], [["A", "B"], ["A1", "B1"]])


class TestConvertLegacyToUniversal(TestCase):
    def test_skip_non_existent_sheets(self):
        datasets = [
            Dataset(
                ("create_flow", "my_basic_flow"),
                headers=("type", "sheet_name"),
                title="content_index",
            )
        ]

        output = parse_legacy_sheets(
            "tests.datarowmodels.nestedmodel",
            DatasetSheetReader(datasets),
        )

        self.assertIn("content_index", output)
        self.assertNotIn("my_basic_flow", output)

    def test_skip_evaluation_of_cells_with_templates(self):
        datasets = [
            Dataset(
                ("template_definition", "my_template"),
                headers=("type", "sheet_name"),
                title="content_index",
            ),
            Dataset(
                ("send_message", "start", "Hello, {{name}}"),
                headers=("type", "from", "message_text"),
                title="my_template",
            ),
        ]

        output = parse_legacy_sheets(
            "tests.datarowmodels.nestedmodel",
            DatasetSheetReader(datasets),
        )

        self.assertEqual(
            output["my_template"][0]["message_text"],
            "Hello, {{name}}",
            "Template notation must remain intact",
        )

    def test_unparseable_sheets_are_converted_to_2d_array(self):
        datasets = [
            Dataset(
                headers=("type", "sheet_name"),
                title="content_index",
            ),
            Dataset(
                ("", "b2"),
                ("c1", ""),
                ("d1", "d2"),
                headers=("", ""),
                title="unparseable",
            ),
        ]

        output = parse_legacy_sheets(
            "tests.datarowmodels.nestedmodel",
            DatasetSheetReader(datasets),
        )

        self.assertEqual(
            output["unparseable"],
            [["", ""], ["", "b2"], ["c1", ""], ["d1", "d2"]],
            "Data should be 2-dimensional array of strings",
        )

    def test_process_content_indices_recursively(self):
        datasets = [
            Dataset(
                ("content_index", "sub_index"),
                headers=("type", "sheet_name"),
                title="content_index",
            ),
            Dataset(
                ("data_sheet", "simpledata", "ListRowModel"),
                headers=("type", "sheet_name", "data_model"),
                title="sub_index",
            ),
            Dataset(
                ("rowID", "val1", "val2"),
                headers=("ID", "list_value.1", "list_value.2"),
                title="simpledata",
            ),
        ]

        output = parse_legacy_sheets(
            "tests.datarowmodels.nestedmodel",
            DatasetSheetReader(datasets),
        )

        self.assertEqual(
            output["simpledata"][0]["list_value"],
            ["val1", "val2"],
            "Data should be converted to nested form because all content indices should"
            " have been processed",
        )

    def test_sheet_order_is_preserved(self):
        datasets = [
            Dataset(
                ("data_sheet", "sheet_2", "SimpleRowModel"),
                ("data_sheet", "sheet_3", "SimpleRowModel"),
                headers=("type", "sheet_name", "data_model"),
                title="content_index",
            ),
            Dataset(
                ("val1", "val2"),
                headers=("value1", "value2"),
                title="sheet_3",
            ),
            Dataset(
                ("val1", "val2"),
                headers=("value1", "value2"),
                title="sheet_2",
            ),
        ]

        output = parse_legacy_sheets(
            "tests.datarowmodels.simplemodel",
            DatasetSheetReader(datasets),
        )

        self.assertEqual(
            list(output.keys()),
            ["content_index", "sheet_3", "sheet_2"],
            "Order of keys should be same as in workbook",
        )

    def test_save_as_dict(self):
        # TODO: Break up this test into smaller, more manageable pieces
        self.maxDiff = None
        datasets = [
            Dataset(
                ("data_sheet", "simpledata", "simpledata_new", "ListRowModel", ""),
                ("create_flow", "my_basic_flow", "", "", ""),
                ("data_sheet", "nesteddata", "", "NestedRowModel", ""),
                ("create_campaign", "my_campaign", "", "", "grp1"),
                headers=("type", "sheet_name", "new_name", "data_model", "group"),
                title="content_index",
            ),
            Dataset(
                ("rowID", "val1", "val2"),
                headers=("ID", "list_value.1", "list_value.2"),
                title="simpledata",
            ),
            Dataset(
                ("row1", "Value1", "Happy1", "Sad1"),
                ("row2", "Value2", "Happy2", "Sad2"),
                headers=("ID", "value1", "custom_field.happy", "custom_field.sad"),
                title="nesteddata",
            ),
            Dataset(
                ("", "send_message", "start", "Some text"),
                headers=("row_id", "type", "from", "message_text"),
                title="my_basic_flow",
            ),
            Dataset(
                ("15", "H", "F", "Last Seen On", "I", "my_basic_flow"),
                headers=(
                    "offset",
                    "unit",
                    "event_type",
                    "relative_to",
                    "start_mode",
                    "flow",
                ),
                title="my_campaign",
            ),
        ]

        output = parse_legacy_sheets(
            "tests.datarowmodels.nestedmodel",
            DatasetSheetReader(datasets),
        )
        exp = {
            "content_index": [
                {
                    "type": "data_sheet",
                    "sheet_name": ["simpledata"],
                    "new_name": "simpledata_new",
                    "data_model": "ListRowModel",
                    "group": "",
                },
                {
                    "type": "create_flow",
                    "sheet_name": ["my_basic_flow"],
                    "new_name": "",
                    "data_model": "",
                    "group": "",
                },
                {
                    "type": "data_sheet",
                    "sheet_name": ["nesteddata"],
                    "new_name": "",
                    "data_model": "NestedRowModel",
                    "group": "",
                },
                {
                    "type": "create_campaign",
                    "sheet_name": ["my_campaign"],
                    "new_name": "",
                    "data_model": "",
                    "group": "grp1",
                },
            ],
            "simpledata": [
                {
                    "ID": "rowID",
                    "list_value": ["val1", "val2"],
                }
            ],
            "nesteddata": [
                {
                    "ID": "row1",
                    "value1": "Value1",
                    "custom_field": {
                        "happy": "Happy1",
                        "sad": "Sad1",
                    },
                },
                {
                    "ID": "row2",
                    "value1": "Value2",
                    "custom_field": {
                        "happy": "Happy2",
                        "sad": "Sad2",
                    },
                },
            ],
            "my_basic_flow": [
                {
                    "row_id": "",
                    "type": "send_message",
                    "from": "start",
                    "message_text": "Some text",
                },
            ],
            "my_campaign": [
                {
                    "offset": "15",
                    "unit": "H",
                    "event_type": "F",
                    "relative_to": "Last Seen On",
                    "start_mode": "I",
                    "flow": "my_basic_flow",
                },
            ],
        }

        self.assertEqual(output, exp)


class TestConvertWorkbookToUniversal(TestCase):

    def test_workbook_converts_to_list_of_objects(self):
        workbook = DatasetSheetReader(
            [
                Dataset(("t1a1", "t1b1"), headers=("T1A", "T1B"), title="table1"),
                Dataset(("t2a1", "t2b1"), headers=("T2A", "T2B"), title="table2"),
            ]
        )

        nested = parse_tables(workbook)

        self.assertIsInstance(nested, list)
        self.assertEqual(len(nested), 2)
        self.assertTrue(all(type(o) is dict for o in nested))


class TestConvertTableToNested(TestCase):

    def test_default_type_is_string(self):
        self.assertEqual(
            parse_table(
                title="title",
                headers=["a"],
                rows=[["a1"]],
            ),
            {
                "_idems": {"tabulate": {"title": {"headers": ["a"]}}},
                "title": [{"a": "a1"}],
            },
        )

    def test_table_must_have_title(self):
        self.assertEqual(parse_table(), {"table": []})

    def test_integer_as_string_is_int(self):
        parsed = parse_table(headers=["a"], rows=[["123"]])

        self.assertEqual(parsed["table"][0]["a"], 123)

    def test_boolean_as_string_is_bool(self):
        parsed = parse_table(headers=("a", "b"), rows=[("true", "false")])

        self.assertEqual(parsed["table"][0]["a"], True)
        self.assertEqual(parsed["table"][0]["b"], False)

    def test_delimited_string_is_array(self):
        parsed = parse_table(headers=["a"], rows=[["one | 2 | true | 3.4"]])

        self.assertEqual(parsed["table"][0]["a"], ["one", 2, True, 3.4])

    def test_columns_with_same_name_are_grouped_into_list(self):
        parsed = parse_table(headers=["a"] * 4, rows=[("one", "2", "true", "3.4")])

        self.assertEqual(parsed["table"][0]["a"], ["one", 2, True, 3.4])
        # self.assertEqual(parsed["_idems"]["tabulate"]["table"]["a"]["layout"], "wide")

    def test_columns_with_same_name_and_delimited_strings_is_2d_array(self):
        parsed = parse_table(headers=["a"] * 2, rows=[("one | 2", "true | 3.4")])

        self.assertEqual(parsed["table"][0]["a"], [["one", 2], [True, 3.4]])

    def test_column_using_dot_notation_is_nested_object_property(self):
        parsed = parse_table(
            headers=("obj.prop1", "obj.prop2"),
            rows=[("one", "2")],
        )

        self.assertEqual(parsed["table"][0]["obj"], {"prop1": "one", "prop2": 2})
        self.assertEqual(
            parsed["_idems"]["tabulate"]["table"]["headers"],
            ("obj.prop1", "obj.prop2"),
        )

    def test_nested_object_with_2d_array_property_value(self):
        parsed = parse_table(headers=["obj.k1"] * 2, rows=[["1 | 2", "3 | 4"]])

        self.assertEqual(parsed["table"][0]["obj"], {"k1": [[1, 2], [3, 4]]})

    def test_nested_object_with_nested_object(self):
        parsed = parse_table(
            headers=["obj.k1"] * 2,
            rows=[["k2: 2 | k3: false", "k4: v4 | k5: true"]],
        )

        self.assertEqual(
            parsed["table"][0]["obj"],
            {"k1": [{"k2": 2, "k3": False}, {"k4": "v4", "k5": True}]},
        )


class TestCellConversion(TestCase):

    def test_convert_cell_string_to_number(self):
        self.assertEqual(convert_cell("123"), 123)
        self.assertEqual(convert_cell("1.23"), 1.23)

    def test_output_clean_string_if_no_conversion_possible(self):
        self.assertEqual(convert_cell("one"), "one")
        self.assertEqual(convert_cell(" one "), "one")
        self.assertEqual(convert_cell(""), "")

    def test_raises_error_if_not_string_input(self):
        self.assertRaises(TypeError, convert_cell, None)
        self.assertRaises(TypeError, convert_cell, 123)

    def test_convert_cell_string_to_bool(self):
        self.assertEqual(convert_cell("true"), True)
        self.assertEqual(convert_cell(" true "), True)
        self.assertEqual(convert_cell("false"), False)

    def test_convert_cell_string_to_list(self):
        self.assertEqual(convert_cell("one | 2 | false"), ["one", 2, False])
        self.assertEqual(convert_cell("one |"), ["one"])
        self.assertEqual(convert_cell("|"), [])
        self.assertEqual(convert_cell("| 2 |"), [2])
        self.assertEqual(convert_cell("k1 | v1 : k2 | v2"), ["k1", "v1 : k2", "v2"])

    def test_convert_cell_string_to_dict(self):
        self.assertEqual(convert_cell("k1: v1"), {"k1": "v1"})
        self.assertEqual(convert_cell(" k1 : v1 "), {"k1": "v1"})
        self.assertEqual(convert_cell("k1: v1 |"), {"k1": "v1"})
        self.assertEqual(convert_cell("k1: k2: v2"), {"k1": "k2: v2"})
        self.assertEqual(convert_cell("k1: 1 | k2: true"), {"k1": 1, "k2": True})
