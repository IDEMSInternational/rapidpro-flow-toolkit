import copy

class MockRowParser:
    def __init__(self):
        self.context = {}

    def unparse_row(self, row):
        return row

    def update_context(self, context):
        self.context = copy.deepcopy(context)

    def parse_row(self, row):
        row = copy.deepcopy(row)
        row["context"] = self.context
        return row
