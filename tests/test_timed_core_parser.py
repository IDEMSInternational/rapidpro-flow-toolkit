import unittest
import json
import copy

from .utils import traverse_flow, Context, get_dict_from_csv
from parsers.creation.timed_core_parser import Parser


class TestTimedCoreParser(unittest.TestCase):
    def setUp(self) -> None:
        rows = get_dict_from_csv('input/timed_core_wrappers.csv')
        parser = Parser(rows=rows)
        parser.parse()
        container = parser.get_container()
        container.update_global_uuids()
        self.output_flows = container.render()

        with open("tests/output/timed_core_flows.json", 'r') as file:
            self.output_exp = json.load(file)

    def check_outputs(self, context):
        for output_flow in self.output_flows["flows"]:
            flow_name = output_flow["name"]
            with self.subTest(flow_name=flow_name):
                for flow in self.output_exp["flows"]:
                    if flow["name"] == flow_name:
                        flow_exp = flow
                        break
                actions = traverse_flow(output_flow, copy.deepcopy(context))
                actions_exp = traverse_flow(flow_exp, copy.deepcopy(context))
                self.assertEqual(actions, actions_exp)

    def test_scenarios(self):
        context = Context(inputs=['expired', 'y', 'expired'])
        self.check_outputs(context)

        context = Context(inputs=['completed', 'yes', 'completed'],
                          variables={ '@fields.toolkit' : 'already completed' })
        self.check_outputs(context)

        context = Context(inputs=['completed', 'no', 'completed'],
                          variables={ '@fields.toolkit' : 'not done yet' })
        self.check_outputs(context)

        context = Context(inputs=['completed', 'something else', 'n', 'completed'],
                          variables={ '@fields.toolkit' : 'not done yet' })
        self.check_outputs(context)
