from unittest import TestCase
from typing import List

from rpft.parsers.common.cellparser import CellParser, unescape
from rpft.parsers.common.rowparser import ParserModel


class InnerModel(ParserModel):
    str_field: str


class OuterModel(ParserModel):
    inner: InnerModel
    strings: List[str]


class TestStringSplitter(TestCase):
    def setUp(self):
        self.parser = CellParser()

    def compare_split_by_separator(self, string, exp):
        out = self.parser.split_by_separator(string, "|")
        self.assertEqual(out, exp)

    def compare_split_into_lists(self, string, exp):
        out = self.parser.split_into_lists(string)
        self.assertEqual(out, exp)

    def compare_join_from_lists(self, string, exp):
        out = self.parser.join_from_lists(string)
        self.assertEqual(out, exp)

    def test_split_by_separator(self):
        self.compare_split_by_separator("a", "a")
        self.compare_split_by_separator("a|b", ["a", "b"])
        self.compare_split_by_separator("a|b|", ["a", "b"])
        self.compare_split_by_separator("a|", ["a"])
        self.compare_split_by_separator("a\\|", "a\\|")

    def test_unescape(self):
        tests = [
            ("a", "a", "Strings without escape sequence should not change"),
            (r"a\|", "a|", "Escape sequence should be removed"),
            (r"a\;", "a;", "Escape sequence should be removed"),
            (r"a\\", "a\\", "Escape sequence should be removed"),
            (r"a\\;", r"a\;", "Escape sequence should be removed"),
            ([[[r"a\;"]]], [[["a;"]]], "List items should be recursively cleansed"),
            ([r"\\", r"\;"], ["\\", ";"], "List items should be recursively cleansed"),
            (" a;\n", "a;", "White space must be removed"),
            ([" a;\n"], ["a;"], "White space must be removed"),
        ]

        for data, expected, msg in tests:
            self.assertEqual(unescape(data), expected, msg)

    SPLIT_TESTS = {
        # Not part of rejoin tests because of non-toplevel separator
        # or unneccesary trailing separator
        "1;": ["1"],
        "1;2": ["1", "2"],
        "1;2;": ["1", "2"],
        "1;2;;": ["1", "2", ""],
        "a|b|": ["a", "b"],
        "1;2|3;4;": [["1", "2"], ["3", "4"]],
    }

    REJOIN_TESTS = {
        # Not part of splitter tests because of non-string types
        "0": 0,
        "True": True,
        "1.0": 1.0,
        "0|True|1.0": [0, True, 1.0],
    }

    SPLIT_REJOIN_TESTS = {
        "1": "1",
        "a\\|": "a|",
        "a\\;": "a;",
        "abc": "abc",
        "a|b|c": ["a", "b", "c"],
        "a|b;c": ["a", ["b", "c"]],
        "a;|": [["a"]],
        "1;2|": [["1", "2"]],
        "1;|2;": [["1"], ["2"]],
        "1;|2": [["1"], "2"],
        "|a": ["", "a"],
        "a|b": ["a", "b"],
        "a|": ["a"],
        "a|\\;": ["a", ";"],
        "a|;": ["a", [""]],
        "1;2|3;4": [["1", "2"], ["3", "4"]],
        "1;2|3;4\\;": [["1", "2"], ["3", "4;"]],
        "1;2|3;4\\|": [["1", "2"], ["3", "4|"]],
        CellParser.escape_string("|;;|\\;\\\\\\|"): "|;;|\\;\\\\\\|",
    }

    def test_split_into_lists(self):
        for inp, outp in TestStringSplitter.SPLIT_TESTS.items():
            self.compare_split_into_lists(inp, outp)
        for inp, outp in TestStringSplitter.SPLIT_REJOIN_TESTS.items():
            self.compare_split_into_lists(inp, outp)

    def test_join_from_lists(self):
        for outp, inp in TestStringSplitter.REJOIN_TESTS.items():
            self.compare_join_from_lists(inp, outp)
        for outp, inp in TestStringSplitter.SPLIT_REJOIN_TESTS.items():
            self.compare_join_from_lists(inp, outp)

    def test_string_stripping(self):
        self.compare_split_into_lists(" a\n|\nb ", ["a", "b"])
        self.compare_split_into_lists("1; 2\n|\n3; 4", [["1", "2"], ["3", "4"]])


class TestCellParser(TestCase):
    def setUp(self):
        self.parser = CellParser()

    def test_strings_without_templates_are_not_changed(self):
        self.assertEqual(
            CellParser().parse_as_string("plain string"),
            ("plain string", False),
        )

    def test_templates_are_rendered(self):
        self.assertEqual(
            CellParser().parse_as_string(" {{var}} string ", context={"var": "abc"}),
            ("abc string", False),
        )

    def test_parse(self):
        out = self.parser.parse("a;b;c")
        self.assertEqual(out, ["a", "b", "c"])

        context = {"list": ["a", "b", "c"]}
        out = self.parser.parse("{% for e in list %}{{e}}{% endfor %}", context=context)
        self.assertEqual(out, "abc")
        # Templating comes first, only then splitting into a list
        out = self.parser.parse(
            "{% for e in list %}{{e}};{% endfor %}", context=context
        )
        self.assertEqual(out, ["a", "b", "c"])

    def test_escape_filter(self):
        out = self.parser.parse('{{"a;b;c"}}')
        self.assertEqual(out, ["a", "b", "c"])
        out = self.parser.parse('{{"a;b;c"|escape}}')
        self.assertEqual(out, "a;b;c")
        string = "\\|;\\"
        out = self.parser.parse("{{string|escape}}", context={"string": string})
        self.assertEqual(out, string)

    def test_indicate_is_object_after_parsing_native_type_template(self):
        self.assertEqual(
            self.parser.parse_as_string(
                ' {@(1, 2, [input == "yes", "a"])@} ',
                context={"input": "yes"},
            ),
            ((1, 2, [True, "a"]), True),
            "Rendered value should not be string; is_object should be True",
        )
