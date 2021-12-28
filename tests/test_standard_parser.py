import unittest
import json
import copy

from .utils import traverse_flow, Context, get_dict_from_csv
from parsers.creation.standard_parser import Parser
from parsers.common.rowparser import RowParser
from parsers.creation.standard_models import RowData
from parsers.common.cellparser import CellParser


class TestStandardParser(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def run_example(self, filename, flow_name, context):
        self.row_parser = RowParser(RowData, CellParser())
        rows = get_dict_from_csv(filename)
        self.rows = [self.row_parser.parse_row(row) for row in rows]

        parser = Parser(None, data_rows=self.rows, flow_name=flow_name)
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

    # def test_switch_nodes(self):
    #     context = Context(inputs=['b', 'Expired'])
    #     self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

    #     context = Context(inputs=['a', 'Complete', '1'],
    #             random_choices=[0],
    #             variables = {
    #                 "expression" : 'a',
    #                 "@contact.name" : 'a',
    #                 "@results.result_wfr" : 'a',
    #             })
    #     self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

    # def test_loop_from_start(self):
    #     context = Context(inputs=['b'])
    #     self.run_example('input/loop_from_start.csv', 'loop_from_start', context)

    #     context = Context(inputs=['a', 'b'])
    #     self.run_example('input/loop_from_start.csv', 'loop_from_start', context)
