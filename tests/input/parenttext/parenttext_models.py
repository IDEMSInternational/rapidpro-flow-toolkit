from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List



###################################################################
class IntroductionBlockModel(ParserModel):
	msg_list: List[str] = []

class ImportanceBlockModel(ParserModel):
	msg_list: List[str] = []

class QuizContentModel(ParserModel):
	question: List[str] = []
	values: List[str] = []
	answer: str = ''
	feedback_correct: List[str] = []
	feedback_incorrect: List[str] = []

class QuizBlockModel(ParserModel):
	intro: str = ''
	content: List[QuizContentModel] = []

class TipModel(ParserModel):
	text: List[str] = []
	image: str = ''

class TipsBlockModel(ParserModel):
	intro: str = ''
	next_button: str = ''
	message: List[TipModel] = []

class ComicBlockModel(ParserModel):
	intro: str = ''
	file_name: str = ''
	n_attachments: str = ''
	next_button: str = ''
	text: List[str] = []

class HomeActivityBlockModel(ParserModel):
	intro: List[str] = []
	activity: str = ''
	positive_msg: str = ''
	negative_msg: str = ''

class CongratulationsBlockModel(ParserModel):
	msg_list: List[str] = []


class VideoBlockModel(ParserModel):
	script: str = ''
	message: str = ''
	file_name: str = ''
	expiration_time_min: str = ''


class AudioBlockModel(ParserModel):
	message: str = ''
	file_name: str = ''
	expiration_time_min: str = ''

class PlhContentModel(DataRowModel):
	module_name: str = ''
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
##goal check in

class TroubleModel(ParserModel):
	pb: str = ''
	tip: List[str] = []

class TroubleshootingModel(DataRowModel):
	question: str = ''
	problems: List[TroubleModel] = []

class GoalCheckInModel(DataRowModel):
	intro_pre_goal: str = ''
	intro_post_goal: str = ''
	pre_question: str = ''
	question: str = ''
	options: List[str] = []
	negative: List[str] = []
	positive: List[str] = []
	improvement: str = ''
	response_positive: str = ''
	response_negative_pre_goal: str = ''
	response_negative_post_goal: str = ''
	troubleshooting: TroubleshootingModel = TroubleshootingModel()
	conclusion: str = ''


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

################################
## LTP activity
class LtpActivityModel (DataRowModel):
	name: str = ''
	text: str = ''
	act_type: List[str] = ["Active"] #???
	act_age: List[int] = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17] #???

################################
## home activity check-in

class HomeActivityCheckInModel(DataRowModel):
	activity: str = ''
	positive_message: str = ''
	negative_message: str = ''

class WhatsappTemplateModel(DataRowModel):
	name: str = ''
	uuid: str = ''
	text: str = ''

#########################
## delivery
from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List


class GoalModel(DataRowModel):
	goal_name: str = ''
	priority: str = ''
	age_group: str = ''
	relationship: str = ''
	modules: List[str] = []
	goal_description_new: str = ''
	goal_description_started: str = ''


class SplitModel(DataRowModel):
	split_variable: str = ''
	flow_name: str = ''
	text_name: str = ''


class ModuleModel(DataRowModel):
	module_name: str = ''
	age_baby: bool = True
	age_child: bool = True
	age_teen: bool = True

class HandlerWrapperModel(DataRowModel):
	pre_update_flow: str = ''
	handler_flow: str = ''
	post_update_flow: str = ''

class OptionsWrapperOneOptionModel(ParserModel):
	message: str = ''
	question: str = ''
	affirmative: str = ''
	negative: str = ''
	no_message: str = ''


class OptionsWrapperModel(DataRowModel):
	list_var: str = ''
	dict_var: str = ''
	n_max_opt: int = 9
	msg_no_options: str = ''
	msg_one_option: OptionsWrapperOneOptionModel = OptionsWrapperOneOptionModel()
	msg_multiple_options: str = ''
	extra_option: str = ''
	extra_message: str = ''
	update_var: str = ''
	update_var_flow: str = ''


class ProceedModel(ParserModel):
	question: str = ''
	yes_opt: str = ''
	no_opt: str = ''
	no_msg: str = ''


class SelectGoalModel(DataRowModel):
	update_prog_var_flow: str = ''
	split_by_goal_update_flow: str = ''	
	proceed: ProceedModel = ProceedModel()

class InteractionOptionModel(ParserModel):
	text: str = ''
	proceed_result_value: str = ''
	stop_message: str = ''

class InteractionModel(DataRowModel):
	question: str = ''
	options: List[InteractionOptionModel] = []
	wa_template_ID: str = ''
	wa_template_vars: List[str] = []

class MenuOptionModel(ParserModel):
	text: str = ''
	flow: str = ''
	
class MessageMenuModel(ParserModel):
	text: str = ''
	image: str = ''

class MenuModel(DataRowModel):
	message: MessageMenuModel = MessageMenuModel()
	return_option: str = ''
	options: List[MenuOptionModel] = []


class TimedProgrammeModel(DataRowModel):
	completion_variable: str = ''
	incomplete_value: str = ''
	incomplete_test: str = ''
	incomplete_name: str = ''
	interaction_flow: str = ''
	interaction_proceed_value: str = ''
	flow: str = ''


class ActivityTypeModel(DataRowModel):
	option_name: str = ''


class ComicNamesModel(DataRowModel):
	names: List[str] = []

class ComicNamesKeyModel(DataRowModel):
	languages: List[str] = []
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