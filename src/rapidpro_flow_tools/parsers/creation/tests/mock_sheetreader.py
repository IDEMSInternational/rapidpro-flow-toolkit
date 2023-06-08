import tablib

class MockSheetReader:

    def __init__(self, main_sheet_data, sheet_data_dict):
        self.main_sheet = tablib.import_set(main_sheet_data, format='csv')
        self.sheet_dict = {}
        for name, content in sheet_data_dict.items():
            self.sheet_dict[name] = tablib.import_set(content, format='csv')

    def get_main_sheet(self):
        return self.main_sheet

    def get_sheet(self, name):
        return self.sheet_dict[name]
