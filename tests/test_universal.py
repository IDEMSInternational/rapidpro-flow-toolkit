from unittest import TestCase

from rpft.parsers.sheets import DatasetSheetReader
from rpft.parsers.universal import (
    bookify,
    parse_cell,
    parse_table,
    parse_tables,
    stringify,
    tabulate,
)
from tablib import Dataset


class TestConvertDataToCell(TestCase):
    def test_delimiters_can_be_configured(self):
        self.assertEqual(
            stringify(
                [
                    ["click", ["auth", "sign_in_google"]],
                    ["click", ["emit", "force_reprocess"]],
                ],
                delimiters=";|:",
            ),
            "click | auth : sign_in_google ; click | emit : force_reprocess",
        )


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

    def test_columns_can_be_ordered_by_metadata(self):
        meta = {"headers": ["integer", "float", "string", "boolean"]}
        data = [
            {
                "boolean": True,
                "float": 1.23,
                "integer": "123",
                "string": "hello",
            },
        ]

        table = tabulate(data, meta)

        self.assertEqual(
            table[1],
            ["123", "1.23", "hello", "true"],
            "Columns should be in the same order as the headers metadata",
        )

    def test_arrays_use_single_cell_layout_by_default(self):
        data = [
            {"h1": ["yes", "no", 1, False]},
            {"h1": ("yes", "no", 1, False)},
        ]

        table = tabulate(data)

        self.assertEqual(table[1], ["yes | no | 1 | false"])
        self.assertEqual(table[2], ["yes | no | 1 | false"])

    def test_array_delimiters_are_escaped(self):
        data = [
            {"h1": [[1, 2], "3 | 4", "5 ; 6"]},
        ]

        table = tabulate(data)

        self.assertEqual(table[1], [r"1 ; 2 | 3 \| 4 | 5 \; 6"])

    def test_delimiters_in_templates_are_not_escaped(self):
        data = [
            {"h1": '{@ values | map(attribute="ID") @}'},
        ]

        table = tabulate(data)

        self.assertEqual(table[1], ['{@ values | map(attribute="ID") @}'])

    def test_single_item_array(self):
        data = [{"k1": ["seq1v1"]}]

        table = tabulate(data)

        self.assertEqual(table[1][0], "seq1v1 |")

    def test_arrays_with_empty_single_item(self):
        data = [{"k1": [""]}]

        table = tabulate(data)

        self.assertEqual(table[1][0], " |")

    def test_arrays_with_empty_last_item(self):
        data = [{"k1": ["v1", ""]}]

        table = tabulate(data)

        self.assertEqual(table[1][0], "v1 | |")

    def test_nested_arrays_within_a_single_cell(self):
        data = [
            {"k1": ["seq1v1", ["seq2v1", "seq2v2"]]},
        ]

        table = tabulate(data)

        self.assertEqual(table[1][0], "seq1v1 | seq2v1 ; seq2v2")

    def test_raise_exception_if_too_much_nesting_for_a_single_cell(self):
        data = [
            {"k1": ["seq1v1", ["seq2v1", ["seq3v1"]]]},
        ]

        self.assertRaises(Exception, tabulate, data)

    def test_arrays_use_wide_layout_if_indicated_by_metadata(self):
        meta = {
            "headers": [
                "choices",
                "choices",
                "choices",
                "choices",
            ]
        }
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

        self.assertEqual(table[1], ["prop1; val1 | prop2; val2"])

    def test_object_with_single_property_within_cell_has_trailing_delimiter(self):
        data = [{"obj": {"k": "v"}}]

        table = tabulate(data)

        self.assertEqual(table[1], ["k; v |"])

    def test_objects_use_wide_layout_if_indicated_by_metadata(self):
        meta = {"headers": ["obj1.k1", "obj1.k2", "seq1.1.k1", "seq1.2.k2"]}
        data = [
            {
                "obj1": {
                    "k1": "obj1_k1_v",
                    "k2": "obj1_k2_v",
                },
                "seq1": [
                    {"k1": "seq1_k1_v"},
                    {"k2": "seq1_k2_v"},
                ],
            },
        ]

        table = tabulate(data, meta)

        self.assertEqual(
            table[0],
            ["obj1.k1", "obj1.k2", "seq1.1.k1", "seq1.2.k2"],
        )
        self.assertEqual(
            table[1],
            ["obj1_k1_v", "obj1_k2_v", "seq1_k1_v", "seq1_k2_v"],
        )


class TestUniversalToWorkbook(TestCase):
    def test_assembly(self):
        data = {
            "group1": [{"a": "a1", "b": "b1"}],
            "group2": [{"A": "A1", "B": "B1"}],
            "_idems": {
                "tabulate": {
                    "group1": {"headers": ["a", "b"]},
                    "group2": {"headers": ["B", "A"]},
                },
            },
        }

        workbook = bookify(data)

        self.assertEqual(len(workbook), 2)
        self.assertEqual(workbook[0][0], "group1")
        self.assertEqual(workbook[0][1], [["a", "b"], ["a1", "b1"]])
        self.assertEqual(workbook[1][0], "group2")
        self.assertEqual(
            workbook[1][1],
            [["B", "A"], ["B1", "A1"]],
            "Columns should be ordered according to metadata",
        )
        self.assertEqual(
            data,
            {
                "group1": [{"a": "a1", "b": "b1"}],
                "group2": [{"A": "A1", "B": "B1"}],
                "_idems": {
                    "tabulate": {
                        "group1": {"headers": ["a", "b"]},
                        "group2": {"headers": ["B", "A"]},
                    },
                },
            },
            "Input data should not be mutated",
        )


class TestConvertWorkbookToUniversal(TestCase):

    def test_workbook_converts_to_object(self):
        workbook = DatasetSheetReader(
            [
                Dataset(("t1a1", "t1b1"), headers=("T1A", "T1B"), title="table1"),
                Dataset(("t2a1", "t2b1"), headers=("T2A", "T2B"), title="table2"),
            ],
            "test"
        )

        nested = parse_tables(workbook)

        self.assertIsInstance(nested, dict)
        self.assertEqual(list(nested.keys()), ["_idems", "table1", "table2"])
        self.assertEqual(
            list(nested["_idems"]["tabulate"].keys()),
            ["table1", "table2"],
        )


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
            rows=[["k2; 2 | k3; false", "k4; v4 | k5; true"]],
        )

        self.assertEqual(
            parsed["table"][0]["obj"],
            {"k1": [[["k2", 2], ["k3", False]], [["k4", "v4"], ["k5", True]]]},
        )


class TestCellConversion(TestCase):

    def setUp(self):
        self.func = parse_cell

    def test_convert_cell_string_to_number(self):
        self.assertEqual(self.func("123"), 123)
        self.assertEqual(self.func("1.23"), 1.23)

    def test_output_clean_string_if_no_conversion_possible(self):
        self.assertEqual(self.func("one"), "one")
        self.assertEqual(self.func(" one "), "one")
        self.assertEqual(self.func(""), "")
        self.assertEqual(self.func("http://example.com/"), "http://example.com/")
        self.assertEqual(self.func("k1: v1"), "k1: v1")

    def test_raises_error_if_not_string_input(self):
        self.assertRaises(TypeError, self.func, None)
        self.assertRaises(TypeError, self.func, 123)

    def test_convert_cell_string_to_bool(self):
        self.assertEqual(self.func("true"), True)
        self.assertEqual(self.func(" true "), True)
        self.assertEqual(self.func("false"), False)

    def test_convert_cell_string_to_list(self):
        self.assertEqual(self.func("one | 2 | false"), ["one", 2, False])
        self.assertEqual(self.func("one ; 2 ; false"), ["one", 2, False])
        self.assertEqual(self.func("one |"), ["one"])
        self.assertEqual(self.func("|"), [""])
        self.assertEqual(self.func("| 2 |"), ["", 2])
        self.assertEqual(self.func("a||"), ["a", ""])
        self.assertEqual(self.func("k1 | v1 : k2 | v2"), ["k1", "v1 : k2", "v2"])

    def test_convert_cell_string_to_list_of_lists(self):
        self.assertEqual(self.func("k1; v1 |"), [["k1", "v1"]])
        self.assertEqual(self.func("k1; k2; v2 |"), [["k1", "k2", "v2"]])
        self.assertEqual(self.func("k1; 1 | k2; true"), [["k1", 1], ["k2", True]])

    def test_delimiters_can_be_configured(self):
        self.assertEqual(
            self.func(
                "click | auth: sign_in_google; click | emit: force_reprocess",
                delimiters=";|:",
            ),
            [
                ["click", ["auth", "sign_in_google"]],
                ["click", ["emit", "force_reprocess"]],
            ],
        )

    def test_inline_templates_are_preserved(self):
        self.assertEqual(self.func("{{ template }}"), "{{ template }}")
        self.assertEqual(self.func("{@ template @}"), "{@ template @}")
        self.assertEqual(
            self.func("{% if other_option!=" "%}1wc;1wt;1wb{%endif-%}"),
            "{% if other_option!=" "%}1wc;1wt;1wb{%endif-%}",
        )
        self.assertEqual(self.func("{{ template }} |"), "{{ template }} |")
        self.assertEqual(
            self.func("{{ template }} | something | {{ blah }}"),
            "{{ template }} | something | {{ blah }}",
        )
        self.assertEqual(
            self.func(
                "{{3*(steps.values()|length -1)}}|{{3*(steps.values()|length -1)+2}}"
            ),
            "{{3*(steps.values()|length -1)}}|{{3*(steps.values()|length -1)+2}}",
        )
        self.assertEqual(
            self.func("6;0{%if skip_option != " " -%};skip{% endif %}"),
            "6;0{%if skip_option != " " -%};skip{% endif %}",
        )
        self.assertEqual(
            self.func('@(fields.survey_behave & "no|")'),
            '@(fields.survey_behave & "no|")',
        )

    def test_delimiters_can_be_escaped(self):
        self.assertEqual(
            self.func(r"1 ; 2 | 3 \| 4 | 5 \; 6 \|"),
            [[1, 2], "3 | 4", "5 ; 6 |"],
        )
