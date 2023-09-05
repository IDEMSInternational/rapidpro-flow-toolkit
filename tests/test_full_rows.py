import unittest
import json

from rpft.parsers.common.rowparser import RowParser
from rpft.parsers.creation.flowrowmodel import FlowRowModel
from tests.mocks import MockCellParser


input1 = {
    'row_id' : '1',
    'type' : 'send_message',
    'from' : 'start',
    'condition_value' : '3',
    'condition_var' : '@fields.name',
    'condition_type' : 'has_phrase',
    'condition_name' : '',
    'message_text' : 'Text of message',
    'choices' : ['Answer 1', 'Answer 2'],
    'ui_position' : '',  # CellParser is unaware of types, so '' is NOT turned into a list by the cell parser.
}

output1_exp = FlowRowModel(**{
    'row_id' : '1',
    'type' : 'send_message',
    'edges' : [
        {
            'from_': 'start',
            'condition': {'value':'3', 'variable':'@fields.name', 'type':'has_phrase', 'name':''},
        }
    ],
    'mainarg_message_text' : 'Text of message',
    'choices' : ['Answer 1', 'Answer 2'],
    'ui_position' : [],  # The RowParser converts '' into []
})


input2 = {
    'row_id' : '1',
    'type' : 'send_message',
    'from' : 'start',
    'condition_value' : ['3', '5'],
    'condition_var' : '@fields.name',
    'condition_type' : 'has_phrase',
    'condition_name' : '',
    'message_text' : 'Text of message',
}

output2_exp = FlowRowModel(**{
    'row_id' : '1',
    'type' : 'send_message',
    'edges' : [
        {
            'from_': 'start',
            'condition': {'value':'3', 'variable':'@fields.name', 'type':'has_phrase', 'name':''},
        },
        {
            'from_': 'start',
            'condition': {'value':'5', 'variable':'@fields.name', 'type':'has_phrase', 'name':''},
        },
    ],
    'mainarg_message_text' : 'Text of message',
})


# This is an interesting case.
# It might be that in practice, we would rather that this is interpreted
# as one from with a condition and one unconditional one.
# To realize that, however, we'd have to decouple from from its conditions.
input3 = {
    'row_id' : '1',
    'type' : 'send_message',
    'from' : ['start', '5'],
    'condition_value' : '3',
    'condition_var' : '@fields.name',
    'condition_type' : 'has_phrase',
    'condition_name' : '',
    'message_text' : 'Text of message',
}

output3_exp = FlowRowModel(**{
    'row_id' : '1',
    'type' : 'send_message',
    'edges' : [
        {
            'from_': 'start',
            'condition': {'value':'3', 'variable':'@fields.name', 'type':'has_phrase', 'name':''},
        },
        {
            'from_': '5',
            'condition': {'value':'3', 'variable':'@fields.name', 'type':'has_phrase', 'name':''},
        },
    ],
    'mainarg_message_text' : 'Text of message',
})


input4 = {
    'row_id' : '1',
    'type' : 'add_to_group',
    'from' : 'start',
    'message_text' : 'Group Name',
}

output4_exp = FlowRowModel(**{
    'row_id' : '1',
    'type' : 'add_to_group',
    'edges' : [
        {
            'from_': 'start',
        },
    ],
    'mainarg_groups' : ['Group Name'],
})


input5 = {
    'row_id' : '1',
    'type' : 'go_to',
    'from' : 'start',
    'message_text' : ['5', '2', '3'],
}

output5_exp = FlowRowModel(**{
    'row_id' : '1',
    'type' : 'go_to',
    'edges' : [
        {
            'from_': 'start',
        },
    ],
    'mainarg_destination_row_ids' : ['5', '2', '3'],
})


input6 = {
    'row_id' : '1',
    'type' : 'send_message',
    'edges' : [
        ['start', ['5']],
        ['start', ['3', '@fields.name', 'has_phrase']]
    ],
    'message_text' : 'Text of message',
}

output6_exp = FlowRowModel(**{
    'row_id' : '1',
    'type' : 'send_message',
    'edges' : [
        {
            'from_': 'start',
            'condition': {'value':'5'},
        },
        {
            'from_': 'start',
            'condition': {'value':'3', 'variable':'@fields.name', 'type':'has_phrase', 'name':''},
        },
    ],
    'mainarg_message_text' : 'Text of message',
})


class TestDifferentWays(unittest.TestCase):

    def setUp(self):
        self.parser = RowParser(FlowRowModel, MockCellParser())

    def test_input_1(self):
        output1 = self.parser.parse_row(input1)
        self.assertEqual(output1, output1_exp)

    def test_input_2(self):
        output2 = self.parser.parse_row(input2)
        self.assertEqual(output2, output2_exp)

    def test_input_3(self):
        output3 = self.parser.parse_row(input3)
        self.assertEqual(output3, output3_exp)

    def test_input_4(self):
        output4 = self.parser.parse_row(input4)
        self.assertEqual(output4, output4_exp)

    def test_input_5(self):
        output5 = self.parser.parse_row(input5)
        self.assertEqual(output5, output5_exp)

    def test_input_6(self):
        output6 = self.parser.parse_row(input6)
        self.assertEqual(output6, output6_exp)


if __name__ == '__main__':
    unittest.main()
