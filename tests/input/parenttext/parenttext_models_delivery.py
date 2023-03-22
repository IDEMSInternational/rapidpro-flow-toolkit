from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List


class GoalModel(DataRowModel):
	goal_name: str = ''
	modules: List[str] = []


class HandlerModel(DataRowModel):
	split_variable: str = ''
	flow_name: str = ''


class ModuleModel(DataRowModel):
	age_baby: bool = True
	age_child: bool = True
	age_teen: bool = True
