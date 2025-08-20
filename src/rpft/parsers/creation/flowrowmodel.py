from pydantic import model_validator

from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation.models import Condition


class Webhook(ParserModel):
    # Headers should ideally be a dict, once that is supported
    url: str = ""
    method: str = ""
    headers: list = []
    body: str = ""


def list_of_pairs_to_dict(headers):
    # Dict is not yet supported in the row parser,
    # so we need to convert a list of pairs into dict.
    if type(headers) is dict:
        return headers

    if type(headers) is list:
        if headers == [""]:
            return {}

        if not all(map(lambda x: type(x) is list and len(x) == 2, headers)):
            raise ValueError("Value must be a list of pairs.")

        return {k: v for k, v in headers}

    raise ValueError("Value must be a dict or list of pairs.")


def dict_to_list_of_pairs(headers):
    if type(headers) is list:
        return headers

    if type(headers) is dict:
        return [[k, v] for k, v in headers.items()]

    raise ValueError("Value must be a list/dict.")


class WhatsAppTemplating(ParserModel):
    name: str = ""
    uuid: str = ""
    variables: list[str] = []


class Edge(ParserModel):
    from_: str = ""
    condition: Condition = Condition()

    def header_name_to_field_name(header):
        field_map = {
            "from": "from_",
        }
        return field_map.get(header, header)

    def field_name_to_header_name(field):
        field_map = {
            "from_": "from",
        }
        return field_map.get(field, field)

    def header_name_to_field_name_with_context(header, row):
        return Edge.header_name_to_field_name(header)


class FlowRowModel(ParserModel):
    row_id: str = ""
    type: str
    edges: list[Edge]
    loop_variable: list[str] = []
    include_if: bool = True
    mainarg_message_text: str = ""
    mainarg_value: str = ""
    mainarg_groups: list[str] = []
    mainarg_none: str = ""
    mainarg_dict: list = []  # encoded as list of pairs
    mainarg_destination_row_ids: list[str] = []
    mainarg_flow_name: str = ""
    mainarg_expression: str = ""
    mainarg_iterlist: list = []
    wa_template: WhatsAppTemplating = WhatsAppTemplating()
    webhook: Webhook = Webhook()
    data_sheet: str = ""
    data_row_id: str = ""
    template_arguments: list = []
    choices: list[str] = []
    save_name: str = ""
    result_category: str = ""
    image: str = ""
    audio: str = ""
    video: str = ""
    attachments: list[str] = []
    urn_scheme: str = ""
    obj_name: str = ""
    obj_id: str = ""
    node_name: str = ""
    node_uuid: str = ""
    no_response: str = ""
    ui_type: str = ""
    ui_position: list[str] = []

    @model_validator(mode="before")
    def set_main_arg(cls, data):
        try:
            name = cls.header_name_to_field_name_with_context("message_text", data)
            data[name] = data.pop("message_text")
        except Exception:
            pass

        return data

    def field_name_to_header_name(field):
        field_map = {
            "node_uuid": "_nodeId",
            "ui_type": "_ui_type",
            "ui_position": "_ui_position",
            "mainarg_message_text": "message_text",
            "mainarg_value": "message_text",
            "mainarg_groups": "message_text",
            "mainarg_none": "message_text",
            "mainarg_destination_row_ids": "message_text",
            "mainarg_flow_name": "message_text",
            "mainarg_expression": "message_text",
            "mainarg_dict": "message_text",
            "webhook.body": "message_text",
        }
        return field_map.get(field, field)

    def header_name_to_field_name_with_context(header, row):
        basic_header_dict = {
            "from": "edges.*.from_",
            "condition": "edges.*.condition.value",
            "condition_value": "edges.*.condition.value",
            "condition_var": "edges.*.condition.variable",
            "condition_variable": "edges.*.condition.variable",
            "condition_type": "edges.*.condition.type",
            "condition_name": "edges.*.condition.name",
            "_nodeId": "node_uuid",
            "_ui_type": "ui_type",
            "_ui_position": "ui_position",
        }
        row_type_to_main_arg = {
            "send_message": "mainarg_message_text",
            "save_value": "mainarg_value",
            "add_to_group": "mainarg_groups",
            "remove_from_group": "mainarg_groups",
            "save_flow_result": "mainarg_value",
            "wait_for_response": "mainarg_none",
            "add_contact_urn": "mainarg_value",
            "set_contact_language": "mainarg_value",
            "set_contact_name": "mainarg_value",
            "set_contact_status": "mainarg_value",
            "set_contact_timezone": "mainarg_value",
            "split_random": "mainarg_none",
            "go_to": "mainarg_destination_row_ids",
            "call_webhook": "webhook.body",
            "transfer_airtime": "mainarg_dict",
            "start_new_flow": "mainarg_flow_name",
            "split_by_value": "mainarg_expression",
            "split_by_group": "mainarg_groups",
            "insert_as_block": "mainarg_flow_name",
            "begin_for": "mainarg_iterlist",
            "end_for": "mainarg_none",
            "begin_block": "mainarg_none",
            "end_block": "mainarg_none",
            "hard_exit": "mainarg_none",
            "loose_exit": "mainarg_none",
            "no_op": "mainarg_none",
        }

        if header in basic_header_dict:
            return basic_header_dict[header]

        if header == "message_text":
            return row_type_to_main_arg[row["type"]]

        return header

    def is_starting_row(self):
        return len(self.edges) == 1 and self.edges[0].from_ == "start"
