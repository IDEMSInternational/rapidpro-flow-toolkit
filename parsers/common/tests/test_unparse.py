import unittest
import json
from typing import List, Dict, Optional
from collections import OrderedDict

from parsers.common.rowparser import RowParser, ParserModel
from .mock_cell_parser import MockCellParser



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
    ('model_default:int_field', 0),
    ('model_default:str_field', ''),
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
    ('model_default:list_str:0', 'a'),
    ('model_default:list_str:1', 'b'),
    ('model_default:list_str:2', 'c'),
    ('model_default:int_field', 5),
    ('model_default:str_field', 'string'),
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
    ('model_default:int_field', 15),
    ('model_default:str_field', ''),
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
    ('model_optional:list_str:0', 'c'),
    ('model_optional:list_str:1', 'd'),
    ('model_optional:int_field', 10),
    ('model_optional:str_field', 'optional'),
    ('model_default:list_str:0', 'a'),
    ('model_default:list_str:1', 'b'),
    ('model_default:int_field', 5),
    ('model_default:str_field', 'default'),
    ('model_list:0:list_str:0', 'A'),
    ('model_list:0:list_str:1', 'B'),
    ('model_list:0:list_str:2', 'C'),
    ('model_list:0:int_field', 0),
    ('model_list:0:str_field', 'string from first model in list'),
    ('model_list:1:int_field', 15),
    ('model_list:1:str_field', ''),
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


if __name__ == '__main__':
    unittest.main()
