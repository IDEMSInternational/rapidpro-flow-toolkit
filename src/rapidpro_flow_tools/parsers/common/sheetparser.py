import copy
from rapidpro_flow_tools.parsers.common.rowdatasheet import RowDataSheet

class SheetParser:

    def __init__(self, row_parser, table, context={}):
        '''
        Args:
            row_parser: parser to convert flat dicts to RowModel instances.
            context: context used for template parsing
            table: Tablib Dataset representing the table to be parsed.
        '''

        self.row_parser = row_parser
        self.bookmarks = {}
        self.input_rows = []
        for row in table:
            row_dict = {h : e for h, e in zip(table.headers, row)}
            self.input_rows.append(row_dict)
        self.iterator = iter(self.input_rows)
        self.context = copy.deepcopy(context)

    def add_to_context(self, key, value):
        self.context[key] = value

    def remove_from_context(self, key):
        self.context.pop(key)

    def create_bookmark(self, name):
        self.bookmarks[name] = copy.copy(self.iterator)

    def go_to_bookmark(self, name):
        self.iterator = copy.copy(self.bookmarks[name])

    def remove_bookmark(self, name):
        self.bookmarks.pop(name)

    def parse_next_row(self, omit_templating=False):
        try:
            input_row = next(self.iterator)
        except StopIteration:
            return None
        context = self.context if not omit_templating else None
        row = self.row_parser.parse_row(input_row, context)
        return row

    def parse_all(self):
        self.iterator = iter(self.input_rows)
        output_rows = []
        row = self.parse_next_row()
        while row is not None:
            output_rows.append(row)
            row = self.parse_next_row()
        return output_rows

    def get_row_data_sheet(self):
        rows = self.parse_all()
        return RowDataSheet(self.row_parser, rows)
