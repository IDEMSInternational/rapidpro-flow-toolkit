import json
import logging
import os
import shutil
from pathlib import Path

from tablib import Databook, Dataset

from rpft.parsers.universal import UniJSONReader, bookify, parse_tables
from rpft.parsers.creation.contentindexparser import ContentIndexParser
from rpft.parsers.creation.tagmatcher import TagMatcher
from rpft.parsers.sheets import (
    AbstractSheetReader,
    CSVSheetReader,
    GoogleSheetReader,
    JSONSheetReader,
    ODSSheetReader,
    XLSXSheetReader,
)
from rpft.rapidpro.models.containers import RapidProContainer
from rpft.sources import JSONDataSource, SheetDataSource


LOGGER = logging.getLogger(__name__)
FMT_READER_MAP = {
    "csv": CSVSheetReader,
    "google_sheets": GoogleSheetReader,
    "json": JSONSheetReader,
    "ods": ODSSheetReader,
    "uni": UniJSONReader,
    "xlsx": XLSXSheetReader,
}


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
        LOGGER.critical(e.args[0] if e.args else e.__class__.__name__)
        raise

    if output_file:
        with open(output_file, "w", encoding="utf8") as export:
            json.dump(flows, export, indent=4)

    return flows


def uni_to_sheets(infile) -> bytes:
    with open(infile, "r") as handle:
        data = json.load(handle)

    sheets = bookify(data)
    book = Databook(
        [Dataset(*table[1:], headers=table[0], title=name) for name, table in sheets]
    )

    return book.export("ods")


def sheets_to_uni(infile) -> list:
    return parse_tables(create_sheet_reader(None, infile))


def get_content_index_parser(input_files, sheet_format, data_models, tags):
    if not sheet_format and not data_models:
        return ContentIndexParser(
            JSONDataSource(input_files), data_models, TagMatcher(tags)
        )

    readers = [
        create_sheet_reader(sheet_format, input_file) for input_file in input_files
    ]

    return ContentIndexParser(SheetDataSource(readers), data_models, TagMatcher(tags))


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
    cls = FMT_READER_MAP.get(sheet_format) or next(
        reader for reader in FMT_READER_MAP.values() if reader.can_process(input_file)
    )

    if cls:
        return cls(input_file)

    raise Exception(f"Format not supported, file={input_file}")


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
