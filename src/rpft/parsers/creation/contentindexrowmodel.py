from enum import Enum
from collections.abc import Sequence

from pydantic import BaseModel, Field, validator

from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation.models import SurveyConfig


def collect(v):
    return v if isinstance(v, Sequence) and not isinstance(v, str) else [v]


def validator_collect(cls, v):
    return collect(v)


def is_pairs(value):
    return all(isinstance(item, Sequence) and len(item) == 2 for item in value)


def populate(cls, v, field):
    if (
        issubclass(field.type_, BaseModel)
        and isinstance(v, Sequence)
        and not is_pairs(v)
    ):
        fields = field.type_.__fields__
        field_count = len(fields)
        vals = (
            v + [""] * (field_count - len(v))
            if len(v) < field_count
            else v[:field_count]
        )

        return {
            f.alias: val[1] if isinstance(val, list) and len(val) > 1 else val
            for f, val in zip(fields.values(), vals)
        }

    return v


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
    sheet_name: list[str] = []
    data_sheet: str = ""
    data_row_id: str = ""
    template_argument_definitions: list[TemplateArgument] = []  # internal name
    template_arguments: list = []
    options: dict = {}
    survey_config: SurveyConfig = SurveyConfig()
    operation: Operation = Field(default_factory=Operation)
    data_model: str = ""
    group: str = ""
    status: str = ""
    tags: list[str] = []

    # def __init__(self, **kwargs):
    #     if kwargs.get("type") == "template_definition" and kwargs.get(
    #         "template_arguments"
    #     ):
    #         kwargs["template_argument_definitions"] = collect(
    #             kwargs["template_arguments"]
    #         )

    #     super().__init__(**kwargs)

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

    # _collect = validator(
    #     "sheet_name",
    #     "template_arguments",
    #     "tags",
    #     "operation",
    #     pre=True,
    #     allow_reuse=True,
    # )(validator_collect)

    # _populate = validator(
    #     "operation",
    #     "survey_config",
    #     pre=True,
    #     allow_reuse=True,
    # )(populate)

    # @validator("template_argument_definitions", pre=True)
    # def from_list(cls, v, values, field):
    #     if (
    #         values["type"] == "template_definition"
    #         and isinstance(v, Sequence)
    #         and not all(isinstance(item, dict) or is_pairs(item) for item in v)
    #     ):
    #         fields = TemplateArgument.__fields__.keys()
    #         v = [{k: v for k, v in zip(fields, collect(item))} for item in v]

    #     return v
