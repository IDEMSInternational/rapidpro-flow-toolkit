import unittest
import json
import copy

from .utils import traverse_flow, Context, get_dict_from_csv
from parsers.creation.standard_parser import Parser

class TestStandardParser(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def run_example(self, filename, flow_name, context):
        self.rows = get_dict_from_csv(filename)

        parser = Parser(None, sheet_rows=self.rows, flow_name=flow_name)
        parser.parse()
        output_flow = parser.container.render()

        with open("tests/output/all_test_flows.json", 'r') as file:
            output_exp = json.load(file)
        for flow in output_exp["flows"]:
            if flow["name"] == flow_name:
                flow_exp = flow
                break

        actions = traverse_flow(output_flow, copy.deepcopy(context))
        actions_exp = traverse_flow(flow_exp, copy.deepcopy(context))
        self.assertEqual(actions, actions_exp)


    def test_no_switch_nodes(self):
        self.run_example('input/no_switch_nodes.csv', 'no_switch_nodes', Context())

