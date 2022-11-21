import unittest
import json
import copy

from .utils import traverse_flow, Context, get_dict_from_csv, get_table_from_file
from parsers.creation.flowparser import FlowParser
from rapidpro.models.containers import RapidProContainer, FlowContainer
from parsers.common.tests.mock_sheetparser import MockSheetParser

class TestFlowParser(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def run_example(self, filename, flow_name, context):
        # Generate a flow from sheet
        table = get_table_from_file(filename)
        parser = FlowParser(RapidProContainer(), flow_name, table)
        flow_container = parser.parse()
        output_flow = flow_container.render()
        # print(json.dumps(output_flow, indent=2))

        # Load the expected output flow
        with open("tests/output/all_test_flows.json", 'r') as file:
            output_exp = json.load(file)
        for flow in output_exp["flows"]:
            if flow["name"] == flow_name:
                flow_exp = flow
                break

        # Ensure the generated flow and expected flow are functionally equivalent
        actions = traverse_flow(output_flow, copy.deepcopy(context))
        actions_exp = traverse_flow(flow_exp, copy.deepcopy(context))
        self.assertEqual(actions, actions_exp)

        # Convert the expected output into a flow and then into a sheet
        flow_container = FlowContainer.from_dict(flow_exp)
        new_rows = flow_container.to_rows()
        # Now convert the sheet back into a flow
        sheet_parser = MockSheetParser(None, new_rows)
        parser2 = FlowParser(RapidProContainer(), flow_name=flow_name, sheet_parser=sheet_parser)
        flow_container = parser2.parse()
        new_output_flow = flow_container.render()

        # Ensure the new generated flow and expected flow are functionally equivalent
        new_actions = traverse_flow(new_output_flow, copy.deepcopy(context))
        self.assertEqual(new_actions, actions_exp)

    def test_no_switch_nodes(self):
        self.run_example('input/no_switch_nodes.csv', 'no_switch_nodes', Context())

    def test_no_switch_nodes(self):
        self.run_example('input/no_switch_nodes_without_row_ids.csv', 'no_switch_nodes', Context())

    def test_switch_nodes(self):
        context = Context(inputs=['b', 'expired'])
        self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

        context = Context(inputs=['a', 'completed'],
                variables = {
                    "expression" : 'not a',
                })
        self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

        context = Context(inputs=['a', 'completed'],
                group_names=['wrong group'],
                variables = {
                    "expression" : 'a',
                    "@contact.name" : 'a',
                    "@results.result_wfr" : 'a',
                })
        self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

        context = Context(inputs=['a', 'completed', 'other'],
                group_names=['test group'],
                variables = {
                    "expression" : 'a',
                    "@contact.name" : 'a',
                    "@results.result_wfr" : 'a',
                })
        self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

        context = Context(inputs=['a', 'completed', 'a'],
                random_choices=[0],
                group_names=['test group'],
                variables = {
                    "expression" : 'a',
                    "@contact.name" : 'a',
                    "@results.result_wfr" : 'a',
                })
        self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

        context = Context(inputs=['a', 'completed', 'a'],
                random_choices=[2],
                group_names=['test group'],
                variables = {
                    "expression" : 'a',
                    "@contact.name" : 'a',
                    "@results.result_wfr" : 'a',
                })
        self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

        context = Context(inputs=['a', 'completed', None, None],
                group_names=['test group'],
                variables = {
                    "expression" : 'a',
                    "@contact.name" : 'a',
                    "@results.result_wfr" : 'a',
                })
        self.run_example('input/switch_nodes.csv', 'switch_nodes', context)

    def test_loop_from_start(self):
        context = Context(inputs=['b'])
        self.run_example('input/loop_from_start.csv', 'loop_from_start', context)

        context = Context(inputs=['a', 'b'])
        self.run_example('input/loop_from_start.csv', 'loop_from_start', context)

    def test_rejoin(self):
        context = Context(random_choices=[0])
        self.run_example('input/rejoin.csv', 'rejoin', context)

        context = Context(random_choices=[1])
        self.run_example('input/rejoin.csv', 'rejoin', context)

        context = Context(random_choices=[2])
        self.run_example('input/rejoin.csv', 'rejoin', context)

    def test_loop_and_multiple_conditions(self):
        context = Context(inputs=['adfgyh'], random_choices=[0])
        self.run_example('input/loop_and_multiple_conditions.csv', 'loop_and_multiple_conditions', context)

        context = Context(inputs=['other'], random_choices=[0])
        self.run_example('input/loop_and_multiple_conditions.csv', 'loop_and_multiple_conditions', context)

        context = Context(random_choices=[1])
        self.run_example('input/loop_and_multiple_conditions.csv', 'loop_and_multiple_conditions', context)

        context = Context(inputs=['other'], random_choices=[2])
        self.run_example('input/loop_and_multiple_conditions.csv', 'loop_and_multiple_conditions', context)

        context = Context(inputs=['b', 'a'], random_choices=[2])
        self.run_example('input/loop_and_multiple_conditions.csv', 'loop_and_multiple_conditions', context)

        context = Context(inputs=['b', 'b', 'c'], random_choices=[2])
        self.run_example('input/loop_and_multiple_conditions.csv', 'loop_and_multiple_conditions', context)

