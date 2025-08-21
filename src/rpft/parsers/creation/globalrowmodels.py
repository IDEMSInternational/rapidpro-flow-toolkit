from rpft.parsers.creation.datarowmodel import DataRowModel
from rpft.parsers.creation.models import SurveyQuestionModel


class SurveyQuestionRowModel(DataRowModel, SurveyQuestionModel):
    pass


class IDValueRowModel(DataRowModel):
    value: str = ""
