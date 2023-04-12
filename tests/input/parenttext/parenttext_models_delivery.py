from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List


class GoalModel(DataRowModel):
	goal_name: str = ''
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
	proceed: str = ''

class InteractionModel(DataRowModel):
	question: str = ''
	options: List[InteractionOptionModel] = []
	wa_template: str = ''