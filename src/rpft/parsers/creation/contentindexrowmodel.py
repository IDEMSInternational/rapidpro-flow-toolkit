from enum import Enum

from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation.models import SurveyConfig


class ContentIndexType(Enum):
    SURVEY = "survey"
    SURVEYQUESTION = "survey_question"


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
    sheet_name: list[str] = []
    data_sheet: str = ""
    data_row_id: str = ""
    template_argument_definitions: list[TemplateArgument] = []  # internal name
    template_arguments: list = []
    options: dict = {}
    survey_config: SurveyConfig = SurveyConfig()
    operation: Operation = Operation()
    data_model: str = ""
    group: str = ""
    status: str = ""
    tags: list[str] = []

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
