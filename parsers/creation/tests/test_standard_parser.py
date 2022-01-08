import json
import unittest

from parsers.creation.standard_parser import Parser
from tests.utils import get_dict_from_csv, find_destination_uuid, Context, find_node_by_uuid

from parsers.common.rowparser import RowParser
from parsers.creation.standard_models import RowData
from parsers.common.cellparser import CellParser

def get_start_row():
    return RowData(**{
        'row_id' : '1',
        'edges' : [{
            'from_': 'start',
        }],
        'type' : 'send_message',
        'mainarg_message_text' : 'Text of message',
        'choices' : ['Answer 1', 'Answer 2'],
    })

def get_unconditional_node_from_1():
    return RowData(**{
        'row_id' : '2',
        'type' : 'send_message',
        'edges' : [
            {
                'from_': '1',
            }
        ],
        'mainarg_message_text' : 'Unconditional message',
    })

def get_conditional_node_from_1():
    return RowData(**{
        'row_id' : '3',
        'type' : 'send_message',
        'edges' : [
            {
                'from_': '1',
                'condition': {'value':'3', 'variable':'@fields.name', 'type':'has_phrase', 'name':''},
            }
        ],
        'mainarg_message_text' : 'Message if @fields.name == 3',
    })

class TestParsing(unittest.TestCase):

    def setUp(self) -> None:
        self.row_parser = RowParser(RowData, CellParser())

    def test_send_message(self):
        parser = Parser(data_rows=[get_start_row()], flow_name='send_message')
        parser.parse()
        render_output = parser.container.render()

        node_0 = render_output['nodes'][0]
        node_0_actions = node_0['actions']

        self.assertEqual(node_0_actions[0]['type'], 'send_msg')
        self.assertEqual(node_0_actions[0]['text'], 'Text of message')
        self.assertEqual(len(node_0_actions[0]['attachments']), 0)
        self.assertEqual(node_0_actions[0]['quick_replies'], ['Answer 1', 'Answer 2'])

    def test_linear(self):
        data_row1 = get_start_row()
        data_row2 = get_unconditional_node_from_1()
        parser = Parser(data_rows=[data_row1, data_row2], flow_name='linear')
        parser.parse()
        render_output = parser.container.render()

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
        parser = Parser(data_rows=[data_row1, data_row3], flow_name='only_conditional')
        parser.parse()
        render_output = parser.container.render()

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
        parser = Parser(data_rows=data_rows, flow_name='split')
        parser.parse()
        render_output = parser.container.render()

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
        rows = get_dict_from_csv('input/no_switch_nodes.csv')
        no_switch_node_rows = [self.row_parser.parse_row(row) for row in rows]
        parser = Parser(data_rows=no_switch_node_rows, flow_name='no_switch_node')
        parser.parse()
        render_output = parser.container.render()

        self.assertEqual(render_output['name'], 'no_switch_node')
        self.assertEqual(render_output['type'], 'messaging')
        self.assertEqual(render_output['language'], 'eng')

        self.assertEqual(len(render_output['nodes']), 5)

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
        self.assertEqual(node_0_actions[1]['attachments'][0], 'image u')
        self.assertEqual(len(node_0_actions[1]['quick_replies']), 0)

        self.assertEqual(node_0_actions[2]['type'], 'send_msg')
        self.assertEqual(node_0_actions[2]['text'], 'message with audio')
        self.assertEqual(len(node_0_actions[2]['attachments']), 1)
        self.assertEqual(node_0_actions[2]['attachments'][0], 'audio u')
        self.assertEqual(len(node_0_actions[2]['quick_replies']), 0)

        self.assertEqual(node_0_actions[3]['type'], 'send_msg')
        self.assertEqual(node_0_actions[3]['text'], 'message with video')
        self.assertEqual(len(node_0_actions[3]['attachments']), 1)
        self.assertEqual(node_0_actions[3]['attachments'][0], 'video u')
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

        self.assertIsNone(node_4['exits'][0]['destination_uuid'])

    def test_switch_node_rows(self):
        rows = get_dict_from_csv('input/switch_nodes.csv')
        switch_node_rows = [self.row_parser.parse_row(row) for row in rows]
        parser = Parser(data_rows=switch_node_rows, flow_name='switch_node')
        parser.parse()

        render_output = parser.container.render()
        # print(json.dumps(render_output, indent=2))
