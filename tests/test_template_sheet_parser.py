import unittest
import copy

from rpft.parsers.common.rowparser import RowParser, ParserModel
from rpft.parsers.common.cellparser import CellParser
from rpft.parsers.creation.template_sheet_parser import TemplateSheetParser
from tests.utils import traverse_flow, Context, get_table_from_file


class ResponseMessages(ParserModel):
    positive: str
    negative: str

class YesNoTemplate(ParserModel):
    ID: str
    prompt: str
    response_messages: ResponseMessages


class TestParsing(unittest.TestCase):

    def setUp(self) -> None:
        row_parser = RowParser(YesNoTemplate, CellParser())
        self.template_sheet_parser = TemplateSheetParser(row_parser)

    def test_parse(self):
        flow_rows = get_table_from_file('input/templates/yes_no_template.csv')
        template_rows = get_table_from_file('input/templates/yes_no_template_instances.csv')
        rapidpro_container = self.template_sheet_parser.parse_sheet(template_rows, flow_rows)

        self.assertEqual(len(rapidpro_container.flows), 2)

        flow0 = rapidpro_container.flows[0].render()
        flow1 = rapidpro_container.flows[1].render()

        context = Context(inputs=['yes'])
        actions0 = traverse_flow(flow0, copy.deepcopy(context))
        actions1 = traverse_flow(flow1, copy.deepcopy(context))
        actions_exp0 = [('send_msg', 'Are you happy?'), ('send_msg', 'Amaaaazing!')]
        actions_exp1 = [('send_msg', 'Are you sad?'), ('send_msg', 'Oh no!')]
        self.assertEqual(actions0, actions_exp0)
        self.assertEqual(actions1, actions_exp1)

        context = Context(inputs=['something', 'no'])
        actions0 = traverse_flow(flow0, copy.deepcopy(context))
        actions1 = traverse_flow(flow1, copy.deepcopy(context))
        actions_exp0 = [
            ('send_msg', 'Are you happy?'), 
            ('send_msg', "Sorry, I don't understand what you mean."), 
            ('send_msg', 'Are you happy?'), 
            ('send_msg', 'Oh no!')
        ]
        actions_exp1 = [
            ('send_msg', 'Are you sad?'), 
            ('send_msg', "Sorry, I don't understand what you mean."), 
            ('send_msg', 'Are you sad?'), 
            ('send_msg', 'Good to hear.')
        ]
        self.assertEqual(actions0, actions_exp0)
        self.assertEqual(actions1, actions_exp1)
