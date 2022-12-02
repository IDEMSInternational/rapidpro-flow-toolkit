from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List


class GenderAnswerModel(ParserModel):
	question: str = ''
	answer_msg: List[str] = []

class AnswerRowModel(DataRowModel):
	NEUTRAL: GenderAnswerModel = GenderAnswerModel()
	FEMALE: GenderAnswerModel = GenderAnswerModel()
	MALE: GenderAnswerModel = GenderAnswerModel()
	prompt: List[str] = []
