import unittest
import json

from parsers.common.rowparser import RowParser
from parsers.common.tests.mock_cell_parser import MockCellParser
from parsers.creation.standard_models import RowData


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
}

output1_exp = RowData(**{
    'row_id' : '1',
    'type' : 'send_message',
    'conditional_from' : [
        {
            'row_id': 'start',
            'condition': {'value':'3', 'var':'@fields.name', 'type':'has_phrase', 'name':''},
        }
    ],
    'mainarg_message_text' : 'Text of message',
    'choices' : ['Answer 1', 'Answer 2'],
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

output2_exp = RowData(**{
    'row_id' : '1',
    'type' : 'send_message',
    'conditional_from' : [
        {
            'row_id': 'start',
            'condition': {'value':'3', 'var':'@fields.name', 'type':'has_phrase', 'name':''},
        },
        {
            'row_id': 'start',
            'condition': {'value':'5', 'var':'@fields.name', 'type':'has_phrase', 'name':''},
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

output3_exp = RowData(**{
    'row_id' : '1',
    'type' : 'send_message',
    'conditional_from' : [
        {
            'row_id': 'start',
            'condition': {'value':'3', 'var':'@fields.name', 'type':'has_phrase', 'name':''},
        },
        {
            'row_id': '5',
            'condition': {'value':'3', 'var':'@fields.name', 'type':'has_phrase', 'name':''},
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

output4_exp = RowData(**{
    'row_id' : '1',
    'type' : 'add_to_group',
    'conditional_from' : [
        {
            'row_id': 'start',
        },
    ],
    'mainarg_group' : 'Group Name',
})


input5 = {
    'row_id' : '1',
    'type' : 'go_to',
    'from' : 'start',
    'message_text' : ['5', '2', '3'],
}

output5_exp = RowData(**{
    'row_id' : '1',
    'type' : 'go_to',
    'conditional_from' : [
        {
            'row_id': 'start',
        },
    ],
    'mainarg_destination_row_ids' : ['5', '2', '3'],
})


input6 = {
    'row_id' : '1',
    'type' : 'send_message',
    'conditional_from' : [
        ['start', ['5']],
        ['start', ['3', '@fields.name', 'has_phrase']]
    ],
    'message_text' : 'Text of message',
}

output6_exp = RowData(**{
    'row_id' : '1',
    'type' : 'send_message',
    'conditional_from' : [
        {
            'row_id': 'start',
            'condition': {'value':'5'},
        },
        {
            'row_id': 'start',
            'condition': {'value':'3', 'var':'@fields.name', 'type':'has_phrase', 'name':''},
        },
    ],
    'mainarg_message_text' : 'Text of message',
})


class TestDifferentWays(unittest.TestCase):

    def setUp(self):
        self.parser = RowParser(RowData, MockCellParser())

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
