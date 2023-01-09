from parsers.common.rowparser import ParserModel
from typing import List

class ContentIndexRowModel(ParserModel):
    type: str = ''
    new_name: str = ''
    sheet_name: List[str] = []
    data_sheet: str = ''
    data_row_id: str = ''
    extra_data_sheets: List[str] = []
    data_model: str = ''
    status: str = ''
