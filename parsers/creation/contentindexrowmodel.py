from parsers.common.rowparser import ParserModel

class ContentIndexRowModel(ParserModel):
    type: str = ''
    sheet_name: str = ''
    data_sheet: str = ''
    data_row_id: str = ''
    new_name: str = ''
    data_model: str = ''
    status: str = ''
