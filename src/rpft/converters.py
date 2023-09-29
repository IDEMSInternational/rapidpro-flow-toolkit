import json
import shutil
from pathlib import Path

from rpft.parsers.creation.contentindexparser import ContentIndexParser
from rpft.parsers.creation.tagmatcher import TagMatcher
from rpft.parsers.sheets.csv_sheet_reader import CSVSheetReader
from rpft.parsers.sheets.google_sheet_reader import GoogleSheetReader
from rpft.parsers.sheets.xlsx_sheet_reader import XLSXSheetReader


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


def sheets_to_csv(path, sheet_ids):
    prepare_dir(path)

    for sid in sheet_ids:
        sheet_to_csv(path, sid)


def sheet_to_csv(path, sheet_id):
    workbook_dir = prepare_dir(Path(path) / sheet_id)
    reader = GoogleSheetReader(sheet_id)

    for name, table in reader.sheets.items():
        with open(
            workbook_dir / f"{name}.csv",
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            csv_file.write(table.export("csv"))


def prepare_dir(path):
    directory = Path(path)

    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)

    return directory
