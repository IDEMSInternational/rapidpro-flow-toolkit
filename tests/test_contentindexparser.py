import unittest
import json

from parsers.sheets.csv_sheet_reader import CSVSheetReader
from parsers.sheets.xlsx_sheet_reader import XLSXSheetReader
from parsers.creation.contentindexparser import ContentIndexParser
from tests.utils import traverse_flow, Context

class TestParsing(unittest.TestCase):

    def compare_messages(self, render_output, flow_name, messages_exp, context=None):
        flow_found = False
        for flow in render_output["flows"]:
            if flow["name"] == flow_name:
                flow_found = True
                actions = traverse_flow(flow, context or Context())
                actions_exp = list(zip(['send_msg']*len(messages_exp), messages_exp))
                self.assertEqual(actions, actions_exp)
        if not flow_found:
            self.assertTrue(False, msg=f'Flow with name "{flow_name}" does not exist in output.')

    def test_example1_csv(self):
        # Same test as test_generate_flows in parsers/creation/tests/test_contentindexparser
        # but with csvs
        sheet_reader = CSVSheetReader('tests/input/example1/content_index.csv')
        ci_parser = ContentIndexParser(sheet_reader, 'tests.input.example1.nestedmodel')
        container = ci_parser.parse_all_flows()
        render_output = container.render()
        self.compare_messages(render_output, 'my_basic_flow', ['Some text'])
        self.compare_messages(render_output, 'my_template - row1', ['Value1', 'Happy1 and Sad1'])
        self.compare_messages(render_output, 'my_template - row2', ['Value2', 'Happy2 and Sad2'])

    def test_example1_xlsx(self):
        # Same test as above
        sheet_reader = XLSXSheetReader('tests/input/example1/content_index.xlsx')
        ci_parser = ContentIndexParser(sheet_reader, 'tests.input.example1.nestedmodel')
        container = ci_parser.parse_all_flows()
        render_output = container.render()
        self.compare_messages(render_output, 'my_basic_flow', ['Some text'])
        self.compare_messages(render_output, 'my_template - row1', ['Value1', 'Happy1 and Sad1'])
        self.compare_messages(render_output, 'my_template - row2', ['Value2', 'Happy2 and Sad2'])
