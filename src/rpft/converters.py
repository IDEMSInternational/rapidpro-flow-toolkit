import json

from rpft.parsers.creation.contentindexparser import ContentIndexParser
from rpft.parsers.creation.tagmatcher import TagMatcher
from rpft.parsers.sheets.csv_sheet_reader import CSVSheetReader
from rpft.parsers.sheets.xlsx_sheet_reader import XLSXSheetReader
from rpft.parsers.sheets.google_sheet_reader import GoogleSheetReader


def create_flows(input_files, output_file, sheet_format, data_models=None, tags=[]):
    parser = ContentIndexParser(
        user_data_model_module_name=data_models, tag_matcher=TagMatcher(tags)
    )

    for input_file in input_files:
        reader = create_sheet_reader(sheet_format, input_file)
        parser.add_content_index(reader)

    json.dump(parser.parse_all().render(), open(output_file, "w"), indent=4)


def create_sheet_reader(sheet_format, input_file, credentials=None):
    if sheet_format == "csv":
        sheet_reader = CSVSheetReader(input_file)
    elif sheet_format == "xlsx":
        sheet_reader = XLSXSheetReader(input_file)
    elif sheet_format == "google_sheets":
        sheet_reader = GoogleSheetReader(input_file)
    else:
        raise Exception(f"Format {sheet_format} currently unsupported.")

    return sheet_reader
