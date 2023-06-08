from typing import List
from rpft.parsers.common.rowparser import ParserModel
from pydantic import Field


class Condition(ParserModel):
    value: str = ''  # Technically, this should be a list as a case may have multiple args
    variable: str = ''
    type: str = ''
    name: str = ''
    # TODO: We could specify proper default values here, and write custom
    # validators that replace '' with the actual default value.


class WhatsAppTemplating(ParserModel):
    name: str = ''
    uuid: str = ''
    variables: List[str] = []


class Edge(ParserModel):
    from_: str = ''
    condition: Condition = Condition()

    def header_name_to_field_name(header):
        field_map = {
            "from" : "from_",
        }
        return field_map.get(header, header)

    def field_name_to_header_name(field):
        field_map = {
            "from_" : "from",
        }
        return field_map.get(field, field)

    def header_name_to_field_name_with_context(header, row):
        return header_name_to_field_name(header)


class FlowRowModel(ParserModel):
    row_id: str = ''
    type: str
    edges: List[Edge]
    # These are the fields that message_text can map to
    loop_variable: List[str] = []
    include_if: bool = True
    mainarg_message_text: str = ''
    mainarg_value: str = ''
    mainarg_groups: List[str] = []
    mainarg_none: str = ''
    mainarg_destination_row_ids: List[str] = []
    mainarg_flow_name: str = ''
    mainarg_expression: str = ''
    mainarg_iterlist: list = [] # no specified type of elements
    wa_template: WhatsAppTemplating = WhatsAppTemplating()
    data_sheet: str = ''
    data_row_id: str = ''
    template_arguments: list = []
    choices: List[str] = []
    save_name: str = ''
    result_category: str = ''
    image: str = ''
    audio: str = ''
    video: str = ''
    obj_name: str = ''  # What is this used for?
    obj_id: str = ''  # This should be a list
    node_name: str = ''  # What is this used for?
    node_uuid: str = ''
    no_response: str = ''
    ui_type: str = ''
    ui_position: List[str] = []

    # TODO: Extra validation here, e.g. from must not be empty
    # type must come from row_type_to_main_arg.keys() (see below)
    # image/audio/video only makes sense if type == send_message
    # mainarg_none should be ''
    # _ui_position should be '' or a list of two ints
    # ...

    def field_name_to_header_name(field):
        field_map = {
            "node_uuid" : "_nodeId",
            "ui_type" : "_ui_type",
            "ui_position" : "_ui_position",
            'mainarg_message_text' : 'message_text',
            'mainarg_value' : 'message_text',
            'mainarg_groups' : 'message_text',
            'mainarg_none' : 'message_text',
            'mainarg_destination_row_ids' : 'message_text',
            'mainarg_flow_name' : 'message_text',
            'mainarg_expression' : 'message_text',
            # 'mainarg_iterlist' : 'message_text',  # Not supported for export
        }
        return field_map.get(field, field)

    def header_name_to_field_name_with_context(header, row):
        # TODO: This should be defined outside of this function
        basic_header_dict = {
            "from" : "edges.*.from_",
            "condition" : "edges.*.condition.value",
            "condition_value" : "edges.*.condition.value",
            "condition_var" : "edges.*.condition.variable",
            "condition_variable" : "edges.*.condition.variable",
            "condition_type" : "edges.*.condition.type",
            "condition_name" : "edges.*.condition.name",
            "_nodeId" : "node_uuid",
            "_ui_type" : "ui_type",
            "_ui_position" : "ui_position",
        }
        # .update({f"choice_{i}" : f"choices:{i}" for i in range(1,11)})

        row_type_to_main_arg = {
            "send_message" : "mainarg_message_text",
            "save_value" : "mainarg_value",
            "add_to_group" : "mainarg_groups",
            "remove_from_group" : "mainarg_groups",
            "save_flow_result" : "mainarg_value",
            "wait_for_response" : "mainarg_none",
            "set_contact_language" : "mainarg_value",
            "set_contact_name" : "mainarg_value",
            "set_contact_status" : "mainarg_value",
            "set_contact_timezone" : "mainarg_value",
            "split_random" : "mainarg_none",
            "go_to" : "mainarg_destination_row_ids",
            "start_new_flow" : "mainarg_flow_name",
            "split_by_value" : "mainarg_expression",
            "split_by_group" : "mainarg_groups",
            "insert_as_block" : "mainarg_flow_name",
            "begin_for" : "mainarg_iterlist",
            "end_for" : "mainarg_none",
            "begin_block" : "mainarg_none",
            "end_block" : "mainarg_none",
            "hard_exit" : "mainarg_none",
            "loose_exit" : "mainarg_none",
            "no_op" : "mainarg_none",
        }

        if header in basic_header_dict:
            return basic_header_dict[header]
        if header == "message_text":
            return row_type_to_main_arg[row["type"]]
        return header

    def is_starting_row(self):
        if len(self.edges) == 1 and self.edges[0].from_ == 'start':
            return True
        return False
