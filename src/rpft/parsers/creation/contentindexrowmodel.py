from enum import Enum
from typing import List

from pydantic.v1 import Field

from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation.flowrowmodel import WhatsAppTemplating, Webhook
from rpft.parsers.creation.models import SurveyConfig


class ContentIndexType(Enum):
    SURVEY = "survey"


class TemplateArgument(ParserModel):
    name: str
    type: str = ""
    default_value: str = ""


class Operation(ParserModel):
    type: str = ""
    expression: str = ""
    order: str = ""


class ContentIndexRowModel(ParserModel):
    type: str = ""
    new_name: str = ""
    sheet_name: List[str] = []
    data_sheet: str = ""
    data_row_id: str = ""
    template_argument_definitions: List[TemplateArgument] = []  # internal name
    template_arguments: list = []
    survey_config: SurveyConfig = SurveyConfig()
    operation: Operation = Operation()
    data_model: str = ""
    group: str = ""
    status: str = ""
    tags: List[str] = []

    def field_name_to_header_name(field):
        if field == "template_argument_definitions":
            return "template_arguments"
        if field == "survey_config":
            return "config"

    def header_name_to_field_name_with_context(header, row):
        if row["type"] == "template_definition" and header == "template_arguments":
            return "template_argument_definitions"
        if row["type"] == ContentIndexType.SURVEY.value and header == "config":
            return "survey_config"
        else:
            return header


class CreateFlowRowModel(ParserModel):
    audio: str = ""
    choices: List[str] = []
    condition: str = ""
    condition_name: str = ""
    condition_type: str = ""
    condition_var: str = ""
    data_row_id: str = ""
    data_sheet: str = ""
    from_: str = Field(alias="from", default="")
    image: str = ""
    include_if: str = ""
    loop_variable: str = ""
    mainarg_destination_row_ids: List[str] = []
    mainarg_expression: str = ""
    message_text: str = ""
    no_response: str = ""
    nodeId: str = Field(alias="_nodeId", default="")
    node_name: str = ""
    obj_id: str = ""
    obj_name: str = ""
    row_id: str = ""
    save_name: str = ""
    template_arguments: list = []
    type: str = ""
    video: str = ""
    wa_template: WhatsAppTemplating = WhatsAppTemplating()
    webhook: Webhook = Webhook()
