from parsers.creation.datarowmodel import DataRowModel
from parsers.common.rowparser import ParserModel
from typing import List


class StationModel(DataRowModel):
	station_name: str = ''
	station_type: str = ''
	station_element: str = ''
	joining_trigger: str = ''



