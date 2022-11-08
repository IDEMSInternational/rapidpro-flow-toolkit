import unittest
import json
from typing import List, Dict, Optional
from collections import OrderedDict

from .mock_row_parser import MockRowParser
from parsers.common.sheetparser import SheetParser


rowA = OrderedDict([
    ('str_field', 'main string A'),
    ('list_str:0', 'a'),
    ('list_str:1', 'b'),
    ('model_default:int_field', 5),
])

rowB = OrderedDict([
    ('str_field', 'main string B'),
    ('2nd_field', '2nd field'),
    ('list_str:0', 'A'),
])

rowC = OrderedDict([
    ('model_default:int_field', 15),
    ('x:y:z', 'x y z'),
])

rowD = OrderedDict()

rowCycle = OrderedDict([
    ('list_str:0', '1'),
    ('str_field', 'main string Cycle'),
])

outputABCD_exp = [
    'str_field',
    '2nd_field',
    'list_str:0',
    'list_str:1',
    'model_default:int_field',
    'x:y:z',
]

outputAC_exp = [
    'str_field',
    'list_str:0',
    'list_str:1',
    'model_default:int_field',
    'x:y:z',
]


class TestUnParse(unittest.TestCase):

    def setUp(self):
        rowparser = MockRowParser()
        self.sheetparser = SheetParser(rowparser)

    def test_get_headers_ABCD(self):
        output = self.sheetparser.get_headers([rowA, rowB, rowC, rowD])
        self.assertEqual(output, outputABCD_exp)

    def test_get_headers_AC(self):
        output = self.sheetparser.get_headers([rowA, rowC])
        self.assertEqual(output, outputAC_exp)

    def test_get_headers_cycle(self):
        with self.assertRaises(ValueError):
            output = self.sheetparser.get_headers([rowA, rowCycle])


if __name__ == '__main__':
    unittest.main()
