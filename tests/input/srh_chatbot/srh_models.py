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
	ID2: str = ''

class TopicItemModel(DataRowModel):
	topic: str = ''
	subtopic: str = ''
	info: str = ''

class TopicNavigationModel(ParserModel):
	name: str = ''
	is_flow: str = ''

class NavigationModel(DataRowModel):
	topic: List[TopicNavigationModel] = []
	level: str = ''



class QuestionsEntryModel(ParserModel):
	qst: str = ''
	has_children: str = ''
	has_answer: str = ''

class TopEntryModel(DataRowModel):
	intro: str = ''
	questions: List[QuestionsEntryModel] = []


