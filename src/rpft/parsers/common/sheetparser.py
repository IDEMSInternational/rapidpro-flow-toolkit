import copy

from rpft.parsers.common.rowdatasheet import RowDataSheet
from rpft.parsers.common.rowparser import RowParser
from rpft.logger.logger import logging_context


class SheetParser:
    def parse_sheet(table, row_model):
        """
        Args:
            table: Tablib Dataset representing the table to be parsed.
            row_model: Data model to convert rows of the sheet into.

        Returns:
            RowDataSheet instance containing a list of row_model instances
        """

        sheet_parser = SheetParser(table, row_model)
        return sheet_parser.get_row_data_sheet()

    def __init__(self, table, row_model=None, row_parser=None, context={}):
        """
        Either a row_parser or a row_model need to be provided.

        Args:
            table: Tablib Dataset representing the table to be parsed.
            row_model: Data model to convert rows of the sheet into.
            row_parser: parser to convert flat dicts to RowModel instances.
            context: context used for template parsing
        """

        if not (row_parser or row_model):
            raise ValueError("SheetParser: needs either row_parser or row_model")
        self.row_parser = row_parser or RowParser(row_model)
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
        self.context.pop(key, None)

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
