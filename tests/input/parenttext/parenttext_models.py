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

class ContentModel(DataRowModel):
	message: str = ''
