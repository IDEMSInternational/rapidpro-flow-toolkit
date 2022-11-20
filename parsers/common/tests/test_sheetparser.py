import unittest
import json
from typing import List, Dict, Optional
from collections import OrderedDict

from parsers.common.rowparser import RowParser, ParserModel
from .mock_row_parser import MockRowParser
from parsers.common.rowdatasheet import RowDataSheet
from parsers.common.sheetparser import SheetParser

class MainModel(ParserModel):
    field1: str = ''
    field2: str = ''


input1 = '''field1,field2
row1f1,row1f2
row2f1,row2f2
row3f1,row3f2
'''

class TestSheetParser(unittest.TestCase):

    def setUp(self):
        self.rowparser = MockRowParser()

    def test_context_and_bookmarks(self):
        parser = SheetParser(self.rowparser, input1)
        row1 = parser.parse_next_row()
        self.assertEqual(row1, {'field1' : 'row1f1', 'field2' : 'row1f2', 'context' : {}})
        parser.create_bookmark('row2')
        parser.add_to_context('key', 'value')
        row2 = parser.parse_next_row()
        self.assertEqual(row2, {'field1' : 'row2f1', 'field2' : 'row2f2', 'context' : {'key': 'value'}})
        parser.remove_from_context('key')
        row3 = parser.parse_next_row()
        self.assertEqual(row3, {'field1' : 'row3f1', 'field2' : 'row3f2', 'context' : {}})
        parser.go_to_bookmark('row2')
        row2b = parser.parse_next_row()
        self.assertEqual(row2b, {'field1' : 'row2f1', 'field2' : 'row2f2', 'context' : {}})

    def test_parse_all(self):
        parser = SheetParser(self.rowparser, input1)
        rows = parser.parse_all()
        self.assertEqual(len(rows), 3)        
        self.assertEqual(rows[0], {'field1' : 'row1f1', 'field2' : 'row1f2', 'context' : {}})        
        self.assertEqual(rows[1], {'field1' : 'row2f1', 'field2' : 'row2f2', 'context' : {}})        
        self.assertEqual(rows[2], {'field1' : 'row3f1', 'field2' : 'row3f2', 'context' : {}})        


if __name__ == '__main__':
    unittest.main()
