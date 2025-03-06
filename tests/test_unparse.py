import unittest
from collections import OrderedDict
from typing import List, Optional

from rpft.parsers.common.cellparser import CellParser
from rpft.parsers.common.rowparser import ParserModel, RowParser, RowParserError
from tests.mocks import MockCellParser


class ModelWithStuff(ParserModel):
    list_str: List[str] = []
    int_field: int = 0
    str_field: str = ""


class MainModel(ParserModel):
    str_field: str = ""
    model_optional: Optional[ModelWithStuff] = None
    model_default: ModelWithStuff = ModelWithStuff()
    model_list: List[ModelWithStuff] = []


input1 = MainModel()
output1_exp = {}

submodel_2_dict = {
    "list_str": ["a", "b", "c"],
    "int_field": 5,
    "str_field": "string",
}

input2 = MainModel(
    **{
        "str_field": "main model string",
        "model_default": submodel_2_dict,
    }
)

output2_exp = OrderedDict(
    [
        ("str_field", "main model string"),
        ("model_default.list_str.1", "a"),
        ("model_default.list_str.2", "b"),
        ("model_default.list_str.3", "c"),
        ("model_default.int_field", 5),
        ("model_default.str_field", "string"),
    ]
)

input3 = MainModel(
    **{
        "str_field": "main model string",
        "model_default": {"list_str": [], "int_field": 15, "str_field": ""},
    }
)

output3_exp = OrderedDict(
    [
        ("str_field", "main model string"),
        ("model_default.int_field", 15),
    ]
)

input4 = MainModel(
    **{
        "str_field": "main model string",
        "model_default": {
            "list_str": ["a", "b"],
            "int_field": 5,
            "str_field": "default",
        },
        "model_optional": {
            "list_str": ["c", "d"],
            "int_field": 10,
            "str_field": "optional",
        },
        "model_list": [
            {
                "list_str": ["A", "B", "C"],
                "str_field": "string from first model in list",
            },
            {
                "int_field": 15,
            },
        ],
    }
)

output4_exp = OrderedDict(
    [
        ("str_field", "main model string"),
        ("model_optional.list_str.1", "c"),
        ("model_optional.list_str.2", "d"),
        ("model_optional.int_field", 10),
        ("model_optional.str_field", "optional"),
        ("model_default.list_str.1", "a"),
        ("model_default.list_str.2", "b"),
        ("model_default.int_field", 5),
        ("model_default.str_field", "default"),
        ("model_list.1.list_str.1", "A"),
        ("model_list.1.list_str.2", "B"),
        ("model_list.1.list_str.3", "C"),
        ("model_list.1.str_field", "string from first model in list"),
        ("model_list.2.int_field", 15),
    ]
)


# ------ Data for remapping test cases ------
class ChildModel(ParserModel):
    some_field: str = ""

    def field_name_to_header_name(field):
        field_map = {
            "some_field": "my_field",
        }
        return field_map.get(field, field)


class ModelWithBasicRemap(ParserModel):
    str_field: str = ""
    new_str_field: str = ""
    list_field: List[str] = []
    child_field: Optional[ChildModel]

    def field_name_to_header_name(field):
        field_map = {
            "new_str_field": "str_field_2",
            "list_field": "cool_list",
        }
        return field_map.get(field, field)


input_remap = ModelWithBasicRemap(
    **{
        "str_field": "main model string",
        "new_str_field": "new string",
        "list_field": ["cool", "list"],
        "child_field": {"some_field": "some value"},
    }
)


output_remap_exp = OrderedDict(
    [
        ("str_field", "main model string"),
        ("str_field_2", "new string"),
        ("cool_list", ["cool", "list"]),
        ("child_field.my_field", "some value"),
    ]
)


class ModelWithClashingRemap(ParserModel):
    str_field: str = ""
    list_field: List[str] = []

    def field_name_to_header_name(field):
        field_map = {
            "str_field": "new_field",
            "list_field": "new_field",
        }
        return field_map.get(field, field)


input_clashing_remap1 = ModelWithClashingRemap(
    **{
        "str_field": "string",
        "list_field": [],
    }
)


input_clashing_remap2 = ModelWithClashingRemap(
    **{
        "str_field": "",
        "list_field": ["cool", "list"],
    }
)


input_clashing_remap3 = ModelWithClashingRemap(
    **{
        "str_field": "string",
        "list_field": ["cool", "list"],
    }
)


output_clashing_remap_exp1 = {"new_field": "string"}
output_clashing_remap_exp2 = {"new_field": ["cool", "list"]}


class TestUnparseWithMockIntoBasicTypes(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.parser = RowParser(MainModel, MockCellParser())

    def test_input_1(self):
        output1 = self.parser.unparse_row(input1)
        self.assertEqual(output1, output1_exp)

    def test_input_2(self):
        output2 = self.parser.unparse_row(input2)
        self.assertEqual(output2, output2_exp)

    def test_input_3(self):
        output3 = self.parser.unparse_row(input3)
        self.assertEqual(output3, output3_exp)

    def test_input_4(self):
        output4 = self.parser.unparse_row(input4)
        self.assertEqual(output4, output4_exp)

    def test_remap(self):
        output_remap = self.parser.unparse_row(input_remap)
        self.assertEqual(output_remap, output_remap_exp)

    def test_clashingremap1(self):
        output_remap = self.parser.unparse_row(input_clashing_remap1)
        self.assertEqual(output_remap, output_clashing_remap_exp1)

    def test_clashingremap2(self):
        output_remap = self.parser.unparse_row(input_clashing_remap2)
        self.assertEqual(output_remap, output_clashing_remap_exp2)

    def test_clashingremap3(self):
        with self.assertRaises(RowParserError):
            self.parser.unparse_row(input_clashing_remap3)


class TestToNestedList(unittest.TestCase):
    def setUp(self):
        self.parser = RowParser(MainModel, MockCellParser())

    def compare_to_nested_list(self, inp, outp_exp):
        outp = self.parser.to_nested_list(inp)
        self.assertEqual(outp, outp_exp)

    def test_to_nested_list(self):
        self.compare_to_nested_list("abc", "abc")
        self.compare_to_nested_list(["a"], ["a"])
        self.compare_to_nested_list(["a", "c"], ["a", "c"])
        self.compare_to_nested_list(["a", ["c"]], ["a", ["c"]])
        in1 = ModelWithStuff(**submodel_2_dict)
        out1 = [
            ["list_str", ["a", "b", "c"]],
            ["int_field", 5],
            ["str_field", "string"],
        ]
        self.compare_to_nested_list(in1, out1)
        self.compare_to_nested_list([in1], [out1])
        output2 = [
            ["str_field", "main model string"],
            ["model_default", out1],
        ]
        self.compare_to_nested_list(input2, output2)


class ModelWithBasicFields(ParserModel):
    int_field: int = 0
    str_field: str = ""


class MetaModel(ParserModel):
    basic_model: ModelWithBasicFields = ModelWithBasicFields()
    string: str = ""


class MetaModelList(ParserModel):
    basic_model_list: List[ModelWithBasicFields] = []
    model_with_stuff: ModelWithStuff = ModelWithStuff()


class TestUnparseToStringDict(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.parser = RowParser(MainModel, CellParser())

        self.mws = ModelWithStuff(**submodel_2_dict)

        self.metainstance = MetaModel(
            basic_model=ModelWithBasicFields(int_field=42, str_field="word"),
            string="metaword",
        )

        self.metalistinstance = MetaModelList(
            basic_model_list=[
                ModelWithBasicFields(int_field=42, str_field="word"),
                ModelWithBasicFields(int_field=14, str_field="draw"),
            ],
            model_with_stuff=self.mws,
        )

    def test_submodel(self):
        output1 = self.parser.unparse_row(self.mws)
        exp1 = {
            "list_str.1": "a",
            "list_str.2": "b",
            "list_str.3": "c",
            "int_field": 5,
            "str_field": "string",
        }
        self.assertEqual(output1, exp1)

        output2 = self.parser.unparse_row(self.mws, target_headers={"list_str"})
        exp2 = {"list_str": "a|b|c", "int_field": 5, "str_field": "string"}
        self.assertEqual(output2, exp2)

    def test_metamodel(self):
        output1 = self.parser.unparse_row(self.metainstance)
        exp1 = {
            "basic_model.int_field": 42,
            "basic_model.str_field": "word",
            "string": "metaword",
        }
        self.assertEqual(output1, exp1)

        output2 = self.parser.unparse_row(
            self.metainstance, target_headers={"basic_model"}
        )
        exp2 = {
            "basic_model": "int_field;42|str_field;word",
            "string": "metaword",
        }
        self.assertEqual(output2, exp2)

    def test_metamodellist(self):
        output1 = self.parser.unparse_row(self.metalistinstance)
        exp1 = {
            "basic_model_list.1.int_field": 42,
            "basic_model_list.1.str_field": "word",
            "basic_model_list.2.int_field": 14,
            "basic_model_list.2.str_field": "draw",
            "model_with_stuff.list_str.1": "a",
            "model_with_stuff.list_str.2": "b",
            "model_with_stuff.list_str.3": "c",
            "model_with_stuff.int_field": 5,
            "model_with_stuff.str_field": "string",
        }
        self.assertEqual(output1, exp1)

        output2 = self.parser.unparse_row(
            self.metalistinstance,
            target_headers={"model_with_stuff.list_str", "basic_model_list.1"},
        )
        exp2 = {
            "basic_model_list.1": "int_field;42|str_field;word",
            "basic_model_list.2.int_field": 14,
            "basic_model_list.2.str_field": "draw",
            "model_with_stuff.list_str": "a|b|c",
            "model_with_stuff.int_field": 5,
            "model_with_stuff.str_field": "string",
        }
        self.assertEqual(output2, exp2)

    def test_asterisk1(self):
        output2 = self.parser.unparse_row(self.mws, target_headers={"*"})
        exp2 = {"list_str": "a|b|c", "int_field": 5, "str_field": "string"}
        self.assertEqual(output2, exp2)

    def test_asterisk2(self):
        output2 = self.parser.unparse_row(
            self.metalistinstance,
            target_headers={"model_with_stuff.*", "basic_model_list.*"},
        )
        exp2 = {
            "basic_model_list.1": "int_field;42|str_field;word",
            "basic_model_list.2": "int_field;14|str_field;draw",
            "model_with_stuff.list_str": "a|b|c",
            "model_with_stuff.int_field": 5,
            "model_with_stuff.str_field": "string",
        }
        self.assertEqual(output2, exp2)

    def test_exclude(self):
        output1 = self.parser.unparse_row(
            self.metalistinstance,
            excluded_headers={"model_with_stuff.int_field", "basic_model_list.1"},
        )
        exp1 = {
            "basic_model_list.2.int_field": 14,
            "basic_model_list.2.str_field": "draw",
            "model_with_stuff.list_str.1": "a",
            "model_with_stuff.list_str.2": "b",
            "model_with_stuff.list_str.3": "c",
            "model_with_stuff.str_field": "string",
        }
        self.assertEqual(output1, exp1)
