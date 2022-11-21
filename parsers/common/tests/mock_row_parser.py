import copy

class MockRowParser:
    def __init__(self):
        self.context = {}

    def unparse_row(self, row):
        return row

    def parse_row(self, row, template_context):
        row = copy.deepcopy(row)
        row["context"] = template_context
        return row
