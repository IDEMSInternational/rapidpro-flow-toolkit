from typing import List

from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation.surveymodels import SurveyConfig


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
        if field in ["template_argument_definitions", "survey_config"]:
            return "template_arguments"

    def header_name_to_field_name_with_context(header, row):
        if row["type"] == "template_definition" and header == "template_arguments":
            return "template_argument_definitions"
        if row["type"] == "create_survey" and header == "template_arguments":
            return "survey_config"
        else:
            return header
