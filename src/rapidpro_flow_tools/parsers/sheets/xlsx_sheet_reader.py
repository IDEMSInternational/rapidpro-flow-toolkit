import tablib
import os

class XLSXSheetReader:

    def __init__(self, filename):
        with open(filename, 'rb') as table_data:
            data = tablib.Databook().load(table_data.read(), 'xlsx')
        self.main_sheet = None
        self.sheets = {}
        for sheet in data.sheets():
            if sheet.title == 'content_index':
                self.main_sheet = sheet
            else:
                self.sheets[sheet.title] = sheet
        if self.main_sheet is None:
            raise ValueError(f'{filename} must have a sheet "content_index"')

    def get_main_sheet(self):
        return self.main_sheet

    def get_sheet(self, name):
        return self.sheets[name]
