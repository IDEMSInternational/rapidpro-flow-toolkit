import copy
from rapidpro_flow_tools.parsers.common.sheetparser import SheetParser

class MockSheetParser(SheetParser):

    def __init__(self, row_parser, rows, context={}):
        '''
        Args:
            row_parser: parser to convert flat dicts to RowModel instances.
            rows: List of instances of the RowModel
            context: context used for template parsing
        '''

        self.row_parser = row_parser  # Unused
        self.bookmarks = {}
        self.input_rows = rows
        self.iterator = iter(self.input_rows)
        self.context = copy.deepcopy(context)

    def parse_next_row(self, omit_templating=False, return_index=False):
        # Simply return the input.
        try:
            input_row = next(self.iterator)
        except StopIteration:
            return (None, None) if return_index else None
        return (input_row, -1) if return_index else None
