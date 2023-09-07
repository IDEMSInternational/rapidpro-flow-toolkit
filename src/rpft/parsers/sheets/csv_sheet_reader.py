import tablib
import os


class CSVSheetReader:
    def __init__(self, filename):
        self.path = os.path.dirname(filename)
        with open(filename, "r") as table_data:
            self.main_sheet = tablib.import_set(table_data, format="csv")

    def get_main_sheet(self):
        return self.main_sheet

    def get_sheet(self, name):
        # Assume same path as the main sheet, and take sheet names
        # relative to that path.
        with open(os.path.join(self.path, f"{name}.csv"), "r") as table_data:
            table = tablib.import_set(table_data, format="csv")
        return table
