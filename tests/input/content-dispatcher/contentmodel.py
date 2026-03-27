from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List

class ContentModel(DataRowModel):
	properties: List[str]
	content: List[str]
