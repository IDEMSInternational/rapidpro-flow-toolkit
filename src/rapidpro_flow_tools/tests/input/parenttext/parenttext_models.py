from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List



###################################################################
class IntroductionBlockModel(ParserModel):
	msg_list: List[str] = []

class ImportanceBlockModel(ParserModel):
	msg_list: List[str] = []

class QuizContentModel(ParserModel):
	question: str = ''
	values: List[str] = []
	answer: str = ''
	feedback_correct: str = ''
	feedback_incorrect: str = ''

class QuizBlockModel(ParserModel):
	intro: str = ''
	content: List[QuizContentModel] = []


class TipsBlockModel(ParserModel):
	intro: str = ''
	next_button: str = ''
	message: List[str] = []

class ComicBlockModel(ParserModel):
	intro: str = ''
	attachment: str = ''
	n_attachments: str = ''
	next_button: str = ''
	text: List[str] = []

class HomeActivityBlockModel(ParserModel):
	activity: str = ''
	positive_msg: str = ''
	negative_msg: str = ''

class CongratulationsBlockModel(ParserModel):
	msg_list: List[str] = []


class VideoBlockModel(ParserModel):
	message: str = ''
	file_name: str = ''
	expiration_time_min: str = ''


class AudioBlockModel(ParserModel):
	message: str = ''
	file_name: str = ''
	expiration_time_min: str = ''

class PlhContentModel(DataRowModel):
	introduction: IntroductionBlockModel = IntroductionBlockModel()
	importance: ImportanceBlockModel = ImportanceBlockModel()
	quiz: QuizBlockModel = QuizBlockModel()
	tips: TipsBlockModel = TipsBlockModel()
	comic: ComicBlockModel = ComicBlockModel()
	home_activity: HomeActivityBlockModel = HomeActivityBlockModel()
	video: VideoBlockModel = VideoBlockModel()
	audio: AudioBlockModel = AudioBlockModel()
	congratulations: CongratulationsBlockModel = CongratulationsBlockModel()


class TrackerInfoModel(ParserModel):
	name: str = ''
	tracker_tot: str = ''
	has_tracker: str = ''

class FlowStructureModel(DataRowModel):
	block: List[TrackerInfoModel] = []


class BlockMetadataModel(DataRowModel):
	include_if_cond: str = ''
	args: str = ''

#########################################################
class PreGoalCheckInModel(DataRowModel):
	question: str = ''
	options: str = ''
	threshold_positive: str = ''
	above_threshold_msg: str = ''
	below_threshold_msg: str = ''
	


###########################################################
# onboarding

class OnboardingStepsModel(DataRowModel):
	flow: str = ''
	variable: str = ''

class OnboardingQuestionOptionModel(ParserModel):
	text: str = ''
	value: str = ''

class OnboardingQuestionWithOptionsModel(DataRowModel):
	question: str = ''
	image: str = ''
	variable: str = ''
	options : List[OnboardingQuestionOptionModel] = []

class OnboardingQuestionInputModel(DataRowModel):
	question: str = ''
	variable: str = ''

class OnboardingRangeModel(ParserModel):
	limit: str = ''
	var_value: str = ''

class OnboardingQuestionRangeModel(DataRowModel):
	question: str = ''
	variable: str = ''
	grouping_variable: str = ''
	lower_bound: int = 0
	low_error_msg: str = ''
	upper_bound: int = 0
	up_error_msg: str = ''
	general_error_msg: str = ''
	ranges: List[OnboardingRangeModel] = []


'''

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
	congratulations_message_list: List[str] = []

class HomeActivityOptionModel(ParserModel):
	option: str = ''
	message: str = ''

class HomeActivityBlockModel(DataRowModel):
	home_activity_interaction: str = ''
	home_activity_positive: HomeActivityOptionModel = HomeActivityOptionModel()
	home_activity_negative: HomeActivityOptionModel = HomeActivityOptionModel()

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

class QuizOptionModel(ParserModel):
	option: str = ''
	feedback: str = ''

class QuizBlockModel(DataRowModel):
	quiz_question: str = ''
	quiz_options: List[QuizOptionModel] = []
	

class SingleTipBlockModel(DataRowModel):
	single_tip_message: str = ''

class ReferralsBlockModel(DataRowModel):
	referrals_message: str = ''


## check-ins

class TroubleModel(ParserModel):
	problem: str = ''
	tip: List[str] = []

class TroubleshootingModel(DataRowModel):
	question: str = ''
	tbs: List[TroubleModel] = []

class CheckInWrapperModel(DataRowModel):
	managed_message: str = ''
	positive_label : str = ''
	negative_label: str = ''
	positive_message: str = ''
	negative_message: str = ''
	how_message: str = ''
	good_label: str = ''
	good_message: str = ''
	good_message_attachment: str = ''
	neutral_label: str = ''
	neutral_message: str = ''
	bad_label: str = ''
	bad_message: str = ''
	other_label: str = '' #remove?
	other_message: str = '' #remove?
	content_offer: str = ''
	no_content_message: str = ''												
'''