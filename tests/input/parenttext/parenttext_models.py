from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List


class GoalModel(DataRowModel):
	goal: str = ''
	modules: List[str] = []
	modules_concat: str = ''

class HandlerModel(DataRowModel):
	split_variable: str = ''
	module: List[str] = []

class ModuleModel(DataRowModel):
	age_baby: bool = True
	age_child: bool = True
	age_teen: bool = True
	template_type: str = ''

class TemplateTypeModel(DataRowModel):
	blocks: List[str] = []


# block models
class IntroductionBlockModel(DataRowModel):
	skill_introduction_msg_list: List[str] = []

class ImportanceBlockModel(DataRowModel):
	skill_importance: str = ''


class SurveyBlockModel(DataRowModel):
	survey_ID: str = ''
	survey_intro: str = ''


class SurveyQuestionModel(DataRowModel):
	survey_question: str = ''
	max_val: int = 7
	improvement: str = ''
	threshold_positive: int = 4
	feedback_better: List[str] = []
	feedback_worse: List[str] = []

class VideoBlockModel(DataRowModel):
	video_message: str = ''
	old_video_message: str = ''
	video_file: str = ''
	audio_message: str = ''
	audio_file: str = ''
	expiration_time_minutes: int = 2

class CongratulationsBlockModel(DataRowModel):
	congratulations_message: str = ''

class HomeActivityBlockModel(DataRowModel):
	home_activity: str = ''

class ComicBlockModel(DataRowModel):
	comic_introduction: str = ''
	comic_attachment: str = ''
	n_comic_attachments: int = 0
	comic_next_button: str = ''
	comic_text: List[str] = []
	comic_interaction: str = ''
	comic_no_message: str = ''

class TipsBlockModel(DataRowModel):
	tip_introduction: str = ''
	tip_interaction: str = ''
	tip_next_button: str = ''
	tip_no_message: str = ''
	tip_message: List[List[str]] = []

"""
class InteractionBlockModel(DataRowModel):

"""

# old - delete?
class ContentModel(DataRowModel):
	message: str = ''
