from parsers.common.rowparser import ParserModel
from typing import List

class ContentIndexRowModel(ParserModel):
    type: str = ''
    sheet_name: str = ''
    data_sheet: str = ''
    data_row_id: str = ''
    extra_data_sheets: List[str] = []
    new_name: str = ''
    data_model: str = ''
    status: str = ''
