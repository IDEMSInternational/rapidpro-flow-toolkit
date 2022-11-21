import unittest
import json
import copy

from .utils import traverse_flow, Context, get_dict_from_csv
from parsers.creation.flowparser import FlowParser
from rapidpro.models.containers import RapidProContainer

class TestFlowParserReverse(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def compare_models_leniently(self, model, model_exp):
        model_dict = model.dict()
        model_exp_dict = model_exp.dict()
        for edge, edge_exp in zip(model_dict["edges"], model_exp_dict["edges"]):
            if edge["condition"]["variable"] == "@input.text" and edge_exp["condition"]["variable"] == "":
                # @input.text is implicit when left blank.
                edge_exp["condition"]["variable"] = "@input.text"
        if model.node_uuid and not model_exp.node_uuid:
            # If no explicit node UUID was specified, don't compare the generated node uuid
            model_dict['node_uuid'] = ''
        if model.obj_id and not model_exp.obj_id:
            # If no explicit object UUID was specified, don't compare
            model_dict['obj_id'] = ''
        for field in ['image', 'audio', 'video', 'obj_name', 'node_name', 'ui_type']:
            # We ignore these. Attachments need to be rethought,
            # the other of these fields may be removed as well.
            model_dict.pop(field)
            model_exp_dict.pop(field)
        # TODO: We have trailing '' quick replies here.
        # They get removed in the conversion process, but probably the RowParser
        # should already take care of them
        model_exp_dict['choices'] = [qr for qr in model_exp_dict['choices'] if qr]
        self.assertEqual(model_dict, model_exp_dict)

    def run_example(self, filename, flow_name):
        self.maxDiff = None
        rows = get_dict_from_csv(filename)
        container = RapidProContainer()
        parser = FlowParser(container, rows=rows, flow_name=flow_name)
        flow = parser.parse()
        container.validate()
        row_models = flow.to_rows()
        self.assertEqual(len(row_models), len(parser.data_rows))
        for model, model_exp in zip(row_models, parser.data_rows):
            self.compare_models_leniently(model, model_exp)

    def test_no_switch_nodes(self):
        self.run_example('input/no_switch_nodes.csv', 'no_switch_nodes')

    def test_switch_nodes(self):
        self.run_example('input/switch_nodes.csv', 'switch_nodes')

    def test_loop_from_start(self):
        self.run_example('input/loop_from_start.csv', 'loop_from_start')

    def test_groups_and_flows(self):
        self.run_example('input/groups_and_flows.csv', 'groups_and_flows')

    def test_loop_and_multiple_conditions(self):
        self.run_example('input/loop_and_multiple_conditions.csv', 'loop_and_multiple_conditions')

    def test_rejoin(self):
        self.run_example('input/rejoin.csv', 'rejoin')
