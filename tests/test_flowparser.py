import copy
import json
import tablib
import unittest

from rpft.parsers.common.cellparser import CellParser
from rpft.parsers.common.rowparser import RowParser
from rpft.parsers.creation.flowrowmodel import FlowRowModel
from rpft.parsers.creation.flowparser import FlowParser
from rpft.rapidpro.models.actions import Group, AddContactGroupAction
from rpft.rapidpro.models.containers import RapidProContainer, FlowContainer
from rpft.rapidpro.models.nodes import BasicNode
from tests import TESTS_ROOT
from tests.mocks import MockSheetParser
from tests.row_data import (
    get_conditional_node_from_1,
    get_message_with_templating,
    get_unconditional_node_from_1,
    get_start_row,
)
from tests.utils import (
    Context,
    get_dict_from_csv,
    get_table_from_file,
    find_destination_uuid,
    find_node_by_uuid,
    traverse_flow,
)


class TestParsing(unittest.TestCase):

    def setUp(self) -> None:
        self.row_parser = RowParser(FlowRowModel, CellParser())

    def get_render_output_from_file(self, flow_name, filename):
        dict_rows = get_dict_from_csv(filename)
        self.rows = [self.row_parser.parse_row(row) for row in dict_rows]
        return self.get_render_output(flow_name, self.rows)

    def get_render_output(self, flow_name, input_rows):
        sheet_parser = MockSheetParser(None, input_rows)
        parser = FlowParser(RapidProContainer(), flow_name=flow_name, sheet_parser=sheet_parser)
        flow_container = parser.parse()
        return flow_container.render()

    def test_send_message(self):
        render_output = self.get_render_output('send_message', [get_start_row()])

        node_0 = render_output['nodes'][0]
        node_0_actions = node_0['actions']

        self.assertEqual(node_0_actions[0]['type'], 'send_msg')
        self.assertEqual(node_0_actions[0]['text'], 'Text of message')
        self.assertEqual(len(node_0_actions[0]['attachments']), 0)
        self.assertEqual(node_0_actions[0]['quick_replies'], ['Answer 1', 'Answer 2'])

    def test_send_message_with_template(self):
        data_row1 = get_start_row()
        data_row2 = get_message_with_templating()
        render_output = self.get_render_output('send_message_with_template', [data_row1, data_row2])

        node_0 = render_output['nodes'][0]
        node_0_action = node_0['actions'][0]
        self.assertNotIn('templating', node_0_action)

        node_1 = render_output['nodes'][1]
        node_1_action = node_1['actions'][0]
        self.assertIn('templating', node_1_action)
        self.assertIn('uuid', node_1_action['templating'])
        self.assertEqual(node_1_action['templating']['template']['name'], 'template name')
        self.assertEqual(node_1_action['templating']['template']['uuid'], 'template uuid')
        self.assertEqual(node_1_action['templating']['variables'], ['var1', 'var2'])

    def test_linear(self):
        data_row1 = get_start_row()
        data_row2 = get_unconditional_node_from_1()
        data_row2.edges[0].from_ = ''  # implicit continue from last node
        render_output = self.get_render_output('linear', [data_row1, data_row2])

        node_0 = render_output['nodes'][0]
        node_1 = render_output['nodes'][1]
        node_1_actions = node_1['actions']

        self.assertEqual(node_1_actions[0]['text'], 'Unconditional message')
        self.assertEqual(len(node_0['exits']), 1)
        self.assertIsNone(node_0.get('router'))
        self.assertEqual(node_0['exits'][0]['destination_uuid'], node_1['uuid'])
        self.assertEqual(node_1['exits'][0]['destination_uuid'], None)

    def test_only_conditional(self):
        data_row1 = get_start_row()
        data_row3 = get_conditional_node_from_1()
        render_output = self.get_render_output('only_conditional', [data_row1, data_row3])

        self.assertEqual(len(render_output['nodes']), 3)
        node_0 = render_output['nodes'][0]
        node_1 = render_output['nodes'][1]
        node_2 = render_output['nodes'][2]
        node_2_actions = node_2['actions']

        self.assertEqual(node_2_actions[0]['text'], 'Message if @fields.name == 3')
        self.assertEqual(len(node_1['exits']), 2)
        self.assertIsNone(node_0.get('router'))
        self.assertIsNotNone(node_1.get('router'))
        self.assertEqual(node_0['exits'][0]['destination_uuid'], node_1['uuid'])
        self.assertEqual(node_1['exits'][0]['destination_uuid'], node_2['uuid'])
        self.assertEqual(node_1['exits'][1]['destination_uuid'], None)
        self.assertEqual(node_2['exits'][0]['destination_uuid'], None)

    def test_split1(self):
        data_row1 = get_start_row()
        data_row2 = get_unconditional_node_from_1()
        data_row3 = get_conditional_node_from_1()
        data_rows = [data_row1, data_row2, data_row3]
        self.check_split(data_rows)

    def test_split2(self):
        data_row1 = get_start_row()
        data_row2 = get_unconditional_node_from_1()
        data_row3 = get_conditional_node_from_1()
        data_rows = [data_row1, data_row3, data_row2]
        self.check_split(data_rows)

    def check_split(self, data_rows):
        render_output = self.get_render_output('split', data_rows)

        node_start = render_output['nodes'][0]
        node_switch = find_node_by_uuid(render_output, node_start['exits'][0]['destination_uuid'])
        default_destination = find_destination_uuid(node_switch, Context(variables={'@fields.name':'5'}))
        node_2 = find_node_by_uuid(render_output, default_destination)
        cond_destination = find_destination_uuid(node_switch, Context(variables={'@fields.name':'3'}))
        node_3 = find_node_by_uuid(render_output, cond_destination)
        node_2_actions = node_2['actions']
        node_3_actions = node_3['actions']

        self.assertEqual(node_3_actions[0]['text'], 'Message if @fields.name == 3')
        self.assertEqual(node_2_actions[0]['text'], 'Unconditional message')
        self.assertEqual(len(node_switch['exits']), 2)
        self.assertIsNone(node_start.get('router'))
        self.assertIsNotNone(node_switch.get('router'))

    def test_no_switch_node_rows(self):
        render_output = self.get_render_output_from_file('no_switch_node', 'input/no_switch_nodes.csv')

        # Check that node UUIDs are maintained
        nodes = render_output['nodes']
        actual_node_uuids = [node['uuid'] for node in nodes]
        expected_node_uuids = [row.node_uuid for row in self.rows][3:-1]  # The first 4 and last 2 rows are actions joined into a single node.
        self.assertEqual(expected_node_uuids, actual_node_uuids)

        self.assertEqual(render_output['name'], 'no_switch_node')
        self.assertEqual(render_output['type'], 'messaging')
        self.assertEqual(render_output['language'], 'eng')

        self.assertEqual(len(render_output['nodes']), 6)

        node_0 = render_output['nodes'][0]
        node_0_actions = node_0['actions']

        self.assertEqual(len(node_0_actions), 4)

        self.assertEqual(node_0_actions[0]['type'], 'send_msg')
        self.assertEqual(node_0_actions[0]['text'], 'this is a send message node')
        self.assertEqual(len(node_0_actions[0]['attachments']), 0)
        self.assertIn('qr1', node_0_actions[0]['quick_replies'])
        self.assertIn('qr2', node_0_actions[0]['quick_replies'])

        self.assertEqual(node_0_actions[1]['type'], 'send_msg')
        self.assertEqual(node_0_actions[1]['text'], 'message with image')
        self.assertEqual(len(node_0_actions[1]['attachments']), 1)
        self.assertEqual(node_0_actions[1]['attachments'][0], 'image:image u')
        self.assertEqual(len(node_0_actions[1]['quick_replies']), 0)

        self.assertEqual(node_0_actions[2]['type'], 'send_msg')
        self.assertEqual(node_0_actions[2]['text'], 'message with audio')
        self.assertEqual(len(node_0_actions[2]['attachments']), 1)
        self.assertEqual(node_0_actions[2]['attachments'][0], 'audio:audio u')
        self.assertEqual(len(node_0_actions[2]['quick_replies']), 0)

        self.assertEqual(node_0_actions[3]['type'], 'send_msg')
        self.assertEqual(node_0_actions[3]['text'], 'message with video')
        self.assertEqual(len(node_0_actions[3]['attachments']), 1)
        self.assertEqual(node_0_actions[3]['attachments'][0], 'video:video u')
        self.assertEqual(len(node_0_actions[3]['quick_replies']), 0)

        node_1 = render_output['nodes'][1]
        node_1_actions = node_1['actions']

        self.assertEqual(node_0['exits'][0]['destination_uuid'], node_1['uuid'])

        self.assertEqual(len(node_1_actions), 1)
        self.assertEqual(node_1_actions[0]['type'], 'set_contact_field')
        self.assertEqual(node_1_actions[0]['field']['key'], 'test_variable')
        self.assertEqual(node_1_actions[0]['field']['name'], 'test variable')
        self.assertEqual(node_1_actions[0]['value'], 'test value ')

        node_2 = render_output['nodes'][2]
        node_2_actions = render_output['nodes'][2]['actions']

        self.assertEqual(node_1['exits'][0]['destination_uuid'], node_2['uuid'])

        self.assertEqual(len(node_2_actions), 1)
        self.assertEqual(node_2_actions[0]['type'], 'add_contact_groups')
        self.assertEqual(len(node_2_actions[0]['groups']), 1)
        self.assertEqual(node_2_actions[0]['groups'][0]['name'], 'test group')

        node_3 = render_output['nodes'][3]
        node_3_actions = render_output['nodes'][3]['actions']

        self.assertEqual(node_2['exits'][0]['destination_uuid'], node_3['uuid'])
        self.assertEqual(len(node_3_actions), 1)
        self.assertEqual('remove_contact_groups', node_3_actions[0]['type'])
        self.assertEqual(len(node_3_actions[0]['groups']), 1)
        self.assertEqual('test group', node_3_actions[0]['groups'][0]['name'])

        # Make sure it's the same group
        self.assertEqual(node_2_actions[0]['groups'][0]['uuid'], node_3_actions[0]['groups'][0]['uuid'])

        node_4 = render_output['nodes'][4]
        node_4_actions = render_output['nodes'][4]['actions']

        self.assertEqual(node_3['exits'][0]['destination_uuid'], node_4['uuid'])
        self.assertEqual(len(node_4_actions), 1)
        self.assertEqual('set_run_result', node_4_actions[0]['type'])
        self.assertEqual('result name', node_4_actions[0]['name'])
        self.assertEqual('result value', node_4_actions[0]['value'])
        self.assertEqual('my_result_cat', node_4_actions[0]['category'])

        node_5 = render_output['nodes'][5]
        self.assertEqual(node_4['exits'][0]['destination_uuid'], node_5['uuid'])
        self.assertIsNone(node_5['exits'][0]['destination_uuid'])
        node_5_actions = node_5['actions']
        self.assertEqual(len(node_5_actions), 2)
        self.assertEqual(node_5_actions[0]['type'], 'set_contact_language')
        self.assertEqual(node_5_actions[0]['language'], 'eng')
        self.assertEqual(node_5_actions[1]['type'], 'set_contact_name')
        self.assertEqual(node_5_actions[1]['name'], 'John Doe')


        # Check UI positions/types of the first two nodes
        render_ui = render_output['_ui']['nodes']
        self.assertIn(node_0['uuid'], render_ui)
        pos0 = render_ui[node_0['uuid']]['position']
        self.assertEqual((280, 73), (pos0['left'], pos0['top']))
        self.assertEqual('execute_actions', render_ui[node_0['uuid']]['type'])
        self.assertIn(node_1['uuid'], render_ui)
        pos1 = render_ui[node_1['uuid']]['position']
        self.assertEqual((280, 600), (pos1['left'], pos1['top']))
        self.assertEqual('execute_actions', render_ui[node_1['uuid']]['type'])

    def test_switch_node_rows(self):
        render_output = self.get_render_output_from_file('switch_node', 'input/switch_nodes.csv')

        # Check that node UUIDs are maintained
        nodes = render_output['nodes']
        actual_node_uuids = [node['uuid'] for node in nodes]
        expected_node_uuids = [row.node_uuid for row in self.rows]
        self.assertEqual(expected_node_uuids, actual_node_uuids)

        # Check that No Response category is created even if not connected
        last_wait_node = nodes[-2]
        self.assertEqual('No Response', last_wait_node['router']['categories'][-1]['name'])

        # TODO: Ideally, there should be more explicit tests here.
        # At least the functionality is covered by the integration tests simulating the flow.
        # print(json.dumps(render_output, indent=2))

        render_ui = render_output['_ui']['nodes']
        f_uuid = lambda i: render_output['nodes'][i]['uuid']
        f_uipos_dict = lambda i: render_ui[f_uuid(i)]['position']
        f_uipos = lambda i: (f_uipos_dict(i)['left'], f_uipos_dict(i)['top'])
        f_uitype = lambda i: render_ui[f_uuid(i)]['type']
        self.assertIn(f_uuid(0), render_ui)
        self.assertEqual((340, 0), f_uipos(0))
        self.assertEqual((360, 180), f_uipos(1))
        self.assertEqual((840, 1200), f_uipos(-2))
        self.assertEqual((740, 300), f_uipos(-1))
        self.assertEqual("wait_for_response", f_uitype(0))
        self.assertEqual("split_by_subflow", f_uitype(1))
        self.assertEqual("split_by_expression", f_uitype(2))
        self.assertEqual("split_by_contact_field", f_uitype(3))
        self.assertEqual("split_by_run_result", f_uitype(4))
        self.assertEqual("split_by_groups", f_uitype(5))
        self.assertEqual("wait_for_response", f_uitype(6))
        self.assertEqual("split_by_random", f_uitype(7))
        self.assertEqual("execute_actions", f_uitype(8))
        self.assertEqual("execute_actions", f_uitype(9))
        self.assertEqual("wait_for_response", f_uitype(-2))

        # Ensure that wait_for_response cases are working as intended
        node6 = render_output['nodes'][6]
        categories = node6["router"]["categories"]
        self.assertEqual(len(categories), 3)
        self.assertEqual(categories[0]["name"], 'A')
        self.assertEqual(categories[1]["name"], 'Other')
        self.assertEqual(categories[2]["name"], 'No Response')
        self.assertEqual(len(node6["router"]["cases"]), 1)

    def test_groups_and_flows(self):
        # We check that references flows and group are assigned uuids consistently
        tiny_uuid = '00000000-acec-434f-bc7c-14c584fc4bc8'
        test_uuid = '8224bfe2-acec-434f-bc7c-14c584fc4bc8'
        other_uuid = '12345678-acec-434f-bc7c-14c584fc4bc8'
        test_group_dict = {'name': 'test group', 'uuid' : test_uuid}
        other_group_dict = {'name': 'other group', 'uuid' : other_uuid}
        tiny_flow_dict = {'name': 'tiny_flow', 'uuid' : tiny_uuid}

        # Make a flow with a single group node (no UUIDs), and put it into new container
        node = BasicNode()
        node.add_action(AddContactGroupAction([Group('test group'), Group('other group')]))
        tiny_flow = FlowContainer('tiny_flow', uuid=tiny_uuid)
        tiny_flow.add_node(node)
        container = RapidProContainer(groups=[Group('other group', other_uuid)])
        container.add_flow(tiny_flow)

        # Add flow from sheet into container
        dict_rows = get_dict_from_csv('input/groups_and_flows.csv')
        rows = [self.row_parser.parse_row(row) for row in dict_rows]
        sheet_parser = MockSheetParser(None, rows)
        parser = FlowParser(container, flow_name='groups_and_flows', sheet_parser=sheet_parser)
        parser.parse()
        # Render also invokes filling in all the flow/group UUIDs
        render_output = container.render()

        # Ensure container groups are complete and have correct UUIDs
        self.assertIn(test_group_dict, render_output['groups'])
        self.assertIn(other_group_dict, render_output['groups'])
        # These UUIDs are inferred from the sheet/the container groups, respectively
        self.assertEqual(render_output['flows'][0]['nodes'][0]['actions'][0]['groups'], [test_group_dict, other_group_dict])

        nodes = render_output['flows'][1]['nodes']
        # This UUID appears only in a later occurrence of the group in the sheet
        self.assertEqual(nodes[0]['actions'][0]['groups'], [test_group_dict])
        # This UUID is missing from the sheet, but explicit in the flow definition
        self.assertEqual(nodes[1]['actions'][0]['flow'], tiny_flow_dict)
        # This UUID is explicit in the sheet
        self.assertEqual(nodes[2]['actions'][0]['groups'], [test_group_dict])
        # This UUID appears in a previous occurrence of the group in the sheet
        self.assertEqual(nodes[3]['router']['cases'][0]['arguments'], [test_uuid, 'test group'])
        # This UUID was part of the groups in the container, but not in the sheet
        self.assertEqual(nodes[6]['actions'][0]['groups'], [other_group_dict])

        tiny_flow.uuid = 'something else'
        with self.assertRaises(ValueError):
            # The enter_flow node has a different uuid than the flow
            container.validate()

        tiny_flow.uuid = tiny_uuid
        container.flows[1].nodes[2].actions[0].groups[0].uuid = 'something else'
        with self.assertRaises(ValueError):
            # The group is referenced by 2 different UUIDs
            container.validate()


class TestBlocks(unittest.TestCase):

    def setUp(self) -> None:
        self.row_parser = RowParser(FlowRowModel, CellParser())

    def render_output_from_table_data(self, table_data, template_context=None):
        table = tablib.import_set(table_data, format='csv')
        parser = FlowParser(RapidProContainer(), 'basic loop', table, context=template_context or {})
        return parser.parse().render()

    def run_example(self, table_data, messages_exp, context=None, template_context=None):
        render_output = self.render_output_from_table_data(table_data, template_context or {})
        actions = traverse_flow(render_output, context or Context())
        actions_exp = list(zip(['send_msg']*len(messages_exp), messages_exp))
        self.assertEqual(actions, actions_exp)

    def run_example_with_actions(self, table_data, actions_exp, context=None, template_context=None):
        render_output = self.render_output_from_table_data(table_data, template_context or {})
        actions = traverse_flow(render_output, context or Context())
        self.assertEqual(actions, actions_exp)


class TestLoops(TestBlocks):

    def test_basic_loop(self):
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '1,begin_for,start,i,1;2;3\n'
            ',send_message,,,{{i}}. Some text\n'
            ',end_for,,,\n'
        )
        render_output = self.render_output_from_table_data(table_data)
        nodes = render_output["nodes"]
        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0]["actions"][0]["type"], 'send_msg')
        self.assertEqual(nodes[0]["actions"][0]["text"], '1. Some text')
        self.assertEqual(nodes[1]["actions"][0]["text"], '2. Some text')
        self.assertEqual(nodes[2]["actions"][0]["text"], '3. Some text')
        # Also check that the connectivity is correct
        messages_exp = ['1. Some text','2. Some text','3. Some text']
        self.run_example(table_data, messages_exp)

    def test_enumerate(self):
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '1,begin_for,start,text;i,A;B;C\n'
            ',send_message,,,{{i+1}}. {{text}}\n'
            ',end_for,,,\n'
        )
        render_output = self.render_output_from_table_data(table_data)
        nodes = render_output["nodes"]
        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0]["actions"][0]["type"], 'send_msg')
        self.assertEqual(nodes[0]["actions"][0]["text"], '1. A')
        self.assertEqual(nodes[1]["actions"][0]["text"], '2. B')
        self.assertEqual(nodes[2]["actions"][0]["text"], '3. C')

    def test_one_element_loop(self):
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '1,begin_for,start,i,label\n'
            ',send_message,,,{{i}}. Some text\n'
            ',end_for,,,\n'
        )
        render_output = self.render_output_from_table_data(table_data)
        nodes = render_output["nodes"]
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["actions"][0]["type"], 'send_msg')
        self.assertEqual(nodes[0]["actions"][0]["text"], 'label. Some text')

    def test_nested_loop(self):
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '1,begin_for,start,i,1;2\n'
            ',begin_for,,j,A;B\n'
            ',send_message,,,{{i}}{{j}}. Some text\n'
            ',end_for,,,\n'
            ',end_for,,,\n'
        )
        messages_exp = ['1A. Some text','1B. Some text','2A. Some text','2B. Some text']
        self.run_example(table_data, messages_exp)

    def test_loop_within_other_nodes(self):
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '1,send_message,start,,Starting text\n'
            '2,begin_for,1,i,1;2\n'
            ',send_message,,,{{i}}. Some text\n'
            ',end_for,,,\n'
            ',send_message,,,Following text\n'
        )
        messages_exp = ['Starting text','1. Some text','2. Some text','Following text']
        self.run_example(table_data, messages_exp)

    def test_nested_loop_with_other_nodes(self):
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '1,begin_for,start,i,1;2\n'
            ',begin_for,,j,A;B\n'
            ',send_message,,,{{i}}{{j}}. Some text\n'
            ',end_for,,,\n'
            ',send_message,,,End of inner loop\n'
            ',end_for,,,\n'
            ',send_message,,,End of outer loop\n'
        )
        messages_exp = ['1A. Some text','1B. Some text','End of inner loop',
                        '2A. Some text','2B. Some text','End of inner loop','End of outer loop']
        self.run_example(table_data, messages_exp)

    def test_loop_with_explicit_following_node(self):
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '2,begin_for,,i,1;2\n'
            ',send_message,,,{{i}}. Some text\n'
            ',end_for,,,\n'
            ',send_message,2,,Following text\n'
        )
        messages_exp = ['1. Some text','2. Some text','Following text']
        self.run_example(table_data, messages_exp)

    def test_loop_with_goto(self):
        table_data = (
            'row_id,type,from,condition,loop_variable,message_text\n'
            '2,begin_for,start,,i,1;2\n'
            ',send_message,,,,{{i}}. Some text\n'
            ',end_for,,,,\n'
            '3,wait_for_response,2,,,\n'
            ',go_to,3,hello,,2\n'
            ',send_message,3,,,Following text\n'
        )
        messages_exp = ['1. Some text','2. Some text','Following text']
        self.run_example(table_data, messages_exp, Context(inputs=['goodbye']))
        messages_exp = ['1. Some text','2. Some text','1. Some text','2. Some text','Following text']
        self.run_example(table_data, messages_exp, Context(inputs=['hello', 'goodbye']))

    def test_loop_with_goto_into_middle_of_loop(self):
        table_data = (
            'row_id,type,from,condition,loop_variable,message_text\n'
            '2,begin_for,start,,i,1;2\n'
            'item{{i}},send_message,,,,{{i}}. Some text\n'
            ',end_for,,,,\n'
            '3,wait_for_response,2,,,\n'
            ',go_to,3,hello,,item2\n'
            ',send_message,3,,,Following text\n'
        )
        messages_exp = ['1. Some text','2. Some text','Following text']
        self.run_example(table_data, messages_exp, Context(inputs=['goodbye']))
        messages_exp = ['1. Some text','2. Some text','2. Some text','Following text']
        self.run_example(table_data, messages_exp, Context(inputs=['hello', 'goodbye']))

    def test_loop_over_object(self):
        class TestObj:
            def __init__(self, value):
                self.value = value
        test_objs = [TestObj('1'), TestObj('2'), TestObj('A')]
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '2,begin_for,start,obj,{@test_objs@}\n'
            ',send_message,,,Value: {{obj.value}}\n'
            ',end_for,,,\n'
        )
        messages_exp = ['Value: 1', 'Value: 2', 'Value: A']
        self.run_example(table_data, messages_exp, template_context={'test_objs' : test_objs})

    def test_loop_over_range(self):
        table_data = (
            'row_id,type,from,loop_variable,message_text\n'
            '2,begin_for,,i,{@range(5)@}\n'
            ',send_message,,,{{i}}. Some text\n'
            ',end_for,,,\n'
        )
        messages_exp = [f'{i}. Some text' for i in range(5)]
        self.run_example(table_data, messages_exp)


class TestConditionals(TestBlocks):

    def test_block_within_other_nodes(self):
        table_data = (
            'row_id,type,from,message_text\n'
            ',send_message,start,Starting text\n'
            ',begin_block,,\n'
            ',send_message,,Some text\n'
            ',end_block,,\n'
            ',send_message,,Following text\n'
        )
        messages_exp = ['Starting text','Some text','Following text']
        self.run_example(table_data, messages_exp)

    def test_block_with_explicit_from(self):
        table_data = (
            'row_id,type,from,message_text\n'
            ',send_message,start,Starting text\n'
            'X,begin_block,,\n'
            ',send_message,,Some text 1\n'
            ',send_message,,Some text 2\n'
            ',end_block,,\n'
            ',send_message,X,Following text\n'
        )
        messages_exp = ['Starting text','Some text 1','Some text 2','Following text']
        self.run_example(table_data, messages_exp)

    def test_block_with_goto(self):
        table_data = (
            'row_id,type,from,condition,message_text\n'
            '2,begin_block,start,,\n'
            ',send_message,,,Some text\n'
            ',end_block,,,\n'
            '3,wait_for_response,2,,\n'
            ',go_to,3,hello,2\n'
            ',send_message,3,,Following text\n'
        )
        messages_exp = ['Some text','Following text']
        self.run_example(table_data, messages_exp, Context(inputs=['goodbye']))
        messages_exp = ['Some text','Some text','Following text']
        self.run_example(table_data, messages_exp, Context(inputs=['hello', 'goodbye']))

    def test_basic_if(self):
        table_data = (
            'row_id,type,from,include_if,message_text\n'
            ',send_message,,,text1\n'
            ',send_message,,FALSE,text2\n'
            ',send_message,,something,text3\n'
            ',send_message,,False,text4\n'
            ',send_message,,{{1 == 0}},text5\n'
            ',send_message,,{@1 == 0@},text6\n'
            ',send_message,,{@1 == 1@},text7\n'
        )
        messages_exp = ['text1', 'text3', 'text7']
        self.run_example(table_data, messages_exp)

    def test_excluded_block_within_other_nodes(self):
        table_data = (
            'row_id,type,from,include_if,message_text\n'
            ',send_message,start,,Starting text\n'
            ',begin_block,,FALSE,\n'
            ',send_message,,,Skipped text\n'
            ',send_message,,TRUE,Skipped text 2\n'  # Should be skipped anyway
            ',end_block,,,\n'
            ',send_message,,,Following text\n'
        )
        messages_exp = ['Starting text','Following text']
        self.run_example(table_data, messages_exp)

    def test_excluded_for_block(self):
        table_data = (
            'row_id,type,from,include_if,message_text\n'
            ',begin_for,,FALSE,1;2\n'  # No loop var; but it's not parsed anyway
            ',send_message,,,Skipped text\n'
            ',end_for,,,\n'
            ',send_message,,,Following text\n'
        )
        messages_exp = ['Following text']
        self.run_example(table_data, messages_exp)

    def test_excluded_block_with_nested_stuff(self):
        table_data = (
            'row_id,type,from,include_if,message_text\n'
            ',begin_block,,FALSE,\n'
            ',begin_block,,,\n'
            ',send_message,,,Skipped text\n'
            ',begin_for,,,1;2;3\n'  # No loop var; but it's not parsed anyway
            ',send_message,,,{{i}}. Some text\n'
            ',end_for,,,\n'
            ',end_block,,,\n'
            ',begin_for,,,A;B\n'
            ',send_message,,,{{i}}. Some other text\n'
            ',end_for,,,\n'
            ',end_block,,,\n'
            ',send_message,,,Following text\n'
        )
        messages_exp = ['Following text']
        self.run_example(table_data, messages_exp)


class TestMultiExitBlocks(TestBlocks):

    def test_split_by_value(self):
        table_data = (
            'row_id,type,from,condition,message_text\n'
            'X,begin_block,,,\n'
            '1,split_by_value,,,@my_field\n'
            ',send_message,1,Value,It has the value\n'
            ',end_block,,,\n'
            ',send_message,X,,Following text\n'
        )
        messages_exp = ['It has the value','Following text']
        self.run_example(table_data, messages_exp, Context(variables={'@my_field' : 'Value'}))
        messages_exp = ['Following text']
        self.run_example(table_data, messages_exp, Context(variables={'@my_field' : 'Other'}))

    def test_split_by_value_hard_loose_exit(self):
        table_data = (
            'row_id,type,from,condition,message_text\n'
            'X,begin_block,,,\n'
            '1,split_by_value,,,@my_field\n'
            ',send_message,1,Value,It has the value\n'
            ',hard_exit,1,Value2,\n'
            ',loose_exit,1,Value3,\n'
            ',end_block,,,\n'
            ',send_message,X,,Following text\n'
        )
        messages_exp = ['It has the value','Following text']
        self.run_example(table_data, messages_exp, Context(variables={'@my_field' : 'Value'}))
        messages_exp = []
        self.run_example(table_data, messages_exp, Context(variables={'@my_field' : 'Value2'}))
        messages_exp = ['Following text']
        self.run_example(table_data, messages_exp, Context(variables={'@my_field' : 'Value3'}))
        messages_exp = ['Following text']
        self.run_example(table_data, messages_exp, Context(variables={'@my_field' : 'Other'}))

    def test_wait_for_response(self):
        table_data = (
            'row_id,type,from,condition,message_text,no_response\n'
            'X,begin_block,,,,\n'
            '1,wait_for_response,,,,60\n'
            ',send_message,1,Value,It has the value,\n'
            ',send_message,1,No Response,No Response,\n'
            ',end_block,,,\n'
            ',send_message,1,,Other,\n'
            ',send_message,X,,Following text,\n'
        )
        messages_exp = ['It has the value','Following text']
        self.run_example(table_data, messages_exp, Context(inputs=['Value']))
        messages_exp = ['No Response','Following text']
        self.run_example(table_data, messages_exp, Context(inputs=[None]))
        messages_exp = ['Other']
        self.run_example(table_data, messages_exp, Context(inputs=['Something else']))

    def test_wait_for_response_hard_exits(self):
        table_data = (
            'row_id,type,from,condition,message_text,no_response\n'
            'X,begin_block,,,,\n'
            '1,wait_for_response,,,,60\n'
            ',send_message,1,Value,It has the value,\n'
            ',hard_exit,,,,\n'
            ',send_message,1,No Response,No Response,\n'
            ',hard_exit,,,,\n'
            ',end_block,,,\n'
            ',send_message,X,,Following text,\n'
        )
        messages_exp = ['It has the value']
        self.run_example(table_data, messages_exp, Context(inputs=['Value']))
        messages_exp = ['No Response']
        self.run_example(table_data, messages_exp, Context(inputs=[None]))
        messages_exp = ['Following text']
        self.run_example(table_data, messages_exp, Context(inputs=['Something else']))

    def test_enter_flow(self):
        table_data = (
            'row_id,type,from,condition,message_text\n'
            ',send_message,start,,Starting text\n'
            'X,begin_block,,,\n'
            '1,start_new_flow,,,Some_flow\n'
            ',send_message,1,completed,Completed\n'
            ',end_block,,,\n'
            ',send_message,X,,Following text\n'
        )
        messages_exp = [
            ('send_msg', 'Starting text'),
            ('enter_flow','Some_flow'),
            ('send_msg','Completed'),
            ('send_msg','Following text'),
        ]
        self.run_example_with_actions(table_data, messages_exp, Context(inputs=['completed']))
        messages_exp = [
            ('send_msg', 'Starting text'),
            ('enter_flow','Some_flow'),
            ('send_msg','Following text'),
        ]
        self.run_example_with_actions(table_data, messages_exp, Context(inputs=['expired']))


class TestNoOpRow(TestBlocks):

    def test_basic_noop(self):
        table_data = (
            'row_id,type,from,message_text\n'
            ',send_message,,Start message\n'
            ',no_op,,\n'
            ',send_message,,End message\n'
        )
        messages_exp = ['Start message','End message']
        self.run_example(table_data, messages_exp)

    def test_multientry_noop(self):
        table_data = (
            'row_id,type,from,condition,message_text\n'
            '1,wait_for_response,,,\n'
            '2,send_message,1,A,Text A\n'
            '3,send_message,1,,Other\n'
            ',no_op,2;3,,\n'
            ',send_message,,,End message\n'
        )
        messages_exp = ['Text A','End message']
        self.run_example(table_data, messages_exp, context=Context(inputs=["A"]))
        messages_exp = ['Other','End message']
        self.run_example(table_data, messages_exp, context=Context(inputs=["something"]))

    def test_multiexit_noop(self):
        table_data = (
            'row_id,type,from,condition_value,condition_variable,message_text\n'
            ',send_message,,,,Start message\n'
            '1,no_op,,,,\n'
            ',send_message,1,A,@field,Text A\n'
            ',send_message,1,,@field,Other\n'
            ',send_message,1,B,@field,Text B\n'
        )
        messages_exp = ['Start message','Text A']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"A"}))
        messages_exp = ['Start message','Text B']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"B"}))
        messages_exp = ['Start message','Other']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"something"}))

    def test_multiexit_noop2(self):
        # only two rows are swapped, compared to previous case
        table_data = (
            'row_id,type,from,condition_value,condition_variable,message_text\n'
            ',send_message,,,,Start message\n'
            '1,no_op,,,,\n'
            ',send_message,1,,@field,Other\n'
            ',send_message,1,A,@field,Text A\n'
            ',send_message,1,B,@field,Text B\n'
        )
        messages_exp = ['Start message','Text A']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"A"}))
        messages_exp = ['Start message','Text B']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"B"}))
        messages_exp = ['Start message','Other']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"something"}))

    def test_multientryexit_noop(self):
        # only two rows are swapped, compared to previous case
        table_data = (
            'row_id,type,from,condition_value,condition_variable,message_text\n'
            '1,wait_for_response,,,,\n'
            '2,send_message,1,A,,Text 1A\n'
            '3,send_message,1,,,Other\n'
            '4,no_op,2;3,,,\n'
            ',send_message,4,A,@field,Text 2A\n'
            ',send_message,4,,@field,Other\n'
            ',send_message,4,B,@field,Text 2B\n'
        )
        messages_exp = ['Text 1A','Text 2A']
        self.run_example(table_data, messages_exp, context=Context(inputs=["A"], variables={'@field':"A"}))
        messages_exp = ['Text 1A','Text 2B']
        self.run_example(table_data, messages_exp, context=Context(inputs=["A"], variables={'@field':"B"}))
        messages_exp = ['Text 1A','Other']
        self.run_example(table_data, messages_exp, context=Context(inputs=["A"], variables={'@field':"something"}))
        messages_exp = ['Other','Text 2A']
        self.run_example(table_data, messages_exp, context=Context(inputs=["something"], variables={'@field':"A"}))
        messages_exp = ['Other','Text 2B']
        self.run_example(table_data, messages_exp, context=Context(inputs=["something"], variables={'@field':"B"}))
        messages_exp = ['Other','Other']
        self.run_example(table_data, messages_exp, context=Context(inputs=["something"], variables={'@field':"something"}))

    def test_noop_in_block_loose(self):
        # only two rows are swapped, compared to previous case
        table_data = (
            'row_id,type,from,condition_value,condition_variable,message_text\n'
            'X,begin_block,,,,\n'
            ',send_message,,,,Start message\n'
            '1,no_op,,,,\n'
            ',end_block,,,,\n'
            ',send_message,,,,End message\n'
        )
        messages_exp = ['Start message','End message']
        self.run_example(table_data, messages_exp)

    def test_noop_in_block_notloose(self):
        # only two rows are swapped, compared to previous case
        table_data = (
            'row_id,type,from,condition_value,condition_variable,message_text\n'
            'X,begin_block,,,,\n'
            ',send_message,,,,Start message\n'
            '1,no_op,,,,\n'
            ',send_message,,,,End message\n'
            ',end_block,,,,\n'
            ',send_message,,,,End message 2\n'
        )
        messages_exp = ['Start message','End message','End message 2']
        self.run_example(table_data, messages_exp)

    def test_noop_in_block2(self):
        # only two rows are swapped, compared to previous case
        table_data = (
            'row_id,type,from,condition_value,condition_variable,message_text\n'
            'X,begin_block,,,,\n'
            ',send_message,,,,Start message\n'
            '1,no_op,,,,\n'
            ',loose_exit,1,,@field,\n'
            ',hard_exit,1,A,@field,\n'
            ',loose_exit,1,B,@field,\n'
            ',end_block,,,,\n'
            ',send_message,,,,End Message\n'
        )
        messages_exp = ['Start message']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"A"}))
        messages_exp = ['Start message','End Message']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"B"}))
        messages_exp = ['Start message','End Message']
        self.run_example(table_data, messages_exp, context=Context(variables={'@field':"something"}))

    def test_multientry_block(self):
        table_data = (
            'row_id,type,from,condition,message_text\n'
            '1,wait_for_response,start,,\n'
            '2,send_message,1,A,Message A\n'
            '3,send_message,1,,Other\n'
            'X,begin_block,2;3,,\n'
            ',send_message,,,Some text 1\n'
            ',end_block,,,\n'
            ',send_message,,,Following text\n'
        )
        messages_exp = ['Message A','Some text 1','Following text']
        self.run_example(table_data, messages_exp, context=Context(inputs=["A"]))
        messages_exp = ['Other','Some text 1','Following text']
        self.run_example(table_data, messages_exp, context=Context(inputs=["something"]))


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
        with open(TESTS_ROOT / "output/all_test_flows.json", 'r') as file:
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

    def test_no_switch_nodes_without_row_ids(self):
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

