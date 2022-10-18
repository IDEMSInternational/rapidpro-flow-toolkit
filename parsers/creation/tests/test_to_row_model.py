import unittest
import json

from parsers.creation.standard_parser import Parser
from tests.utils import get_dict_from_csv, find_destination_uuid, Context, find_node_by_uuid
from rapidpro.models.containers import RapidProContainer, FlowContainer
from rapidpro.models.actions import Group, SendMessageAction, AddContactGroupAction, SetRunResultAction
from rapidpro.models.nodes import BasicNode, SwitchRouterNode, RandomRouterNode, EnterFlowNode
from parsers.creation.standard_models import RowData, Edge, Condition

from .row_data import get_start_row, get_unconditional_node_from_1


class TestToRowModels(unittest.TestCase):

    def compare_row_models_without_uuid(self, row_models1, row_models2):
        self.maxDiff = None
        self.assertEqual(len(row_models1), len(row_models2))
        for model1, model2 in zip(row_models1, row_models2):
            data1 = model1.dict()
            data1.pop('node_uuid')
            data2 = model2.dict()
            data2.pop('node_uuid')
            self.assertEqual(data1, data2)


class TestNodes(TestToRowModels):

    def test_basic_node(self):
        row_data = get_start_row()
        node = BasicNode()
        action = SendMessageAction(row_data.mainarg_message_text, quick_replies=row_data.choices)
        node.add_action(action)
        node.initiate_row_models(1, Edge(from_='start'))
        row_models = node.get_row_models()
        self.compare_row_models_without_uuid(row_models, [row_data])

    def test_basic_node_two_actions(self):
        row_data1 = get_start_row()
        row_data2 = get_unconditional_node_from_1()
        node = BasicNode()
        action = SendMessageAction(row_data1.mainarg_message_text, quick_replies=row_data1.choices)
        node.add_action(action)
        action = SendMessageAction(row_data2.mainarg_message_text, quick_replies=row_data2.choices)
        node.add_action(action)
        node.initiate_row_models(1, Edge(from_='start'))
        row_models = node.get_row_models()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_add_group_node(self):
        row_data = RowData(**{
            'row_id' : '1',
            'type' : 'add_to_group',
            'mainarg_groups' : ['test group'],
            'obj_id' : '8224bfe2-acec-434f-bc7c-14c584fc4bc8',
            'edges' : [{ 'from_': 'start' }],
        })
        node = BasicNode()
        action = AddContactGroupAction([Group(row_data.mainarg_groups[0], row_data.obj_id)])
        node.add_action(action)
        node.initiate_row_models(1, Edge(from_='start'))
        row_models = node.get_row_models()
        self.compare_row_models_without_uuid(row_models, [row_data])


class TestFlowContainer(TestToRowModels):

    def test_basic_node(self):
        row_data = get_start_row()
        node = BasicNode()
        action = SendMessageAction(row_data.mainarg_message_text, quick_replies=row_data.choices)
        node.add_action(action)
        container = FlowContainer('test_flow')
        container.add_node(node)
        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data])

    def test_two_basic_nodes(self):
        row_data1 = get_start_row()
        row_data2 = get_unconditional_node_from_1()
        node1 = BasicNode()
        node2 = BasicNode()
        action1 = SendMessageAction(row_data1.mainarg_message_text, quick_replies=row_data1.choices)
        action2 = SendMessageAction(row_data2.mainarg_message_text, quick_replies=row_data2.choices)
        node1.add_action(action1)
        node2.add_action(action2)
        node1.update_default_exit(node2.uuid)
        container = FlowContainer('test_flow')
        container.add_node(node1)
        container.add_node(node2)
        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_conditional_edge(self):
        row_data1 = RowData(**{
            'row_id' : '1',
            'type' : 'split_by_value',
            'edges' : [{ 'from_': 'start' }],
            'mainarg_value' : '@fields.name',
        })
        row_data2 = RowData(**{
            'row_id' : '2',
            'type' : 'send_message',
            'edges' : [
                {
                    'from_': '1',
                    'condition': {'value':'3', 'variable':'@fields.name', 'type':'has_phrase', 'name':'3'},
                }
            ],
            'mainarg_message_text' : 'Message if @fields.name == 3',
        })
        case = row_data2.edges[0].condition
        container = FlowContainer('test_flow')

        node1 = SwitchRouterNode(case.variable)
        node2 = BasicNode()

        node1.add_choice(case.variable, case.type, [case.value], case.name, node2.uuid)
        container.add_node(node1)

        action2 = SendMessageAction(row_data2.mainarg_message_text, quick_replies=row_data2.choices)
        node2.add_action(action2)
        container.add_node(node2)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_random_double_edge(self):
        # Two edges into the same node (i.e. forward edge in the tree)
        # Uses random router

        row_data1 = RowData(**{
            'row_id' : '1',
            'type' : 'split_random',
            'edges' : [{ 'from_': 'start' }],
        })

        row_data2 = RowData(**{
            'row_id' : '2',
            'type' : 'send_message',
            'edges' : [
                { 'from_': '1', 'condition': {'value':'1'}, },
                { 'from_': '1', 'condition': {'value':'2'}, }
            ],
            'mainarg_message_text' : 'Second node message',
        })

        case1 = row_data2.edges[0].condition
        case2 = row_data2.edges[1].condition
        container = FlowContainer('test_flow')

        node1 = RandomRouterNode()
        node2 = BasicNode()

        node1.add_choice(row_data2.edges[0].condition.value, node2.uuid)
        node1.add_choice(row_data2.edges[1].condition.value, node2.uuid)
        container.add_node(node1)

        action2 = SendMessageAction(row_data2.mainarg_message_text)
        node2.add_action(action2)
        container.add_node(node2)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_cyclic_wait_edge(self):
        # An edge for a wait_for_response node to itself (cycle) via go_to

        row_data1 = RowData(**{
            'row_id' : '1',
            'type' : 'wait_for_response',
            'save_name' : 'wait_result',
            'no_response' : '300',
            'edges' : [{ 'from_': 'start' }],
        })

        row_data2 = RowData(**{
            'row_id' : '2',
            'type' : 'go_to',
            'edges' : [
                {
                    'from_': '1',
                    'condition': {'value':'word', 'variable':'@input.text', 'type':'has_any_word', 'name':'Word'},
                }
            ],
            'mainarg_value' : '1',
        })

        case1 = row_data2.edges[0].condition
        container = FlowContainer('test_flow')
        node1 = SwitchRouterNode('@input.text', result_name=row_data1.save_name, wait_timeout=int(row_data1.no_response))
        node1.add_choice(case1.variable, case1.type, [case1.value], case1.name, node1.uuid)
        container.add_node(node1)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_enter_flow_edge(self):
        # Test expired (default) edge of enter_flow node
        # test save_value with a @result (set_run_result in rapidpro)

        row_data1 = RowData(**{
            'row_id' : '1',
            'type' : 'start_new_flow',
            'mainarg_flow_name' : 'sample_flow',
            'obj_id' : '8224bfe2-acec-434f-bc7c-14c584fc4bc8',
            'edges' : [{ 'from_': 'start' }],
        })

        row_data2 = RowData(**{
            'row_id' : '2',
            'type' : 'save_value',
            'edges' : [
                {
                    'from_': '1',
                    'condition': {'value':'expired', 'variable':'@child.run.status', 'type':'has_only_text', 'name':'Expired'},
                }
            ],
            'mainarg_value' : 'Value',
            'save_name' : '@results.my_result',
        })

        case1 = row_data2.edges[0].condition
        container = FlowContainer('test_flow')

        node1 = EnterFlowNode(row_data1.mainarg_flow_name, row_data1.obj_id)
        node2 = BasicNode()
        node1.add_choice(case1.variable, case1.type, [case1.value], case1.name, node2.uuid, is_default=True)
        container.add_node(node1)

        action2 = SetRunResultAction(row_data2.save_name, row_data2.mainarg_value)
        node2.add_action(action2)
        container.add_node(node2)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])
