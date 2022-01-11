from typing import List
from parsers.common.rowparser import ParserModel


class Condition(ParserModel):
    value: str = ''
    var: str = ''
    type: str = ''
    name: str = ''
    # TODO: We could specify proper default values here, and write custom
    # validators that replace '' with the actual default value.


class ConditionalFrom(ParserModel):
    row_id: str
    condition: Condition = Condition()


class RowData(ParserModel):
    row_id: str
    type: str
    conditional_from: List[ConditionalFrom]
    choices: List[str] = []
    save_name: str = ''
    image: str = ''
    audio: str = ''
    video: str = ''
    obj_name: str = ''
    obj_id: str = ''
    node_name: str = ''
    _nodeId: str = ''
    no_response: str = ''
    _ui_type: str = ''
    _ui_position: str = ''
    # These are the fields that message_text can map to
    mainarg_message_text: str = ''
    mainarg_value: str = ''
    mainarg_group: str = ''
    mainarg_flowresult: str = ''
    mainarg_none: str = ''
    mainarg_destination_row_ids: List[str] = []
    mainarg_flow_name: str = ''
    mainarg_expression: str = ''

    # TODO: Extra validation here, e.g. from must not be empty
    # type must come from row_type_to_main_arg.keys() (see below)
    # image/audio/video only makes sense if type == send_message
    # mainarg_none should be ''
    # _ui_position should be '' or a list of two ints
    # ...

    def header_name_to_field_name(header):
        field_map = {
            # "from" : "from_",
        }
        return field_map.get(header, header)

    def header_name_to_field_name_with_context(header, row):
        # TODO: This should be defined outside of this function
        basic_header_dict = {
            "from" : "conditional_from:*:row_id",
            "condition_value" : "conditional_from:*:condition:value",
            "condition_var" : "conditional_from:*:condition:var",
            "condition_type" : "conditional_from:*:condition:type",
            "condition_name" : "conditional_from:*:condition:name",
        }

        row_type_to_main_arg = {
            "send_message" : "mainarg_message_text",
            "save_value" : "mainarg_value",
            "add_to_group" : "mainarg_group",
            "remove_from_group" : "mainarg_group",
            "save_flow_result" : "mainarg_flowresult",
            "wait_for_response" : "mainarg_none",
            "split_random" : "mainarg_none",
            "go_to" : "mainarg_destination_row_ids",
            "start_new_flow" : "mainarg_flow_name",
            "split_by_value" : "mainarg_expression",
            "split_by_group" : "mainarg_group",
        }

        if header in basic_header_dict:
            return basic_header_dict[header]
        if header == "message_text":
            return row_type_to_main_arg[row["type"]]
        return header
