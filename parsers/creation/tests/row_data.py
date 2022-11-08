from parsers.creation.standard_models import RowData

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
                'condition': {'value':'3', 'variable':'@fields.name', 'type':'has_phrase', 'name':'3'},
            }
        ],
        'mainarg_message_text' : 'Message if @fields.name == 3',
    })
