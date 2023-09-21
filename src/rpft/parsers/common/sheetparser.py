import copy
from rpft.parsers.common.rowdatasheet import RowDataSheet
from rpft.logger.logger import get_logger, logging_context

LOGGER = get_logger()


class SheetParser:
    def __init__(self, row_parser, table, context={}):
        """
        Args:
            row_parser: parser to convert flat dicts to RowModel instances.
            context: context used for template parsing
            table: Tablib Dataset representing the table to be parsed.
        """

        self.row_parser = row_parser
        self.bookmarks = {}
        self.input_rows = []
        for row_idx, row in enumerate(table):
            row_dict = {h: e for h, e in zip(table.headers, row)}
            self.input_rows.append((row_dict, row_idx + 2))
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

    def parse_next_row(self, omit_templating=False, return_index=False):
        try:
            input_row, row_idx = next(self.iterator)
        except StopIteration:
            return (None, None) if return_index else None
        context = self.context if not omit_templating else None
        with logging_context(f"row {row_idx}"):
            row = self.row_parser.parse_row(input_row, context)
        return (row, row_idx) if return_index else row

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
