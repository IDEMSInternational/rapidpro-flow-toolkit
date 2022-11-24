import unittest
import json

from .mock_sheetreader import MockSheetReader
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

    def test_basic_template_definition(self):
        ci_sheet = (
            'type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n'
            'template_definition,my_template,,,,,\n'
            'template_definition,my_template2,,,,,draft\n'
        )
        my_template = (
            'row_id,type,from,message_text\n'
            ',send_message,start,Some text\n'
        )

        sheet_reader = MockSheetReader(ci_sheet, {'my_template' : my_template})
        ci_parser = ContentIndexParser(sheet_reader)
        template_table = ci_parser.get_template_table('my_template')
        self.assertEqual(template_table[0][1], 'send_message')
        self.assertEqual(template_table[0][3], 'Some text')
        with self.assertRaises(KeyError):
            ci_parser.get_template_table('my_template2')

    def test_basic_nesting(self):
        ci_sheet = (
            'type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n'
            'template_definition,my_template,,,,,\n'
            'content_index,ci_sheet2,,,,,\n'
        )
        ci_sheet2 = (
            'type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n'
            'template_definition,my_template2,,,,,\n'
        )
        my_template = (
            'row_id,type,from,message_text\n'
            ',send_message,start,Some text\n'
        )
        my_template2 = (
            'row_id,type,from,message_text\n'
            ',send_message,start,Other text\n'
        )
        sheet_dict = {
            'ci_sheet2' : ci_sheet2,
            'my_template' : my_template,
            'my_template2' : my_template2,
        }

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader)
        template_table = ci_parser.get_template_table('my_template')
        self.assertEqual(template_table[0][3], 'Some text')
        template_table = ci_parser.get_template_table('my_template2')
        self.assertEqual(template_table[0][3], 'Other text')

    def test_basic_user_model(self):
        ci_sheet = (
            'type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n'
            'data_sheet,simpledata,,,,SimpleRowModel,\n'
        )
        simpledata = (
            'ID,value1,value2\n'
            'rowA,1A,2A\n'
            'rowB,1B,2B\n'
        )

        sheet_reader = MockSheetReader(ci_sheet, {'simpledata' : simpledata})
        ci_parser = ContentIndexParser(sheet_reader, 'parsers.creation.tests.datarowmodels.simplemodel')
        datamodelA = ci_parser.get_data_model_instance('simpledata', 'rowA')
        datamodelB = ci_parser.get_data_model_instance('simpledata', 'rowB')
        self.assertEqual(datamodelA.value1, '1A')
        self.assertEqual(datamodelA.value2, '2A')
        self.assertEqual(datamodelB.value1, '1B')
        self.assertEqual(datamodelB.value2, '2B')

    def test_generate_flows(self):
        ci_sheet = (
            'type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n'
            'create_flow,my_template,nesteddata,row1,,,\n'
            'create_flow,my_template,nesteddata,row2,,,\n'
            'create_flow,my_basic_flow,,,,,\n'
            'data_sheet,nesteddata,,,,NestedRowModel,\n'
        )
        nesteddata = (
            'ID,value1,custom_field:happy,custom_field:sad\n'
            'row1,Value1,Happy1,Sad1\n'
            'row2,Value2,Happy2,Sad2\n'
        )
        my_template = (
            'row_id,type,from,message_text\n'
            ',send_message,start,{{value1}}\n'
            ',send_message,,{{custom_field.happy}} and {{custom_field.sad}}\n'
        )
        my_basic_flow = (
            'row_id,type,from,message_text\n'
            ',send_message,start,Some text\n'
        )
        sheet_dict = {
            'nesteddata' : nesteddata,
            'my_template' : my_template,
            'my_basic_flow' : my_basic_flow,
        }

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, 'parsers.creation.tests.datarowmodels.nestedmodel')
        container = ci_parser.parse_all_flows()
        render_output = container.render()
        self.compare_messages(render_output, 'my_basic_flow', ['Some text'])
        self.compare_messages(render_output, 'my_template - row1', ['Value1', 'Happy1 and Sad1'])
        self.compare_messages(render_output, 'my_template - row2', ['Value2', 'Happy2 and Sad2'])
