import copy
import tablib
from .rowdatasheet import RowDataSheet

class SheetParser:

    def __init__(self, row_parser, data_stream, file_format='csv', context={}):
        '''
        Args:
            row_parser: parser to convert flat dicts to RowModel instances.
            context: context used for template parsing
            data_stream: IO stream with the source data
            format: Import file format.
                Supported file formats as supported by tablib,
                see https://tablib.readthedocs.io/en/stable/formats.html
        '''

        self.row_parser = row_parser
        self.bookmarks = {}
        rows = tablib.import_set(data_stream, format=file_format)
        self.input_rows = []
        for row in rows:
            row_dict = {h : e for h, e in zip(rows.headers, row)}
            self.input_rows.append(row_dict)
        self.iterator = iter(self.input_rows)
        self.context = copy.deepcopy(context)

    def add_to_context(self, key, value):
        self.context[key] = value
        self.row_parser.update_context(self.context)

    def remove_from_context(self, key):
        self.context.pop(key)
        self.row_parser.update_context(self.context)

    def create_bookmark(self, name):
        self.bookmarks[name] = copy.copy(self.iterator)

    def go_to_bookmark(self, name):
        self.iterator = self.bookmarks[name]

    def parse_next_row(self):
        try:
            input_row = next(self.iterator)
        except StopIteration:
            return None
        row = self.row_parser.parse_row(input_row)  #, context=self.context
        return row

    def parse_all(self):
        output_rows = []
        row = self.parse_next_row()
        while row is not None:
            output_rows.append(row)
            row = self.parse_next_row()
        return output_rows

    def get_row_data_sheet(self):
        rows = self.parse_all()
        return RowDataSheet(self.row_parser, rows)
