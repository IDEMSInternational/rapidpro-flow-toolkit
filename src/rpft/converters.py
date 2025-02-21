import json
import logging
import os
import shutil
import sys
from pathlib import Path

from rpft.parsers.creation.contentindexparser import ContentIndexParser
from rpft.parsers.creation.tagmatcher import TagMatcher
from rpft.parsers.sheets import (
    AbstractSheetReader,
    CompositeSheetReader,
    CSVSheetReader,
    GoogleSheetReader,
    JSONSheetReader,
    XLSXSheetReader,
)
from rpft.rapidpro.models.containers import RapidProContainer


LOGGER = logging.getLogger(__name__)


def create_flows(input_files, output_file, sheet_format, data_models=None, tags=[]):
    """
    Convert source spreadsheet(s) into RapidPro flows.

    :param input_files: list of source spreadsheets to convert
    :param output_files: (deprecated) path of file to export flows to as JSON
    :param sheet_format: format of the spreadsheets
    :param data_models: name of module containing supporting Python data classes
    :param tags: names of tags to be used to filter the source spreadsheets
    :returns: dict representing the RapidPro import/export format.
    """

    try:
        flows = (
            get_content_index_parser(input_files, sheet_format, data_models, tags)
            .parse_all()
            .render()
        )
    except Exception as e:
        LOGGER.critical(e.args[0])
        sys.exit(1)

    if output_file:
        with open(output_file, "w", encoding="utf8") as export:
            json.dump(flows, export, indent=4)

    return flows


def save_data_sheets(input_files, output_file, sheet_format, data_models=None, tags=[]):
    """
    Save data sheets as JSON.

    Collect the data sheets referenced in the source content index spreadsheet(s) and
    save this collection in a single JSON file. Returns the output as a dict.

    :param sources: list of source spreadsheets
    :param output_files: (deprecated) path of file to export output to as JSON
    :param sheet_format: format of the spreadsheets
    :param data_models: name of module containing supporting Python data classes
    :param tags: names of tags to be used to filter the source spreadsheets
    :returns: dict representing the collection of data sheets.
    """

    parser = get_content_index_parser(input_files, sheet_format, data_models, tags)

    output = parser.data_sheets_to_dict()

    if output_file:
        with open(output_file, "w") as export:
            json.dump(output, export, indent=4)

    return output


def get_content_index_parser(input_files, sheet_format, data_models, tags):
    reader = CompositeSheetReader()

    for input_file in input_files:
        reader.add_reader(create_sheet_reader(sheet_format, input_file))

    return ContentIndexParser(reader, data_models, TagMatcher(tags))


def convert_to_json(input_file, sheet_format):
    """
    Convert source spreadsheet(s) into json.

    :param input_file: source spreadsheet to convert
    :param sheet_format: format of the input spreadsheet
    :returns: content of the input file converted to json.
    """

    return to_json(create_sheet_reader(sheet_format, input_file))


def flows_to_sheets(
    input_file, output_folder, format="csv", strip_uuids=False, numbered=False
):
    """
    Convert source RapidPro JSON to spreadsheet(s).

    Each flow in the JSON will become a separate output file.

    :param input_file: source JSON file to convert
    :param output_folder: destination folder for output files
    :param format: Output file format.
    :param strip_uuids: Strip all UUIDs from output to allow for comparing outputs.
    :param numbered: Use sequential numbers instead of short reps for row IDs.
    :returns: None.
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    container = RapidProContainer.from_dict(data)
    for flow in container.flows:
        rds = flow.to_row_data_sheet(strip_uuids, numbered)
        rds.export(os.path.join(output_folder, f"{flow.name}.{format}"), format)


def create_sheet_reader(sheet_format, input_file):
    if sheet_format == "csv":
        sheet_reader = CSVSheetReader(input_file)
    elif sheet_format == "xlsx":
        sheet_reader = XLSXSheetReader(input_file)
    elif sheet_format == "json":
        sheet_reader = JSONSheetReader(input_file)
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

    for name, sheet in reader.sheets.items():
        with open(
            workbook_dir / f"{name}.csv",
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            csv_file.write(sheet.table.export("csv"))


def to_json(reader: AbstractSheetReader) -> str:
    book = {
        "meta": {
            "version": "0.1.0",
        },
        "sheets": {name: sheet.table.dict for name, sheet in reader.sheets.items()},
    }

    return json.dumps(book, ensure_ascii=False, indent=2)


def prepare_dir(path):
    directory = Path(path)

    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)

    return directory
