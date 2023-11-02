import copy
import tablib

from rpft.parsers.common.sheetparser import SheetParser
from rpft.parsers.sheets import AbstractSheetReader, Sheet, SheetDictSheetReader


class MockCellParser:
    def parse(self, value, context={}):
        return value

    def parse_as_string(self, value, context={}):
        return value


class MockRowParser:
    def __init__(self):
        self.context = {}

    def unparse_row(self, row):
        return row

    def parse_row(self, row, template_context):
        row = copy.deepcopy(row)
        row["context"] = template_context
        return row


class MockSheetParser(SheetParser):
    def __init__(self, row_parser, rows, context={}):
        """
        Args:
            row_parser: parser to convert flat dicts to RowModel instances.
            rows: List of instances of the RowModel
            context: context used for template parsing
        """

        self.row_parser = row_parser
        self.bookmarks = {}
        self.input_rows = rows
        self.iterator = iter(self.input_rows)
        self.context = copy.deepcopy(context)

    def parse_next_row(self, omit_templating=False, return_index=False):
        try:
            input_row = next(self.iterator)
        except StopIteration:
            return (None, None) if return_index else None
        return (input_row, -1) if return_index else None


class MockSheetReader(SheetDictSheetReader):
    def __init__(self, main_sheet_data=None, sheet_data_dict={}):
        self.name = "MockSheetReader"
        self.sheets = {}
        if main_sheet_data:
            main_sheet = tablib.import_set(main_sheet_data, format="csv")
            self.sheets["content_index"] = Sheet(self.name, main_sheet)
        for name, content in sheet_data_dict.items():
            sheet = tablib.import_set(content, format="csv")
            self.sheets[name] = Sheet(self.name, sheet)
