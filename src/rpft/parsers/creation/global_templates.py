import os

from rpft.parsers.sheets import CSVSheetReader


def get_survey_reader():
    path = os.path.join(os.path.dirname(__file__), "survey_templates")
    return CSVSheetReader(path)
