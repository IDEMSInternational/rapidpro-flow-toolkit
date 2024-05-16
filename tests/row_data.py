from rpft.parsers.creation.flowrowmodel import FlowRowModel


def get_start_row():
    return FlowRowModel(
        row_id="1",
        edges=[{"from_": "start"}],
        type="send_message",
        mainarg_message_text="Text of message",
        choices=["Answer 1", "Answer 2"],
    )


def get_message_with_templating():
    return FlowRowModel(
        row_id="1",
        edges=[{"from_": "start"}],
        type="send_message",
        mainarg_message_text="Default text of message",
        wa_template={
            "name": "template name",
            "uuid": "template uuid",
            "variables": ["var1", "var2"],
        },
    )


def get_unconditional_node_from_1():
    return FlowRowModel(
        row_id="2",
        type="send_message",
        edges=[{"from_": "1"}],
        mainarg_message_text="Unconditional message",
    )


def get_conditional_node_from_1():
    return FlowRowModel(
        row_id="3",
        type="send_message",
        edges=[
            {
                "from_": "1",
                "condition": {
                    "value": "3",
                    "variable": "@fields.name",
                    "type": "has_phrase",
                    "name": "3",
                },
            }
        ],
        mainarg_message_text="Message if @fields.name == 3",
    )
