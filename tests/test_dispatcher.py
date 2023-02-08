import unittest
import json

from parsers.creation.contentindexparser import ContentIndexParser
from parsers.sheets.csv_sheet_reader import CSVSheetReader
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

    def test_parsing(self):
        self.maxDiff = None
        sheet_reader = CSVSheetReader('tests/input/content-dispatcher/content-index.csv')
        ci_parser = ContentIndexParser(sheet_reader, user_data_model_module_name='tests.input.content-dispatcher.contentmodel')
        container = ci_parser.parse_all_flows()
        render_output = container.render()
        messages_exp = [
            'Nice to see you :)Bye :)',
        ]
        self.compare_messages(render_output, 'dispatcher_main', messages_exp, Context(variables={'@field.mood':'happy'}))
