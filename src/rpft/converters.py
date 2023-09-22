import json
import os
import time
import csv

from rpft.parsers.creation.contentindexparser import ContentIndexParser
from rpft.parsers.creation.tagmatcher import TagMatcher
from rpft.parsers.sheets.csv_sheet_reader import CSVSheetReader
from rpft.parsers.sheets.xlsx_sheet_reader import XLSXSheetReader
from rpft.parsers.sheets.google_sheet_reader import GoogleSheetReader
from rpft.parsers.sheets.google_sheet_reader import get_credentials


def create_flows(input_files, output_file, sheet_format, data_models=None, tags=[]):
    parser = ContentIndexParser(
        user_data_model_module_name=data_models, tag_matcher=TagMatcher(tags)
    )

    for input_file in input_files:
        reader = create_sheet_reader(sheet_format, input_file)
        parser.add_content_index(reader)

    json.dump(parser.parse_all().render(), open(output_file, "w"), indent=4)


def google_sheets_as_csv(input_files, output_folder):
    for sheet_id in input_files:
        reader = GoogleSheetReader(sheet_id)
        service = reader.get_api_service()
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = spreadsheet["sheets"]
        workbook_folder = os.path.join(output_folder, sheet_id)
        os.makedirs(workbook_folder, exist_ok=True)

        for sheet in sheets:
            sheet_title = sheet["properties"]["title"]
            range_name = f"'{sheet_title}'"

            request = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheet_id, range=range_name)
            )
            response = None

            while response is None:
                try:
                    response = request.execute()
                except Exception as e:
                    if "quota" in str(e).lower():
                        print("Rate limit exceeded. Backing off and retrying...")
                        time.sleep(10)
                    else:
                        raise

            csv_path = os.path.join(workbook_folder, f"{sheet_title}.csv")

            with open(
                csv_path, "w", newline="", encoding="utf-8"
            ) as csv_file:  # Specify encoding
                csv_writer = csv.writer(csv_file)
                csv_writer.writerows(response["values"])


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
