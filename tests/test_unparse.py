import unittest
import json
from typing import List, Dict, Optional
from collections import OrderedDict

from rpft.parsers.common.rowparser import RowParser, ParserModel
from tests.mocks import MockCellParser


class ModelWithStuff(ParserModel):
    list_str: List[str] = []
    int_field: int = 0
    str_field: str = ''


class MainModel(ParserModel):
    str_field: str = ''
    model_optional: Optional[ModelWithStuff]
    model_default: ModelWithStuff = ModelWithStuff()
    model_list: List[ModelWithStuff] = []


input1 = MainModel()

output1_exp = OrderedDict([
    ('str_field', ''),
    ('model_default.int_field', 0),
    ('model_default.str_field', ''),
])

input2 = MainModel(**{
    'str_field' : 'main model string',
    'model_default' : {
        'list_str' : ['a', 'b', 'c'],
        'int_field' : 5,
        'str_field' : 'string'
    }
})

output2_exp = OrderedDict([
    ('str_field', 'main model string'),
    ('model_default.list_str.1', 'a'),
    ('model_default.list_str.2', 'b'),
    ('model_default.list_str.3', 'c'),
    ('model_default.int_field', 5),
    ('model_default.str_field', 'string'),
])

input3 = MainModel(**{
    'str_field' : 'main model string',
    'model_default' : {
        'list_str' : [],
        'int_field' : 15,
        'str_field' : ''
    }
})

output3_exp = OrderedDict([
    ('str_field', 'main model string'),
    ('model_default.int_field', 15),
    ('model_default.str_field', ''),
])

input4 = MainModel(**{
    'str_field' : 'main model string',
    'model_default' : {
        'list_str' : ['a', 'b'],
        'int_field' : 5,
        'str_field' : 'default'
    },
    'model_optional' : {
        'list_str' : ['c', 'd'],
        'int_field' : 10,
        'str_field' : 'optional'
    },
    'model_list' : [
        {
            'list_str' : ['A', 'B', 'C'],
            'str_field' : 'string from first model in list'
        },
        {
            'int_field' : 15,
        },
    ],
})

output4_exp = OrderedDict([
    ('str_field', 'main model string'),
    ('model_optional.list_str.1', 'c'),
    ('model_optional.list_str.2', 'd'),
    ('model_optional.int_field', 10),
    ('model_optional.str_field', 'optional'),
    ('model_default.list_str.1', 'a'),
    ('model_default.list_str.2', 'b'),
    ('model_default.int_field', 5),
    ('model_default.str_field', 'default'),
    ('model_list.1.list_str.1', 'A'),
    ('model_list.1.list_str.2', 'B'),
    ('model_list.1.list_str.3', 'C'),
    ('model_list.1.int_field', 0),
    ('model_list.1.str_field', 'string from first model in list'),
    ('model_list.2.int_field', 15),
    ('model_list.2.str_field', ''),
])


# ------ Data for remapping test cases ------
class ChildModel(ParserModel):
    some_field: str = ''

    def field_name_to_header_name(field):
        field_map = {
            "some_field" : "my_field",
        }
        return field_map.get(field, field)

class ModelWithRemap(ParserModel):
    str_field: str = ''
    new_str_field: str = ''
    list_field: List[str] = []
    child_field: Optional[ChildModel]

    def field_name_to_header_name(field):
        field_map = {
            "new_str_field" : "str_field_2",
            "list_field" : "cool_list",
        }
        return field_map.get(field, field)

input_remap = ModelWithRemap(**{
    'str_field' : 'main model string',
    'new_str_field' : 'new string',
    'list_field' : ['cool', 'list'],
    'child_field' : {
        'some_field' : 'some value'
    }
})

output_remap_exp = OrderedDict([
    ('str_field', 'main model string'),
    ('str_field_2', 'new string'),
    ('cool_list.1', 'cool'),
    ('cool_list.2', 'list'),
    ('child_field.my_field', 'some value'),
])


class TestUnparse(unittest.TestCase):

    def setUp(self):
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


if __name__ == '__main__':
    unittest.main()
